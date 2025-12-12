from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Dict

@dataclass
class Message:

    message_id: str
    sender_id: str
    sender_name: str
    receiver_id: str
    content: str
    timestamp: float
    msg_type: str = "text"
    file_name: str = None
    file_data: str = None
    audio_data: str = None
    video_data: str = None

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(**data)

    @classmethod
    def from_json(cls, payload: str) -> "Message":
        return cls.from_dict(json.loads(payload))

    @classmethod
    def create(cls, sender_id: str, sender_name: str, receiver_id: str, content: str, 
               msg_type: str = "text", file_name: str = None, file_data: str = None, 
               audio_data: str = None) -> "Message":
        return cls(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content=content,
            timestamp=time.time(),
            msg_type=msg_type,
            file_name=file_name,
            file_data=file_data,
            audio_data=audio_data,
        )
    
    @classmethod
    def create_friend_request(cls, sender_id: str, sender_name: str, receiver_id: str, tcp_port: int = 0) -> "Message":
        import json
        content_data = {
            "tcp_port": tcp_port
        }
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content=json.dumps(content_data),
            msg_type="FRIEND_REQUEST",
        )
    
    @classmethod
    def create_friend_accept(cls, sender_id: str, sender_name: str, receiver_id: str) -> "Message":
        
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content="FRIEND_ACCEPT",
            msg_type="FRIEND_ACCEPT",
        )
    
    @classmethod
    def create_friend_reject(cls, sender_id: str, sender_name: str, receiver_id: str) -> "Message":
        
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content="FRIEND_REJECT",
            msg_type="FRIEND_REJECT",
        )
    
    @classmethod
    def create_friend_sync(cls, sender_id: str, sender_name: str, receiver_id: str, 
                          peer_ip: str, peer_tcp_port: int) -> "Message":
        
        import json
        sync_data = {
            "peer_id": sender_id,
            "display_name": sender_name,
            "ip": peer_ip,
            "tcp_port": peer_tcp_port
        }
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content=json.dumps(sync_data),
            msg_type="FRIEND_SYNC",
        )
    
    @classmethod
    def create_online_status(cls, sender_id: str, sender_name: str, receiver_id: str, avatar_base64: str = None) -> "Message":
        
        content_data = {"status": "ONLINE"}
        if avatar_base64:
            content_data["avatar_base64"] = avatar_base64
        
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content=json.dumps(content_data),
            msg_type="ONLINE",
        )
    
    @classmethod
    def create_offline_status(cls, sender_id: str, sender_name: str, receiver_id: str) -> "Message":
        
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content="OFFLINE",
            msg_type="OFFLINE",
        )
    
    @classmethod
    def create_hello(cls, sender_id: str, sender_name: str, receiver_id: str, tcp_port: int = 0, sender_ip: str = "") -> "Message":
        import json
        content_data = {
            "tcp_port": tcp_port,
            "sender_ip": sender_ip
        }
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content=json.dumps(content_data),
            msg_type="HELLO",
        )
    
    @classmethod
    def create_hello_reply(cls, sender_id: str, sender_name: str, receiver_id: str, 
                          peer_ip: str, peer_tcp_port: int) -> "Message":
        import json
        reply_data = {
            "peer_id": sender_id,
            "display_name": sender_name,
            "ip": peer_ip,
            "tcp_port": peer_tcp_port
        }
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content=json.dumps(reply_data),
            msg_type="HELLO_REPLY",
        )
    
    @classmethod
    def create_call_request(cls, sender_id: str, sender_name: str, receiver_id: str,
                           call_type: str, audio_port: int, video_port: int = 0) -> "Message":
        import json
        call_data = {
            "call_type": call_type,
            "audio_port": audio_port,
            "video_port": video_port
        }
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content=json.dumps(call_data),
            msg_type="CALL_REQUEST",
        )
    
    @classmethod
    def create_call_accept(cls, sender_id: str, sender_name: str, receiver_id: str,
                          audio_port: int, video_port: int = 0) -> "Message":
        import json
        accept_data = {
            "audio_port": audio_port,
            "video_port": video_port
        }
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content=json.dumps(accept_data),
            msg_type="CALL_ACCEPT",
        )
    
    @classmethod
    def create_call_reject(cls, sender_id: str, sender_name: str, receiver_id: str) -> "Message":
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content="CALL_REJECT",
            msg_type="CALL_REJECT",
        )
    
    @classmethod
    def create_call_end(cls, sender_id: str, sender_name: str, receiver_id: str) -> "Message":
        return cls.create(
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            content="CALL_END",
            msg_type="CALL_END",
        )
