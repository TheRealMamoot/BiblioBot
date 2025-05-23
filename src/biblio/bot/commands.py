from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import show_help, show_support_message, show_user_agreement
from src.biblio.config.config import States
from src.biblio.utils.keyboards import generate_agreement_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.bot_data.setdefault('user_chat_ids', {})
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
