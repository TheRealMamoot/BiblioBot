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


async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sheet_env = context.bot_data.get('sheet_env')
    auth_mode = context.bot_data.get('auth_mode')
    user_input = update.message.text.strip()

    if user_input == "🆕 Let's go again!":
        keyboard = keyboards.generate_reservation_type_keyboard()

        await update.message.reply_text('Ah ****, here we go again! 😪', reply_markup=keyboard)
        logging.info(f'⏳ {update.effective_user} reinitiated the process at {datetime.now(ZoneInfo("Europe/Rome"))}')
        return States.RESERVE_TYPE

    elif user_input == '💡 Feedback':
        await update.message.reply_text(
            utils.show_support_message(),
            parse_mode='Markdown',
        )
        return States.RETRY

    elif user_input == '🗓️ Current reservations':
        await update.message.reply_text(
            utils.show_existing_reservations(update, context, get_wks(sheet_env, auth_mode).get_as_df()),
            parse_mode='Markdown',
        )
        return States.RETRY

    elif user_input == '🚫 Cancel reservation':
        reservations = utils.show_existing_reservations(
            update, context, history=get_wks(sheet_env, auth_mode).get_as_df(), cancel_stage=True
        )
        choices = {}
        buttons = []

        if not isinstance(reservations, DataFrame):
            await update.message.reply_text('_You have no reservations at the moment._', parse_mode='Markdown')
            return States.RETRY

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
            return States.RETRY

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

    elif user_input == '🫶 Donate':
        await update.message.reply_text(
            utils.show_donate_message(),
            parse_mode='Markdown',
        )
        return States.RETRY

    else:
        await update.message.reply_text(
            textwrap.dedent(
                """
            Off you go now, Bye. 😘
            Don't you dare /start again 😠!
            """
            ),
            parse_mode='Markdown',
        )
        return States.RETRY
