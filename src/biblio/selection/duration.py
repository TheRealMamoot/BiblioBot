import logging
import textwrap
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.access import get_wks
from src.biblio.config.config import States
from src.biblio.utils import keyboards
from src.biblio.utils.validation import duration_overlap


async def duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sheet_env = context.bot_data.get('sheet_env')
    auth_mode = context.bot_data.get('auth_mode')
    user_input = update.message.text.strip()

    if user_input == '⬅️':
        keyboard = keyboards.generate_time_keyboard(
            context.user_data.get('selected_date'), instant=context.user_data['instant']
        )
        await update.message.reply_text('Make up your mind! choose a time ALREADY 🙄', reply_markup=keyboard)
        return States.CHOOSING_TIME

    selected_time = context.user_data.get('selected_time')
    duration_selection = keyboards.generate_duration_keyboard(selected_time, context)[
        1
    ]  # [0] for the reply, [1] for the values
    max_dur = max(duration_selection)

    if not user_input.isdigit():
        await update.message.reply_text("Now you're just messing with me. Just pick the duration!")
        return States.CHOOSING_DUR

    if int(user_input) > max_dur:
        await update.message.reply_text('Well they are not going to let you sleep there! Try again. 🤷‍♂️')
        return States.CHOOSING_DUR

    if duration_overlap(update, context, get_wks(sheet_env, auth_mode).get_as_df()):
        await update.message.reply_text(
            textwrap.dedent(
                """
            ⚠️ Your reservation overlaps with an existing one! 
            Choose a different duration.
            """
            )
        )
        return States.CHOOSING_DUR

    context.user_data['selected_duration'] = user_input
    res_type = 'INSTANT' if context.user_data['instant'] else 'REGULAR'
    logging.info(f'🔄 {update.effective_user} selected {res_type} duration at {datetime.now(ZoneInfo("Europe/Rome"))}')

    start_time = context.user_data.get('selected_time')
    end_time = datetime.strptime(start_time, '%H:%M') + timedelta(hours=int(context.user_data.get('selected_duration')))
    end_time = end_time.strftime('%H:%M')

    keyboard = keyboards.generate_confirmation_keyboard()
    await update.message.reply_text(
        textwrap.dedent(
            f"""
            All looks good?
            Codice Fiscale: *{context.user_data.get('codice_fiscale')}*
            Full Name: *{context.user_data.get('name')}*
            Email: *{context.user_data.get('email')}*
            On *{context.user_data.get('selected_date')}*
            From *{start_time}* - *{end_time}* (*{context.user_data.get('selected_duration')} Hours*)
            """
        ),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )
    return States.CONFIRMING
