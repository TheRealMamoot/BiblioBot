import os

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from src.biblio.config.config import State, check_is_admin

MAINTENANCE_MESSAGE = (
    "*🚧 Bot is not available at the moment. Please try again later. 🚧*"
)


def is_maintenance_enabled() -> bool:
    return os.getenv("MAINTENANCE_MODE", "").lower() in {"1", "true", "yes", "on"}


def should_block(chat_id: str | int) -> bool:
    if not is_maintenance_enabled():
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

    if not should_block(chat_id=chat_id):
        return

    if update.message:
        await update.message.reply_text(
            MAINTENANCE_MESSAGE,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    raise ApplicationHandlerStop
