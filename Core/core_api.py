"""
High-level ChatCore API exposed to the GUI layer.
Wraps MessageRouter and hides threading/network details.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

# Import Qt for thread-safe signals
try:
    from PySide6.QtCore import QObject, Signal
    QT_AVAILABLE = True
except ImportError:
    # Fallback if Qt is not available (should not happen in GUI app)
    QT_AVAILABLE = False
    QObject = object
    Signal = None

from Core.routing.message_router import MessageRouter
from Core.models.message import Message
from Core.models.peer_info import PeerInfo

# Initialize logger
log = logging.getLogger(__name__)


class CoreSignals(QObject):
    """
    Qt Signals for thread-safe communication from Core to GUI.
    All signals are emitted from background threads and handled in main thread.
    """
    # Signal emitted when a new message is received
    message_received = Signal(dict)  # payload dict
    # Signal emitted when known peer is updated
    peer_updated = Signal(dict)  # peer_info dict
    # Signal emitted when temporary discovered peer is found
    temp_peer_updated = Signal(dict)  # peer_info dict
    # Signal emitted when peer is removed from suggestions (became friend)
    temp_peer_removed = Signal(str)  # peer_id
    # Signal emitted when friend request is received
    friend_request_received = Signal(str, str)  # peer_id, display_name
    # Signal emitted when friend request is accepted
    friend_accepted = Signal(str)  # peer_id
    # Signal emitted when friend request is rejected
    friend_rejected = Signal(str)  # peer_id


def _format_time(ts: float) -> str:
    return time.strftime("%H:%M", time.localtime(ts))


def _format_date(ts: float) -> str:
    return time.strftime("%d %b %Y", time.localtime(ts))


class ChatCore:
    """
    Public API consumed by the GUI.
    Uses Qt Signals for thread-safe communication from background threads to GUI.
    """

    def __init__(
        self,
        username: str,
        display_name: str,
        tcp_port: int,
        on_message_callback: Optional[Callable[[Dict], None]] = None,
        on_peer_update: Optional[Callable[[Dict], None]] = None,
    ):
        """
        Initialize ChatCore.
        
        Args:
            username: Username for folder structure (normalized)
            display_name: Display name for UI and peer communication
            tcp_port: TCP port to listen on
            on_message_callback: DEPRECATED - Use signals instead. Kept for backward compatibility.
            on_peer_update: DEPRECATED - Use signals instead. Kept for backward compatibility.
        """
        self.username = username
        self.display_name = display_name
        self.tcp_port = tcp_port
        
        # Create Qt Signals object for thread-safe communication
        self.signals = CoreSignals()
        
        # Keep old callbacks for backward compatibility (but prefer signals)
        self._on_message_callback = on_message_callback
        self._on_peer_update = on_peer_update
        self._on_temp_peer_update: Optional[Callable[[Dict], None]] = None
        self._on_friend_request: Optional[Callable[[str, str], None]] = None  # peer_id, display_name
        self._on_friend_accepted: Optional[Callable[[str], None]] = None  # peer_id
        self._on_friend_rejected: Optional[Callable[[str], None]] = None  # peer_id

        self.router = MessageRouter()
        self.peer_id = self.router.peer_id
        self._running = False

    # ------------------------------------------------------------------ #
    def start(self):
        """
        Start ChatCore. This initializes MessageRouter, starts PeerListener, and starts Discovery.
        IMPORTANT: PeerListener is started FIRST to ensure socket is open before any messages are sent.
        """
        if self._running:
            return
        
        # Set all callbacks BEFORE connecting core
        self.router.set_peer_callback(self._handle_peer_update)
        # Set callback for temporary discovered peers (for Suggestions)
        self.router.set_temp_peer_callback(self._handle_temp_peer_update)
        # Set callback for when peer is removed from suggestions
        self.router.set_temp_peer_removed_callback(self._handle_temp_peer_removed)
        # Set callbacks for friend requests
        self.router.set_friend_request_callback(self._handle_friend_request)
        self.router.set_friend_accepted_callback(self._handle_friend_accepted)
        self.router.set_friend_rejected_callback(self._handle_friend_rejected)
        
        # Connect core - this will:
        # 1. Load TCP port from profile.json (if exists)
        # 2. Start PeerListener FIRST
        # 3. Wait for socket to open
        # 4. Start Discovery
        # 5. Load existing peers
        self.router.connect_core(self.username, self.display_name, self.tcp_port, self._handle_router_message)
        
        # Update peer_id and tcp_port after connection
        self.peer_id = self.router.peer_id
        self.tcp_port = self.router.tcp_port
        
        # Mark as running
        self._running = True
        log.info("ChatCore started successfully (peer_id: %s, tcp_port: %s)", self.peer_id, self.tcp_port)

    def stop(self):
        if not self._running:
            return
        self.router.stop()
        self._running = False

    # ------------------------------------------------------------------ #
    def send_message(self, peer_id: str, content: str, msg_type: str = "text") -> bool:
        success, message = self.router.send_message(peer_id, content, msg_type=msg_type)
        if success and message:
            self._emit_message(message)
        return success

    def get_known_peers(self) -> List[Dict]:
        peers = self.router.get_known_peers()
        return [self._peer_to_dict(peer) for peer in peers]

    def get_message_history(self, peer_id: Optional[str] = None) -> List[Dict]:
        history = self.router.get_message_history(peer_id)
        return [self._message_to_dict(msg) for msg in history]
    
    def add_peer(self, peer_id: str) -> bool:
        """
        Add a discovered peer to the friends list.
        This saves the peer to peers.json and removes it from temp_discovered_peers.
        
        Args:
            peer_id: The peer_id to add
            
        Returns:
            True if peer was added successfully, False otherwise
        """
        return self.router.add_peer(peer_id)
    
    def get_temp_discovered_peers(self) -> List[Dict]:
        """
        Get list of temporarily discovered peers (not yet added to friends).
        These are peers found by discovery but not yet saved.
        Used for Suggestions list in GUI.
        """
        peers = self.router.get_temp_discovered_peers()
        return [self._peer_to_dict(peer) for peer in peers]
    
    def remove_temp_peer(self, peer_id: str) -> bool:
        """
        Remove a peer from temp_discovered_peers (suggestions).
        This is called when peer becomes a friend or request is sent.
        
        Args:
            peer_id: The peer_id to remove
            
        Returns:
            True if peer was removed, False if not found
        """
        return self.router.remove_temp_peer(peer_id)
    
    def set_temp_peer_update_callback(self, callback: Optional[Callable[[Dict], None]]):
        """
        DEPRECATED: Use signals.temp_peer_updated instead.
        Set callback for temporary discovered peers (for Suggestions list).
        This callback is called when a new peer is discovered but not yet added.
        """
        self._on_temp_peer_update = callback
    
    def set_friend_request_callback(self, callback: Optional[Callable[[str, str], None]]):
        """
        DEPRECATED: Use signals.friend_request_received instead.
        Set callback for friend requests.
        Called when a peer sends a friend request.
        Args:
            callback: Function(peer_id: str, display_name: str)
        """
        self._on_friend_request = callback
    
    def set_friend_accepted_callback(self, callback: Optional[Callable[[str], None]]):
        """
        DEPRECATED: Use signals.friend_accepted instead.
        Set callback when friend request is accepted.
        Called when a peer accepts our friend request.
        Args:
            callback: Function(peer_id: str)
        """
        self._on_friend_accepted = callback
    
    def set_friend_rejected_callback(self, callback: Optional[Callable[[str], None]]):
        """
        DEPRECATED: Use signals.friend_rejected instead.
        Set callback when friend request is rejected.
        Called when a peer rejects our friend request.
        Args:
            callback: Function(peer_id: str)
        """
        self._on_friend_rejected = callback
    
    def send_friend_request(self, peer_id: str) -> bool:
        """
        Send a friend request to a discovered peer.
        
        Args:
            peer_id: The peer_id to send request to
            
        Returns:
            True if request sent successfully, False otherwise
        """
        return self.router.send_friend_request(peer_id)
    
    def accept_friend(self, peer_id: str) -> bool:
        """
        Accept a friend request from a peer.
        This will save the peer to peers.json and notify the sender.
        
        Args:
            peer_id: The peer_id who sent the request
            
        Returns:
            True if accept sent successfully, False otherwise
        """
        return self.router.send_friend_accept(peer_id)
    
    def reject_friend(self, peer_id: str) -> bool:
        """
        Reject a friend request from a peer.
        
        Args:
            peer_id: The peer_id who sent the request
            
        Returns:
            True if reject sent successfully, False otherwise
        """
        return self.router.send_friend_reject(peer_id)
    
    def cleanup_offline_peers(self, max_offline_time: float = 600.0) -> int:
        """
        Remove peers that have been offline for more than max_offline_time seconds.
        
        Args:
            max_offline_time: Maximum time (seconds) a peer can be offline before removal (default: 10 minutes)
            
        Returns:
            Number of peers removed
        """
        return self.router.cleanup_offline_peers(max_offline_time)

    # ------------------------------------------------------------------ #
    def _handle_router_message(self, message: Message):
        """
        Handle message from MessageRouter (called from network thread).
        This is called immediately when message is received - realtime processing.
        """
        self._emit_message(message)

    def _emit_message(self, message: Message):
        """
        Emit message to GUI via Qt Signal (thread-safe).
        This is called from background threads and safely handled in main thread.
        """
        payload = self._message_to_dict(message)
        # Emit Qt Signal - automatically queued to main thread
        # DO NOT call old callback - it may be called from background thread
        self.signals.message_received.emit(payload)

    def _handle_peer_update(self, peer_info: PeerInfo):
        """
        Handle update for known peer (added friend).
        Emits Qt Signal for thread-safe GUI update.
        Called from background thread - MUST only emit signal, no direct GUI calls.
        """
        peer_dict = self._peer_to_dict(peer_info)
        # Emit Qt Signal - automatically queued to main thread
        # DO NOT call old callback - it may be called from background thread
        self.signals.peer_updated.emit(peer_dict)
    
    def _handle_temp_peer_update(self, peer_info: PeerInfo):
        """
        Handle update for temporary discovered peer (not yet added).
        This is called when discovery finds a new peer.
        Emits Qt Signal for thread-safe GUI update.
        Called from background thread - MUST only emit signal, no direct GUI calls.
        """
        peer_dict = self._peer_to_dict(peer_info)
        # Emit Qt Signal - automatically queued to main thread
        # DO NOT call old callback - it may be called from background thread
        self.signals.temp_peer_updated.emit(peer_dict)
    
    def _handle_temp_peer_removed(self, peer_id: str):
        """
        Handle when a temporary discovered peer is removed (became friend).
        Emits Qt Signal for thread-safe GUI update.
        """
        # Emit Qt Signal - automatically queued to main thread
        self.signals.temp_peer_removed.emit(peer_id)
    
    def _handle_friend_request(self, peer_id: str, display_name: str):
        """
        Handle incoming friend request from a peer.
        Emits Qt Signal for thread-safe GUI update.
        Called from background thread - MUST only emit signal, no direct GUI calls.
        """
        # Emit Qt Signal - automatically queued to main thread
        # DO NOT call old callback - it may be called from background thread
        self.signals.friend_request_received.emit(peer_id, display_name)
    
    def _handle_friend_accepted(self, peer_id: str):
        """
        Handle when our friend request is accepted.
        Emits Qt Signal for thread-safe GUI update.
        Called from background thread - MUST only emit signal, no direct GUI calls.
        """
        # Emit Qt Signal - automatically queued to main thread
        # DO NOT call old callback - it may be called from background thread
        self.signals.friend_accepted.emit(peer_id)
    
    def _handle_friend_rejected(self, peer_id: str):
        """
        Handle when our friend request is rejected.
        Emits Qt Signal for thread-safe GUI update.
        Called from background thread - MUST only emit signal, no direct GUI calls.
        """
        # Emit Qt Signal - automatically queued to main thread
        # DO NOT call old callback - it may be called from background thread
        self.signals.friend_rejected.emit(peer_id)

    # ------------------------------------------------------------------ #
    def _peer_to_dict(self, peer: PeerInfo) -> Dict:
        return {
            "peer_id": peer.peer_id,
            "display_name": peer.display_name,
            "ip": peer.ip,
            "tcp_port": peer.tcp_port,
            "last_seen": peer.last_seen,
            "status": peer.status,
        }

    def _message_to_dict(self, message: Message) -> Dict:
        peer_id = message.receiver_id if message.sender_id == self.peer_id else message.sender_id
        return {
            "message_id": message.message_id,
            "peer_id": peer_id,
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "content": message.content,
            "timestamp": message.timestamp,
            "time_str": _format_time(message.timestamp),
            "date_str": _format_date(message.timestamp),
            "is_sender": message.sender_id == self.peer_id,
        }

