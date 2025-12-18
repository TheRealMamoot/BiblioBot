import logging
import textwrap
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import State, UserDataKey
from src.biblio.reservation.reservation import get_available_slots
from src.biblio.utils.keyboards import Keyboard, Label
from src.biblio.utils.validation import duration_overlap


async def duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        keyboard = Keyboard.time(
            context.user_data.get(UserDataKey.SELECTED_DATE),
            instant=context.user_data[UserDataKey.INSTANT],
        )
        await update.message.reply_text(
            "Make up your mind! choose a time ALREADY 🙄", reply_markup=keyboard
        )
        return State.CHOOSING_TIME

    selected_time = context.user_data.get(UserDataKey.SELECTED_TIME)
    duration_selection = Keyboard.duration(selected_time, context)[
        1
    ]  # [0] for the reply, [1] for the values
    max_dur = max(duration_selection)

    if not user_input.isdigit():
        await update.message.reply_text(
            "Now you're just messing with me. Just pick the duration!"
        )
        return State.CHOOSING_DUR

    if int(user_input) > max_dur:
        await update.message.reply_text(
            "Well they are not going to let you sleep there! Try again. 🤷‍♂️"
        )
        return State.CHOOSING_DUR

    if await duration_overlap(update, context):
        await update.message.reply_text(
            textwrap.dedent(
                """
            ⚠️ Your reservation overlaps with an existing one! 
            Choose a different duration.
            """
            )
        )
        return State.CHOOSING_DUR

    context.user_data[UserDataKey.SELECTED_DURATION] = user_input
    res_type = "INSTANT" if context.user_data[UserDataKey.INSTANT] else "REGULAR"
    logging.info(
        f"🔄 {update.effective_user} selected {res_type} duration at {datetime.now(ZoneInfo('Europe/Rome'))}"
    )

    start_time = context.user_data.get(UserDataKey.SELECTED_TIME)
    end_time = datetime.strptime(start_time, "%H:%M") + timedelta(
        hours=int(context.user_data.get(UserDataKey.SELECTED_DURATION))
    )
    end_time = end_time.strftime("%H:%M")

    keyboard = Keyboard.confirmation()
    await update.message.reply_text(
        textwrap.dedent(
            f"""
            All looks good?
            Codice Fiscale: *{context.user_data.get(UserDataKey.CODICE_FISCALE)}*
            Full Name: *{context.user_data.get(UserDataKey.NAME)}*
            Email: *{context.user_data.get(UserDataKey.EMAIL)}*
            On *{context.user_data.get(UserDataKey.SELECTED_DATE)}*
            From *{start_time}* - *{end_time}* (*{context.user_data.get(UserDataKey.SELECTED_DURATION)} Hours*)
            """
        ),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return State.CONFIRMING


async def duration_availability(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        state = context.user_data.get(UserDataKey.STATE)
        instant = True if context.user_data.get(UserDataKey.INSTANT) else False
        date = context.user_data.get(UserDataKey.SELECTED_DATE)
        keyboard = (
            Keyboard.reservation_type(context.user_data[UserDataKey.IS_ADMIN])
            if state == State.RESERVE_TYPE
            else Keyboard.date()
            if state == State.CHOOSING_DATE
            else Keyboard.time(selected_date=date, instant=instant)
            if state == State.CHOOSING_TIME
            else Keyboard.retry()
            if state == State.RETRY
            else None
        )
        await update.message.reply_text("Whatever 🙄", reply_markup=keyboard)
        return state

    if not user_input.isdigit():
        await update.message.reply_text(
            "Now you're just messing with me. Just pick the duration!"
        )
        return State.CHOOSING_AVAILABLE

    selected_time = context.user_data.get(UserDataKey.SELECTED_TIME)
    duration_selection = Keyboard.duration(selected_time, context, show_available=True)[
        1
    ]
    max_dur = max(duration_selection)

    if int(user_input) > max_dur:
        await update.message.reply_text(
            "Well they are not going to let you sleep there! Try again. 🤷‍♂️"
        )
        return State.CHOOSING_AVAILABLE

    hour = int(int(user_input) * 60 * 60)
    await update.message.reply_text(
        textwrap.dedent("🔄 Getting data..."),
        parse_mode="Markdown",
    )

    try:
        slots = await get_available_slots(hour=str(hour))
    except Exception:
        logging.error("[GET] Failed to fetch available slots")
        await update.message.reply_text(
            "😵‍💫 Something went wrong while checking availability.\nPlease try again in a moment."
        )
        return State.CHOOSING_AVAILABLE

    if not slots:
        formatted = "_There are no free slots at the moment_"
    else:
        message_lines = []
        for slot, free in slots.items():
            status = (
                "🔴"
                if free == 0
                else "🟠"
                if free < 10
                else "🟡"
                if free < 20
                else "🟢"
            )
            message_lines.append(f"{slot} | {str(free).ljust(3)} {status}")

        formatted = "```\n" + "\n".join(message_lines) + "\n```"

    await update.message.reply_text(
        textwrap.dedent(f"*Free Slots:*\n{formatted}"),
        parse_mode="Markdown",
    )

    return State.CHOOSING_AVAILABLE
