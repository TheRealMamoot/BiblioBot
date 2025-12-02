import asyncio
import os

from telegram import Bot

from src.biblio.config.config import get_parser, load_env
from src.biblio.config.logger import setup_logger
from src.biblio.db.build import build_db
from src.biblio.jobs import schedule_reserve_job


async def main():
    setup_logger()
    parser = get_parser()
    args = parser.parse_args()
    load_env(args.env)
    await build_db()
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    schedule_reserve_job(bot)
    await asyncio.Event().wait()  # keep loop alive


if __name__ == "__main__":
    asyncio.run(main())
