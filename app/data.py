from app.models.dashboard import AlertSummary, AssetSummary, DashboardStats, TicketSummary

DASHBOARD_STATS = DashboardStats(
    asset_total=128,
    online_hosts=121,
    open_alerts=7,
    pending_tickets=12,
)

ASSETS = [
    AssetSummary("web-prod-01", "云主机", "平台组", "在线", "10.10.1.12"),
    AssetSummary("db-prod-01", "数据库", "DBA", "在线", "10.10.1.21"),
    AssetSummary("waf-gateway", "网络设备", "安全组", "维护中", "10.10.1.2"),
]

ALERTS = [
    AlertSummary("CPU 使用率过高", "高", "web-prod-01", "处理中"),
    AlertSummary("磁盘空间不足", "中", "db-prod-01", "待确认"),
    AlertSummary("证书 7 天后到期", "低", "api.example.com", "未处理"),
]

TICKETS = [
    TicketSummary("新增监控项", "张三", "普通", "处理中"),
    TicketSummary("数据库慢查询排查", "李四", "高", "待处理"),
    TicketSummary("证书续期", "王五", "紧急", "已创建"),
]
