import logging
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import show_existing_reservations
from src.biblio.config.config import States
from src.biblio.utils.keyboards import Keyboards, Labels
from src.biblio.utils.validation import time_not_overlap


async def time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Labels.BACK:
        if context.user_data['instant']:
            await update.message.reply_text(
                textwrap.dedent(
                    """
                Just decide already!
                """
                ),
                parse_mode='Markdown',
                reply_markup=Keyboards.reservation_type(),
            )
            return States.RESERVE_TYPE

        keyboard = Keyboards.date()
        await update.message.reply_text('Choose a date, AGAIN! 😒', reply_markup=keyboard)
        return States.CHOOSING_DATE

    elif user_input == Labels.CURRENT_RESERVATIONS:
        await update.message.reply_text(
            await show_existing_reservations(update, context),
            parse_mode='Markdown',
        )
        return States.CHOOSING_TIME

    try:
        datetime.strptime(user_input, '%H:%M')
        time_obj = datetime.strptime(user_input, '%H:%M').replace(tzinfo=ZoneInfo('Europe/Rome'))
        if (time_obj.hour + time_obj.minute / 60) < 9:
            await update.message.reply_text(
                textwrap.dedent(
                    """
                ⚠️ Starting time can't be before 09:00! 
                Choose a different time.
                """
                )
            )
            return States.CHOOSING_TIME

    except ValueError:
        await update.message.reply_text('Not that difficult to pick an option form the list! Just saying. 🤷‍♂️')
        return States.CHOOSING_TIME

    if not await time_not_overlap(update, context):
        await update.message.reply_text(
            textwrap.dedent(
                """
            ⚠️ Your reservation overlaps with an existing one! 
            Choose a different time.
            """
            )
        )
        return States.CHOOSING_TIME
    context.user_data['selected_time'] = user_input
    keyboard = Keyboards.duration(user_input, context)[0]  # [0] for the reply, [1] for the values

    await update.message.reply_text(
        'How long will you absolutely NOT be productive over there? 🕦 Give me hours.',
        reply_markup=keyboard,
    )

    res_type = 'INSTANT' if context.user_data['instant'] else 'REGULAR'
    logging.info(f'🔄 {update.effective_user} selected {res_type} time at {datetime.now(ZoneInfo("Europe/Rome"))}')
    return States.CHOOSING_DUR
