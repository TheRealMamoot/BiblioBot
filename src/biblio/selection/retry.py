import logging
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from pandas import DataFrame
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import show_donate_message, show_existing_reservations, show_support_message
from src.biblio.config.config import Schedule, States
from src.biblio.utils.keyboards import Keyboard, Label

LIB_SCHEDULE = Schedule.weekly()


async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.RETRY:
        keyboard = Keyboard.reservation_type()

        await update.message.reply_text('Ah ****, here we go again! 😪', reply_markup=keyboard)
        logging.info(f'⏳ {update.effective_user} reinitiated the process at {datetime.now(ZoneInfo("Europe/Rome"))}')
        return States.RESERVE_TYPE

    elif user_input == Label.FEEDBACK:
        await update.message.reply_text(
            show_support_message(),
            parse_mode='Markdown',
        )
        return States.RETRY

    elif user_input == Label.HISTORY:
        keyboard = Keyboard.date(days_past=5, days_future=0, history_state=True)
        await update.message.reply_text(
            'So, when will it be? You can see the data for the past *6 days*. 📅',
            reply_markup=keyboard,
            parse_mode='Markdown',
        )
        return States.CHOOSING_DATE_HISTORY

    elif user_input == Label.CURRENT_RESERVATIONS:
        await update.message.reply_text(
            await show_existing_reservations(update, context),
            parse_mode='Markdown',
        )
        return States.RETRY

    elif user_input == Label.AVAILABLE_SLOTS:
        context.user_data['state'] = States.RETRY
        now = datetime.now(ZoneInfo('Europe/Rome'))

        open_time, close_time = LIB_SCHEDULE.get_hours(now.weekday())

        if now.hour < (open_time - 2) or now.hour >= close_time:
            await update.message.reply_text("It's over for today! Go home. 😌", reply_markup=Keyboard.retry())
            return States.RETRY

        time = now.replace(minute=(0 if now.minute < 30 else 30), second=0, microsecond=0)
        time = time.strftime('%H:%M')
        context.user_data['selected_time'] = time

        await update.message.reply_text(
            'How many hours are we looking at? 🕦',
            parse_mode='Markdown',
            reply_markup=Keyboard.duration(time, context, show_available=True)[0],
        )
        return States.CHOOSING_AVAILABLE

    elif user_input == Label.CANCEL_RESERVATION:
        reservations = await show_existing_reservations(update, context, cancel_stage=True)
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
                else '✴️'
                if row['status'] == 'existing'
                else ''
            )
            start_time_str = row['start_time'].strftime('%H:%M')
            end_time_str = row['end_time'].strftime('%H:%M')
            selected_date = row['selected_date'].strftime('%A, %Y-%m-%d')
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
            return States.RETRY

        context.user_data['cancelation_choices'] = choices
        keyboard = Keyboard.cancelation_options(buttons)

        logging.info(f'🔄 {update.effective_user} started cancelation at {datetime.now(ZoneInfo("Europe/Rome"))}')
        await update.message.reply_text(
            textwrap.dedent(
                """
                    ❗ *Please make sure your reservation time has not ended*❗
                    ✅ *Success*: Reservation was _succesful_. Booking code _available_.
                    🔄 *Pending*: Reservation in progress and will be processed when slots open.
                    ⚠️ *Failed*: Reservation was _unsucessful_ but the request will be retried at :00 and :30 again.
                    ✴️ *Existing*: Reservation was _partly succesful_. Booking code _unavailable_. *Check your email.*

                    That being said, which one will it be?
                    """
            ),
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
        return States.CANCELATION_SLOT_CHOICE

    elif user_input == Label.DONATE:
        await update.message.reply_text(
            show_donate_message(),
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
