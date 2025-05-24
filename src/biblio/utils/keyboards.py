from datetime import datetime, timedelta
from math import ceil
from zoneinfo import ZoneInfo

from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from src.biblio.utils.utils import generate_days


def generate_agreement_keyboard():
    keyboard_buttons = [[KeyboardButton('👍 Yes, I agree.')], [KeyboardButton("👎 No, I don't agree.")]]
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def generate_start_keyboard(edit_credential_stage: bool = False):
    keyboard_buttons = [[KeyboardButton('🤝 Reach out!')], [KeyboardButton('❓ Help')]]
    if edit_credential_stage:
        keyboard_buttons = [[KeyboardButton('➡️ Changed my mind.')]]

    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def generate_welcome_back_keyboard():
    keyboard_buttons = [
        [KeyboardButton('👍 Yes, go right on.')],
        [KeyboardButton('🆕 No, I want to change.')],
    ]
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def generate_reservation_type_keyboard():
    keyboard_buttons = [
        [KeyboardButton('🫶 Donate')],
        [KeyboardButton('🗓️ Current reservations')],
        [KeyboardButton('⏳ I need a slot for later.')],
        [KeyboardButton('⚡️ I need a slot for now.')],
        [KeyboardButton('🚫 Cancel reservation')],
        [KeyboardButton('⬅️ Edit credentials')],
        [KeyboardButton('📝 Agreement'), KeyboardButton('❓ Help')],
    ]
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def generate_date_keyboard():
    dates = generate_days()
    keyboard_buttons = []
    for i in range(0, len(dates), 3):
        row = [KeyboardButton(date) for date in dates[i : i + 3]]
        keyboard_buttons.append(row)

    keyboard_buttons.insert(0, [KeyboardButton('🗓️ Current reservations')])
    keyboard_buttons.append([KeyboardButton('⬅️ Edit reservation type')])

    return ReplyKeyboardMarkup(keyboard_buttons)


def generate_time_keyboard(selected_date: str, instant: bool = False):
    now = datetime.now(ZoneInfo('Europe/Rome'))
    date_obj = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')
    date_obj = date_obj.replace(tzinfo=ZoneInfo('Europe/Rome'))
    year = now.year if now.month <= date_obj.month else now.year + 1
    full_date = datetime(year, date_obj.month, date_obj.day, tzinfo=ZoneInfo('Europe/Rome'))
    end_hour = 13 if full_date.weekday() == 5 else 22  # Saturdays

    # Check starting time.
    current = datetime(year, date_obj.month, date_obj.day, 9, 0, tzinfo=ZoneInfo('Europe/Rome'))
    if full_date.date() == now.date():
        if now.hour < 9:
            current = datetime(year, date_obj.month, date_obj.day, 9, 0, tzinfo=ZoneInfo('Europe/Rome'))
        else:
            hour = now.hour
            minute = 0 if now.minute < 30 else 30
            current = datetime(year, date_obj.month, date_obj.day, hour, minute, tzinfo=ZoneInfo('Europe/Rome'))
    times = []
    while current.hour < end_hour or (current.hour == end_hour and current.minute == 0):
        times.append(current.strftime('%H:%M'))
        current += timedelta(minutes=30)

    keyboard_buttons = [[KeyboardButton(time) for time in times[i : i + 5]] for i in range(0, len(times), 5)]
    keyboard_buttons.append([KeyboardButton('⬅️')])

    if instant:
        keyboard_buttons.insert(0, [KeyboardButton('🗓️ Current reservations')])

    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def generate_duration_keyboard(selected_time: str, context: ContextTypes.DEFAULT_TYPE):
    selected_date = context.user_data.get('selected_date')
    selected_date = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')

    time_obj = datetime.strptime(selected_time, '%H:%M')
    date_obj = datetime(selected_date.year, selected_date.month, selected_date.day, time_obj.hour, time_obj.minute)

    end_hour = 14 if selected_date.weekday() == 5 else 23  # Saturdays
    selected_date = selected_date + timedelta(hours=end_hour)

    durations = ceil(
        (selected_date - date_obj + timedelta(minutes=30)).seconds / 3600
    )  # ceil in case of **:30 start time formats
    durations = list(range(1, durations))

    keyboard_buttons = [[KeyboardButton(dur) for dur in durations[i : i + 8]] for i in range(0, len(durations), 8)]
    keyboard_buttons.append([KeyboardButton('⬅️')])

    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True), durations


def generate_confirmation_keyboard():
    keyboard_buttons = [[KeyboardButton('✅ Yes, all looks good.')], [KeyboardButton('⬅️ No, take me back.')]]
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def generate_retry_keyboard():
    keyboard_buttons = [
        [KeyboardButton("🆕 Let's go again!")],
        [KeyboardButton('🗓️ Current reservations')],
        [KeyboardButton('🚫 Cancel reservation')],
        [KeyboardButton('💡 Feedback')],
        [KeyboardButton('🫶 Donate')],
    ]
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def generate_cancelation_options_keyboard(reservations: list):
    keyboard_buttons = [[KeyboardButton(slot)] for slot in reservations]
    keyboard_buttons.append([KeyboardButton('⬅️ Back to reservation type')])
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)


def generate_cancelation_confirm_keyboard():
    keyboard_buttons = [[KeyboardButton("📅❌ Yes, I'm sure.")], [KeyboardButton('⬅️ No, take me back.')]]
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)
