import asyncio
import logging
import os
import textwrap
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import aiofiles
from telegram import Bot
from telegram.error import Forbidden, TelegramError

from src.biblio.config.config import Status
from src.biblio.db.fetch import (
    fetch_all_user_chat_ids,
    fetch_reservations,
    fetch_setting,
)

DEPLOY_NOTIF = textwrap.dedent(
    """
    📦🛠️ *Bot Updated!*
    
    👉 *Please use /start again to refresh your session.*
    """
)

MAINTENANCE_ON_NOTIF = textwrap.dedent(
    """
    🚧 *Maintenance Enabled*

    The bot is temporarily on hold while maintenance is in progress.
    Please check back later.
    """
)

MAINTENANCE_OFF_NOTIF = textwrap.dedent(
    """
    ✅ *Maintenance Disabled*

    The bot is back *online*.
    👉 *Please use /start to continue.*
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

DONATION_NOTIF = textwrap.dedent(
    """سلام به همگی 👋
برای توسعه و نگهداری این پروژه، هم *هزینه* و هم از اون مهم‌تر، *زمان زیادی* صرف شده تا بتونه به بهترین شکل کار کنه. اگر این بات یه بخش *خیلی کوچیک* از دغدغه‌هاتون رو برطرف کرده، خوشحال می‌شم اگر از طریق لینک‌های زیر دونیت کنین:
🔗 [Revolut/mamoot](https://revolut.me/mamoot)  
🔗 [PayPal/TheRealMamoot](https://www.paypal.com/paypalme/TheRealMamoot)

کمک شما هم باعث *دلگرمیه*، هم باعث میشه با *انرژی بیشتری* روی کیفیت بات کار کنم.  
اگه اکانت GitHub دارید، ممنون می‌شم اگه ریپوی بات رو *استار* کنید: 
🌟 [GitHub/TheRealMamoot](https://github.com/TheRealMamoot/BiblioBot)

*مرسی از حمایت‌تون!* 🙏

P.S. *English version above ❗️*
    """
)

DONATION_NOTIF_ENG = textwrap.dedent(
    """
    Hello everyone 👋  

    A lot of *time* — and *money* — has gone into developing and maintaining this project to make it work as well as possible.  
    If this bot has helped solve *even a small part* of your daily hassle, I’d really appreciate a donation via the links below:

    🔗 [Revolut/mamoot](https://revolut.me/mamoot)  
    🔗 [PayPal/TheRealMamoot](https://www.paypal.com/paypalme/TheRealMamoot)

    Your support not only boosts morale, but also motivates me to invest *even more energy* into improving the bot.  

    And if you have a GitHub account, I’d be super grateful if you could *star the repo*:  

    🌟 [GitHub/TheRealMamoot](https://github.com/TheRealMamoot/BiblioBot)

    *Thanks a lot for your support!* 🙏
    """
)


async def _safe_notify(bot: Bot, chat_id: int, text: str, context: str) -> None:
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Forbidden:
        logging.warning(
            f"[{context.upper()}] Bot was blocked by user {chat_id}, skipping."
        )
    except TelegramError as e:
        logging.error(f"[{context.upper()}] Failed to notify {chat_id}: {e}")


async def notify_deployment(bot: Bot) -> None:
    maintenance = await fetch_setting("maintenance")
    if maintenance is not None and str(maintenance).lower() in {"1", "true", "yes", "on"}:
        logging.info("[DEPLOY] Maintenance enabled — skipping deployment notification.")
        return

    current_id = os.environ.get("RAILWAY_DEPLOYMENT_ID")
    cache_file = ".last_deploy_id"

    if not current_id:
        logging.info("[DEPLOY] Not running on Railway — no deployment ID found.")
        return

    last_id = None
    if os.path.exists(cache_file):
        async with aiofiles.open(cache_file, "r") as f:
            last_id = (await f.read()).strip()

    if current_id == last_id:
        logging.info(
            "[DEPLOY] No new deployment detected — skipping restart notification."
        )
        return

    async with aiofiles.open(cache_file, "w") as f:
        await f.write(current_id)

    logging.info("[DEPLOY] New Railway deployment detected — notifying users.")

    chat_ids = await fetch_all_user_chat_ids()
    tasks = [
        _safe_notify(bot=bot, chat_id=chat_id, text=DEPLOY_NOTIF, context="deploy")
        for chat_id in chat_ids
    ]
    await asyncio.gather(*tasks)


async def notify_maintenance(bot: Bot, enabled: bool) -> None:
    text = MAINTENANCE_ON_NOTIF if enabled else MAINTENANCE_OFF_NOTIF
    state = "enabled" if enabled else "disabled"
    logging.info(f"[MAINTENANCE] Notifying users: maintenance {state}.")

    chat_ids = await fetch_all_user_chat_ids()
    tasks = [
        _safe_notify(bot=bot, chat_id=chat_id, text=text, context="maintenance")
        for chat_id in chat_ids
    ]
    await asyncio.gather(*tasks)


async def notify_reminder(bot: Bot) -> None:
    tomorrow = datetime.now(ZoneInfo("Europe/Rome")) + timedelta(days=1)

    reservations = await fetch_reservations(
        statuses=[Status.PENDING], date=tomorrow.date()
    )
    all_chat_ids = await fetch_all_user_chat_ids()
    pending_chat_ids = [res["chat_id"] for res in reservations]
    to_notify_chat_ids = set(all_chat_ids) - set(pending_chat_ids)
    if not to_notify_chat_ids:
        logging.info("[NOTIF] No users to notify.")
        return

    tasks = [
        _safe_notify(bot=bot, chat_id=chat_id, text=REMINDER, context="deploy")
        for chat_id in to_notify_chat_ids
    ]
    await asyncio.gather(*tasks)
    logging.info(f"[NOTIF] Sent {len(tasks)} reminders for tomorrow")


async def notify_reservation_activation(bot: Bot) -> None:
    now = datetime.now(ZoneInfo("Europe/Rome"))
    reservations = await fetch_reservations(statuses=[Status.SUCCESS])

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
        start_time = reservation["start_time"]
        if start_time == past_time:
            reminders_to_send.append((reservation, past_time, "after"))
        elif (
            start_time == upcoming_time
        ):  # skip reminders for upcoming reservations for now
            continue
            reminders_to_send.append((reservation, upcoming_time, "before"))

    if not reminders_to_send:
        logging.info("[NOTIF] No matching reservations for reminder times.")
        return

    tasks = []
    for reservation, slot_time, phase in reminders_to_send:
        if phase == "before":  # Skip reminders for the "before" phase for now
            continue
            reminder = "🕒 *Reminder* 🕒"
            headline = f"Your reservation starts at *{slot_time.strftime('%H:%M')}*."
            activation_note = "_⚠️ Don’t forget to activate!_"
        else:
            reminder = "❗️🕒 *Reminder* 🕒❗️"
            headline = f"You have a reservation at *{slot_time.strftime('%H:%M')}*. Have you activated the slot ?"
            activation_note = "_⚠️ If not, you should do it now!_"

        start_str = (
            reservation["start_time"].strftime("%H:%M")
            if isinstance(reservation["start_time"], time)
            else reservation["start_time"]
        )
        end_str = (
            reservation["end_time"].strftime("%H:%M")
            if isinstance(reservation["end_time"], time)
            else reservation["end_time"]
        )

        message = textwrap.dedent(
            f"""
            {reminder}
            {headline}

            📄 *Details*
            Codice Fiscale: *{reservation["codice_fiscale"]}*
            Full Name: *{reservation["name"]}*
            From: *{start_str}* - *{end_str}* (*{reservation["selected_duration"]}* hours)
            Booking Code: *{(reservation["booking_code"]).upper()}*

            {activation_note}
            """
        )

        task = _safe_notify(
            bot=bot,
            chat_id=reservation["chat_id"],
            text=message,
            context="reminder",
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logging.error(
                f"[NOTIF] Error sending reminder to {reminders_to_send[i][0]['chat_id']}: {result}"
            )
        else:
            logging.info(
                f"[NOTIF] Sent reminder for chat_id {reminders_to_send[i][0]['chat_id']}"
            )


# TODO: Refactor w/ asyncio.gather
async def notify_donation(bot: Bot) -> None:
    chat_ids = await fetch_all_user_chat_ids()
    sent = 0
    for chat_id in chat_ids:
        if chat_id == os.getenv("BOTLORD_CHAT_ID"):
            continue
        try:
            await bot.send_message(
                chat_id=chat_id, text=DONATION_NOTIF_ENG, parse_mode="Markdown"
            )
            await bot.send_message(
                chat_id=chat_id, text=DONATION_NOTIF, parse_mode="Markdown"
            )
            sent += 1
        except Forbidden:
            logging.warning(f"[NOTIF] Bot was blocked by user {chat_id}, skipping.")
        except Exception as e:
            logging.error(f"[NOTIF] Failed to send to {chat_id}: {e}")

    logging.info(f"[NOTIF] Sent {sent} donation notifications.")
