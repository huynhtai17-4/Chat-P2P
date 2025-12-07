"""
Coordinator that glues together discovery, TCP listener and TCP client logic.
Exposes a simple API for the rest of the application (e.g., GUI).
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Callable, Dict, List, Optional, Tuple

from Core.discovery.peer_discovery import PeerDiscovery
from Core.models.message import Message
from Core.models.peer_info import PeerInfo
from Core.networking.peer_client import PeerClient
from Core.networking.peer_listener import PeerListener
from Core.storage.data_manager import DataManager
from Core.utils import config

log = logging.getLogger(__name__)


class MessageRouter:
    """
    High-level facade that:
        * loads/saves peer + message data
        * starts discovery + TCP listener
        * exposes send/get APIs for GUI
    """

    def __init__(self):
        # peer_id will be loaded from profile or generated if not exists
        self.peer_id: Optional[str] = None  # Will be set in connect_core
        self.display_name: Optional[str] = None
        self.tcp_port = config.TCP_BASE_PORT

        self.data_manager: Optional[DataManager] = None
        self.peer_listener: Optional[PeerListener] = None
        self.peer_discovery: Optional[PeerDiscovery] = None
        self.peer_client = PeerClient()

        self._on_message_callback: Optional[Callable[[Message], None]] = None
        self._on_peer_callback: Optional[Callable[[PeerInfo], None]] = None
        self._on_temp_peer_callback: Optional[Callable[[PeerInfo], None]] = None
        self._on_temp_peer_removed_callback: Optional[Callable[[str], None]] = None  # peer_id
        self._on_friend_request_callback: Optional[Callable[[str, str], None]] = None  # peer_id, display_name
        self._on_friend_accepted_callback: Optional[Callable[[str], None]] = None  # peer_id
        self._on_friend_rejected_callback: Optional[Callable[[str], None]] = None  # peer_id
        self._lock = threading.RLock()
        
        # Friends list (loaded from peers.json)
        self._peers: Dict[str, PeerInfo] = {}
        
        # Temporary discovered peers (not yet added to friends list)
        self.temp_discovered_peers: Dict[str, PeerInfo] = {}
        
        # Track friend request states
        self._outgoing_requests: set[str] = set()  # peer_ids we sent FRIEND_REQUEST to
        self._incoming_requests: set[str] = set()  # peer_ids that sent us FRIEND_REQUEST
        self._friend_request_emitted: set[str] = set()  # peer_ids we already emitted friend_request callback for
        
        # Track send failures for stale peer detection
        self._peer_send_failures: Dict[str, int] = {}  # peer_id -> failure count
        
        # Network mode (detected once at startup)
        from Core.utils.network_mode import detect_network_mode
        self._network_mode = detect_network_mode()
        log.info("MessageRouter network mode: %s", self._network_mode)
        
        # Track pending friend accepts waiting for discovery
        self._pending_friend_accepts: Dict[str, float] = {}  # peer_id -> timestamp when accept was requested

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def connect_core(self, username: str, display_name: str, tcp_port: int, on_message_callback: Callable[[Message], None]):
        """
        Initialize the current peer.
        
        Args:
            username: Username for folder structure (normalized)
            display_name: Display name for UI and peer communication
            tcp_port: TCP port to listen on (will be loaded from profile.json if exists)
            on_message_callback: Callback for incoming messages
        """
        self.display_name = display_name
        self._on_message_callback = on_message_callback

        # Use username (not display_name) for folder structure
        self.data_manager = DataManager(username)
        profile = self.data_manager.load_profile()
        
        # Load peer_id from profile.json if exists, otherwise generate new one
        # This ensures we keep the same peer_id across restarts
        saved_peer_id = profile.get("peer_id")
        if saved_peer_id and isinstance(saved_peer_id, str) and len(saved_peer_id) > 0:
            self.peer_id = saved_peer_id
            log.info("Loaded peer_id %s from profile.json", self.peer_id)
        else:
            # Generate new peer_id and save it
            self.peer_id = str(uuid.uuid4())
            log.info("Generated new peer_id %s (saving to profile)", self.peer_id)
        
        # Load TCP port from profile.json if exists, otherwise use provided tcp_port
        # This ensures we use the same port across restarts
        saved_tcp_port = profile.get("tcp_port")
        if saved_tcp_port and isinstance(saved_tcp_port, int) and saved_tcp_port > 0:
            self.tcp_port = saved_tcp_port
            log.info("Loaded TCP port %s from profile.json", self.tcp_port)
        else:
            # Use provided port and save it
            self.tcp_port = tcp_port
            log.info("Using provided TCP port %s (saving to profile)", self.tcp_port)
        
        # Update profile with current info
        profile.update({"display_name": display_name, "peer_id": self.peer_id, "tcp_port": self.tcp_port})
        self.data_manager.save_profile(profile)

        # TCP listener - MUST START FIRST before any other operations
        # Create a wrapper that doesn't need data_manager for friend messages
        def message_handler(msg, ip, port):
            self._handle_incoming_message_with_addr(msg, ip, port)
        
        self.peer_listener = PeerListener(self.peer_id, self.data_manager, message_handler)
        try:
            actual_port = self.peer_listener.start(port=self.tcp_port)
            # Update tcp_port if listener bound to different port (e.g., port was in use)
            if actual_port != self.tcp_port:
                log.warning("TCP port changed from %s to %s (port was in use)", self.tcp_port, actual_port)
                self.tcp_port = actual_port
                # Save updated port to profile
                profile = self.data_manager.load_profile()
                profile["tcp_port"] = actual_port
                self.data_manager.save_profile(profile)
            
            # Wait a short time to ensure socket is fully open before proceeding
            import time
            time.sleep(0.1)
            log.info("PeerListener started successfully on port %s", self.tcp_port)
        except Exception as e:
            log.error("Failed to start PeerListener: %s", e)
            raise RuntimeError(f"Failed to start TCP listener: {e}")

        # Load existing friends into memory
        if self.data_manager:
            self._peers = self.data_manager.load_peers()
            log.info("Loaded %s friends from peers.json", len(self._peers))
        
        # Discovery
        self.peer_discovery = PeerDiscovery(
            peer_id=self.peer_id,
            display_name=self.display_name,
            tcp_port=self.tcp_port,
            data_manager=self.data_manager,
            on_peer_found=self._handle_peer_discovered,
        )
        self.peer_discovery.start()
        self._notify_existing_peers()
        log.info("MessageRouter ready as %s (%s)", self.display_name, self.peer_id)

    def stop(self):
        if self.peer_discovery:
            self.peer_discovery.stop()
        if self.peer_listener:
            self.peer_listener.stop()

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def _handle_peer_discovered(self, peer_info: PeerInfo):
        """
        Handle peer discovered by PeerDiscovery.
        This peer is NOT automatically saved - only added to temp_discovered_peers.
        User must click "Add" to save to peers.json.
        
        IMPORTANT: Do NOT add peer to suggestions if:
        - Peer is already in friends list (_peers)
        - Peer is already in temp_discovered_peers (duplicate)
        - Peer is in _outgoing_requests (we already sent request)
        - Peer is in _incoming_requests (they sent us request, waiting for Accept/Reject)
        """
        # CRITICAL: Validate tcp_port from discovery
        if not peer_info.tcp_port or peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
            log.warning("Discovered peer %s has invalid tcp_port %s, skipping", peer_info.peer_id, peer_info.tcp_port)
            return
        
        log.info("Discovered peer %s (%s) @ %s:%s", peer_info.display_name, peer_info.peer_id, peer_info.ip, peer_info.tcp_port)
        
        with self._lock:
            # Check if peer is already a friend - ALWAYS update from discovery (authoritative)
            if peer_info.peer_id in self._peers:
                existing_peer = self._peers[peer_info.peer_id]
                # ALWAYS update IP and tcp_port from discovery (discovery is authoritative)
                updated = False
                if existing_peer.ip != peer_info.ip:
                    log.info("Updating friend %s IP from %s to %s (from discovery)", 
                            peer_info.peer_id, existing_peer.ip, peer_info.ip)
                    existing_peer.ip = peer_info.ip
                    updated = True
                if existing_peer.tcp_port != peer_info.tcp_port:
                    log.info("Updating friend %s port from %s to %s (from discovery)", 
                            peer_info.peer_id, existing_peer.tcp_port, peer_info.tcp_port)
                    existing_peer.tcp_port = peer_info.tcp_port
                    updated = True
                existing_peer.status = "online"
                existing_peer.touch("online")
                if updated and self.data_manager:
                    # Only save if tcp_port is valid
                    if existing_peer.tcp_port and 55000 <= existing_peer.tcp_port <= 55199:
                        self.data_manager.update_peer(existing_peer)
                    else:
                        log.warning("Cannot save peer %s: tcp_port is invalid (%s). Waiting for valid discovery.", 
                                   peer_info.peer_id, existing_peer.tcp_port)
                
                # Check if there's a pending friend accept for this peer
                if peer_info.peer_id in self._pending_friend_accepts:
                    log.info("Discovery updated peer %s with valid tcp_port %s. Completing pending friend accept.", 
                            peer_info.peer_id, peer_info.tcp_port)
                    # Complete the pending accept
                    self._complete_pending_friend_accept(peer_info.peer_id)
                
                return  # Already a friend - don't add to suggestions
            
            # Check if already in temp_discovered_peers (prevent duplicates)
            if peer_info.peer_id in self.temp_discovered_peers:
                # Update existing entry with fresh info from discovery
                existing = self.temp_discovered_peers[peer_info.peer_id]
                existing.ip = peer_info.ip
                existing.tcp_port = peer_info.tcp_port
                existing.touch("online")
                log.debug("Updated existing temp peer %s with fresh discovery info", peer_info.peer_id)
                return
            
            # Check if we already sent friend request to this peer
            if peer_info.peer_id in self._outgoing_requests:
                log.debug("Ignoring discovered peer %s: already sent friend request", peer_info.peer_id)
                return  # Waiting for their response - don't add to suggestions
            
            # Check if they sent us friend request (waiting for our Accept/Reject)
            if peer_info.peer_id in self._incoming_requests:
                log.debug("Ignoring discovered peer %s: already received friend request from them", peer_info.peer_id)
                return  # Waiting for our response - don't add to suggestions
            
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
                return  # Don't continue - accept is being processed
            
            # CRITICAL: If peer has pending friend request (in _incoming_requests) but callback wasn't emitted yet,
            # emit it now that we have valid tcp_port from discovery
            # This handles the case where FRIEND_REQUEST arrived before discovery
            if peer_info.peer_id in self._incoming_requests:
                # Only emit callback once - check if already emitted
                if peer_info.peer_id not in self._friend_request_emitted:
                    log.info("Discovery updated peer %s with valid tcp_port %s. Emitting pending friend request callback.", 
                            peer_info.peer_id, peer_info.tcp_port)
                    # Mark as emitted to prevent duplicate
                    self._friend_request_emitted.add(peer_info.peer_id)
                    # Emit friend request callback now that we have valid peer info
                    if self._on_friend_request_callback:
                        try:
                            self._on_friend_request_callback(peer_info.peer_id, peer_info.display_name)
                        except Exception as e:
                            log.error("Error in _on_friend_request_callback for %s: %s", peer_info.peer_id, e, exc_info=True)
                else:
                    log.debug("Friend request callback already emitted for %s, skipping", peer_info.peer_id)
                return  # Don't add to suggestions - waiting for Accept/Reject
        
        # Notify GUI about temporary peer (for Suggestions list)
        # Wrap callback in try-except to prevent crash
        if self._on_temp_peer_callback:
            try:
                self._on_temp_peer_callback(peer_info)
            except Exception as e:
                log.error("Error in _on_temp_peer_callback for %s: %s", peer_info.peer_id, e, exc_info=True)
        
        # DO NOT call _on_peer_callback - that's only for known peers (added friends)

    def _handle_incoming_message_with_addr(self, message: Message, sender_ip: str = "", sender_port: int = 0):
        """
        Wrapper to handle incoming message with sender address info.
        """
        self._handle_incoming_message(message, sender_ip, sender_port)
    
    def _handle_incoming_message(self, message: Message, sender_ip: str = "", sender_port: int = 0):
        """
        Handle incoming message from PeerListener (called from network thread).
        This is called immediately when message is received - realtime processing.
        
        Args:
            message: The received message
            sender_ip: IP address of sender (from TCP connection)
            sender_port: Port of sender (from TCP connection)
        """
        msg_type = message.msg_type
        
        # Handle friend request messages separately
        if msg_type == "FRIEND_REQUEST":
            log.info("Friend request from %s (%s)", message.sender_name, message.sender_id)
            
            with self._lock:
                # Check if already a friend - ignore duplicate request
                if message.sender_id in self._peers:
                    log.debug("Ignoring friend request from %s: already a friend", message.sender_id)
                    return
                
                # Check if already received request from this peer - only emit once
                if message.sender_id in self._incoming_requests:
                    log.debug("Ignoring duplicate friend request from %s: already in _incoming_requests", message.sender_id)
                    return  # Already processed - don't emit signal again
                
                # Mark as incoming request (prevent duplicate popups)
                self._incoming_requests.add(message.sender_id)
            
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
            else:
                # Update IP only - NEVER update tcp_port from TCP connection
                # sender_port is ephemeral port, NOT listener port
                if sender_ip:
                    peer_info.ip = sender_ip
                # tcp_port must come from Discovery Broadcast (already in peer_info from discovery)
                peer_info.touch("online")
                log.debug("Updated peer %s IP to %s (tcp_port from discovery: %s)", 
                         message.sender_id, sender_ip, peer_info.tcp_port)
            
            # Notify GUI about friend request (only once per peer)
            # Mark as emitted to prevent duplicate emissions
            if message.sender_id not in self._friend_request_emitted:
                self._friend_request_emitted.add(message.sender_id)
                # Wrap callback in try-except to prevent crash
                if self._on_friend_request_callback:
                    try:
                        self._on_friend_request_callback(message.sender_id, message.sender_name)
                    except Exception as e:
                        log.error("Error in _on_friend_request_callback for %s: %s", message.sender_id, e, exc_info=True)
            else:
                log.debug("Friend request callback already emitted for %s, skipping", message.sender_id)
            # Don't save friend request as regular message
            return
        
        elif msg_type == "FRIEND_ACCEPT":
            log.info("Friend accepted by %s (%s)", message.sender_name, message.sender_id)
            
            with self._lock:
                # Check if already a friend - just update status
                if message.sender_id in self._peers:
                    existing_peer = self._peers[message.sender_id]
                    existing_peer.touch("online")
                    if sender_ip:
                        existing_peer.ip = sender_ip
                    # CRITICAL: NEVER update tcp_port from sender_port (ephemeral port)
                    # tcp_port must come from Discovery Broadcast only
                    # Discovery will update port when it broadcasts
                    if self.data_manager:
                        self.data_manager.update_peer(existing_peer)
                    # Wrap callbacks in try-except to prevent crash
                    if self._on_peer_callback:
                        try:
                            self._on_peer_callback(existing_peer)
                        except Exception as e:
                            log.error("Error in _on_peer_callback for existing friend %s: %s", message.sender_id, e, exc_info=True)
                    if self._on_friend_accepted_callback:
                        try:
                            self._on_friend_accepted_callback(message.sender_id)
                        except Exception as e:
                            log.error("Error in _on_friend_accepted_callback for %s: %s", message.sender_id, e, exc_info=True)
                    return
                
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
                
                # Update IP only - NEVER update tcp_port from TCP connection
                if sender_ip:
                    peer_info.ip = sender_ip
                # tcp_port must come from Discovery Broadcast (already in peer_info from discovery)
                peer_info.touch("online")
                log.debug("Updated peer %s IP to %s (tcp_port from discovery: %s)", 
                         message.sender_id, sender_ip, peer_info.tcp_port)
                
                # CRITICAL: Add to friends list IMMEDIATELY, even if tcp_port is 0
                # We'll update tcp_port later from discovery or FRIEND_SYNC
                # This ensures mutual friendship is established on both sides
                self._peers[message.sender_id] = peer_info
                
                # Remove from temp_discovered_peers
                if message.sender_id in self.temp_discovered_peers:
                    del self.temp_discovered_peers[message.sender_id]
                
                # Remove from request tracking
                self._outgoing_requests.discard(message.sender_id)
                self._incoming_requests.discard(message.sender_id)
                self._friend_request_emitted.discard(message.sender_id)  # Allow new requests in future
                self._friend_request_emitted.discard(message.sender_id)  # Allow new requests in future
            
            # CRITICAL: Save to peers.json IMMEDIATELY, even if tcp_port is 0
            # This ensures the peer entry exists on both sides
            # tcp_port will be updated later from discovery or FRIEND_SYNC
            if self.data_manager:
                # Temporarily allow saving with tcp_port=0 for mutual friendship
                # We'll update it later when discovery provides valid port
                if peer_info.tcp_port and 55000 <= peer_info.tcp_port <= 55199:
                    # Valid port - save normally
                    self.data_manager.update_peer(peer_info)
                    log.info("Saved peer %s (%s) to friends list with TCP port %s", 
                            peer_info.display_name, message.sender_id, peer_info.tcp_port)
                else:
                    # Invalid port - save with placeholder, will update later
                    log.warning("Saving peer %s with invalid tcp_port %s. Will update when discovery provides valid port.", 
                               message.sender_id, peer_info.tcp_port)
                    # Use a placeholder port (55000) temporarily to allow save
                    # This ensures mutual friendship is established
                    temp_peer = PeerInfo(
                        peer_id=peer_info.peer_id,
                        display_name=peer_info.display_name,
                        ip=peer_info.ip,
                        tcp_port=55000,  # Placeholder - will be updated by discovery
                        last_seen=peer_info.last_seen,
                        status=peer_info.status,
                    )
                    # Save with placeholder
                    peers = self.data_manager.load_peers()
                    peers[message.sender_id] = temp_peer
                    self.data_manager.save_peers(peers)
                    log.info("Saved peer %s (%s) with placeholder port. Will update when discovery provides valid port.", 
                            peer_info.display_name, message.sender_id)
            
            # Emit temp_peer_removed signal (so GUI removes from suggestions)
            # Wrap all callbacks in try-except to prevent crash
            if self._on_temp_peer_removed_callback:
                try:
                    self._on_temp_peer_removed_callback(message.sender_id)
                except Exception as e:
                    log.error("Error in _on_temp_peer_removed_callback for %s: %s", message.sender_id, e, exc_info=True)
            
            # Notify GUI about new known peer
            if self._on_peer_callback:
                try:
                    self._on_peer_callback(peer_info)
                except Exception as e:
                    log.error("Error in _on_peer_callback for new friend %s: %s", message.sender_id, e, exc_info=True)
            
            # Notify about acceptance
            if self._on_friend_accepted_callback:
                try:
                    self._on_friend_accepted_callback(message.sender_id)
                except Exception as e:
                    log.error("Error in _on_friend_accepted_callback for %s: %s", message.sender_id, e, exc_info=True)
            
            # Send FRIEND_SYNC to ensure the other side also has our peer info
            # This guarantees mutual friendship
            if peer_info.ip and peer_info.tcp_port and 55000 <= peer_info.tcp_port <= 55199:
                sync_message = Message.create_friend_sync(
                    sender_id=self.peer_id,
                    sender_name=self.display_name or "Unknown",
                    receiver_id=message.sender_id,
                    peer_ip=self._get_local_ip_for_sync(),
                    peer_tcp_port=self.tcp_port,
                )
                try:
                    self.peer_client.send(peer_info.ip, peer_info.tcp_port, sync_message)
                    log.info("Sent FRIEND_SYNC to %s to ensure mutual friendship", message.sender_id)
                except Exception as e:
                    log.warning("Failed to send FRIEND_SYNC to %s: %s", message.sender_id, e)
            else:
                log.warning("Cannot send FRIEND_SYNC to %s: invalid IP/port. Will send when discovery updates.", 
                           message.sender_id)
            
            # Don't save friend accept as regular message
            return
        
        elif msg_type == "FRIEND_SYNC":
            # Handle FRIEND_SYNC message to ensure mutual friendship
            log.info("FRIEND_SYNC received from %s (%s)", message.sender_name, message.sender_id)
            
            try:
                import json
                sync_data = json.loads(message.content)
                peer_ip = sync_data.get("ip", sender_ip if sender_ip else "127.0.0.1")
                peer_tcp_port = int(sync_data.get("tcp_port", 0))
                
                # Validate port
                if peer_tcp_port < 55000 or peer_tcp_port > 55199:
                    log.warning("FRIEND_SYNC from %s has invalid tcp_port %s, ignoring", message.sender_id, peer_tcp_port)
                    return
                
                # Create or update peer info
                with self._lock:
                    if message.sender_id in self._peers:
                        # Update existing peer with correct info from sync
                        existing_peer = self._peers[message.sender_id]
                        existing_peer.ip = peer_ip
                        existing_peer.tcp_port = peer_tcp_port
                        existing_peer.display_name = message.sender_name
                        existing_peer.touch("online")
                        peer_info = existing_peer
                    else:
                        # Create new peer entry
                        peer_info = PeerInfo(
                            peer_id=message.sender_id,
                            display_name=message.sender_name,
                            ip=peer_ip,
                            tcp_port=peer_tcp_port,
                            last_seen=message.timestamp,
                            status="online",
                        )
                        self._peers[message.sender_id] = peer_info
                    
                    # Remove from temp and request tracking
                    if message.sender_id in self.temp_discovered_peers:
                        del self.temp_discovered_peers[message.sender_id]
                    self._outgoing_requests.discard(message.sender_id)
                    self._incoming_requests.discard(message.sender_id)
                
                # Save to peers.json
                if self.data_manager:
                    self.data_manager.update_peer(peer_info)
                    log.info("Saved peer %s (%s) from FRIEND_SYNC with TCP port %s", 
                            peer_info.display_name, message.sender_id, peer_info.tcp_port)
                
                # Notify GUI
                if self._on_peer_callback:
                    try:
                        self._on_peer_callback(peer_info)
                    except Exception as e:
                        log.error("Error in _on_peer_callback for FRIEND_SYNC %s: %s", message.sender_id, e, exc_info=True)
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                log.error("Failed to parse FRIEND_SYNC from %s: %s", message.sender_id, e)
            
            return
        
        elif msg_type == "FRIEND_REJECT":
            log.info("Friend rejected by %s (%s)", message.sender_name, message.sender_id)
            # Remove from outgoing_requests (they rejected, we can try again later)
            with self._lock:
                self._outgoing_requests.discard(message.sender_id)
            # Keep in temp_discovered_peers (user might want to try again)
            # Notify GUI - wrap callback in try-except to prevent crash
            if self._on_friend_rejected_callback:
                try:
                    self._on_friend_rejected_callback(message.sender_id)
                except Exception as e:
                    log.error("Error in _on_friend_rejected_callback for %s: %s", message.sender_id, e, exc_info=True)
            # Don't save friend reject as regular message
            return
        
        # Regular text messages
        log.info(
            "Message from %s (%s): %s",
            message.sender_name,
            message.sender_id,
            message.content,
        )
        
        # Save message to storage (non-blocking, thread-safe)
        if self.data_manager:
            self.data_manager.append_message(message)
        
        # Call callback immediately - this triggers realtime update chain
        # Callback will be handled in appropriate thread by ChatCore
        if self._on_message_callback:
            self._on_message_callback(message)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def send_message(self, to_peer_id: str, content: str, msg_type: str = "text") -> Tuple[bool, Optional[Message]]:
        """
        Send a message to a peer.
        Only sends if:
        1. Router is initialized
        2. Peer is in known peers (has accepted friend request)
        3. Peer has valid IP and TCP port
        4. Listener is running (we can receive responses)
        """
        if not self.data_manager:
            log.error("Router not initialized. Cannot send message.")
            raise RuntimeError("Router not initialized.")

        # Check if listener is running
        if not self.peer_listener or not self.peer_listener._thread or not self.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send message.")
            return False, None

        # Only send to peers that have accepted friend request (in _peers)
        with self._lock:
            target = self._peers.get(to_peer_id)
        if not target:
            log.warning("Cannot send message to %s: Peer not in friends list (not accepted)", to_peer_id)
            return False, None

        # Validate peer info
        if not target.ip or not target.tcp_port:
            log.warning("Cannot send message to %s: Invalid IP (%s) or port (%s)", to_peer_id, target.ip, target.tcp_port)
            return False, None

        # Validate IP format (basic check)
        if target.ip == "0.0.0.0" or target.ip == "":
            log.warning("Cannot send message to %s: Invalid IP address", to_peer_id)
            return False, None

        # CRITICAL: Validate tcp_port is not 0
        if target.tcp_port == 0:
            log.warning("Cannot send message to %s: tcp_port is 0 (not discovered yet). Removing peer.", to_peer_id)
            # Remove peer with invalid port
            with self._lock:
                if to_peer_id in self._peers:
                    del self._peers[to_peer_id]
            if self.data_manager:
                peers = self.data_manager.load_peers()
                peers.pop(to_peer_id, None)
                self.data_manager.save_peers(peers)
            return False, None
        
        # Validate port range (must be 55000-55199)
        if target.tcp_port < 55000 or target.tcp_port > 55199:
            log.warning("Cannot send message to %s: Port %s is outside valid range (55000-55199). "
                       "This may be a stale/ephemeral port. Removing peer.", to_peer_id, target.tcp_port)
            # Remove stale peer
            with self._lock:
                if to_peer_id in self._peers:
                    del self._peers[to_peer_id]
            if self.data_manager:
                peers = self.data_manager.load_peers()
                peers.pop(to_peer_id, None)
                self.data_manager.save_peers(peers)
            return False, None
        
        # Validate peer status
        if target.status != "online":
            log.warning("Cannot send message to %s: Peer status is %s (not online)", to_peer_id, target.status)
            return False, None
        
        # Validate last_seen freshness (< 300 seconds)
        time_since_last_seen = time.time() - target.last_seen
        if time_since_last_seen > 300:  # 5 minutes
            log.warning("Cannot send message to %s: Peer last_seen is too old (%s seconds ago). "
                       "Marking as offline.", to_peer_id, int(time_since_last_seen))
            target.status = "offline"
            if self.data_manager:
                self.data_manager.update_peer(target)
            return False, None

        message = Message.create(
            sender_id=self.peer_id,
            sender_name=self.display_name or "Unknown",
            receiver_id=to_peer_id,
            content=content,
            msg_type=msg_type,
        )

        log.info("Sending message to %s (%s) at %s:%s", target.display_name, to_peer_id, target.ip, target.tcp_port)
        success = self.peer_client.send(target.ip, target.tcp_port, message)
        if success:
            # Reset failure count on success
            self._peer_send_failures.pop(to_peer_id, None)
            if self.data_manager:
                self.data_manager.append_message(message)
            log.info("Message sent successfully to %s (%s) at %s:%s", target.display_name, to_peer_id, target.ip, target.tcp_port)
        else:
            # Increment failure count
            failures = self._peer_send_failures.get(to_peer_id, 0) + 1
            self._peer_send_failures[to_peer_id] = failures
            
            # If fail 3 times consecutively, mark peer as offline
            if failures >= 3:
                log.warning("Peer %s failed %s times, marking as offline", to_peer_id, failures)
                target.status = "offline"
                if self.data_manager:
                    self.data_manager.update_peer(target)
                # Reset failure count
                self._peer_send_failures.pop(to_peer_id, None)
            
            log.warning("Failed to send message to %s (%s) at %s:%s - connection refused or peer offline", to_peer_id, target.display_name, target.ip, target.tcp_port)
        return success, message if success else None

    def get_known_peers(self) -> List[PeerInfo]:
        """Get list of known peers (friends)."""
        with self._lock:
            now = time.time()
            return sorted(
                list(self._peers.values()),
                key=lambda peer: now - peer.last_seen,
            )

    def get_message_history(self, peer_id: Optional[str] = None) -> List[Message]:
        if not self.data_manager:
            return []
        return self.data_manager.load_messages(peer_id=peer_id)

    # ------------------------------------------------------------------ #
    def set_peer_callback(self, callback: Optional[Callable[[PeerInfo], None]]):
        self._on_peer_callback = callback

    def add_peer(self, peer_id: str) -> bool:
        """
        Add a discovered peer to the known peers list (friends list).
        This saves the peer to peers.json and removes it from temp_discovered_peers.
        
        Args:
            peer_id: The peer_id to add
            
        Returns:
            True if peer was added successfully, False if peer not found
        """
        with self._lock:
            # Check if already in friends
            if peer_id in self._peers:
                log.info("Peer %s already in friends list", peer_id)
                return True
            
            # Check if peer exists in temp_discovered_peers
            if peer_id not in self.temp_discovered_peers:
                log.warning("Peer %s not found in discovered peers", peer_id)
                return False
            
            # Get peer info from temp_discovered_peers
            peer_info = self.temp_discovered_peers[peer_id]
            
            # Add to friends list in memory
            self._peers[peer_id] = peer_info
            
            # Remove from temp and request tracking
            del self.temp_discovered_peers[peer_id]
            self._outgoing_requests.discard(peer_id)
            self._incoming_requests.discard(peer_id)
            
            # Store peer_info for use after lock release
            peer_info_copy = peer_info
        
        # CRITICAL: Validate tcp_port before saving to DataManager
        if not peer_info_copy.tcp_port or peer_info_copy.tcp_port < 55000 or peer_info_copy.tcp_port > 55199:
            log.warning("Cannot add peer %s: invalid tcp_port %s (must be 55000-55199). "
                       "Peer added to memory but not saved. Waiting for discovery to update.", 
                       peer_id, peer_info_copy.tcp_port)
            return False
        
        # Save to DataManager (this writes to peers.json)
        if self.data_manager:
            self.data_manager.update_peer(peer_info_copy)
            log.info("Added peer %s (%s) to known peers with tcp_port %s", 
                    peer_info_copy.display_name, peer_id, peer_info_copy.tcp_port)
        
        # Emit temp_peer_removed signal
        if self._on_temp_peer_removed_callback:
            self._on_temp_peer_removed_callback(peer_id)
        
        # Notify GUI about new known peer - wrap callback in try-except to prevent crash
        if self._on_peer_callback:
            try:
                self._on_peer_callback(peer_info_copy)
            except Exception as e:
                log.error("Error in _on_peer_callback for added peer %s: %s", peer_id, e, exc_info=True)
        
        return True
    
    def get_temp_discovered_peers(self) -> List[PeerInfo]:
        """
        Get list of temporarily discovered peers (not yet added to friends).
        These are peers found by discovery but not yet saved.
        Already filters out friends and pending requests.
        """
        with self._lock:
            # Filter out peers that are already in friends or pending requests
            temp_only = [
                peer for peer_id, peer in self.temp_discovered_peers.items()
                if peer_id not in self._peers
                and peer_id not in self._outgoing_requests
                and peer_id not in self._incoming_requests
            ]
            return temp_only
    
    def set_temp_peer_callback(self, callback: Optional[Callable[[PeerInfo], None]]):
        """
        Set callback for temporary discovered peers (for Suggestions list).
        This is different from set_peer_callback which is for known peers.
        """
        self._on_temp_peer_callback = callback
    
    def set_temp_peer_removed_callback(self, callback: Optional[Callable[[str], None]]):
        """
        Set callback when a temporary discovered peer is removed (became friend).
        This callback is called when a peer is removed from temp_discovered_peers.
        """
        self._on_temp_peer_removed_callback = callback
    
    def remove_temp_peer(self, peer_id: str) -> bool:
        """
        Remove a peer from temp_discovered_peers (suggestions).
        This is called when peer becomes a friend or request is sent.
        
        Args:
            peer_id: The peer_id to remove
            
        Returns:
            True if peer was removed, False if not found
        """
        with self._lock:
            if peer_id in self.temp_discovered_peers:
                del self.temp_discovered_peers[peer_id]
                log.info("Removed peer %s from suggestions", peer_id)
                # Notify GUI that peer was removed from suggestions - wrap callback in try-except
                if self._on_temp_peer_removed_callback:
                    try:
                        self._on_temp_peer_removed_callback(peer_id)
                    except Exception as e:
                        log.error("Error in _on_temp_peer_removed_callback for %s: %s", peer_id, e, exc_info=True)
                return True
        return False
    
    def set_friend_request_callback(self, callback: Optional[Callable[[str, str], None]]):
        """Set callback for friend requests (peer_id, display_name)."""
        self._on_friend_request_callback = callback
    
    def set_friend_accepted_callback(self, callback: Optional[Callable[[str], None]]):
        """Set callback when friend request is accepted (peer_id)."""
        self._on_friend_accepted_callback = callback
    
    def set_friend_rejected_callback(self, callback: Optional[Callable[[str], None]]):
        """Set callback when friend request is rejected (peer_id)."""
        self._on_friend_rejected_callback = callback
    
    def send_friend_request(self, peer_id: str) -> bool:
        """
        Send a friend request to a discovered peer.
        The peer must be in temp_discovered_peers.
        Adds peer_id to _outgoing_requests but keeps in temp_discovered_peers.
        
        Args:
            peer_id: The peer_id to send request to
            
        Returns:
            True if request sent successfully, False otherwise
        """
        # Check if listener is running
        if not self.peer_listener or not self.peer_listener._thread or not self.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send friend request.")
            return False
        
        with self._lock:
            # Get peer info from temp_discovered_peers
            peer_info = self.temp_discovered_peers.get(peer_id)
            if not peer_info:
                log.warning("Peer %s not found in discovered peers", peer_id)
                return False
            
            # Validate peer info
            if not peer_info.ip or not peer_info.tcp_port:
                log.warning("Cannot send friend request to %s: Invalid IP (%s) or port (%s)", peer_id, peer_info.ip, peer_info.tcp_port)
                return False
            
            if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
                log.warning("Cannot send friend request to %s: Invalid IP address", peer_id)
                return False
            
            if peer_info.tcp_port <= 0 or peer_info.tcp_port > 65535:
                log.warning("Cannot send friend request to %s: Invalid port %s", peer_id, peer_info.tcp_port)
                return False
            
            # CRITICAL: Validate tcp_port is not 0
            if peer_info.tcp_port == 0:
                log.warning("Cannot send friend request to %s: tcp_port is 0 (not discovered yet)", peer_id)
                return False
            
            # Validate port range (55000-55199)
            if peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
                log.warning("Cannot send friend request to %s: Port %s is outside valid range (55000-55199)", 
                           peer_id, peer_info.tcp_port)
                return False
            
            # Mark as outgoing request (so it won't appear in suggestions)
            self._outgoing_requests.add(peer_id)
        
        # Create friend request message
        message = Message.create_friend_request(
            sender_id=self.peer_id,
            sender_name=self.display_name or "Unknown",
            receiver_id=peer_id,
        )
        
        # Send via TCP
        log.info("Sending friend request to %s (%s:%s)", peer_info.display_name, peer_info.ip, peer_info.tcp_port)
        success = self.peer_client.send(peer_info.ip, peer_info.tcp_port, message)
        if success:
            log.info("Friend request sent to %s (%s)", peer_info.display_name, peer_id)
            # Keep peer in temp_discovered_peers (for when we receive ACCEPT)
            # But peer_id is in _outgoing_requests, so get_temp_discovered_peers() will filter it out
            # GUI will also filter based on pending_friend_requests
            # No need to emit temp_peer_removed - GUI will filter it out
        else:
            # Remove from outgoing_requests if send failed
            with self._lock:
                self._outgoing_requests.discard(peer_id)
            log.warning("Failed to send friend request to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
        
        return success
    
    def send_friend_accept(self, peer_id: str) -> bool:
        """
        Send friend accept response to a peer who sent friend request.
        Also saves the peer to known_peers immediately (local side).
        
        Args:
            peer_id: The peer_id who sent the request
            
        Returns:
            True if accept sent successfully, False otherwise
        """
        # Check if listener is running
        if not self.peer_listener or not self.peer_listener._thread or not self.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send friend accept.")
            return False
        
        with self._lock:
            # Check if already a friend
            if peer_id in self._peers:
                log.info("Peer %s already in friends list", peer_id)
                # Still send accept message in case they didn't receive it
                peer_info = self._peers[peer_id]
            else:
                # Get peer info from temp_discovered_peers
                peer_info = self.temp_discovered_peers.get(peer_id)
                if not peer_info:
                    # CRITICAL: If peer not discovered yet, mark as pending and wait for discovery
                    log.info("Peer %s not found in discovered peers. Marking as pending accept, waiting for discovery.", peer_id)
                    self._pending_friend_accepts[peer_id] = time.time()
                    # Return False but discovery will complete it later
                    return False
                
                # Add to friends list in memory
                self._peers[peer_id] = peer_info
                
                # Remove from temp and request tracking
                if peer_id in self.temp_discovered_peers:
                    del self.temp_discovered_peers[peer_id]
                self._outgoing_requests.discard(peer_id)
                self._incoming_requests.discard(peer_id)
            
            # Validate peer info
            if not peer_info.ip or not peer_info.tcp_port:
                log.warning("Cannot send friend accept to %s: Invalid IP (%s) or port (%s)", peer_id, peer_info.ip, peer_info.tcp_port)
                return False
            
            if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
                log.warning("Cannot send friend accept to %s: Invalid IP address", peer_id)
                return False
            
            if peer_info.tcp_port <= 0 or peer_info.tcp_port > 65535:
                log.warning("Cannot send friend accept to %s: Invalid port %s", peer_id, peer_info.tcp_port)
                return False
            
            # CRITICAL: Validate tcp_port is not 0
            if peer_info.tcp_port == 0:
                log.info("Peer %s has tcp_port=0. Marking as pending accept, waiting for discovery to update.", peer_id)
                self._pending_friend_accepts[peer_id] = time.time()
                return False
            
            # Validate port range (55000-55199)
            if peer_info.tcp_port < 55000 or peer_info.tcp_port > 55199:
                log.warning("Cannot send friend accept to %s: Port %s is outside valid range (55000-55199). "
                           "This may be a stale/ephemeral port. Waiting for discovery to update.", 
                           peer_id, peer_info.tcp_port)
                return False
        
        # CRITICAL: Save to peers.json IMMEDIATELY, even if tcp_port is 0
        # This ensures mutual friendship is established on both sides
        if self.data_manager:
            if peer_info.tcp_port and 55000 <= peer_info.tcp_port <= 55199:
                # Valid port - save normally
                self.data_manager.update_peer(peer_info)
                log.info("Saved peer %s (%s) to friends list with tcp_port %s", 
                        peer_info.display_name, peer_id, peer_info.tcp_port)
            else:
                # Invalid port - save with placeholder, will update later
                log.warning("Saving peer %s with invalid tcp_port %s. Will update when discovery provides valid port.", 
                           peer_id, peer_info.tcp_port)
                # Use a placeholder port (55000) temporarily to allow save
                temp_peer = PeerInfo(
                    peer_id=peer_info.peer_id,
                    display_name=peer_info.display_name,
                    ip=peer_info.ip,
                    tcp_port=55000,  # Placeholder - will be updated by discovery
                    last_seen=peer_info.last_seen,
                    status=peer_info.status,
                )
                peers = self.data_manager.load_peers()
                peers[peer_id] = temp_peer
                self.data_manager.save_peers(peers)
                log.info("Saved peer %s (%s) with placeholder port. Will update when discovery provides valid port.", 
                        peer_info.display_name, peer_id)
        
        # Emit temp_peer_removed signal (so GUI removes from suggestions)
        # Wrap callbacks in try-except to prevent crash
        if self._on_temp_peer_removed_callback:
            try:
                self._on_temp_peer_removed_callback(peer_id)
            except Exception as e:
                log.error("Error in _on_temp_peer_removed_callback for %s: %s", peer_id, e, exc_info=True)
        
        # Notify GUI about new known peer (local side)
        if self._on_peer_callback:
            try:
                self._on_peer_callback(peer_info)
            except Exception as e:
                log.error("Error in _on_peer_callback for accepted friend %s: %s", peer_id, e, exc_info=True)
        
        # Create friend accept message
        message = Message.create_friend_accept(
            sender_id=self.peer_id,
            sender_name=self.display_name or "Unknown",
            receiver_id=peer_id,
        )
        
        # Send via TCP
        log.info("Sending friend accept to %s (%s:%s)", peer_info.display_name, peer_info.ip, peer_info.tcp_port)
        success = self.peer_client.send(peer_info.ip, peer_info.tcp_port, message)
        if success:
            log.info("Friend accept sent to %s (%s)", peer_info.display_name, peer_id)
            
            # Send FRIEND_SYNC to ensure the other side also has our peer info
            # This guarantees mutual friendship
            sync_message = Message.create_friend_sync(
                sender_id=self.peer_id,
                sender_name=self.display_name or "Unknown",
                receiver_id=peer_id,
                peer_ip=self._get_local_ip_for_sync(),
                peer_tcp_port=self.tcp_port,
            )
            try:
                self.peer_client.send(peer_info.ip, peer_info.tcp_port, sync_message)
                log.info("Sent FRIEND_SYNC to %s to ensure mutual friendship", peer_id)
            except Exception as e:
                log.warning("Failed to send FRIEND_SYNC to %s: %s", peer_id, e)
        else:
            log.warning("Failed to send friend accept to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
        
        return success
    
    def send_friend_reject(self, peer_id: str) -> bool:
        """
        Send friend reject response to a peer who sent friend request.
        
        Args:
            peer_id: The peer_id who sent the request
            
        Returns:
            True if reject sent successfully, False otherwise
        """
        # Check if listener is running
        if not self.peer_listener or not self.peer_listener._thread or not self.peer_listener._thread.is_alive():
            log.error("PeerListener not running. Cannot send friend reject.")
            return False
        
        # Get peer info from temp_discovered_peers
        peer_info = self.temp_discovered_peers.get(peer_id)
        if not peer_info:
            log.warning("Peer %s not found in discovered peers", peer_id)
            return False
        
        # Validate peer info
        if not peer_info.ip or not peer_info.tcp_port:
            log.warning("Cannot send friend reject to %s: Invalid IP (%s) or port (%s)", peer_id, peer_info.ip, peer_info.tcp_port)
            return False
        
        if peer_info.ip == "0.0.0.0" or peer_info.ip == "":
            log.warning("Cannot send friend reject to %s: Invalid IP address", peer_id)
            return False
        
        if peer_info.tcp_port <= 0 or peer_info.tcp_port > 65535:
            log.warning("Cannot send friend reject to %s: Invalid port %s", peer_id, peer_info.tcp_port)
            return False
        
        # Create friend reject message
        message = Message.create_friend_reject(
            sender_id=self.peer_id,
            sender_name=self.display_name or "Unknown",
            receiver_id=peer_id,
        )
        
        # Send via TCP
        log.info("Sending friend reject to %s (%s:%s)", peer_info.display_name, peer_info.ip, peer_info.tcp_port)
        success = self.peer_client.send(peer_info.ip, peer_info.tcp_port, message)
        if success:
            log.info("Friend reject sent to %s (%s)", peer_info.display_name, peer_id)
        else:
            log.warning("Failed to send friend reject to %s (%s:%s)", peer_id, peer_info.ip, peer_info.tcp_port)
        
        return success
    
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

    def cleanup_offline_peers(self, max_offline_time: float = 600.0) -> int:
        """
        Remove peers that have been offline for more than max_offline_time seconds.
        
        Args:
            max_offline_time: Maximum time in seconds a peer can be offline before removal (default: 600 = 10 minutes)
            
        Returns:
            Number of peers removed
        """
        from Core.utils import config
        offline_timeout = getattr(config, 'OFFLINE_PEER_CLEANUP_TIMEOUT', max_offline_time)
        
        with self._lock:
            peers_to_remove = []
            now = time.time()
            for peer_id, peer in self._peers.items():
                if peer.status == "offline" and (now - peer.last_seen > offline_timeout):
                    peers_to_remove.append(peer_id)
            
            for peer_id in peers_to_remove:
                log.info("Removing offline peer %s from friends list (offline for > %s seconds)", peer_id, offline_timeout)
                del self._peers[peer_id]
                if self.data_manager:
                    self.data_manager.remove_peer(peer_id)
                # Emit signal to GUI to remove from chat list
                if self._on_peer_callback:
                    try:
                        # Create a peer info with status="removed" to signal removal
                        removed_peer = PeerInfo(peer_id=peer_id, display_name="", ip="", tcp_port=0, last_seen=0, status="removed")
                        self._on_peer_callback(removed_peer)
                    except Exception as e:
                        log.error("Error in _on_peer_callback for removed peer %s: %s", peer_id, e, exc_info=True)
        
        return len(peers_to_remove)
    
    def _get_local_ip_for_sync(self) -> str:
        """Get local IP address for FRIEND_SYNC message."""
        try:
            from Core.utils.network_mode import get_local_ip
            return get_local_ip(self._network_mode)
        except Exception:
            return "127.0.0.1"

    def _notify_existing_peers(self):
        """
        Notify GUI about existing known peers (from peers.json).
        This is called on startup to load saved friends.
        """
        if not self._on_peer_callback:
            return
        # _peers was already loaded in connect_core()
        # Wrap callback in try-except to prevent crash
        with self._lock:
            for peer in self._peers.values():
                try:
                    self._on_peer_callback(peer)
                except Exception as e:
                    log.error("Error in _on_peer_callback for peer %s: %s", peer.peer_id, e, exc_info=True)
                    # Continue with other peers even if one fails

