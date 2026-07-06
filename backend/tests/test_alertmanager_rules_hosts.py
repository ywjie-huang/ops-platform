import asyncio

from app.services import alertmanager


class _FakeQueryResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"status": "success", "data": {"result": []}}


class _FakeAsyncClient:
    def __init__(self, queries: list[str], *args, **kwargs):
        self._queries = queries

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, params=None):
        self._queries.append(params["query"])
        return _FakeQueryResponse()


def test_get_rules_hosts_queries_only_requested_rule_names(monkeypatch):
    queries: list[str] = []
    alertmanager._rules_hosts_cache = {}
    alertmanager._rules_hosts_cache_ts = 0

    async def fake_get_rules(db=None):
        return [
            {"name": "cpu-high", "query": "cpu_query"},
            {"name": "memory-high", "query": "memory_query"},
        ]

    async def fake_discover_instances(prom_url=""):
        return {}

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(queries, *args, **kwargs)

    monkeypatch.setattr(alertmanager, "get_rules", fake_get_rules)
    monkeypatch.setattr("app.services.prometheus.discover_instances", fake_discover_instances)
    monkeypatch.setattr(alertmanager.httpx, "AsyncClient", fake_async_client)

    result = asyncio.run(alertmanager.get_rules_hosts(rule_names=["cpu-high"]))

    assert queries == ["cpu_query"]
    assert result == {"cpu-high": []}
