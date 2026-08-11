from app.services import k8s


def test_empty_k8s_token_omits_authorization_header(monkeypatch):
    captured_headers = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"gitVersion": "v1.30.0"}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, headers):
            captured_headers.append(headers)
            return FakeResponse()

    monkeypatch.setattr(k8s.httpx, "Client", lambda **kwargs: FakeClient())

    result = k8s.test_connection("https://k8s.example.com", "  ")

    assert result["ok"] is True
    assert captured_headers == [{"Accept": "application/json"}]


def test_get_deployments_exposes_label_selector_for_pod_drilldown(monkeypatch):
    selector = {
        "matchLabels": {"app.kubernetes.io/name": "logstash"},
        "matchExpressions": [{"key": "tier", "operator": "In", "values": ["logging"]}],
    }

    def fake_get_list(endpoint, token, path):
        assert endpoint == "https://k8s.example.com"
        assert token == "secret-token"
        assert path == "/apis/apps/v1/deployments"
        return [{
            "metadata": {"name": "logstash", "namespace": "logging", "labels": {"app": "logging"}},
            "spec": {
                "replicas": 2,
                "selector": selector,
                "template": {"spec": {"containers": [{"image": "docker.elastic.co/logstash:8.0"}]}},
            },
            "status": {"readyReplicas": 2, "availableReplicas": 2},
        }]

    monkeypatch.setattr(k8s, "_get_list", fake_get_list)

    deployments = k8s.get_deployments("https://k8s.example.com", "secret-token")

    assert deployments[0]["selector"] == selector


def test_restarted_within_filters_old_restarts():
    """巡检「频繁重启」时间窗：93 天前的老重启不算近期，刚重启的才算。
    这是修复「93 天前重启 7 次永久标记异常」bug 的核心断言。"""
    from datetime import timedelta
    from app.core.config import CHINA_TZ
    from app.services.patrol import _restarted_within
    from datetime import datetime

    now = datetime.now(CHINA_TZ)

    # 93 天前重启 → 不算近期
    old = (now - timedelta(days=93)).isoformat()
    assert _restarted_within(old, now, hours=24) is False

    # 2 小时前重启 → 算近期
    recent = (now - timedelta(hours=2)).isoformat()
    assert _restarted_within(recent, now, hours=24) is True

    # 刚好 24 小时前 → 算近期（边界包含）
    boundary = (now - timedelta(hours=24, seconds=-1)).isoformat()
    assert _restarted_within(boundary, now, hours=24) is True

    # 25 小时前 → 不算
    over = (now - timedelta(hours=25)).isoformat()
    assert _restarted_within(over, now, hours=24) is False

    # 无时间戳（但 restarts>0，无法判断）→ 保守返回 True，避免漏报
    assert _restarted_within("", now, hours=24) is True

    # 非法时间戳 → 保守返回 True
    assert _restarted_within("not-a-date", now, hours=24) is True


def test_pod_data_includes_last_restart_at(monkeypatch):
    """k8s Pod 数据应提取 lastState.terminated.finishedAt 作为 last_restart_at。"""
    def fake_get_list(endpoint, token, path):
        assert path == "/api/v1/pods"
        return [{
            "metadata": {"name": "api-pod", "namespace": "prod"},
            "spec": {"nodeName": "node-1", "containers": [{"image": "app:v1"}]},
            "status": {
                "phase": "Running",
                "containerStatuses": [{
                    "restartCount": 7,
                    "lastState": {"terminated": {"finishedAt": "2026-05-10T03:20:00Z"}},
                    "ready": True,
                    "state": {"running": {}},
                }],
            },
        }]

    monkeypatch.setattr(k8s, "_get_list", fake_get_list)

    pods = k8s.get_pods("https://k8s.example.com", "token")
    assert len(pods) == 1
    assert pods[0]["restarts"] == 7
    assert pods[0]["last_restart_at"] == "2026-05-10T03:20:00Z"
