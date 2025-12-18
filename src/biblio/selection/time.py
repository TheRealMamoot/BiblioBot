import logging
import textwrap
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.bot.messages import show_existing_reservations, show_slot_history
from src.biblio.config.config import Schedule, State, UserDataKey
from src.biblio.utils.keyboards import Keyboard, Label
from src.biblio.utils.utils import utc_tuple_to_rome_time
from src.biblio.utils.validation import normalize_slot_input, time_not_overlap

LIB_SCHEDULE = Schedule.weekly()
JOB_SCHEDULE = Schedule.jobs(daylight_saving=True)
JOB_START, JOB_END = JOB_SCHEDULE.get_hours("availability")
MIN_AVAILABILITY_START = utc_tuple_to_rome_time(hour_minute=(JOB_START, 0))
MAX_AVAILABILITY_END = utc_tuple_to_rome_time(hour_minute=(JOB_END, 59))


# TODO: add check for time selection
async def time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        if context.user_data[UserDataKey.INSTANT]:
            await update.message.reply_text(
                textwrap.dedent("Just decide already!"),
                parse_mode="Markdown",
                reply_markup=Keyboard.reservation_type(context.user_data[UserDataKey.IS_ADMIN]),
            )
            return State.RESERVE_TYPE

        keyboard = Keyboard.date()
        await update.message.reply_text(
            "Choose a date, AGAIN! 😒", reply_markup=keyboard
        )
        return State.CHOOSING_DATE

    elif user_input == Label.CURRENT_RESERVATIONS:
        await update.message.reply_text(
            await show_existing_reservations(update, context),
            parse_mode="Markdown",
        )
        return State.CHOOSING_TIME

    elif user_input == Label.AVAILABLE_SLOTS:
        context.user_data[UserDataKey.STATE] = State.CHOOSING_TIME
        now = datetime.now(ZoneInfo("Europe/Rome"))

        open_time, close_time = LIB_SCHEDULE.get_hours(now.weekday())

        if now.hour < (open_time - 2) or now.hour >= close_time:
            await update.message.reply_text(
                "It's over for today! Go home. 😌",
                reply_markup=Keyboard.time(
                    selected_date=context.user_data.get(UserDataKey.SELECTED_DATE),
                    instant=context.user_data.get(UserDataKey.INSTANT),
                ),
            )
            return State.CHOOSING_TIME

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

    try:
        datetime.strptime(user_input, "%H:%M")
        time_obj = datetime.strptime(user_input, "%H:%M").replace(
            tzinfo=ZoneInfo("Europe/Rome")
        )
        if (time_obj.hour + time_obj.minute / 60) < 9:
            await update.message.reply_text(
                textwrap.dedent(
                    """
                ⚠️ Starting time can't be before 09:00! 
                Choose a different time.
                """
                )
            )
            return State.CHOOSING_TIME

    except ValueError:
        await update.message.reply_text(
            "Not that difficult to pick an option form the list! Just saying. 🤷‍♂️"
        )
        return State.CHOOSING_TIME

    if not await time_not_overlap(update, context):
        await update.message.reply_text(
            textwrap.dedent(
                """
            ⚠️ Your reservation overlaps with an existing one! 
            Choose a different time.
            """
            )
        )
        return State.CHOOSING_TIME
    context.user_data[UserDataKey.SELECTED_TIME] = user_input
    keyboard = Keyboard.duration(user_input, context)[
        0
    ]  # [0] for the reply, [1] for the values

    await update.message.reply_text(
        "How long will you absolutely NOT be productive over there? 🕦 Give me hours.",
        reply_markup=keyboard,
    )

    res_type = "INSTANT" if context.user_data[UserDataKey.INSTANT] else "REGULAR"
    logging.info(
        f"🔄 {update.effective_user} selected {res_type} time at {datetime.now(ZoneInfo('Europe/Rome'))}"
    )
    return State.CHOOSING_DUR


async def slot_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        keyboard = Keyboard.date(days_past=5, days_future=0, history_state=True)
        await update.message.reply_text(
            "Choose a date, AGAIN! 😒", reply_markup=keyboard
        )
        return State.CHOOSING_DATE_HISTORY

    keyboard = Keyboard.slot(context.user_data[UserDataKey.SLOT_HISTORY])
    buttons = [button.text for row in keyboard.keyboard for button in row][
        :-1
    ]  # excluding the back button

    if user_input not in buttons:
        await update.message.reply_text("Just pick an option form the list! 😒")
        return State.CHOOSING_SLOT

    context.user_data[UserDataKey.SLOT] = user_input

    await update.message.reply_text(
        textwrap.dedent(
            f"""
            *Slot {context.user_data[UserDataKey.SLOT]}*

            📈 You can view how the availability of seats changed over time.

            ⏰ *Pick* a starting time from below *OR*:

            ✍️ *Manually write* the *starting time* for the time range you’d like to see the activity for.

            ❗ Example: *7:15*, *12:20*, *8*, etc. 
            """
        ),
        parse_mode="Markdown",
        reply_markup=Keyboard.filter(start_state=True),
    )

    logging.info(
        f"🔄 {update.effective_user} selected {context.user_data[UserDataKey.SLOT]} at {datetime.now(ZoneInfo('Europe/Rome'))}"
    )
    return State.CHOOSING_FILTER_START


async def filter_start_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        keyboard = Keyboard.slot(context.user_data[UserDataKey.SLOT_HISTORY])
        await update.message.reply_text("Just choose a slot. 😒", reply_markup=keyboard)
        return State.CHOOSING_SLOT

    elif user_input == Label.HOME:
        keyboard = Keyboard.reservation_type(context.user_data[UserDataKey.IS_ADMIN])
        await update.message.reply_text(
            "Let's try again, shall we? 😪", reply_markup=keyboard
        )
        return State.RESERVE_TYPE

    filter_start = normalize_slot_input(hour=user_input)
    if filter_start is None:
        await update.message.reply_text(
            textwrap.dedent(
                """
                ❗ *Invalid format*. 
                *Try something like 7, 8:10, or 7:30.*
                """
            ),
            parse_mode="Markdown",
        )
        return State.CHOOSING_FILTER_START

    filter_time = datetime.strptime(filter_start, "%H:%M").time()
    if not (
        time(*MIN_AVAILABILITY_START) <= filter_time <= time(*MAX_AVAILABILITY_END)
    ):
        await update.message.reply_text(
            textwrap.dedent(
                f"""
                ⛔ *Out of range!*
                Choose a time between *{time(*MIN_AVAILABILITY_START).strftime("%H:%M")}* and *{time(*MAX_AVAILABILITY_END).strftime("%H:%M")}*."""
            ),
            parse_mode="Markdown",
        )
        return State.CHOOSING_FILTER_START

    context.user_data[UserDataKey.FILTER_START] = filter_start

    await update.message.reply_text(
        textwrap.dedent(
            f"""
            ⏰ You Picked: *{filter_start}*. 
            Now *Pick* an ending time from below *OR*:

            ✍️ *Manually write* any hour for the time range.

            ❗ *Don't choose a time before your starting time!*
            """
        ),
        parse_mode="Markdown",
        reply_markup=Keyboard.filter(start_state=False),
    )
    logging.info(
        f"🔄 {update.effective_user} selected filter start: {filter_start} at {datetime.now(ZoneInfo('Europe/Rome'))}"
    )
    return State.CHOOSING_FILTER_END


async def filter_end_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_input = update.message.text.strip()

    if user_input == Label.BACK:
        keyboard = Keyboard.filter(start_state=True)
        await update.message.reply_text("Starting time please!", reply_markup=keyboard)
        return State.CHOOSING_FILTER_START

    elif user_input == Label.HOME:
        keyboard = Keyboard.reservation_type(context.user_data[UserDataKey.IS_ADMIN])
        await update.message.reply_text(
            "Let's try again, shall we? 😪", reply_markup=keyboard
        )
        return State.RESERVE_TYPE

    filter_end = normalize_slot_input(hour=user_input)
    if filter_end is None:
        await update.message.reply_text(
            textwrap.dedent(
                """
                ❗ *Invalid format*. 
                *Try something like 7, 8:10, or 7:30.*
                """
            ),
            parse_mode="Markdown",
        )
        return State.CHOOSING_FILTER_END

    end_time = datetime.strptime(filter_end, "%H:%M").time()
    start_time = datetime.strptime(context.user_data[UserDataKey.FILTER_START], "%H:%M").time()

    if not (start_time <= end_time <= time(*MAX_AVAILABILITY_END)):
        await update.message.reply_text(
            textwrap.dedent(
                f"""
                ⛔ *Out of range!*
                The end time must be:
                – *After or equal* to your start time: *{start_time.strftime("%H:%M")}*
                – *Before or equal* to the latest available time: *{time(*MAX_AVAILABILITY_END).strftime("%H:%M")}*
                """
            ),
            parse_mode="Markdown",
        )
        return State.CHOOSING_FILTER_END

    context.user_data[UserDataKey.FILTER_END] = filter_end
    await update.message.reply_text(
        f"🔄 Preparing history: *{context.user_data[UserDataKey.FILTER_START]} - {context.user_data[UserDataKey.FILTER_END]}*",
        parse_mode="Markdown",
    )

    history_graph = await show_slot_history(
        update=update,
        history=context.user_data[UserDataKey.SLOT_HISTORY],
        date=context.user_data[UserDataKey.SELECTED_DATE_HISTORY],
        slot=context.user_data[UserDataKey.SLOT],
        start=context.user_data[UserDataKey.FILTER_START],
        end=context.user_data[UserDataKey.FILTER_END],
    )
    if history_graph is None:
        keyboard = Keyboard.filter(start_state=False)
        await update.message.reply_text(
            text="ℹ️ No data available for this time range. Try again.",
            reply_markup=keyboard,
        )
        return State.CHOOSING_FILTER_END

    await update.message.reply_photo(
        photo=history_graph, reply_markup=Keyboard.filter(start_state=True)
    )
    await update.message.reply_text("🆕 Pick the starting time again.")
    return State.CHOOSING_FILTER_START
