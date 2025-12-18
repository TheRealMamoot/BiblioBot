import logging
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import BookingCodeStatus, States, Status
from src.biblio.db.fetch import fetch_reservation_by_id
from src.biblio.db.update import update_cancel_status
from src.biblio.reservation.reservation import cancel_reservation
from src.biblio.utils.keyboards import Keyboard, Label


async def cancelation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.RESERVATION_TYPE_BACK:
        await update.message.reply_text(
            "You are so determined, wow!",
            reply_markup=Keyboard.reservation_type(context.user_data["is_admin"]),
        )
        return States.RESERVE_TYPE

    choices: dict = context.user_data["cancelation_choices"]
    cancelation_id = next(
        (id for id, deatils in choices.items() if deatils["button"] == user_input), None
    )

    if not cancelation_id:
        await update.message.reply_text(
            "Pick from the list!",
        )
        return States.CANCELATION_SLOT_CHOICE

    context.user_data["cancelation_chosen_slot_id"] = cancelation_id
    logging.info(
        f"🔄 {update.effective_user} selected cancelation slot at {datetime.now(ZoneInfo('Europe/Rome'))}"
    )

    status: str = choices[cancelation_id]["status"].title()
    await update.message.reply_text(
        textwrap.dedent(
            f"""
            Are you sure you want to cancel this slot ?
            Codice Fiscale: *{context.user_data.get("codice_fiscale")}*
            Full Name: *{context.user_data.get("name")}*
            Email: *{context.user_data.get("email")}*
            On *{choices[cancelation_id]["selected_date"]}*
            From *{choices[cancelation_id]["start_time"]}* - *{choices[cancelation_id]["end_time"]}* (*{choices[cancelation_id]["selected_duration"]}* hours)
            Satus: *{(Status(status.lower())).emoji} {status}*
            """
        ),
        parse_mode="Markdown",
        reply_markup=Keyboard.cancelation_confirm(),
    )
    return States.CANCELATION_CONFIRMING


async def cancelation_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.CONFIRM_NO:
        choices: dict = context.user_data["cancelation_choices"]
        reservation_buttons = [choice["button"] for choice in choices.values()]
        await update.message.reply_text(
            "God kill me now! 😭",
            reply_markup=Keyboard.cancelation_options(reservation_buttons),
        )
        return States.CANCELATION_SLOT_CHOICE

    elif user_input == Label.CANCEL_CONFIRM_YES:
        reservation_id: str = context.user_data["cancelation_chosen_slot_id"]
        history = await fetch_reservation_by_id(reservation_id)
        failure = False
        if history:
            booking_code = history["booking_code"]
            if booking_code not in [BookingCodeStatus.TBD, BookingCodeStatus.NA]:
                try:
                    await cancel_reservation(
                        context.user_data["codice_fiscale"], booking_code
                    )
                except Exception:
                    try:
                        await cancel_reservation(
                            context.user_data["codice_fiscale"],
                            booking_code,
                            mode="update",
                        )
                    except Exception as e:
                        logging.error(
                            f"[CANCEL] {update.effective_user} cancelation was not completed at {datetime.now(ZoneInfo('Europe/Rome'))} -- {e}"
                        )
                        failure = True
                        await update.message.reply_text(
                            textwrap.dedent(
                                """
                                ⚠️ You don't appear to have an active reservation! 
                                This may be because the slot:
                                - has *expired*
                                - was *canceled manually*
                                - was *partly successful* 
                                (status: *existing*)
                                - wasn't *activated* by the library staff. 
                                ❗ In any case, you can now *book a new slot*.
                                """
                            ),
                            parse_mode="Markdown",
                            reply_markup=Keyboard.reservation_type(
                                context.user_data["is_admin"]
                            ),
                        )

            await update_cancel_status(reservation_id)
            logging.info(
                f"✔️ {update.effective_user} confirmed cancelation at {datetime.now(ZoneInfo('Europe/Rome'))}"
            )

            if not failure:
                await update.message.reply_text(
                    "✔️ Reservation canceled successfully!",
                    reply_markup=Keyboard.reservation_type(
                        context.user_data["is_admin"]
                    ),
                )
            return States.RESERVE_TYPE

        else:
            logging.info(
                f"⚠️ {update.effective_user} cancelation slot NOT FOUND at {datetime.now(ZoneInfo('Europe/Rome'))}"
            )
            await update.message.reply_text(
                "⚠️ Reservation cancelation usuccessfull!",
                reply_markup=Keyboard.reservation_type(context.user_data["is_admin"]),
            )
            return States.RESERVE_TYPE

    else:
        await update.message.reply_text(
            "Just click. Please! 😭",
        )
        return States.CANCELATION_CONFIRMING
