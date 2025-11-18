import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import show_existing_reservations
from src.biblio.config.config import Schedule, States
from src.biblio.db.fetch import fetch_slot_history
from src.biblio.utils import utils
from src.biblio.utils.keyboards import Keyboard, Label

LIB_SCHEDULE = Schedule.weekly()


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

    elif user_input == Label.AVAILABLE_SLOTS:
        context.user_data['state'] = States.CHOOSING_DATE
        now = datetime.now(ZoneInfo('Europe/Rome'))

        open_time, close_time = LIB_SCHEDULE.get_hours(now.weekday())

        if now.hour < (open_time - 2) or now.hour >= close_time:
            await update.message.reply_text(
                "It's over for today! Go home. 😌",
                reply_markup=Keyboard.date(),
            )
            return States.CHOOSING_DATE

        time = now.replace(minute=(0 if now.minute < 30 else 30), second=0, microsecond=0)
        time = time.strftime('%H:%M')
        context.user_data['selected_time'] = time

        await update.message.reply_text(
            'How many hours are we looking at? 🕦',
            parse_mode='Markdown',
            reply_markup=Keyboard.duration(time, context, show_available=True)[0],
        )
        return States.CHOOSING_AVAILABLE

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


async def date_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.RESERVATION_TYPE_EDIT:
        await update.message.reply_text(
            'Fine, just be quick. 🙄',
            parse_mode='Markdown',
            reply_markup=Keyboard.reservation_type(),
        )
        return States.RESERVE_TYPE
    try:
        datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text('Umm, that does not look like a date to me. 🤨 Just pick one from the list.')
        return States.CHOOSING_DATE_HISTORY

    available_dates = utils.generate_days(past=5, future=0)
    available_dates = [datetime.strptime(date.split(' ')[-1], '%Y-%m-%d') for date in available_dates]

    if datetime.strptime(user_input.split(' ')[-1], '%Y-%m-%d') not in available_dates:
        await update.message.reply_text('🚫 Not available! Choose again from the list.')
        return States.CHOOSING_DATE_HISTORY

    context.user_data['selected_date_history'] = user_input

    history = await fetch_slot_history(
        date=datetime.strptime(context.user_data['selected_date_history'], '%A, %Y-%m-%d')
    )

    if history is None:
        await update.message.reply_text('🚫 No data! Choose again from the list.')
        return States.CHOOSING_DATE_HISTORY

    context.user_data['slot_history'] = history
    logging.info(f'🔄 fetched history for {update.effective_user} at {datetime.now(ZoneInfo("Europe/Rome"))}')

    keyboard = Keyboard.slot(history)

    await update.message.reply_text(
        f'You picked *{user_input}*.\nNow choose a slot.',
        reply_markup=keyboard,
        parse_mode='Markdown',
    )
    return States.CHOOSING_SLOT
