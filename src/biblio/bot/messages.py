import logging
import textwrap
import traceback
from datetime import datetime, time
from io import BytesIO
from zoneinfo import ZoneInfo

import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import BookingCodeStatus, Schedule, Status, UserDataKey
from src.biblio.db.fetch import fetch_user_reservations
from src.biblio.utils.utils import plot_slot_history, utc_tuple_to_rome_time

JOB_SCHEDULE = Schedule.jobs(daylight_saving=True)
JOB_START, _ = JOB_SCHEDULE.get_hours("availability")
MIN_AVAILABILITY_START = utc_tuple_to_rome_time(hour_minute=(JOB_START, 0))


async def show_existing_reservations(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    cancel_stage: bool = False,
) -> str:
    coidce = context.user_data[UserDataKey.CODICE_FISCALE]
    email = context.user_data[UserDataKey.EMAIL]
    try:
        history: pd.DataFrame = await fetch_user_reservations(
            coidce, email, include_date=False
        )
        if history.empty:
            return "_You have no reservations at the moment._"
        history["datetime"] = pd.to_datetime(
            history["selected_date"].astype(str) + " " + history["end_time"].astype(str)
        )  # ' ' acts as space
        history["datetime"] = (
            history["datetime"].dt.tz_localize("UTC").dt.tz_convert("Europe/Rome")
        )
        current = history[history["datetime"] > datetime.now(ZoneInfo("Europe/Rome"))]
        current = current.sort_values("datetime", ascending=True)
        name = (
            update.effective_user.username
            if update.effective_user.username
            else update.effective_user.first_name
        )
        message = textwrap.dedent(
            f"Reservations for *{name}*\nCodice Fiscale: *{coidce}*\nEmail: {email}\n-----------------------\n"
        )
        if len(current) != 0:
            if cancel_stage:
                return current

            idx = 1
            for _, row in current.iterrows():
                try:
                    status_enum = Status(row["status"])
                    status = f"{status_enum.emoji} {row['status']}"
                except ValueError:
                    status = "undefined"
                booking_code: str = str(row["booking_code"])
                booking_code = (
                    booking_code.replace(".", "").replace("+", "").replace("-", "")
                )
                if len(booking_code) < 6 and booking_code not in [
                    BookingCodeStatus.TBD,
                    BookingCodeStatus.NA,
                    "INF",
                    "inf",
                ]:
                    booking_code = booking_code.zfill(6)
                res_type = "Instant" if row["instant"] == "True" else "Regular"
                retry = (
                    " - Retry at :00 and :30 of every hour."
                    if row["status"] == Status.FAIL
                    else ""
                )
                start_time_str = row["start_time"].strftime("%H:%M")
                end_time_str = row["end_time"].strftime("%H:%M")
                selected_date = row["selected_date"].strftime("%A, %Y-%m-%d")
                message += textwrap.dedent(
                    f"Reservation NO: *{idx:02d}*\n"
                    f"Date: *{selected_date}*\n"
                    f"Time: *{start_time_str}* - *{end_time_str}*\n"
                    f"Duration: *{row['selected_duration']}* *hours*\n"
                    f"Booking Code: *{booking_code.upper()}*\n"
                    f"Reservation Type: *{res_type}*\n"
                    f"Status: *{status.title()}*_{retry}_\n"
                    f"-----------------------\n"
                )
                idx += 1
        else:
            message += "_You have no reservations at the moment._"
        return message
    except Exception as e:
        logging.error(f"[Bot.messages:show_existing_reservations] {e}")
        traceback.print_exc()


def show_notification(status: str, record: dict, booking_code: str) -> str:
    if status == Status.SUCCESS:
        status_message = "✅ Reservation *Successful*!"
        retry_message = "Enjoy your stay 🤝"
    elif status == Status.FAIL:
        status_message = "⚠️ Reservation *Failed*!"
        retry_message = "*❗ Trying again ❗*"
    elif status == Status.TERMINATED:
        status_message = "⛔️ Reservation *Terminated*!"
        retry_message = "*‼️ No more Retries ‼️*"
    elif status == Status.EXISTING:
        status_message = "✴️ Reservation *Exists* probably!"
        retry_message = "*❗ Check your email.* There seems to be a reservation already made for this slot. The bot will not retry."
    else:
        status_message = ""
        retry_message = ""

    date = record["selected_date"].strftime("%A, %Y-%m-%d")
    start_time = record["start_time"].strftime("%H:%M")
    end_time = record["end_time"].strftime("%H:%M")
    duration = int(record["selected_duration"])
    text = f"""
        {status_message}
        {retry_message}
        On: *{date}*
        From: *{start_time}* - *{end_time}* (*{duration}* hours)
        Booking Code: *{booking_code.upper()}*
    """
    return textwrap.dedent(text)


def show_user_agreement() -> str:
    text = textwrap.dedent(
        """
        *📄 User Agreement*
        *📣 Data Usage Notice*

        ❗ By using this bot, you agree to the collection and storage of the following *data*:

        📌 Your *Telegram username*, *first name*, and *last name* (if available)
        📌 Your provided *Codice Fiscale*, *full name*, and *email address*
        📌 Your selected *reservation date*, *time*, and *duration* at Università degli Studi di Milano's Library of Biology, Computer Science, Chemistry and Physics (*BICF*)
        📌 The *status* of your reservation (*active* or *cancelled*) 
        📌 *General activity data*, including your *interactions* with the bot during the reservation process

        ❕ This data is used *exclusively* for making and managing *BICF reservations* more easily on your behalf.
        ❕ Your data is *never shared* with third parties and is used solely to assist with *reservation automation* and *troubleshooting*.

        🤝🏻 By continuing to use this bot, you *agree to these terms*.
        """
    )
    return text


def show_support_message() -> str:
    text = """
        Thank you for using *Biblio*.
        Tell your friends, but not all of them!

        Contacts:
        [GitHub](https://github.com/TheRealMamoot)
        [Linkedin](https://www.linkedin.com/in/alireza-mahmoudian-5b0276246/)
        
        Bug report, suggestions & feedback: 
        [@BiblioSupport](https://t.me/BiblioSupport)

        Cool guy, check him out! 😏
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

        ✴️ *Existing*: The bot has detected that you already have a reservation for this slot. It will not retry.

        ℹ️ You'll be notified if your reservation succeeds or fails permanently.
        
        💡 *Recommendation*
        --------------------------
        ❕ To increase your chances, it's highly recommended to use the *"I need a slot for later"* option and book in advance, before the day of your visit.

        ❕ Please avoid sharing the bot with a wide audience. Too many users may cause the system to slow down or fail, and it could reduce everyone's chances of getting a reservation.

        ❕ In case of any unforseen behaviour, please use /start to reset the bot. You can also use /help, /feedback and /agreemnt at any time.

        🏹 Happy hunting...for slots!!!
        """
    )
    return message


async def show_slot_history(
    update: Update,
    history: pd.DataFrame,
    date: str,
    slot: str,
    start: str = time(*MIN_AVAILABILITY_START).strftime("%H:%M"),
    end: str | None = None,
) -> None | BytesIO:
    slot_end_str = slot.split("-")[1]
    slot_end = datetime.strptime(slot_end_str, "%H:%M").time()
    parsed_start = datetime.strptime(start, "%H:%M").time()
    parsed_end = datetime.strptime(end, "%H:%M").time() if end else slot_end

    all_slots = history.copy()
    all_slots.rename(columns={"job_timestamp": "time"}, inplace=True)

    all_slots["time"] = all_slots["time"].apply(
        lambda t: t.replace(tzinfo=ZoneInfo("UTC"))
        .astimezone(ZoneInfo("Europe/Rome"))
        .strftime("%H:%M:%S")
    )

    all_slots = all_slots[
        all_slots["time"].apply(
            lambda t: parsed_start
            <= datetime.strptime(t, "%H:%M:%S").time()
            < parsed_end
        )
    ]

    selected_slot = all_slots[all_slots["slot"] == slot][["time", "available"]]
    if selected_slot.empty:
        return None

    history_graph = plot_slot_history(
        selected_slot, date, slot, start, end=parsed_end.strftime("%H:%M")
    )
    return history_graph
