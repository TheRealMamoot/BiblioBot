from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import States
from src.biblio.utils.keyboards import Keyboard, Label

MAX_CONCURRENCY = 10


async def select_admin_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        is_admin = context.user_data.get("is_admin", False)
        await update.message.reply_text(
            "Sure thing!", reply_markup=Keyboard.reservation_type(is_admin=is_admin)
        )
        return States.RESERVE_TYPE

    elif user_input == Label.ADMIN_SEND_NOTIF:
        await update.message.reply_text(
            "please write the message",
            reply_markup=Keyboard.admin_notif(confirm_stage=False),
        )
        return States.ADMIN_NOTIF

    else:
        await update.message.reply_text(
            "Unknown command!",
            reply_markup=Keyboard.admin_panel(),
        )
        return States.ADMIN_PANEL
