import asyncio
import logging
import os
import textwrap
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import aiofiles
from telegram import Bot

from src.biblio.db.fetch import fetch_all_user_chat_ids, fetch_reservations

DEPLOY_NOTIF = textwrap.dedent(
    """
    📦🛠️ *Bot updated v2.0.2* 🎉

    ✅ Added *@BiblioSupport* for bug reports and suggestions. 
    You can now contact the _Bot Lord_ directly for any issues you encounter.

    ✅ Added *reminders* for reservations. 
    You will receive a notification *15 minutes* before and after your reservation starts, in case you forget to activate it.

    ✅ Bug fixes.

    Please use /start 
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


async def notify_reservation_activation(bot: Bot) -> None:
    now = datetime.now(ZoneInfo('Europe/Rome'))
    reservations = await fetch_reservations(statuses=['success'])

    # Determine reminder targets for "before" and "after" cases
    if now.minute == 15:
        past_time = now.replace(minute=0, second=0, microsecond=0).time()
        upcoming_time = now.replace(minute=30, second=0, microsecond=0).time()
    elif now.minute == 45:
        past_time = now.replace(minute=30, second=0, microsecond=0).time()
        next_hour = now + timedelta(hours=1)
        upcoming_time = next_hour.replace(minute=0, second=0, microsecond=0).time()
    else:
        return

    reminders_to_send = []
    for reservation in reservations:
        start_time = reservation['start_time']
        if start_time == past_time:
            reminders_to_send.append((reservation, past_time, 'after'))
        elif start_time == upcoming_time:
            reminders_to_send.append((reservation, upcoming_time, 'before'))

    if not reminders_to_send:
        logging.info('[NOTIF] No matching reservations for reminder times.')
        return

    tasks = []
    for reservation, slot_time, phase in reminders_to_send:
        if phase == 'before':
            reminder = '🕒 *Reminder* 🕒'
            headline = f'Your reservation starts at *{slot_time.strftime("%H:%M")}*.'
            activation_note = '_⚠️ Don’t forget to activate!_'
        else:
            reminder = '❗️ *Reminder* ❗️'
            headline = f'You should have activated your reservation at *{slot_time.strftime("%H:%M")}*.'
            activation_note = '_⚠️ If not, do it now!_'

        start_str = (
            reservation['start_time'].strftime('%H:%M')
            if isinstance(reservation['start_time'], time)
            else reservation['start_time']
        )
        end_str = (
            reservation['end_time'].strftime('%H:%M')
            if isinstance(reservation['end_time'], time)
            else reservation['end_time']
        )

        message = textwrap.dedent(
            f"""
            {reminder}
            {headline}

            📄 *Details*
            Codice Fiscale: *{reservation['codice_fiscale']}*
            Full Name: *{reservation['name']}*
            From: *{start_str}* - *{end_str}* (*{reservation['selected_duration']}* hours)
            Booking Code: *{(reservation['booking_code']).upper()}*

            {activation_note}
            """
        )

        task = bot.send_message(chat_id=reservation['chat_id'], text=message, parse_mode='Markdown')
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logging.error(f'[NOTIF] Error sending reminder to {reminders_to_send[i][0]["chat_id"]}: {result}')
        else:
            logging.info(f'[NOTIF] Sent reminder for chat_id {reminders_to_send[i][0]["chat_id"]}')
