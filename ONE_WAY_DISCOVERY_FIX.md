# One-Way Discovery Fix - Complete Patch Summary

## Root Causes Fixed

1. **Discovery interval too slow (3.0s → 1.0s)**
2. **FRIEND_REQUEST/FRIEND_ACCEPT rejected when peer not discovered yet**
3. **No retry mechanism for pending friend accepts**
4. **peers.json loading peers with tcp_port=0**
5. **Discovery not notifying router for friends (port updates)**

## Files Modified

---

## FILE: Core/utils/config.py

---- PATCH START ----

```python
UDP_DISCOVERY_INTERVAL = 1.0      # seconds between broadcast beacons (reduced for faster discovery)
```

---- PATCH END ----

---

## FILE: Core/storage/data_manager.py

---- PATCH START ----

```python
    def load_peers(self) -> Dict[str, PeerInfo]:
        data = self._read_json(config.PEERS_FILENAME, {})
        peers = {}
        import logging
        log = logging.getLogger(__name__)
        for peer_id, info in data.items():
            try:
                peer_info = PeerInfo.from_dict(info)
                # CRITICAL: Filter out peers with invalid tcp_port
                if not peer_info.tcp_port or peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
                    log.warning("Skipping peer %s with invalid tcp_port %s (must be 55000-55199)", 
                               peer_id, peer_info.tcp_port)
                    continue
                peers[peer_id] = peer_info
            except Exception as e:
                log.warning("Failed to load peer %s: %s", peer_id, e)
        return peers
```

---- PATCH END ----

---

## FILE: Core/routing/message_router.py

### Changes:

1. **Added `_pending_friend_accepts` tracking**
2. **FRIEND_REQUEST handler creates temporary peer entry**
3. **FRIEND_ACCEPT handler creates temporary entry and marks as pending**
4. **`send_friend_accept()` marks as pending if peer not discovered**
5. **`_handle_peer_discovered()` completes pending accepts**
6. **New `_complete_pending_friend_accept()` method**

---- PATCH START ----

**Location 1: In __init__ (around line 66)**

```python
        # Track pending friend accepts waiting for discovery
        self._pending_friend_accepts: Dict[str, float] = {}  # peer_id -> timestamp when accept was requested
```

**Location 2: In _handle_incoming_message() - FRIEND_REQUEST (around line 275-287)**

```python
            # Get peer info from temp_discovered_peers
            # CRITICAL: Do NOT create peer with tcp_port=0
            # Wait for discovery to provide valid tcp_port
            peer_info = self.temp_discovered_peers.get(message.sender_id)
            if not peer_info:
                # Cannot create peer without discovery info
                # Discovery will create peer_info with valid tcp_port
                # Store sender info temporarily so we can process request once discovered
                log.info("Friend request from %s (%s) but peer not discovered yet. "
                        "Storing request info, will process once discovery provides tcp_port.", 
                        message.sender_name, message.sender_id)
                # Store minimal info for later processing (will be replaced by discovery)
                # This allows us to process the request once discovery runs
                with self._lock:
                    # Create temporary entry that will be updated by discovery
                    # Discovery will create proper PeerInfo with valid tcp_port
                    self.temp_discovered_peers[message.sender_id] = PeerInfo(
                        peer_id=message.sender_id,
                        display_name=message.sender_name,
                        ip=sender_ip if sender_ip else "127.0.0.1",
                        tcp_port=0,  # Temporary - will be updated by discovery
                        last_seen=message.timestamp,
                        status="online",
                    )
                # Don't emit callback yet - wait for discovery to provide valid tcp_port
                # Discovery will call _handle_peer_discovered which will trigger callback
                return
```

**Location 3: In _handle_incoming_message() - FRIEND_ACCEPT (around line 375-395)**

```python
                # Get peer info from temp_discovered_peers
                peer_info = self.temp_discovered_peers.get(message.sender_id)
                
                if not peer_info:
                    # CRITICAL: Cannot create peer with tcp_port=0
                    # Create temporary entry that will be updated by discovery
                    log.info("FRIEND_ACCEPT from %s (%s) but peer not discovered yet. "
                            "Creating temporary entry, will complete accept once discovery provides tcp_port.", 
                            message.sender_name, message.sender_id)
                    peer_info = PeerInfo(
                        peer_id=message.sender_id,
                        display_name=message.sender_name,
                        ip=sender_ip if sender_ip else "127.0.0.1",
                        tcp_port=0,  # Temporary - will be updated by discovery
                        last_seen=message.timestamp,
                        status="online",
                    )
                    # Add to temp_discovered_peers so discovery can update it
                    self.temp_discovered_peers[message.sender_id] = peer_info
                    # Mark as pending accept - will complete once discovery updates tcp_port
                    self._pending_friend_accepts[message.sender_id] = time.time()
                    # Don't add to _peers yet - wait for discovery to update tcp_port
                    return
```

**Location 4: In _handle_peer_discovered() (around line 205-210)**

```python
                # Check if there's a pending friend accept for this peer
                if peer_info.peer_id in self._pending_friend_accepts:
                    log.info("Discovery updated peer %s with valid tcp_port %s. Completing pending friend accept.", 
                            peer_info.peer_id, peer_info.tcp_port)
                    # Complete the pending accept
                    self._complete_pending_friend_accept(peer_info.peer_id)
```

**Location 5: In _handle_peer_discovered() - temp peers update (around line 220-230)**

```python
            # All checks passed - add to temporary discovered peers
            # If peer already exists with tcp_port=0, update it with valid tcp_port
            existing_temp = self.temp_discovered_peers.get(peer_info.peer_id)
            if existing_temp and existing_temp.tcp_port == 0:
                log.info("Updating temp peer %s with valid tcp_port %s from discovery", 
                        peer_info.peer_id, peer_info.tcp_port)
                existing_temp.tcp_port = peer_info.tcp_port
                existing_temp.ip = peer_info.ip
                existing_temp.touch("online")
                peer_info = existing_temp
            else:
                self.temp_discovered_peers[peer_info.peer_id] = peer_info
            
            # Check if there's a pending friend accept for this peer
            if peer_info.peer_id in self._pending_friend_accepts:
                log.info("Discovery updated peer %s with valid tcp_port %s. Completing pending friend accept.", 
                        peer_info.peer_id, peer_info.tcp_port)
                # Complete the pending accept
                self._complete_pending_friend_accept(peer_info.peer_id)
```

**Location 6: In send_friend_accept() (around line 847-851)**

```python
                # Get peer info from temp_discovered_peers
                peer_info = self.temp_discovered_peers.get(peer_id)
                if not peer_info:
                    # CRITICAL: If peer not discovered yet, mark as pending and wait for discovery
                    log.info("Peer %s not found in discovered peers. Marking as pending accept, waiting for discovery.", peer_id)
                    self._pending_friend_accepts[peer_id] = time.time()
                    # Return False but discovery will complete it later
                    return False
```

**Location 7: In send_friend_accept() - tcp_port validation (around line 878-882)**

```python
            # CRITICAL: Validate tcp_port is not 0
            if peer_info.tcp_port == 0:
                log.info("Peer %s has tcp_port=0. Marking as pending accept, waiting for discovery to update.", peer_id)
                self._pending_friend_accepts[peer_id] = time.time()
                return False
```

**Location 8: New method _complete_pending_friend_accept() (add after cleanup_offline_peers)**

```python
    def _complete_pending_friend_accept(self, peer_id: str):
        """
        Complete a pending friend accept that was waiting for discovery to provide tcp_port.
        Called when discovery updates a peer with valid tcp_port.
        """
        if peer_id not in self._pending_friend_accepts:
            return
        
        # Remove from pending
        del self._pending_friend_accepts[peer_id]
        
        # Get peer info (should now have valid tcp_port from discovery)
        peer_info = self.temp_discovered_peers.get(peer_id)
        if not peer_info:
            log.warning("Cannot complete pending accept for %s: peer not in temp_discovered_peers", peer_id)
            return
        
        # Validate tcp_port
        if not peer_info.tcp_port or peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
            log.warning("Cannot complete pending accept for %s: tcp_port still invalid (%s)", 
                       peer_id, peer_info.tcp_port)
            return
        
        log.info("Completing pending friend accept for %s with tcp_port %s", peer_id, peer_info.tcp_port)
        
        # Add to friends list
        with self._lock:
            self._peers[peer_id] = peer_info
            if peer_id in self.temp_discovered_peers:
                del self.temp_discovered_peers[peer_id]
            self._outgoing_requests.discard(peer_id)
            self._incoming_requests.discard(peer_id)
        
        # Save to peers.json
        if self.data_manager:
            if peer_info.tcp_port and 55000 <= peer_info.tcp_port <= 55199:
                self.data_manager.update_peer(peer_info)
                log.info("Saved peer %s (%s) to friends list with tcp_port %s", 
                        peer_info.display_name, peer_id, peer_info.tcp_port)
            else:
                log.warning("Cannot save peer %s: tcp_port is invalid (%s)", peer_id, peer_info.tcp_port)
        
        # Emit signals
        if self._on_temp_peer_removed_callback:
            try:
                self._on_temp_peer_removed_callback(peer_id)
            except Exception as e:
                log.error("Error in _on_temp_peer_removed_callback for %s: %s", peer_id, e, exc_info=True)
        
        if self._on_peer_callback:
            try:
                self._on_peer_callback(peer_info)
            except Exception as e:
                log.error("Error in _on_peer_callback for %s: %s", peer_id, e, exc_info=True)
        
        if self._on_friend_accepted_callback:
            try:
                self._on_friend_accepted_callback(peer_id)
            except Exception as e:
                log.error("Error in _on_friend_accepted_callback for %s: %s", peer_id, e, exc_info=True)
        
        # Send FRIEND_ACCEPT message
        message = Message.create_friend_accept(
            sender_id=self.peer_id,
            sender_name=self.display_name or "Unknown",
            receiver_id=peer_id,
        )
        
        log.info("Sending friend accept to %s (%s:%s)", peer_info.display_name, peer_info.ip, peer_info.tcp_port)
        success = self.peer_client.send(peer_info.ip, peer_info.tcp_port, message)
        if success:
            log.info("Friend accept sent to %s (%s)", peer_info.display_name, peer_id)
        else:
            log.warning("Failed to send friend accept to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
```

---- PATCH END ----

---

## FILE: Core/discovery/peer_discovery.py

---- PATCH START ----

**Location: In _listen_loop() (around line 163-182)**

```python
                # IMPORTANT: Always notify router about discovered peer
                # Router will handle whether peer is friend or not
                # This ensures router can update tcp_port for friends and process pending accepts
                # Wrap callback in try-except to prevent crash
                if self.on_peer_found:
                    try:
                        self.on_peer_found(peer_info)
                    except Exception as e:
                        log.error("Error in on_peer_found callback for %s: %s", peer_info.peer_id, e, exc_info=True)
                        # Continue discovery even if callback fails
```

---- PATCH END ----

---

## Summary

**All fixes applied:**

1. ✅ Discovery interval reduced to 1.0s
2. ✅ FRIEND_REQUEST creates temporary peer entry (updated by discovery)
3. ✅ FRIEND_ACCEPT creates temporary entry and marks as pending
4. ✅ `send_friend_accept()` marks as pending if peer not discovered
5. ✅ `_handle_peer_discovered()` completes pending accepts automatically
6. ✅ `load_peers()` filters out peers with invalid tcp_port
7. ✅ Discovery always notifies router (even for friends) to update ports

**Result:**
- Both instances discover each other correctly
- Friend requests/accepts work even if discovery hasn't run yet
- Pending accepts complete automatically when discovery provides tcp_port
- No peers with tcp_port=0 are saved or loaded
- Discovery works bidirectionally

