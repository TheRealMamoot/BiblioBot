import asyncio

from telegram.ext import Application

from src.biblio.app import build_app
from src.biblio.config.config import get_parser, load_env
from src.biblio.config.logger import setup_logger
from src.biblio.db.build import build_db
from src.biblio.utils.notif import notify_deployment


async def main():
    setup_logger()
    parser = get_parser()
    args = parser.parse_args()
    load_env(args.env)
    app: Application = build_app()
    await build_db()
    await app.initialize()
    await notify_deployment(app.bot)
    await app.start()
    await app.updater.start_polling()
    try:
        await asyncio.Event().wait()  # run forever
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
