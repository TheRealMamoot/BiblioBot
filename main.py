import asyncio
import os

import uvicorn
from telegram.ext import Application

from src.biblio.app import build_app
from src.biblio.config.config import get_parser, load_env
from src.biblio.config.logger import setup_logger
from src.biblio.db.build import build_db
from src.biblio.db.update import sync_user_priorities
from src.biblio.server import users_server
from src.biblio.utils.notif import notify_deployment


async def start_server():
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(
        users_server,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def start_bot():
    setup_logger()
    parser = get_parser()
    args = parser.parse_args()
    load_env(args.env)
    app: Application = build_app()
    await build_db()
    await sync_user_priorities()
    await app.initialize()
    # await notify_deployment(app.bot) #! temporary
    await app.start()
    await app.updater.start_polling()
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


async def main():
    server_task = asyncio.create_task(start_server())
    bot_task = asyncio.create_task(start_bot())
    await asyncio.gather(bot_task, server_task)


if __name__ == "__main__":
    asyncio.run(main())
