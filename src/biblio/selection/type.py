import logging
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from pandas import DataFrame
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import (
    show_cancel_message,
    show_donate_message,
    show_existing_reservations,
    show_help,
    show_support_message,
    show_user_agreement,
)
from src.biblio.config.config import Schedule, State, Status, UserDataKey
from src.biblio.utils.keyboards import Keyboard, Label

LIB_SCHEDULE = Schedule.weekly()


async def type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.ADMIN_PANEL and context.user_data[UserDataKey.IS_ADMIN]:
        await update.message.reply_text(
            "Welcome master!",
            reply_markup=Keyboard.admin_panel(),
        )
        return State.ADMIN_PANEL

    elif user_input == Label.CREDENTIALS_EDIT:
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
            parse_mode="Markdown",
            reply_markup=Keyboard.start(edit_credential_stage=True),
        )
        return State.CREDENTIALS

    elif user_input == Label.SLOT_LATER:
        await update.message.reply_text(
            "So, when will it be? 📅", reply_markup=Keyboard.date()
        )
        context.user_data[UserDataKey.INSTANT] = False
        logging.info(
            f"🔄 {update.effective_user} selected REGULAR reservation at {datetime.now(ZoneInfo('Europe/Rome'))}"
        )
        return State.CHOOSING_DATE

    elif user_input == Label.SLOT_INSTANT:
        now = datetime.now(ZoneInfo("Europe/Rome"))
        now_day = now.strftime("%A")
        now_date = now.strftime("%Y-%m-%d")

        open_time, close_time = LIB_SCHEDULE.get_hours(now.weekday())

        if now.hour < (open_time - 2) or now.hour >= close_time:
            await update.message.reply_text(
                "It's over for today! Go home. 😌",
                reply_markup=Keyboard.reservation_type(
                    context.user_data[UserDataKey.IS_ADMIN]
                ),
            )
            return State.RESERVE_TYPE

        # * Sundays are temporarily open
        # if week_day == 6:  # Sunday
        #     await update.message.reply_text(
        #         "It's Sunday! Come on, chill. 😌",
        #         reply_markup=Keyboard.reservation_type(context.user_data[UserDataKey.IS_ADMIN]),
        #     )
        #     return State.RESERVE_TYPE

        date = f"{now_day}, {now_date}"
        await update.message.reply_text(
            "So, when will it be? 🕑",
            reply_markup=Keyboard.time(date, instant=True),
        )
        context.user_data[UserDataKey.INSTANT] = True
        context.user_data[UserDataKey.SELECTED_DATE] = date
        logging.info(
            f"🔄 {update.effective_user} selected INSTANT reservation at {datetime.now(ZoneInfo('Europe/Rome'))}"
        )
        return State.CHOOSING_TIME

    elif user_input == Label.CURRENT_RESERVATIONS:
        text = await show_existing_reservations(update, context)
        if not text:
            text = "_No reservations found._"
        await update.message.reply_text(text, parse_mode="Markdown")
        return State.RESERVE_TYPE

    elif user_input == Label.CANCEL_RESERVATION:
        reservations = await show_existing_reservations(
            update, context, cancel_stage=True
        )
        choices = {}
        buttons = []

        if not isinstance(reservations, DataFrame):
            await update.message.reply_text(
                "_You have no reservations at the moment._", parse_mode="Markdown"
            )
            return State.RESERVE_TYPE

        for _, row in reservations.iterrows():
            if row["status"] in (Status.TERMINATED, Status.CANCELED):
                continue
            try:
                status = Status(row["status"]).emoji
            except ValueError:
                status = ""
            start_time_str = row["start_time"].strftime("%H:%M")
            end_time_str = row["end_time"].strftime("%H:%M")
            selected_date = row["selected_date"].strftime("%A %Y-%m-%d")
            button = f"{status} {selected_date} at {start_time_str} - {end_time_str}"

            choices[f"{row['id']}"] = {
                "selected_date": selected_date,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "selected_duration": row["selected_duration"],
                "booking_code": row["booking_code"],
                "status": row["status"],
                "button": button,
            }
            buttons.append(button)

        if len(buttons) == 0:
            await update.message.reply_text(
                "_You have no reservations at the moment._", parse_mode="Markdown"
            )
            return State.RESERVE_TYPE

        context.user_data[UserDataKey.CANCELATION_CHOICES] = choices

        logging.info(
            f"🔄 {update.effective_user} started cancelation at {datetime.now(ZoneInfo('Europe/Rome'))}"
        )
        await update.message.reply_text(
            show_cancel_message(),
            parse_mode="Markdown",
            reply_markup=Keyboard.cancelation_options(buttons),
        )
        return State.CANCELATION_SLOT_CHOICE

    elif user_input == Label.AVAILABLE_SLOTS:
        context.user_data[UserDataKey.STATE] = State.RESERVE_TYPE
        now = datetime.now(ZoneInfo("Europe/Rome"))

        open_time, close_time = LIB_SCHEDULE.get_hours(now.weekday())

        if now.hour < (open_time - 2) or now.hour >= close_time:
            await update.message.reply_text(
                "It's over for today! Go home. 😌",
                reply_markup=Keyboard.reservation_type(
                    context.user_data[UserDataKey.IS_ADMIN]
                ),
            )
            return State.RESERVE_TYPE

        time = now.replace(
            minute=(0 if now.minute < 30 else 30), second=0, microsecond=0
        )
        time = time.strftime("%H:%M")
        context.user_data[UserDataKey.SELECTED_TIME] = time

        await update.message.reply_text(
            "How many hours are we looking at? 🕦",
            parse_mode="Markdown",
            reply_markup=Keyboard.duration(time, context, show_available=True)[0],
        )
        return State.CHOOSING_AVAILABLE

    elif user_input == Label.HISTORY:
        keyboard = Keyboard.date(days_past=5, days_future=0, history_state=True)
        await update.message.reply_text(
            "So, when will it be? You can see the data for the past *6 days*. 📅",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        logging.info(
            f"🔄 {update.effective_user} selected History records at {datetime.now(ZoneInfo('Europe/Rome'))}"
        )
        return State.CHOOSING_DATE_HISTORY

    elif user_input == Label.HELP:
        await update.message.reply_text(
            show_help(),
            parse_mode="Markdown",
            reply_markup=Keyboard.reservation_type(
                context.user_data[UserDataKey.IS_ADMIN]
            ),
        )
        return State.RESERVE_TYPE

    elif user_input == Label.DONATE:
        await update.message.reply_text(
            show_donate_message(),
            parse_mode="Markdown",
            reply_markup=Keyboard.reservation_type(
                context.user_data[UserDataKey.IS_ADMIN]
            ),
        )
        return State.RESERVE_TYPE

    elif user_input == Label.AGREEMENT:
        await update.message.reply_text(
            show_user_agreement(),
            parse_mode="Markdown",
            reply_markup=Keyboard.reservation_type(
                context.user_data[UserDataKey.IS_ADMIN]
            ),
        )
        return State.RESERVE_TYPE

    elif user_input == Label.FEEDBACK:
        await update.message.reply_text(
            show_support_message(),
            parse_mode="Markdown",
            reply_markup=Keyboard.reservation_type(
                context.user_data[UserDataKey.IS_ADMIN]
            ),
        )
        return State.RESERVE_TYPE

    else:
        await update.message.reply_text(
            "The options are right there you know. Pick one, that's it.",
            reply_markup=Keyboard.reservation_type(
                is_admin=context.user_data[UserDataKey.IS_ADMIN]
            ),
        )
        return State.RESERVE_TYPE
