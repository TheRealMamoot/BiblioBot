import logging
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from pandas import DataFrame
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.access import get_wks
from src.biblio.config.config import States
from src.biblio.utils import keyboards, utils


async def type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sheet_env = context.bot_data.get('sheet_env')
    auth_mode = context.bot_data.get('auth_mode')
    user_input = update.message.text.strip()
    keyboard = keyboards.generate_reservation_type_keyboard()

    if user_input == '⬅️ Edit credentials':
        await update.message.reply_text(
            textwrap.dedent(
                """
            Messed it up already?! _sighs_
            your _Codice Fiscale_, _Full Name_, and _Email_.
            Example: 
            *ABCDEF12G34H567I*, 
            *Mamoot Real*, 
            *brain@rot.com*
            """
            ),
            parse_mode='Markdown',
            reply_markup=keyboards.generate_start_keyboard(edit_credential_stage=True),
        )
        return States.CREDENTIALS

    elif user_input == '⏳ I need a slot for later.':
        keyboard = keyboards.generate_date_keyboard()
        await update.message.reply_text('So, when will it be? 📅', reply_markup=keyboard)
        context.user_data['instant'] = False
        logging.info(
            f'🔄 {update.effective_user} selected REGULAR reservation at {datetime.now(ZoneInfo("Europe/Rome"))}'
        )
        return States.CHOOSING_DATE

    elif user_input == '⚡️ I need a slot for now.':
        now = datetime.now(ZoneInfo('Europe/Rome'))
        now_day = now.strftime('%A')
        now_date = now.strftime('%Y-%m-%d')
        week_day = now.weekday()

        open_time = 9
        close_time = 22
        if week_day == 5:
            close_time = 13
        if now.hour < open_time or now.hour >= close_time:
            await update.message.reply_text(
                "It's over for today! Go home. 😌",
                reply_markup=keyboards.generate_reservation_type_keyboard(),
            )
            return States.RESERVE_TYPE

        if week_day == 6:  # Sunday
            await update.message.reply_text(
                "It's Sunday! Come on, chill. 😌",
                reply_markup=keyboards.generate_reservation_type_keyboard(),
            )
            return States.RESERVE_TYPE

        date = f'{now_day}, {now_date}'
        await update.message.reply_text(
            'So, when will it be? 🕑',
            reply_markup=keyboards.generate_time_keyboard(date, instant=True),
        )
        context.user_data['instant'] = True
        context.user_data['selected_date'] = date
        logging.info(
            f'🔄 {update.effective_user} selected INSTANT reservation at {datetime.now(ZoneInfo("Europe/Rome"))}'
        )
        return States.CHOOSING_TIME

    elif user_input == '🗓️ Current reservations':
        await update.message.reply_text(
            utils.show_existing_reservations(update, context, get_wks(sheet_env, auth_mode).get_as_df()),
            parse_mode='Markdown',
        )
        return States.RESERVE_TYPE

    elif user_input == '🚫 Cancel reservation':
        reservations = utils.show_existing_reservations(
            update, context, history=get_wks(sheet_env, auth_mode).get_as_df(), cancel_stage=True
        )
        choices = {}
        buttons = []

        if not isinstance(reservations, DataFrame):
            await update.message.reply_text('_You have no reservations at the moment._', parse_mode='Markdown')
            return States.RESERVE_TYPE

        for _, row in reservations.iterrows():
            if row['status'] == 'terminated':
                continue
            status = (
                '🔄'
                if row['status'] == 'pending'
                else '⚠️'
                if row['status'] == 'fail'
                else '✅'
                if row['status'] == 'success'
                else ''
            )
            button = f'{status} {row["selected_date"]} at {row["start"]} - {row["end"]}'

            choices[f'{row["id"]}'] = {
                'selected_date': row['selected_date'],
                'start': row['start'],
                'end': row['end'],
                'selected_dur': row['selected_dur'],
                'booking_code': row['booking_code'],
                'status': row['status'],
                'button': button,
            }
            buttons.append(button)

        if len(buttons) == 0:
            await update.message.reply_text('_You have no reservations at the moment._', parse_mode='Markdown')
            return States.RESERVE_TYPE

        context.user_data['cancelation_choices'] = choices
        keyboard = keyboards.generate_cancelation_options_keyboard(buttons)

        logging.info(f'🔄 {update.effective_user} started cancelation at {datetime.now(ZoneInfo("Europe/Rome"))}')
        await update.message.reply_text(
            textwrap.dedent(
                """
                    ❗ *Please make sure your reservation time has not ended*❗
                    🔄 *Pending*: Reservation will be processed when slots open.
                    ⚠️ *Failed*: Reservation request will be retried at :00 and :30 again.
                    ✅ *Success*: Reservation was succesful.

                    That being said, which one will it be?
                    """
            ),
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
        return States.CANCELATION_SLOT_CHOICE

    elif user_input == '❓ Help':
        await update.message.reply_text(
            utils.show_help(),
            parse_mode='Markdown',
            reply_markup=keyboards.generate_reservation_type_keyboard(),
        )
        return States.RESERVE_TYPE

    elif user_input == '🫶 Donate':
        await update.message.reply_text(
            utils.show_donate_message(),
            parse_mode='Markdown',
            reply_markup=keyboards.generate_reservation_type_keyboard(),
        )
        return States.RESERVE_TYPE

    else:
        await update.message.reply_text(
            "The options are right there you know. Pick one, that's it.",
            reply_markup=keyboard,
        )
        return States.RESERVE_TYPE
