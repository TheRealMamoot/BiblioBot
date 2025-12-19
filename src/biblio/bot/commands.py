import textwrap

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.admin.maintenance import (
    block_user_activity,
    should_block,
)
from src.biblio.bot.messages import (
    show_donate_message,
    show_help,
    show_support_message,
    show_user_agreement,
)
from src.biblio.config.config import (
    DEFAULT_PRIORITY,
    State,
    UserDataKey,
    check_is_admin,
    get_priorities,
)
from src.biblio.db.fetch import fetch_existing_user
from src.biblio.utils.keyboards import Keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    chat_id = update.effective_chat.id
    username = user.username

    is_admin = check_is_admin(chat_id=chat_id)
    context.user_data[UserDataKey.IS_ADMIN] = is_admin

    if should_block(chat_id=chat_id):
        await block_user_activity(update, context)
        return State.MAINTENANCE

    existing_user = await fetch_existing_user(chat_id)

    if existing_user:
        user_id = existing_user["id"]
        codice: str = existing_user["codice_fiscale"]
        name = existing_user["name"]
        first_name = user.first_name if user.first_name else username
        email: str = existing_user["email"]
        message = textwrap.dedent(
            f"""
            Welcome back *{first_name}*!

            Proceed with current credentials?
            Codice Fiscale: *{codice}*
            Name: *{name}*
            Email: *{email}*
            """
        )
        priorities = get_priorities()
        context.user_data[UserDataKey.FIRST_NAME] = user.first_name
        context.user_data[UserDataKey.LAST_NAME] = user.last_name
        context.user_data[UserDataKey.ID] = user_id
        context.user_data[UserDataKey.USERNAME] = username
        context.user_data[UserDataKey.CODICE_FISCALE] = codice.upper()
        context.user_data[UserDataKey.NAME] = name
        context.user_data[UserDataKey.EMAIL] = email.lower()
        context.user_data[UserDataKey.PRIORITY] = int(
            priorities.get(codice.upper(), DEFAULT_PRIORITY)
        )

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=Keyboard.welcome_back(is_admin=is_admin),
        )
        return State.WELCOME_BACK

    context.user_data.clear()
    await update.message.reply_text(
        show_user_agreement(),
        parse_mode="Markdown",
        reply_markup=Keyboard.agreement(),
    )
    return State.AGREEMENT


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_help(), parse_mode="Markdown")


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_support_message(), parse_mode="Markdown")


async def agreement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_user_agreement(), parse_mode="Markdown")


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_donate_message(), parse_mode="Markdown")
