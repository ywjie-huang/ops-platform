from dataclasses import dataclass, field


@dataclass
class DashboardStats:
    asset_total: int
    online_hosts: int
    open_alerts: int
    pending_tickets: int
    user_total: int
    role_total: int
    offline_assets: int
    maintenance_assets: int
    user_growth_7d: int


@dataclass
class DashboardQuickStat:
    label: str
    value: str
    hint: str
    tone: str = "blue"


@dataclass
class DashboardActivityItem:
    title: str
    meta: str
    detail: str
    tag: str
    tone: str = "default"


@dataclass
class DashboardDistributionItem:
    label: str
    value: int
    tone: str = "neutral"


@dataclass
class DashboardTypeBreakdown:
    label: str
    value: int
    color: str = "#3b82f6"


@dataclass
class DashboardSummary:
    quick_stats: list[DashboardQuickStat]
    recent_asset_changes: list[DashboardActivityItem]
    recent_users: list[DashboardActivityItem]
    role_distribution: list[DashboardDistributionItem]
    type_breakdown: list[DashboardTypeBreakdown] = field(default_factory=list)
    max_type_value: int = 0
    recent_tickets: list[DashboardActivityItem] = field(default_factory=list)
    recent_alerts: list[DashboardActivityItem] = field(default_factory=list)


@dataclass
class NavItem:
    label: str
    href: str
    key: str
