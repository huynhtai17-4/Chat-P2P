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
    last_seen: float
    status: str = "unknown"  # online/offline/unknown

    def touch(self, status: Optional[str] = None):
        self.last_seen = time.time()
        if status:
            self.status = status

    def to_dict(self) -> Dict:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "PeerInfo":
        return cls(**data)
