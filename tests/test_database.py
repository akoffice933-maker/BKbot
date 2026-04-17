import pytest

from statbet_bot.database import Database


class DummyConfig:
    database_url = "postgresql://user:password@localhost/statbet"
    redis_url = "redis://localhost:6379"


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, existing_tables: set[str]):
        self.existing_tables = existing_tables

    async def fetchval(self, _query: str, regclass_name: str):
        table_name = regclass_name.split(".", 1)[1]
        if table_name in self.existing_tables:
            return regclass_name
        return None


class FakePool:
    def __init__(self, existing_tables: set[str]):
        self.conn = FakeConnection(existing_tables)
        self.closed = False

    def acquire(self):
        return FakeAcquire(self.conn)

    async def close(self):
        self.closed = True


class FakeRedis:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_database_init_requires_existing_migrated_schema(monkeypatch):
    pool = FakePool(set(Database.REQUIRED_TABLES))
    redis_client = FakeRedis()

    async def fake_create_pool(url):
        assert url == DummyConfig.database_url
        return pool

    def fake_from_url(url):
        assert url == DummyConfig.redis_url
        return redis_client

    monkeypatch.setattr("statbet_bot.database.asyncpg.create_pool", fake_create_pool)
    monkeypatch.setattr("statbet_bot.database.redis.from_url", fake_from_url)

    db = Database(DummyConfig())
    await db.init()

    assert db.pool is pool
    assert db.redis is redis_client


@pytest.mark.asyncio
async def test_database_init_fails_when_schema_missing(monkeypatch):
    pool = FakePool({"users"})
    redis_client = FakeRedis()

    async def fake_create_pool(_url):
        return pool

    def fake_from_url(_url):
        return redis_client

    monkeypatch.setattr("statbet_bot.database.asyncpg.create_pool", fake_create_pool)
    monkeypatch.setattr("statbet_bot.database.redis.from_url", fake_from_url)

    db = Database(DummyConfig())

    with pytest.raises(RuntimeError, match="Run 'alembic upgrade head'"):
        await db.init()
