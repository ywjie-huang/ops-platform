from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.alert_event import AlertEvent
from app.services.alertmanager import get_rule_event_stats


def _make_db():
    engine = create_engine("sqlite://")
    AlertEvent.__table__.create(engine)
    return Session(engine)


def _add_event(db, alert_name: str, days_ago: int, status: str = "firing"):
    db.add(AlertEvent(
        alert_name=alert_name,
        status=status,
        received_at=datetime.now() - timedelta(days=days_ago),
    ))


def test_rule_event_stats_aggregates_daily_counts():
    db = _make_db()
    _add_event(db, "cpu-high", 0)
    _add_event(db, "cpu-high", 0)
    _add_event(db, "cpu-high", 2)
    _add_event(db, "cpu-high", 8)   # 超出 7 天窗口，不计入
    _add_event(db, "other-rule", 0) # 其它规则，不计入

    stats = get_rule_event_stats(db, "cpu-high", days=7, recent=3)

    assert stats["total"] == 3
    assert len(stats["daily"]) == 7
    assert stats["daily"][-1]["count"] == 2  # 今天
    assert stats["daily"][-3]["count"] == 1  # 前天
    assert len(stats["recent"]) == 3
    assert all(e["status"] == "firing" for e in stats["recent"])


def test_rule_event_stats_empty_when_no_events():
    db = _make_db()
    stats = get_rule_event_stats(db, "nothing")
    assert stats["total"] == 0
    assert stats["recent"] == []
    assert all(d["count"] == 0 for d in stats["daily"])
