import logging
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from pandas import DataFrame
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import (
    show_donate_message,
    show_existing_reservations,
    show_help,
    show_support_message,
    show_user_agreement,
)
from src.biblio.config.config import States
from src.biblio.utils.keyboards import Keyboards, Labels


async def type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    keyboard = Keyboards.reservation_type()

    if user_input == Labels.CREDENTIALS_EDIT:
        await update.message.reply_text(
            textwrap.dedent(
                """
            Messed it up already?! _sighs_
            your _Codice Fiscale_, _Full Name_, and _Email_.
            Example: 
            *ABCDEF12G34H567I*, 
            *Mamoot Real*, 
            *brain@rot.com*

            📌_Comma placement matters. Spacing does not._
            """
            ),
            parse_mode='Markdown',
            reply_markup=Keyboards.start(edit_credential_stage=True),
        )
        return States.CREDENTIALS

    elif user_input == Labels.SLOT_LATER:
        keyboard = Keyboards.date()
        await update.message.reply_text('So, when will it be? 📅', reply_markup=keyboard)
        context.user_data['instant'] = False
        logging.info(
            f'🔄 {update.effective_user} selected REGULAR reservation at {datetime.now(ZoneInfo("Europe/Rome"))}'
        )
        return States.CHOOSING_DATE

    elif user_input == Labels.SLOT_INSTANT:
        now = datetime.now(ZoneInfo('Europe/Rome'))
        now_day = now.strftime('%A')
        now_date = now.strftime('%Y-%m-%d')
        week_day = now.weekday()

        open_time = 9
        close_time = 22
        if week_day == 5:
            close_time = 13
        if now.hour < (open_time - 2) or now.hour >= close_time:
            await update.message.reply_text(
                "It's over for today! Go home. 😌",
                reply_markup=Keyboards.reservation_type(),
            )
            return States.RESERVE_TYPE

        if week_day == 6:  # Sunday
            await update.message.reply_text(
                "It's Sunday! Come on, chill. 😌",
                reply_markup=Keyboards.reservation_type(),
            )
            return States.RESERVE_TYPE

        date = f'{now_day}, {now_date}'
        await update.message.reply_text(
            'So, when will it be? 🕑',
            reply_markup=Keyboards.time(date, instant=True),
        )
        context.user_data['instant'] = True
        context.user_data['selected_date'] = date
        logging.info(
            f'🔄 {update.effective_user} selected INSTANT reservation at {datetime.now(ZoneInfo("Europe/Rome"))}'
        )
        return States.CHOOSING_TIME

    elif user_input == Labels.CURRENT_RESERVATIONS:
        text = await show_existing_reservations(update, context)
        if not text:
            text = '_No reservations found._'
        await update.message.reply_text(text, parse_mode='Markdown')
        return States.RESERVE_TYPE

    elif user_input == Labels.CANCEL_RESERVATION:
        reservations = await show_existing_reservations(update, context, cancel_stage=True)
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
            start_time_str = row['start_time'].strftime('%H:%M')
            end_time_str = row['end_time'].strftime('%H:%M')
            selected_date = row['selected_date'].strftime('%A %Y-%m-%d')
            button = f'{status} {selected_date} at {start_time_str} - {end_time_str}'

            choices[f'{row["id"]}'] = {
                'selected_date': selected_date,
                'start_time': start_time_str,
                'end_time': end_time_str,
                'selected_duration': row['selected_duration'],
                'booking_code': row['booking_code'],
                'status': row['status'],
                'button': button,
            }
            buttons.append(button)

        if len(buttons) == 0:
            await update.message.reply_text('_You have no reservations at the moment._', parse_mode='Markdown')
            return States.RESERVE_TYPE

        context.user_data['cancelation_choices'] = choices
        keyboard = Keyboards.cancelation_options(buttons)

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

    elif user_input == Labels.HELP:
        await update.message.reply_text(
            show_help(),
            parse_mode='Markdown',
            reply_markup=Keyboards.reservation_type(),
        )
        return States.RESERVE_TYPE

    elif user_input == Labels.DONATE:
        await update.message.reply_text(
            show_donate_message(),
            parse_mode='Markdown',
            reply_markup=Keyboards.reservation_type(),
        )
        return States.RESERVE_TYPE

    elif user_input == Labels.AGREEMENT:
        await update.message.reply_text(
            show_user_agreement(),
            parse_mode='Markdown',
            reply_markup=Keyboards.reservation_type(),
        )
        return States.RESERVE_TYPE

    elif user_input == Labels.FEEDBACK:
        await update.message.reply_text(
            show_support_message(),
            parse_mode='Markdown',
            reply_markup=Keyboards.reservation_type(),
        )
        return States.RESERVE_TYPE

    else:
        await update.message.reply_text(
            "The options are right there you know. Pick one, that's it.",
            reply_markup=keyboard,
        )
        return States.RESERVE_TYPE
