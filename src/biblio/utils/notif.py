import asyncio
import logging
import os
import textwrap

import aiofiles
from telegram import Bot

from src.biblio.db.fetch import fetch_all_user_chat_ids

NOTIF = textwrap.dedent(
    """
    📦🛠️ *Bot updated*
    - User agreement updated.
    - Performance enhanced.
    Please use /start again!
    """
)


async def notify_on_deploy(bot: Bot) -> None:
    current_id = os.environ.get('RAILWAY_DEPLOYMENT_ID')
    cache_file = '.last_deploy_id'

    if not current_id:
        logging.info('[DEPLOY] Not running on Railway — no deployment ID found.')
        return

    last_id = None
    if os.path.exists(cache_file):
        async with aiofiles.open(cache_file, 'r') as f:
            last_id = (await f.read()).strip()

    if current_id == last_id:
        logging.info('[DEPLOY] No new deployment detected — skipping restart notification.')
        return

    async with aiofiles.open(cache_file, 'w') as f:
        await f.write(current_id)

    logging.info('[DEPLY] New Railway deployment detected — notifying users.')

    chat_ids = await fetch_all_user_chat_ids()
    tasks = [bot.send_message(chat_id=chat_id, text=NOTIF, parse_mode='Markdown') for chat_id in chat_ids]
    await asyncio.gather(*tasks)
