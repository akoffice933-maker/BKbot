import asyncio
import logging
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from statbet_bot.config import Config
from statbet_bot.handlers import register_handlers
from statbet_bot.database import Database
from statbet_bot.middleware import ErrorHandlerMiddleware, RateLimitMiddleware

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def main():
    bot: Bot | None = None
    db: Database | None = None

    try:
        # Load and validate configuration
        config = Config.load()
        logger.info("Configuration loaded successfully")

        # Initialize bot and dispatcher
        bot = Bot(token=config.telegram_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()

        # Register error handling middleware
        dp.message.middleware(ErrorHandlerMiddleware())
        dp.callback_query.middleware(ErrorHandlerMiddleware())

        # Register rate limiting middleware
        dp.message.middleware(RateLimitMiddleware())

        # Initialize database
        db = Database(config)
        await db.init()
        logger.info("Database initialized")

        # Inject db into all handlers via dispatcher workflow_data
        dp["db"] = db

        # Register handlers
        register_handlers(dp)

        # Setup graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start polling
        logger.info("Starting bot...")
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if db is not None:
            await db.close()
            logger.info("Database connections closed")
        if bot is not None:
            await bot.session.close()
            logger.info("Bot session closed")
        logger.info("Bot shutdown complete")


def entry_point():
    """Entry point for console_scripts (pip install)."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())

