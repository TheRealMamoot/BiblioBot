import textwrap

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import show_help, show_support_message, show_user_agreement
from src.biblio.config.config import States
from src.biblio.db.fetch import fetch_existing_user
from src.biblio.utils.keyboards import generate_agreement_keyboard, generate_welcome_back_keyboard
from src.biblio.utils.utils import get_priorities


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    username = user.username
    if not username:
        return States.AGREEMENT

    existing_user = await fetch_existing_user(username)

    if existing_user:
        user_id = existing_user['id']
        codice: str = existing_user['codice_fiscale']
        name = existing_user['name']
        email = existing_user['email']
        name = user.first_name if user.first_name else username
        message = textwrap.dedent(
            f"""
            Welcome back *{name}*!

            Proceed with current credentials?
            Codice Fiscale: *{codice}*
            Name: *{name}*
            Email: *{email}*
            """
        )
        priorities = get_priorities()
        context.user_data['user_firstname'] = user.first_name
        context.user_data['user_lastname'] = user.last_name
        context.user_data['user_id'] = user_id
        context.user_data['username'] = username
        context.user_data['codice_fiscale'] = codice.upper()
        context.user_data['name'] = name.lower()
        context.user_data['email'] = email
        context.user_data['priority'] = int(priorities.get(codice.upper(), 2))

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=generate_welcome_back_keyboard(),
        )
        return States.WELCOME_BACK

    context.user_data.clear()
    await update.message.reply_text(
        show_user_agreement(),
        parse_mode='Markdown',
        reply_markup=generate_agreement_keyboard(),
    )
    return States.AGREEMENT


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_help(), parse_mode='Markdown')


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_support_message(), parse_mode='Markdown')


async def agreement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_user_agreement(), parse_mode='Markdown')
