from app.services import k8s


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
