from dataclasses import dataclass


@dataclass
class DashboardStats:
    asset_total: int
    online_hosts: int
    open_alerts: int
    pending_tickets: int


@dataclass
class AssetSummary:
    name: str
    asset_type: str
    owner: str
    status: str
    ip_address: str


@dataclass
class AlertSummary:
    title: str
    severity: str
    source: str
    status: str


@dataclass
class TicketSummary:
    title: str
    assignee: str
    priority: str
    status: str
