import logging
import os

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from src.biblio.admin.railway import redeploy_service
from src.biblio.config.config import State, UserDataKey, check_is_admin
from src.biblio.db.fetch import fetch_setting
from src.biblio.db.update import upsert_setting
from src.biblio.utils.keyboards import Keyboard, Label
from src.biblio.utils.notif import notify_maintenance

MAINTENANCE_MESSAGE = (
    "*🚧 Bot is not available at the moment. Please try again later. 🚧*"
)


async def is_maintenance_enabled() -> bool:
    setting = await fetch_setting("maintenance")
    if setting is None:
        return False
    return str(setting).lower() in {"1", "true", "yes", "on"}


async def should_block(chat_id: str | int) -> bool:
    if not await is_maintenance_enabled():
        return False

    if chat_id is not None and check_is_admin(chat_id=chat_id):
        return False

    return True


async def block_user_activity(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.message.reply_text(
        MAINTENANCE_MESSAGE,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return State.MAINTENANCE


async def maintenance_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None)

    if not await should_block(chat_id=chat_id):
        return False

    if update.message:
        await update.message.reply_text(
            MAINTENANCE_MESSAGE,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    raise ApplicationHandlerStop


async def set_maintenance(value: str) -> None:
    await upsert_setting("maintenance", value)


async def toggle_maintenance_mode(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None | int:
    if not context.user_data.get(UserDataKey.IS_ADMIN, False):
        return

    admin_input = update.message.text.strip()

    old_mode = await is_maintenance_enabled()
    new_mode = not old_mode
    new_status = "ON" if new_mode else "OFF"

    if admin_input == Label.CONFIRM_NO:
        await update.message.reply_text(
            "Sure thing!", reply_markup=Keyboard.admin_panel()
        )
        return State.ADMIN_PANEL

    elif admin_input == Label.CONFIRM_YES:
        await upsert_setting("maintenance", str(new_mode))
        await update.message.reply_text(
            f"Maintenance mode turned *{new_status}*!",
            reply_markup=Keyboard.admin_panel(),
            parse_mode="Markdown",
        )
        try:
            env = (os.getenv("ENV") or "staging").lower()
            bot_ok = await redeploy_service("BiblioBot")
            other_service = "Reservation Job" if env == "staging" else "Reservation"
            await redeploy_service(other_service)
            if bot_ok:
                try:
                    await notify_maintenance(context.bot, enabled=new_mode)
                except Exception as e:
                    logging.error(f"[MAINTENANCE] Notify failed: {e}")
                await update.message.reply_text(
                    "Maintenance notification sent (redeploy OK).",
                    reply_markup=Keyboard.admin_panel(),
                )
            else:
                logging.error(
                    "[MAINTENANCE] BiblioBot redeploy failed — skipping notify."
                )
                await update.message.reply_text(
                    "Maintenance redeploy failed — notification skipped.",
                    reply_markup=Keyboard.admin_panel(),
                )
            return State.ADMIN_PANEL
        except Exception as e:
            logging.error(f"[MAINTENANCE] Redeploy failed: {e}")
            await update.message.reply_text(
                "Maintenance redeploy failed — notification skipped.",
                reply_markup=Keyboard.admin_panel(),
            )
