import asyncio
import logging
import os
import textwrap

import aiofiles
from telegram import Bot

from src.biblio.db.fetch import fetch_all_user_chat_ids

DEPLOY_NOTIF = textwrap.dedent(
    """
    📦🛠️ *Bot updated*
    Please press /start 
    """
)

REMINDER = textwrap.dedent(
    """
    *⏱️ Don't forget to book! ⏱️*
    You will have a much better chance if you schedule in advance.
    Don't leave it for tommorow. 
    Do it...*NOW*! 🥸
    """
)


async def notify_deployment(bot: Bot) -> None:
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
    tasks = [bot.send_message(chat_id=chat_id, text=DEPLOY_NOTIF, parse_mode='Markdown') for chat_id in chat_ids]
    await asyncio.gather(*tasks)


async def notify_reminder(bot: Bot) -> None:
    chat_ids = await fetch_all_user_chat_ids()
    tasks = [bot.send_message(chat_id=chat_id, text=REMINDER, parse_mode='Markdown') for chat_id in chat_ids]
    await asyncio.gather(*tasks)
