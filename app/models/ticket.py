"""Ticket data model."""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Ticket:
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    priority: str = "normal"   # low / normal / high / critical
    status: str = "open"       # open / in_progress / resolved / closed
    assignee: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
