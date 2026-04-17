import asyncpg
import redis.asyncio as redis
from statbet_bot.config import Config


class Database:
    REQUIRED_TABLES = ("users", "matches", "predictions", "virtual_bets")

    def __init__(self, config: Config):
        self.config = config
        self.pool: asyncpg.Pool = None
        self.redis: redis.Redis = None

    async def init(self):
        """Initialize database connections and verify migrated schema."""
        self.pool = await asyncpg.create_pool(self.config.database_url)
        self.redis = redis.from_url(self.config.redis_url)
        await self._verify_schema()

    async def _verify_schema(self):
        """Fail fast when required tables have not been created by Alembic."""
        missing_tables: list[str] = []

        async with self.pool.acquire() as conn:
            for table_name in self.REQUIRED_TABLES:
                regclass = await conn.fetchval("SELECT to_regclass($1)", f"public.{table_name}")
                if regclass is None:
                    missing_tables.append(table_name)

        if missing_tables:
            formatted = ", ".join(missing_tables)
            raise RuntimeError(
                "Database schema is not initialized. "
                f"Missing tables: {formatted}. Run 'alembic upgrade head' before starting the bot."
            )

    async def close(self):
        if self.pool:
            await self.pool.close()
        if self.redis:
            await self.redis.close()
