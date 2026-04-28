from dataclasses import dataclass


@dataclass
class DashboardStats:
    asset_total: int
    online_hosts: int
    open_alerts: int
    pending_tickets: int
