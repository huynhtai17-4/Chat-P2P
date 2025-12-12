from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

@dataclass
class PeerInfo:
    peer_id: str
    display_name: str
    ip: str
    tcp_port: int
    status: str = "offline"
    avatar_path: str = None

    def to_dict(self) -> Dict:
        return {
            "peer_id": self.peer_id,
            "display_name": self.display_name,
            "ip": self.ip,
            "tcp_port": self.tcp_port,
            "avatar_path": self.avatar_path,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PeerInfo":
        return cls(
            peer_id=data.get("peer_id", ""),
            display_name=data.get("display_name", "Unknown"),
            ip=data.get("ip", ""),
            tcp_port=data.get("tcp_port", 0),
            status="offline",
            avatar_path=data.get("avatar_path"),
        )
