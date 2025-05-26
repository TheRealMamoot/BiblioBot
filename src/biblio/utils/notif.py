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

    *Hello everyone*

    Today we experienced very poor and slow service from the library. This also affected the bot, and many people couldn’t book a slot.  
    I’ve made some changes and I hope we won’t face issues this severe again — though at some point, it’s out of my hands.  
    Anyway, the bot is working now, and you can use it *(cautiously!)* 😁

    *Bot Lord*
    ---------
    *سلام به همگی*

    امروز شاهد سرویس بسیار بد و کند کتابخونه بودیم.
    این مورد روی بات هم تاثیر خودشو گذاشت و خیلیا نتوسنتن وقت بگیرن.  
    مواردیو تغییر دادم و امیدوارم دیگه به این شدت با مشکل مواجه نشیم، هرچند از یه جایی به بعد دیگه دست من نیست.  
    به هر حال بات کار میکنه و میتونید با *احتیاط*! ازش استفاده کنید 😁

    *صاب بات*
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
