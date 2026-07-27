import asyncio
from collections import Counter

import httpx

from app.services import prometheus


class _FakeAsyncClient:
    active = 0
    max_active = 0
    calls: Counter[str] = Counter()

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, params):
        query = str(params["query"])
        self.calls[query] += 1
        type(self).active += 1
        type(self).max_active = max(type(self).max_active, type(self).active)
        try:
            await asyncio.sleep(0)
        finally:
            type(self).active -= 1

        request = httpx.Request("GET", url)
        if self.calls[query] == 1:
            return httpx.Response(502, request=request)
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {"resultType": "vector", "result": []},
            },
            request=request,
        )


def test_query_batch_limits_concurrency_and_retries_gateway_errors(monkeypatch):
    _FakeAsyncClient.active = 0
    _FakeAsyncClient.max_active = 0
    _FakeAsyncClient.calls = Counter()
    monkeypatch.setattr(prometheus.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(prometheus, "_RETRY_BACKOFF_SECONDS", 0)

    expressions = {f"metric_{index}": f"up_{index}" for index in range(20)}
    result = asyncio.run(prometheus._query_batch(expressions, "http://prometheus"))

    assert set(result) == set(expressions)
    assert all(count == 2 for count in _FakeAsyncClient.calls.values())
    assert _FakeAsyncClient.max_active <= prometheus._QUERY_CONCURRENCY


def test_query_batch_groups_final_failures_into_one_log(monkeypatch, caplog):
    class AlwaysFailClient(_FakeAsyncClient):
        async def get(self, url, params):
            type(self).calls[str(params["query"])] += 1
            request = httpx.Request("GET", url)
            return httpx.Response(502, request=request)

    AlwaysFailClient.calls = Counter()
    monkeypatch.setattr(prometheus.httpx, "AsyncClient", AlwaysFailClient)
    monkeypatch.setattr(prometheus, "_RETRY_BACKOFF_SECONDS", 0)

    with caplog.at_level("WARNING"):
        result = asyncio.run(
            prometheus._query_batch(
                {"cpu": "up", "memory": "up", "disk": "up"},
                "http://prometheus",
            )
        )

    assert set(result) == {"cpu", "memory", "disk"}
    assert len(caplog.records) == 1
    assert "3/3 failures" in caplog.records[0].message
