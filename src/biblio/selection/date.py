import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.access import get_wks
from src.biblio.config.config import States
from src.biblio.utils import keyboards, utils


async def date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sheet_env = context.bot_data.get('sheet_env')
    auth_mode = context.bot_data.get('auth_mode')
    user_input = update.message.text.strip()

    if user_input == '⬅️ Edit reservation type':
        await update.message.reply_text(
            'Fine, just be quick. 🙄',
            parse_mode='Markdown',
            reply_markup=keyboards.generate_reservation_type_keyboard(),
        )
        return States.RESERVE_TYPE

    elif user_input == '🗓️ Current reservations':
        await update.message.reply_text(
            utils.show_existing_reservations(update, context, get_wks(sheet_env, auth_mode).get_as_df()),
            parse_mode='Markdown',
        )
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
    keyboard = keyboards.generate_time_keyboard(user_input)

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
