import asyncio
import logging
import os
import textwrap

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import States
from src.biblio.db.fetch import fetch_all_user_chat_ids
from src.biblio.utils.keyboards import Keyboard, Label

MAX_CONCURRENCY = 10


async def _send_notification(
    client: httpx.AsyncClient,
    url: str,
    chat_id: int,
    notif: str,
    sem: asyncio.Semaphore,
):
    async with sem:
        try:
            resp = await client.post(
                url,
                data={"chat_id": chat_id, "text": notif, "parse_mode": "Markdown"},
                timeout=20,
            )
            resp.raise_for_status()
            return chat_id, None
        except Exception as exc:
            logging.warning("Push notif failed for chat_id=%s: %s", chat_id, exc)
            return chat_id, exc


async def prepare_notification(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        await update.message.reply_text(
            "Sure thing!", reply_markup=Keyboard.admin_panel()
        )
        return States.ADMIN_PANEL

    notif = textwrap.dedent(update.message.text)
    context.user_data["notification"] = notif

    await update.message.reply_text(
        f"*Preview:*\n\n{notif}",
        reply_markup=Keyboard.admin_notif(confirm_stage=True),
        parse_mode="Markdown",
    )
    return States.ADMIN_NOTIF_CONFIRM


async def push_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    notif = context.user_data["notification"]

    if user_input == Label.CONFIRM_NO:
        await update.message.reply_text(
            "Sure thing!", reply_markup=Keyboard.admin_notif()
        )
        return States.ADMIN_NOTIF

    elif user_input == Label.CONFIRM_YES:
        ids = await fetch_all_user_chat_ids()
        url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/sendMessage"

        ids = [
            chat_id for chat_id in ids if str(chat_id) != os.getenv("BOTLORD_CHAT_ID")
        ]

        if not ids:
            await update.message.reply_text(
                "No recipients found.", reply_markup=Keyboard.admin_panel()
            )
            return States.ADMIN_PANEL

        sem = asyncio.Semaphore(MAX_CONCURRENCY)
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *(
                    _send_notification(client, url, chat_id, notif, sem)
                    for chat_id in ids
                )
            )

        sent = sum(1 for _, err in results if err is None)
        failed_ids = [chat_id for chat_id, err in results if err is not None]

        failed_block = (
            "\nFailed ids:\n" + "\n".join(map(str, failed_ids)) if failed_ids else ""
        )

        await update.message.reply_text(
            f"Number of IDs: {len(ids) - 1}\nNotifications sent: *{sent}*\n*Failed*: {len(failed_ids)}"
            f"{failed_block}",
            reply_markup=Keyboard.admin_panel(),
            parse_mode="Markdown",
        )
        return States.ADMIN_PANEL

    else:
        await update.message.reply_text(
            "Unknown command!",
            reply_markup=Keyboard.admin_notif(confirm_stage=True),
        )
        return States.ADMIN_NOTIF_CONFIRM
