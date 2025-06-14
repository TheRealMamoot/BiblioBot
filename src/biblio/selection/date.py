import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import show_existing_reservations
from src.biblio.config.config import States
from src.biblio.utils import utils
from src.biblio.utils.keyboards import Keyboard, Label


async def date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.RESERVATION_TYPE_EDIT:
        await update.message.reply_text(
            'Fine, just be quick. 🙄',
            parse_mode='Markdown',
            reply_markup=Keyboard.reservation_type(),
        )
        return States.RESERVE_TYPE

    elif user_input == Label.CURRENT_RESERVATIONS:
        text = await show_existing_reservations(update, context)
        if not text:
            text = '_No reservations found._'
        await update.message.reply_text(text, parse_mode='Markdown')
        return States.CHOOSING_DATE

    try:
        datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text('Umm, that does not look like a date to me. 🤨 Just pick one from the list.')
        return States.CHOOSING_DATE

    available_dates = utils.generate_days()
    available_dates = [datetime.strptime(date.split(' ')[-1], '%Y-%m-%d') for date in available_dates]

    if datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d') not in available_dates:
        await update.message.reply_text('🚫 Not available! Choose again from the list.')
        return States.CHOOSING_DATE

    context.user_data['selected_date'] = user_input
    keyboard = Keyboard.time(user_input)

    if len(keyboard.keyboard) <= 1:
        await update.message.reply_text(
            'Oops! There are no available time slots for that date.\nCry about it ☺️. Choose another one.'
        )
        return States.CHOOSING_DATE

    await update.message.reply_text(
        f'Fine. You picked *{user_input}*.\nNow choose a starting time.',
        reply_markup=keyboard,
        parse_mode='Markdown',
    )
    logging.info(f'🔄 {update.effective_user} selected date at {datetime.now(ZoneInfo("Europe/Rome"))}')
    return States.CHOOSING_TIME
