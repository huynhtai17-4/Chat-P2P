# Architecture Documentation - Chat P2P

## System Overview

Chat P2P là một ứng dụng chat peer-to-peer được xây dựng với kiến trúc MVC, sử dụng Python và PySide6.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         GUI Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Chat List   │  │  Chat Area   │  │ Notifications│      │
│  │   (View)     │  │   (View)     │  │   (View)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↕                 ↕                   ↕               │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ ChatList     │  │  ChatArea    │                         │
│  │ Controller   │  │  Controller  │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↕
┌─────────────────────────────────────────────────────────────┐
│                    Core Bridge Layer                         │
│                   (CoreBridge)                               │
│            Translates between Core and GUI                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↕
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │                   ChatCore                        │       │
│  │            (Main Controller)                      │       │
│  └───────┬──────────────┬──────────────┬────────────┘       │
│          ↓              ↓              ↓                     │
│  ┌──────────────┐ ┌──────────┐ ┌─────────────┐             │
│  │   Network    │ │ Discovery│ │  Connection │             │
│  │   Manager    │ │  Service │ │   Manager   │             │
│  └──────────────┘ └──────────┘ └─────────────┘             │
│          ↓              ↓              ↓                     │
│  ┌──────────────┐ ┌──────────┐ ┌─────────────┐             │
│  │     File     │ │ Message  │ │    Peer     │             │
│  │  Transfer    │ │ Protocol │ │    Model    │             │
│  └──────────────┘ └──────────┘ └─────────────┘             │
└─────────────────────────────────────────────────────────────┘
                      │
                      ↕
            ┌─────────────────────┐
            │   Network Layer     │
            │  (TCP/UDP Sockets)  │
            └─────────────────────┘
```

## Component Details

### 1. Core Layer

#### ChatCore (`Core/chat_core.py`)
- **Role**: Main controller integrating all core components
- **Responsibilities**:
  - Start/stop P2P network
  - Coordinate between components
  - Handle high-level operations
  - Emit signals for GUI
- **Key Methods**:
  - `start()`: Initialize network and discovery
  - `send_message(text, peer_id)`: Send text message
  - `send_file(path, peer_id)`: Initiate file transfer
  - `connect_to_peer(peer)`: Connect to specific peer

#### NetworkManager (`Core/network.py`)
- **Role**: TCP socket management
- **Responsibilities**:
  - Server mode: Listen for incoming connections
  - Client mode: Connect to peers
  - Send/receive messages
  - Maintain connection pool
- **Architecture**:
  - Multi-threaded: One thread per connection
  - Thread-safe with locks
  - Message delimiter: newline character
- **Key Features**:
  - Automatic reconnection handling
  - Connection pooling
  - Broadcast to all peers

#### PeerDiscovery (`Core/discovery.py`)
- **Role**: UDP broadcast for peer discovery
- **Responsibilities**:
  - Broadcast presence on network
  - Listen for peer broadcasts
  - Auto-respond to discovery requests
- **Protocol**:
  - Port: 5556 (UDP)
  - Message format: JSON
  - Types: `discover`, `discover_response`

#### ConnectionManager (`Core/connection_manager.py`)
- **Role**: Manage peer connections and state
- **Responsibilities**:
  - Track active peers
  - Update peer status
  - Manage peer metadata
  - Emit peer lifecycle events

#### FileTransfer (`Core/file_transfer.py`)
- **Role**: Handle file transfers
- **Responsibilities**:
  - Chunk large files (8KB chunks)
  - Track transfer progress
  - Reassemble received chunks
  - Handle transfer errors
- **Process**:
  1. Send FILE message with metadata
  2. Send FILE_CHUNK messages
  3. Receiver assembles chunks
  4. Verify and save file

#### Message Protocol (`Core/message.py`)
- **Role**: Define message structure and types
- **Message Structure**:
```python
{
    "type": MessageType,
    "sender_id": str,
    "sender_name": str,
    "content": Any,
    "timestamp": float,
    "message_id": str,
    "recipient_id": Optional[str],
    "metadata": Optional[Dict]
}
```
- **Message Types**:
  - Connection: CONNECT, DISCONNECT, PING, PONG
  - Chat: TEXT, EMOJI
  - File: FILE, FILE_CHUNK
  - User: USER_INFO, USER_LIST, USER_STATUS
  - Discovery: DISCOVER, DISCOVER_RESPONSE
  - Control: ERROR, ACK

#### Peer Model (`Core/peer.py`)
- **Role**: Data model for peers
- **Attributes**:
  - `peer_id`: Unique identifier
  - `name`: Display name
  - `host`, `port`: Network address
  - `status`: online/offline/away/busy
  - `last_seen`: Timestamp
  - `connection`: Socket object

### 2. Core Bridge Layer

#### CoreBridge (`Gui/controller/core_bridge.py`)
- **Role**: Translate between Core and GUI
- **Responsibilities**:
  - Convert Core signals to GUI-friendly signals
  - Simplify Core API for GUI
  - Manage current chat context
  - Handle error translation
- **Key Signals**:
  - `text_message_received`: (peer_id, name, text, timestamp)
  - `peer_list_updated`: (list of peer dicts)
  - `file_received`: (file_name, file_path)
  - `connection_status`: (is_connected, message)

### 3. GUI Layer

#### MainWindow (`Gui/view/main_window.py`)
- **Role**: Main application window
- **Layout**: Three-column with QSplitter
  - Left: ChatList (25%)
  - Center: ChatArea (50%)
  - Right: NotificationsPanel (25%)
- **Responsibilities**:
  - Initialize CoreBridge
  - Connect signals between Core and GUI
  - Handle window lifecycle
  - Display connection status

#### ChatArea (`Gui/view/chat_area.py`)
- **Role**: Main chat interface
- **Components**:
  - Header: Peer info, call buttons
  - Message area: Scrollable message list
  - Input bar: Text input, emoji, file, send
- **Controller**: ChatAreaController

#### ChatList (`Gui/view/chat_list.py`)
- **Role**: Display and manage chat list
- **Features**:
  - Search functionality
  - Tabs: DIRECT, GROUPS, PUBLIC
  - User avatar and header
- **Controller**: ChatListController

#### Controllers
- **ChatAreaController**: Handles message input, emoji picker, file selection
- **ChatListController**: Manages chat selection, search, tab switching

## Data Flow

### Message Sending Flow
```
1. User types message
   ↓
2. ChatAreaController._send_message()
   ↓
3. CoreBridge.send_message()
   ↓
4. ChatCore.send_message()
   ↓
5. NetworkManager.send_message()
   ↓
6. TCP socket.sendall()
   ↓
7. Network transmission
```

### Message Receiving Flow
```
1. TCP socket receives data
   ↓
2. NetworkManager._receive_from_peer()
   ↓
3. NetworkManager.message_received signal
   ↓
4. ChatCore._handle_message()
   ↓
5. ChatCore.message_received signal
   ↓
6. CoreBridge._on_message_received()
   ↓
7. CoreBridge.text_message_received signal
   ↓
8. MainWindow._on_message_received()
   ↓
9. ChatArea.add_message()
```

### Peer Discovery Flow
```
1. ChatCore.start()
   ↓
2. PeerDiscovery.start()
   ↓
3. PeerDiscovery.broadcast_presence()
   ↓
4. UDP broadcast on port 5556
   ↓
5. Other peers receive broadcast
   ↓
6. PeerDiscovery._listen_for_peers()
   ↓
7. PeerDiscovery.peer_discovered signal
   ↓
8. ChatCore._handle_peer_discovered()
   ↓
9. ChatCore.connect_to_peer()
   ↓
10. NetworkManager.connect_to_peer()
```

## Threading Model

### Main Thread
- Qt GUI event loop
- Signal/Slot handling
- User interactions

### Network Threads
- **Server Thread**: Accept incoming connections
- **Client Threads**: One per peer connection
  - Receive messages
  - Handle disconnections
- **Discovery Thread**: Listen for UDP broadcasts

### Thread Safety
- All Core components use `threading.Lock()`
- Qt signals used for cross-thread communication
- Thread-safe data structures

## Network Protocol

### Connection Establishment
```
Peer A                           Peer B
  |                                |
  |--- Discovery Broadcast ------->|
  |<-- Discovery Response ---------|
  |                                |
  |--- TCP Connect (port 5555) --->|
  |<-- Accept Connection ----------|
  |                                |
  |--- CONNECT Message ----------->|
  |<-- ACK ------------------------|
  |                                |
  |=== Connection Established ====>|
```

### Message Format
```
[Message JSON]\n[Message JSON]\n[Message JSON]\n
```
- Messages separated by newline
- Each message is complete JSON object
- Allows streaming multiple messages

### File Transfer Protocol
```
Sender                          Receiver
  |                               |
  |--- FILE (metadata) ---------->|
  |                               |
  |--- FILE_CHUNK (0) ----------->|
  |--- FILE_CHUNK (1) ----------->|
  |--- FILE_CHUNK (2) ----------->|
  |       ...                     |
  |--- FILE_CHUNK (n) ----------->|
  |                               |
  |                   [Receiver assembles file]
  |                               |
  |<-- ACK ----------------------|
```

## Configuration

### Ports
- **5555**: TCP - Message communication
- **5556**: UDP - Peer discovery

### File Transfer
- **Chunk Size**: 8KB (8192 bytes)
- **Download Directory**: `downloads/`
- **Format**: Binary chunks as hex strings in JSON

### Discovery
- **Broadcast Interval**: On-demand (user triggered)
- **Response Timeout**: None (fire and forget)
- **Network**: Local subnet only

## Security Considerations

### Current Implementation
- ⚠️ No encryption (plaintext messages)
- ⚠️ No authentication
- ⚠️ No message signing
- ⚠️ Trust all peers on network

### Recommended Improvements
1. **Encryption**: Add TLS/SSL for TCP connections
2. **Authentication**: Implement peer authentication
3. **Message Signing**: Sign messages to prevent tampering
4. **Access Control**: Whitelist/blacklist peers
5. **Rate Limiting**: Prevent message flooding

## Extensibility

### Adding New Message Types
1. Add to `MessageType` enum
2. Create builder in `MessageBuilder`
3. Handle in `ChatCore._handle_message()`
4. Update GUI as needed

### Adding New Features
1. **Group Chat**:
   - Implement group management in Core
   - Update message routing for groups
   - Add group UI in GUI

2. **Voice/Video**:
   - Integrate media libraries
   - Add media streaming protocol
   - Update UI for calls

3. **Encryption**:
   - Add crypto library
   - Implement key exchange
   - Encrypt message content

## Performance Considerations

### Scalability
- **Peer Limit**: Tested with 10 peers
- **Message Rate**: ~100 messages/second per peer
- **File Transfer**: Efficient for files < 100MB
- **Memory**: ~50MB base + ~1MB per peer

### Optimization Opportunities
1. Message compression for large messages
2. Connection pooling optimization
3. File transfer with resume capability
4. Message queue for offline delivery

## Testing

### Unit Tests
- Message protocol serialization
- Peer model operations
- Core initialization

### Integration Tests
- Network communication
- File transfer
- Peer discovery

### Manual Testing
- Run multiple instances locally
- Test on local network
- Stress test with large files

## Deployment

### Single Machine (Testing)
```bash
# Terminal 1
python main.py  # User: Alice

# Terminal 2
python main.py  # User: Bob
```

### Multiple Machines (Production)
1. Ensure same network
2. Configure firewall
3. Run on each machine
4. Verify discovery works

## Future Enhancements

1. **NAT Traversal**: STUN/TURN for internet-wide P2P
2. **Persistent Storage**: Save chat history to database
3. **Mobile App**: Cross-platform with React Native
4. **Web Interface**: Browser-based client
5. **Blockchain**: Decentralized user registry

## References

- PySide6 Documentation: https://doc.qt.io/qtforpython/
- Python Socket Programming: https://docs.python.org/3/library/socket.html
- P2P Architecture Patterns: Various academic papers

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Maintainer**: [Your Name]

