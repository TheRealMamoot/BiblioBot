from datetime import datetime, timedelta
from math import ceil
from zoneinfo import ZoneInfo

from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from src.biblio.utils.utils import generate_days


class Label:
    AGREEMENT = '📝 Agreement'
    AGREEMENT_AGREE = '👍 Yes, I agree.'
    AGREEMENT_DISAGREE = "👎 No, I don't agree."
    BACK = '⬅️'
    CANCEL_CONFIRM_YES = "📅❌ Yes, I'm sure."
    CANCEL_RESERVATION = '🚫 Cancel reservation'
    CONFIRM_NO = '⬅️ No, take me back.'
    CONFIRM_YES = '✅ Yes, all looks good.'
    CONTINUE = '👍 Yes, go right on.'
    CREDENTIALS_EDIT = '⬅️ Edit credentials'
    CREDENTIALS_NEW = '🆕 No, I want to change.'
    CREDENTIALS_RETURN = '➡️ Changed my mind.'
    CURRENT_RESERVATIONS = '🗓️ Current reservations'
    DONATE = '🫶 Donate'
    FEEDBACK = '💡 Feedback'
    HELP = '❓ Help'
    RESERVATION_TYPE_BACK = '⬅️ Back to reservation type'
    RESERVATION_TYPE_EDIT = '⬅️ Edit reservation type'
    RETRY = "🆕 Let's go again!"
    SLOT_INSTANT = '⚡️ I need a slot for now.'
    SLOT_LATER = '⏳ I need a slot for later.'
    SUPPORT = '🤝 Reach out!'


class Keyboard:
    @staticmethod
    def agreement():
        return ReplyKeyboardMarkup(
            [[KeyboardButton(Label.AGREEMENT_AGREE)], [KeyboardButton(Label.AGREEMENT_DISAGREE)]],
            resize_keyboard=True,
        )

    @staticmethod
    def start(edit_credential_stage: bool = False):
        if edit_credential_stage:
            return ReplyKeyboardMarkup([[KeyboardButton(Label.CREDENTIALS_RETURN)]], resize_keyboard=True)
        return ReplyKeyboardMarkup(
            [[KeyboardButton(Label.SUPPORT)], [KeyboardButton(Label.HELP)]], resize_keyboard=True
        )

    @staticmethod
    def welcome_back():
        return ReplyKeyboardMarkup(
            [[KeyboardButton(Label.CONTINUE)], [KeyboardButton(Label.CREDENTIALS_NEW)]],
            resize_keyboard=True,
        )

    @staticmethod
    def reservation_type():
        keyboard_buttons = [
            [KeyboardButton(Label.DONATE), KeyboardButton(Label.FEEDBACK)],
            [KeyboardButton(Label.CURRENT_RESERVATIONS)],
            [KeyboardButton(Label.SLOT_LATER)],
            [KeyboardButton(Label.SLOT_INSTANT)],
            [KeyboardButton(Label.CANCEL_RESERVATION)],
            [KeyboardButton(Label.CREDENTIALS_EDIT)],
            [KeyboardButton(Label.AGREEMENT), KeyboardButton(Label.HELP)],
        ]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def date():
        dates = generate_days()
        keyboard_buttons = []
        for i in range(0, len(dates), 3):
            row = [KeyboardButton(date) for date in dates[i : i + 3]]
            keyboard_buttons.append(row)

        keyboard_buttons.insert(0, [KeyboardButton(Label.CURRENT_RESERVATIONS)])
        keyboard_buttons.append([KeyboardButton(Label.RESERVATION_TYPE_EDIT)])

        return ReplyKeyboardMarkup(keyboard_buttons)

    @staticmethod
    def time(selected_date: str, instant: bool = False):
        now = datetime.now(ZoneInfo('Europe/Rome'))
        date_obj = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')
        date_obj = date_obj.replace(tzinfo=ZoneInfo('Europe/Rome'))
        year = now.year if now.month <= date_obj.month else now.year + 1
        full_date = datetime(year, date_obj.month, date_obj.day, tzinfo=ZoneInfo('Europe/Rome'))
        end_hour = 13 if full_date.weekday() == 5 else 22
        current = datetime(year, date_obj.month, date_obj.day, 9, 0, tzinfo=ZoneInfo('Europe/Rome'))
        if full_date.date() == now.date() and now.hour >= 9:
            hour = now.hour
            minute = 0 if now.minute < 30 else 30
            current = datetime(year, date_obj.month, date_obj.day, hour, minute, tzinfo=ZoneInfo('Europe/Rome'))
        print(f'curent: {current}')

        times = []
        while current.hour < end_hour or (current.hour == end_hour and current.minute == 0):
            times.append(current.strftime('%H:%M'))
            current += timedelta(minutes=30)

        keyboard_buttons = [[KeyboardButton(time) for time in times[i : i + 5]] for i in range(0, len(times), 5)]
        keyboard_buttons.append([KeyboardButton(Label.BACK)])

        if instant:
            keyboard_buttons.insert(0, [KeyboardButton(Label.CURRENT_RESERVATIONS)])

        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def duration(selected_time: str, context: ContextTypes.DEFAULT_TYPE):
        selected_date = context.user_data.get('selected_date')
        selected_date = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')

        time_obj = datetime.strptime(selected_time, '%H:%M')
        date_obj = datetime(selected_date.year, selected_date.month, selected_date.day, time_obj.hour, time_obj.minute)

        end_hour = 14 if selected_date.weekday() == 5 else 23
        selected_date = selected_date + timedelta(hours=end_hour)

        durations = ceil((selected_date - date_obj + timedelta(minutes=30)).seconds / 3600)
        durations = list(range(1, durations))

        keyboard_buttons = [[KeyboardButton(dur) for dur in durations[i : i + 8]] for i in range(0, len(durations), 8)]
        keyboard_buttons.append([KeyboardButton(Label.BACK)])

        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True), durations

    @staticmethod
    def confirmation():
        keyboard_buttons = [[KeyboardButton(Label.CONFIRM_YES)], [KeyboardButton(Label.CONFIRM_NO)]]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def retry():
        keyboard_buttons = [
            [KeyboardButton(Label.RETRY)],
            [KeyboardButton(Label.CURRENT_RESERVATIONS)],
            [KeyboardButton(Label.CANCEL_RESERVATION)],
            [KeyboardButton(Label.FEEDBACK)],
            [KeyboardButton(Label.DONATE)],
        ]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def cancelation_options(reservations: list):
        keyboard_buttons = [[KeyboardButton(slot)] for slot in reservations]
        keyboard_buttons.append([KeyboardButton(Label.RESERVATION_TYPE_BACK)])
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def cancelation_confirm():
        keyboard_buttons = [[KeyboardButton(Label.CANCEL_CONFIRM_YES)], [KeyboardButton(Label.CONFIRM_NO)]]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)
