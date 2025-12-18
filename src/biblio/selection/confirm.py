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
            f"✅ **1** {res_type} Slot identified for {user_data['cognome_nome']}"
        )
        logging.info(
            f"{update.effective_user} request confirmed at {datetime.now(ZoneInfo('Europe/Rome'))}"
        )
        context.user_data[UserDataKey.CREATED_AT] = datetime.now(ZoneInfo("Europe/Rome"))
        context.user_data[UserDataKey.STATUS] = Status.PENDING
        context.user_data[UserDataKey.BOOKING_CODE] = BookingCodeStatus.TBD
        context.user_data[UserDataKey.RETRIES] = "0"

        if context.user_data[UserDataKey.INSTANT]:
            try:
                timeout = calculate_timeout(
                    retries=0, base=120
                )  # todo: change to dynamic based on retries
                reservation_response = await set_reservation(
                    start, end, duration, user_data, timeout
                )
                logging.info(
                    f"✅ **2** {res_type} Reservation set for {user_data['cognome_nome']}"
                )
                await confirm_reservation(reservation_response["entry"])
                logging.info(
                    f"✅ **3** {res_type} Reservation confirmed for {user_data['cognome_nome']}"
                )
                context.user_data[UserDataKey.STATUS] = Status.SUCCESS
                context.user_data[UserDataKey.BOOKING_CODE] = (
                    f"{reservation_response['codice_prenotazione']}"
                )
                context.user_data[UserDataKey.SUCCESS_AT] = datetime.now(
                    ZoneInfo("Europe/Rome")
                )
                context.user_data[UserDataKey.UPDATED_AT] = datetime.now(
                    ZoneInfo("Europe/Rome")
                )
                request_status_message = "✅ Reservation *successful*!"
                retry_status_message = ""

            except Exception as e:
                logging.error(
                    f"❌ {res_type} Reservation failed for {user_data['cognome_nome']} — {e}"
                )
                context.user_data[UserDataKey.RETRIES] = "1"
                context.user_data[UserDataKey.STATUS] = Status.FAIL
                context.user_data[UserDataKey.BOOKING_CODE] = BookingCodeStatus.NA
                context.user_data[UserDataKey.FAIL_AT] = datetime.now(
                    ZoneInfo("Europe/Rome")
                )
                context.user_data[UserDataKey.UPDATED_AT] = datetime.now(
                    ZoneInfo("Europe/Rome")
                )
                request_status_message = (
                    "⛔ Reservation *failed*! *Slot not available*."
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
