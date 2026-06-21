import asyncio
import threading
import logging
import uvicorn
from database import init_db, seed_demo_data
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_admin():
    uvicorn.run("admin:app", host="0.0.0.0", port=8000, log_level="info")


async def run_bot():
    from bot import build_app
    app = build_app()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("Telegram bot is running...")
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


async def main():
    await init_db()
    await seed_demo_data()
    logger.info("Database initialized with demo data")

    admin_thread = threading.Thread(target=run_admin, daemon=True)
    admin_thread.start()
    logger.info("Admin dashboard running at http://localhost:8000")

    if BOT_TOKEN and BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        await run_bot()
    else:
        logger.info("No BOT_TOKEN set. Admin dashboard only mode.")
        logger.info("Set BOT_TOKEN environment variable to enable the Telegram bot.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    asyncio.run(main())
