import os

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.admin.maintenance import is_maintenance_enabled
from src.biblio.admin.railway import list_services
from src.biblio.config.config import State, UserDataKey
from src.biblio.utils.keyboards import Keyboard, Label

MAX_CONCURRENCY = 10


async def select_admin_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        is_admin = context.user_data.get(UserDataKey.IS_ADMIN, False)
        await update.message.reply_text(
            "Sure thing!", reply_markup=Keyboard.reservation_type(is_admin=is_admin)
        )
        return State.RESERVE_TYPE

    elif user_input == Label.ADMIN_SEND_NOTIF:
        await update.message.reply_text(
            "please write the message",
            reply_markup=Keyboard.admin_notif(confirm_stage=False),
        )
        return State.ADMIN_NOTIF

    elif user_input == Label.ADMIN_MANAGE_SERVICES:
        services = await list_services()
        context.user_data[UserDataKey.AMDMIN_SERVICES] = services
        await update.message.reply_text(
            "please choose a service.",
            reply_markup=Keyboard.admin_services(services, os.getenv("ENV")),
        )
        return State.ADMIN_MANAGE_SERVICES

    elif user_input == Label.ADMIN_SET_MAINTANANCE:
        old_mode = await is_maintenance_enabled()
        old_status = "ON" if old_mode else "OFF"
        new_status = "OFF" if old_mode else "ON"
        await update.message.reply_text(
            f"Maintenance is currently turned *{old_status}*. Proceed to turn it *{new_status}*?",
            reply_markup=Keyboard.confirmation(),
            parse_mode="Markdown",
        )
        return State.ADMIN_MAINTANANCE_CONFIRM

    else:
        await update.message.reply_text(
            "Unknown command!",
            reply_markup=Keyboard.admin_panel(),
        )
        return State.ADMIN_PANEL
