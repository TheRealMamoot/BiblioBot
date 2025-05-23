import logging
import textwrap
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.db.fetch import fetch_user_reservations


async def show_existing_reservations(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    cancel_stage: bool = False,
) -> str:
    coidce = context.user_data['codice_fiscale']
    email = context.user_data['email']
    try:
        history: pd.DataFrame = await fetch_user_reservations(coidce, email, include_date=False)
        history['datetime'] = pd.to_datetime(
            history['selected_date'].astype(str) + ' ' + history['end_time'].astype(str)
        )  # ' ' acts as space
        history['datetime'] = history['datetime'].dt.tz_localize('UTC').dt.tz_convert('Europe/Rome')
        current = history[history['datetime'] > datetime.now(ZoneInfo('Europe/Rome'))]
        current = current.sort_values('datetime', ascending=True)
        name = update.effective_user.username if update.effective_user.username else update.effective_user.first_name
        message = textwrap.dedent(
            f'Reservations for *{name}*\nCodice Fiscale: *{coidce}*\nEmail: {email}\n-----------------------\n'
        )
        if len(current) != 0:
            if cancel_stage:
                return current

            idx = 1
            for _, row in current.iterrows():
                status = (
                    f'✅ {row["status"]}'
                    if row['status'] == 'success'
                    else f'🔄 {row["status"]}'
                    if row['status'] == 'pending'
                    else f'⚠️ {row["status"]}'
                    if row['status'] == 'fail'
                    else f'❌ {row["status"]}'
                    if row['status'] == 'terminated'
                    else 'undefined'
                )
                booking_code: str = str(row['booking_code'])
                booking_code = booking_code.replace('.', '').replace('+', '').replace('-', '')
                if len(booking_code) < 6 and booking_code not in ['TBD', 'NA', 'INF', 'inf']:
                    booking_code = booking_code.zfill(6)
                res_type = 'Instant' if row['instant'] == 'True' else 'Regular'
                retry = ' - Retry at :00 and :30 of every hour.' if row['status'] == 'fail' else ''
                start_time_str = row['start_time'].strftime('%H:%M')
                end_time_str = row['end_time'].strftime('%H:%M')
                selected_date = row['selected_date'].strftime('%A, %Y-%m-%d')
                message += textwrap.dedent(
                    f'Reservation NO: *{idx:02d}*\n'
                    f'Date: *{selected_date}*\n'
                    f'Time: *{start_time_str}* - *{end_time_str}*\n'
                    f'Duration: *{row["selected_duration"]}* *hours*\n'
                    f'Booking Code: *{booking_code.upper()}*\n'
                    f'Reservation Type: *{res_type}*\n'
                    f'Status: *{status.title()}*_{retry}_\n'
                    f'-----------------------\n'
                )
                idx += 1
        else:
            message += '_You have no reservations at the moment._'
        return message
    except Exception as e:
        logging.error(f'[Bot.messages:show_existing_reservations] {e}')
        traceback.print_exc()


def show_support_message() -> str:
    text = """
            Thank you for using *Biblio*.
            Tell your friends, but not all of them!
            If anything was not to your liking, I don't really care. Blame this guy not me.

            [Linkedin](https://www.linkedin.com/in/alireza-mahmoudian-5b0276246/)
            [GitHub](https://github.com/TheRealMamoot)
            alireza.mahmoudian.am@gmail.com

            Cool person, check him out! 😏
    """
    return textwrap.dedent(text)


def show_donate_message() -> str:
    message = textwrap.dedent(
        """
        *🤝 Thanks for Helping Out!*
        Your support means the world! ❤️
        If you find the bot helpful and would like to contribute to its development, your donation would be truly appreciated.
        [Revolut](https://revolut.me/mamoot)
        [PayPal](https://www.paypal.com/paypalme/TheRealMamoot)
        Cheers! 🍻
        """
    )
    return message


def show_help() -> str:
    message = textwrap.dedent(
        """
        📖 *How it works*
        --------------------------
        You can reserve your slot at *BICF* either for *later* or *instantly*:

        ⏳ If you choose *"I need a slot for later"*, your requested slot will be queued and the bot will attempt to make your reservation at the next reset time, which occurs at *:00* and *:30* minute marks.

        ⚡️ If you choose *"I need a slot for now"*, the bot will try to reserve your slot *immediately*. If the slot is not available, it will automatically be queued for the next reset time — just like the "later" option. This option is only for the current day.
        
        ❗ You do not need to book multiple times. If your original reservation time hasn't passed, the bot will retry automatically. The maximum number of retries for a request is *18*. Afterwards the request will be *terminated*.

        🔔 You will be notified when your reservation is made or if it eventually fails.

        📅 You can see all your reservations and their states by choosing *"Current reservations"*.

        🚫 You can also *cancel* your request. Doing this *without* the bot might cause issues with your next slot request.
        
        📌 *Reservation Statuses*
        --------------------------
        🔄 *Pending*: Your request is in the queue and will be processed at the next slot opening at :00 or :30.

        ✅ *Success*: Your reservation was successful. You can now go to the library — you can check your email to be sure.

        ⚠️ *Fail*: The reservation was unsuccessful but will be retried several times. You don't need to request again yet.

        ❌ *Terminated*: Your request has either expired, exceeded the retry limit or canceled by you. You'll need to make a new reservation.

        ℹ️ You'll be notified if your reservation succeeds or fails permanently.
        
        💡 *Recommendation*
        --------------------------
        ❕ To increase your chances, it's highly recommended to use the *"I need a slot for later"* option and book in advance, before the day of your visit.

        ❕ Please avoid sharing the bot with a wide audience. Too many users may cause the system to slow down or fail, and it could reduce everyone's chances of getting a reservation.

        ❕ In case of any unforseen behaviour, please use /start to reset the bot. You can also use /help and /feedback at any time.

        🏹 Happy hunting...for slots!!!
        """
    )
    return message


def show_notification(status: str, record: dict, booking_code: str) -> str:
    if status == 'success':
        status_message = '✅ Reservation *Successful*!'
        retry_message = '*🤝 Enjoy your stay 🤝*'
    elif status == 'fail':
        status_message = '⚠️ Reservation *Failed*!'
        retry_message = '*❗ Retrying. Be patient... ❗*'
    elif status == 'terminated':
        status_message = '⛔️ Reservation *Terminated*!'
        retry_message = '*‼️ No more Retries ‼️*'

    date = record['selected_date'].strftime('%A, %Y-%m-%d')
    start_time = record['start_time'].strftime('%H:%M')
    end_time = record['end_time'].strftime('%H:%M')
    duration = int(record['selected_duration'])
    text = f"""
        {status_message}
        {retry_message}
        On: *{date}*
        From: *{start_time}* - *{end_time}* (*{duration}* hours)
        Booking Code: *{booking_code.upper()}*
    """
    return textwrap.dedent(text)
