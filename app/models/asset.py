"""Asset data model."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Asset:
    id: Optional[int] = None
    name: str = ""
    type: str = ""          # server / container / domain / cert
    ip: str = ""
    status: str = "online"  # online / offline / unknown
    owner: str = ""
    tags: list = field(default_factory=list)
