from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hey! who or what do you think I am? 😑 use /start again if NOTHING is working.')


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Piano piano eh? use /start first.')


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update and hasattr(update, 'message'):
        await update.message.reply_text(
            '😵 Oops, something went wrong.\nTry /start to begin again.',
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove(),
        )
    print(f'Update {update} caused error {context.error}')
