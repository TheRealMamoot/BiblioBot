import textwrap

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import States
from src.biblio.utils.keyboards import generate_agreement_keyboard
from src.biblio.utils.utils import show_help, show_support_message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.bot_data.setdefault('user_chat_ids', {})
    await update.message.reply_text(
        textwrap.dedent(
            """
        *📄 User Agreement*
        *📣 Data Usage Notice*

        ❗ By using this bot, you agree to the collection and temporary storage of the following *data*:

        📌 Your *Telegram username*, *first name*, and *last name* (if available)
        📌 Your provided *Codice Fiscale*, *full name*, and *email address*
        📌 Your selected *reservation date*, *time*, and *duration* at Università degli Studi di Milano's Library of Biology, Computer Science, Chemistry and Physics (*BICF*)
        📌 The *status* of your reservation (*active* or *cancelled*) 
        📌 *General activity data*, including your *interactions* with the bot during the reservation process

        ❕ This data is used *exclusively* for making and managing *BICF reservations* more easily on your behalf.
        ❕ Your data is *never shared* with third parties and is used solely to assist with *reservation automation* and *troubleshooting*.

        🤝🏻 By continuing to use this bot, you *agree to these terms*.
        """
        ),
        parse_mode='Markdown',
        reply_markup=generate_agreement_keyboard(),
    )
    return States.AGREEMENT


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_help(), parse_mode='Markdown')


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(show_support_message(), parse_mode='Markdown')
