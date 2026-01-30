import asyncio
import logging
import textwrap
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import BookingCodeStatus, State, Status, UserDataKey
from src.biblio.db.insert import writer
from src.biblio.reservation.reservation import (
    calculate_timeout,
    confirm_reservation,
    set_reservation,
)
from src.biblio.reservation.slot_datetime import reserve_datetime
from src.biblio.utils.keyboards import Keyboard, Label


def _set_user_data_status(
    context: ContextTypes.DEFAULT_TYPE,
    status: str,
    booking_code: str,
    retries: str | None = None,
    created_at: bool = False,
    success_at: bool = False,
    fail_at: bool = False,
) -> None:
    now = datetime.now(ZoneInfo("Europe/Rome"))
    if created_at:
        context.user_data[UserDataKey.CREATED_AT] = now
    if success_at:
        context.user_data[UserDataKey.SUCCESS_AT] = now
    if fail_at:
        context.user_data[UserDataKey.FAIL_AT] = now
    if retries is not None:
        context.user_data[UserDataKey.RETRIES] = retries
    context.user_data[UserDataKey.STATUS] = status
    context.user_data[UserDataKey.BOOKING_CODE] = booking_code
    context.user_data[UserDataKey.UPDATED_AT] = now


async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    start_time = context.user_data.get(UserDataKey.SELECTED_TIME)
    end_time = datetime.strptime(start_time, "%H:%M") + timedelta(
        hours=int(context.user_data.get(UserDataKey.SELECTED_DURATION))
    )
    end_time = end_time.strftime("%H:%M")
    date: str = context.user_data[UserDataKey.SELECTED_DATE]
    date = date.split(" ")[-1]
    selected_duration = int(context.user_data[UserDataKey.SELECTED_DURATION])
    start, end, duration = reserve_datetime(date, start_time, selected_duration)

    if user_input == Label.CONFIRM_YES:
        user_data = {
            "codice_fiscale": context.user_data[UserDataKey.CODICE_FISCALE],
            "cognome_nome": context.user_data[UserDataKey.NAME],
            "email": context.user_data[UserDataKey.EMAIL],
        }
        request_status_message = "⏳ Slot *Scheduled*. Status *Pending*."
        retry_status_message = "‼️ Reservation request will be processed when slots *reset*. *Be patient!* you will be notified."
        res_type = "INSTANT" if context.user_data[UserDataKey.INSTANT] else "REGULAR"

        logging.info(
            f"[RESERVE] 1️⃣ ⏱️ {res_type} Slot identified for {user_data['cognome_nome']}"
        )
        logging.info(
            f"{update.effective_user} request confirmed at {datetime.now(ZoneInfo('Europe/Rome'))}"
        )
        _set_user_data_status(
            context,
            status=Status.PENDING,
            booking_code=BookingCodeStatus.TBD,
            retries="0",
            created_at=True,
        )

        if context.user_data[UserDataKey.INSTANT]:
            try:
                await asyncio.sleep(1)
                await update.message.reply_text(
                    "⏳ *Please wait...*", parse_mode="Markdown"
                )
                timeout = calculate_timeout(
                    retries=0, base=120
                )  # todo: change to dynamic based on retries
                reservation_response = await set_reservation(
                    start,
                    end,
                    duration,
                    user_data,
                    timeout,
                )
                logging.info(
                    f"[SET] 2️⃣ ⏱️ ⚡ {res_type} Reservation set for {user_data['cognome_nome']}"
                )
                await confirm_reservation(reservation_response["entry"])
                logging.info(
                    f"[CONFIRM] 3️⃣ ⏱️ ⚡ {res_type} Reservation confirmed for {user_data['cognome_nome']}"
                )
                _set_user_data_status(
                    context,
                    status=Status.SUCCESS,
                    booking_code=f"{reservation_response['codice_prenotazione']}",
                    success_at=True,
                )
                request_status_message = "✅ Reservation *successful*!"
                retry_status_message = ""

            except Exception as e:
                logging.error(
                    f"❌ {res_type} Reservation failed for {user_data['cognome_nome']} — {e}"
                )
                _set_user_data_status(
                    context,
                    status=Status.FAIL,
                    booking_code=BookingCodeStatus.NA,
                    retries="1",
                    fail_at=True,
                )
                request_status_message = (
                    "⚠️ Reservation *retrying*! *Slot not available*."
                )
                retry_status_message = "‼️ *No need to try again!* I will automatically try to get it when slots open, unless the time for the requested slot *has passed*."

        await writer(update, context)
        await update.message.reply_text(
            textwrap.dedent(
                f"""
                    {request_status_message}
                    Requested at *{datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d %H:%M:%S")}*

                    Codice Fiscale: *{context.user_data.get(UserDataKey.CODICE_FISCALE)}*
                    Full Name: *{context.user_data.get(UserDataKey.NAME)}*
                    Email: *{context.user_data.get(UserDataKey.EMAIL)}*
                    On: *{context.user_data.get(UserDataKey.SELECTED_DATE)}*
                    From: *{start_time}* - *{end_time}* (*{context.user_data.get(UserDataKey.SELECTED_DURATION)}* hours)
                    Booking Code: *{context.user_data[UserDataKey.BOOKING_CODE].upper()}*
                    Reservation Type: *{res_type.title()}*
                    {retry_status_message}

                    Do you want to go for another slot?
                    """
            ),
            parse_mode="Markdown",
            reply_markup=Keyboard.retry(),
        )

        return State.RETRY

    elif user_input == Label.CONFIRM_NO:
        keyboard = Keyboard.duration(
            context.user_data.get(UserDataKey.SELECTED_TIME), context
        )[0]
        await update.message.reply_text(
            "I overestimated you it seems. Duration please. 😬", reply_markup=keyboard
        )
        return State.CHOOSING_DUR

    else:
        await update.message.reply_text(
            "JUST.CLICK...PLEASE!",
            reply_markup=Keyboard.confirmation(),
        )
        return State.CONFIRMING
