from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class PeerInfo:
    peer_id: str
    display_name: str
    ip: str
    tcp_port: int
    last_seen: float = 0.0  # retained for informational use only
    status: str = "offline"  # runtime-only; never persisted

    def touch(self, status: Optional[str] = None):
        self.last_seen = time.time()
        if status:
            self.status = status

    def to_dict(self) -> Dict:
        # Persist only non-status fields; status is runtime-only
        return {
            "peer_id": self.peer_id,
            "display_name": self.display_name,
            "ip": self.ip,
            "tcp_port": self.tcp_port,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PeerInfo":
        return cls(
            peer_id=data.get("peer_id", ""),
            display_name=data.get("display_name", "Unknown"),
            ip=data.get("ip", ""),
            tcp_port=data.get("tcp_port", 0),
            last_seen=data.get("last_seen", 0.0),
            status="offline",  # always start offline; will update on ONLINE event
        )
