import app.db.redis as redis_store


def test_failed_connection_is_cached_until_retry_window(monkeypatch):
    attempts = []
    now = [100.0]

    class FailingClient:
        def ping(self):
            attempts.append("ping")
            raise TimeoutError("Redis is down")

    monkeypatch.setattr(redis_store.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(redis_store.redis, "ConnectionPool", lambda **kwargs: attempts.append(kwargs))
    monkeypatch.setattr(redis_store.redis, "Redis", lambda connection_pool: FailingClient())
    monkeypatch.setattr(redis_store, "_RETRY_INTERVAL", 30.0)
    redis_store.reset_redis()

    assert redis_store.get_redis() is None
    assert redis_store.get_redis() is None
    assert len([item for item in attempts if item == "ping"]) == 1
    assert attempts[0]["socket_connect_timeout"] == 0.5

    now[0] += 31
    assert redis_store.get_redis() is None
    assert len([item for item in attempts if item == "ping"]) == 2


def test_successful_connection_is_reused(monkeypatch):
    clients = []

    class HealthyClient:
        def ping(self):
            clients.append(self)

        def close(self):
            pass

    client = HealthyClient()
    monkeypatch.setattr(redis_store.redis, "ConnectionPool", lambda **kwargs: object())
    monkeypatch.setattr(redis_store.redis, "Redis", lambda connection_pool: client)
    redis_store.reset_redis()

    assert redis_store.get_redis() is client
    assert redis_store.get_redis() is client
    assert clients == [client]

