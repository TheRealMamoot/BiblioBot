import asyncio
import logging

from telegram.ext import Application

from src.biblio.app import build_app
from src.biblio.utils.parser import get_parser


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = get_parser()
    args = parser.parse_args()
    app: Application = build_app(token_env=args.token_env, priorities_env=args.priorities_env, db_env=args.db_env)
    await app.initialize()
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
