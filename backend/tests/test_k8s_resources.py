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
