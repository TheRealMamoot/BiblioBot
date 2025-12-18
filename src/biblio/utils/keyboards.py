from datetime import datetime, timedelta
from enum import Enum
from math import ceil
from zoneinfo import ZoneInfo

from pandas import DataFrame
from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from src.biblio.config.config import Schedule
from src.biblio.utils.utils import generate_days

LIB_SCHEDULE = Schedule.weekly()


class Label(str, Enum):
    AGREEMENT = "📝 Agreement"
    AGREEMENT_AGREE = "👍 Yes, I agree."
    AGREEMENT_DISAGREE = "👎 No, I don't agree."
    AVAILABLE_SLOTS = "🗒️ Available slots"
    BACK = "⬅️"
    CANCEL_CONFIRM_YES = "📅❌ Yes, I'm sure."
    CANCEL_RESERVATION = "🚫 Cancel reservation"
    CONFIRM_NO = "⬅️ No, take me back."
    CONFIRM_YES = "✅ Yes, all looks good."
    CONTINUE = "👍 Yes, go right on."
    CREDENTIALS_EDIT = "🪪 Edit credentials"
    CREDENTIALS_NEW = "🆕 No, I want to change."
    CREDENTIALS_RETURN = "⬅️ Changed my mind."
    CURRENT_RESERVATIONS = "🗓️ Current reservations"
    ADMIN_PANEL = "🛡️ Admin panel"
    ADMIN_SEND_NOTIF = "🔔 Send notification"
    DONATE = "🫶 Donate"
    FEEDBACK = "💡 Feedback"
    HELP = "❓ Help"
    HISTORY = "📊 Slots history"
    HOME = "🏠 Home"
    RESERVATION_TYPE_BACK = "⬅️ Back to reservation type"
    RESERVATION_TYPE_EDIT = "⬅️ Edit reservation type"
    RETRY = "🆕 Let's go again!"
    SLOT_INSTANT = "⚡️ I need a slot for now."
    SLOT_LATER = "⏳ I need a slot for later."
    SUPPORT = "🤝 Reach out!"


class Keyboard:
    @staticmethod
    def agreement():
        return ReplyKeyboardMarkup(
            [
                [KeyboardButton(Label.AGREEMENT_AGREE)],
                [KeyboardButton(Label.AGREEMENT_DISAGREE)],
            ],
            resize_keyboard=True,
        )

    @staticmethod
    def start(edit_credential_stage: bool = False):
        if edit_credential_stage:
            return ReplyKeyboardMarkup(
                [[KeyboardButton(Label.CREDENTIALS_RETURN)]], resize_keyboard=True
            )
        return ReplyKeyboardMarkup(
            [[KeyboardButton(Label.SUPPORT)], [KeyboardButton(Label.HELP)]],
            resize_keyboard=True,
        )

    @staticmethod
    def welcome_back(is_admin=False):
        keyboard_buttons = [
            [KeyboardButton(Label.CONTINUE)],
            [KeyboardButton(Label.CREDENTIALS_NEW)],
        ]
        if is_admin:
            keyboard_buttons.insert(0, [KeyboardButton(Label.ADMIN_PANEL)])
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def admin_panel():
        keyboard_buttons = [
            [KeyboardButton(Label.ADMIN_SEND_NOTIF)],
            [KeyboardButton(Label.BACK)],
        ]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def admin_notif(confirm_stage=False):
        keyboard_buttons = [[KeyboardButton(Label.BACK)]]

        if confirm_stage:
            keyboard_buttons = [
                [KeyboardButton(Label.CONFIRM_YES)],
                [KeyboardButton(Label.CONFIRM_NO)],
            ]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def reservation_type(is_admin=False):
        keyboard_buttons = [
            [KeyboardButton(Label.DONATE), KeyboardButton(Label.FEEDBACK)],
            [
                KeyboardButton(Label.HISTORY),
                KeyboardButton(Label.AVAILABLE_SLOTS),
            ],
            [KeyboardButton(Label.CURRENT_RESERVATIONS)],
            [KeyboardButton(Label.SLOT_LATER)],
            [KeyboardButton(Label.SLOT_INSTANT)],
            [KeyboardButton(Label.CANCEL_RESERVATION)],
            [KeyboardButton(Label.CREDENTIALS_EDIT)],
            [KeyboardButton(Label.AGREEMENT), KeyboardButton(Label.HELP)],
        ]
        if is_admin:
            keyboard_buttons.insert(0, [KeyboardButton(Label.ADMIN_PANEL)])
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def date(days_past: int = 0, days_future: int = 5, history_state=False):
        dates = generate_days(past=days_past, future=days_future)
        keyboard_buttons = []
        n = 3
        for i in range(0, len(dates), n):
            row = [KeyboardButton(date) for date in dates[i : i + n]]
            keyboard_buttons.append(row)
        if not history_state:
            keyboard_buttons.insert(
                0,
                [
                    KeyboardButton(Label.CURRENT_RESERVATIONS),
                    KeyboardButton(Label.AVAILABLE_SLOTS),
                ],
            )
        keyboard_buttons.append([KeyboardButton(Label.RESERVATION_TYPE_EDIT)])

        return ReplyKeyboardMarkup(keyboard_buttons)

    @staticmethod
    def time(selected_date: str, instant: bool = False):
        now = datetime.now(ZoneInfo("Europe/Rome"))
        date_obj = datetime.strptime(selected_date.split(" ")[-1], "%Y-%m-%d")
        date_obj = date_obj.replace(tzinfo=ZoneInfo("Europe/Rome"))
        year = now.year if now.month <= date_obj.month else now.year + 1
        full_date = datetime(
            year, date_obj.month, date_obj.day, tzinfo=ZoneInfo("Europe/Rome")
        )
        start_hour, end_hour = LIB_SCHEDULE.get_hours(full_date.weekday())
        current = datetime(
            year,
            date_obj.month,
            date_obj.day,
            start_hour,
            0,
            tzinfo=ZoneInfo("Europe/Rome"),
        )
        if full_date.date() == now.date() and now.hour >= start_hour:
            hour = now.hour
            minute = 0 if now.minute < 30 else 30
            current = datetime(
                year,
                date_obj.month,
                date_obj.day,
                hour,
                minute,
                tzinfo=ZoneInfo("Europe/Rome"),
            )
        print(f"curent: {current}")

        times = []
        while current.hour < end_hour or (
            current.hour == end_hour and current.minute == 0
        ):
            times.append(current.strftime("%H:%M"))
            current += timedelta(minutes=30)

        n = 5
        keyboard_buttons = [
            [KeyboardButton(time) for time in times[i : i + n]]
            for i in range(0, len(times), n)
        ]
        keyboard_buttons.append([KeyboardButton(Label.BACK)])

        if instant:
            keyboard_buttons.insert(
                0,
                [
                    KeyboardButton(Label.CURRENT_RESERVATIONS),
                    KeyboardButton(Label.AVAILABLE_SLOTS),
                ],
            )

        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def slot(history: DataFrame):
        slots = list(history["slot"].unique())
        n = 3
        keyboard_buttons = [
            [KeyboardButton(slot) for slot in slots[i : i + n]]
            for i in range(0, len(slots), n)
        ]
        keyboard_buttons.insert(0, [KeyboardButton(Label.BACK)])

        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def filter(start_state=True):
        start_times = [
            "07:00",
            "07:10",
            "07:15",
            "07:20",
            "07:25",
            "07:30",
            "07:35",
            "07:40",
            "07:45",
            "07:50",
        ]
        end_times = [
            "07:10",
            "07:20",
            "07:30",
            "07:40",
            "07:50",
            "08:00",
            "08:10",
            "08:20",
            "08:30",
            "08:40",
        ]
        times = start_times if start_state else end_times

        n = 5
        keyboard_buttons = [
            [KeyboardButton(t) for t in times[i : i + n]]
            for i in range(0, len(times), n)
        ]
        keyboard_buttons.append(
            [KeyboardButton(Label.BACK), KeyboardButton(Label.HOME)]
        )
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def duration(
        selected_time: str,
        context: ContextTypes.DEFAULT_TYPE,
        show_available: bool = False,
    ):
        if show_available:
            selected_date = datetime.now()
        else:
            selected_date: str = context.user_data.get("selected_date")
            selected_date = datetime.strptime(selected_date.split(" ")[-1], "%Y-%m-%d")

        time_obj = datetime.strptime(selected_time, "%H:%M")
        date_obj = datetime(
            selected_date.year,
            selected_date.month,
            selected_date.day,
            time_obj.hour,
            time_obj.minute,
        )

        _, end_hour = LIB_SCHEDULE.get_hours(selected_date.weekday())
        end_dt = datetime(
            selected_date.year, selected_date.month, selected_date.day, end_hour + 1, 0
        )  # ! for duration: +1 unlike time

        durations = ceil((end_dt - date_obj + timedelta(minutes=30)).seconds / 3600)

        durations = list(range(1, durations))

        n = 8
        keyboard_buttons = [
            [KeyboardButton(dur) for dur in durations[i : i + n]]
            for i in range(0, len(durations), n)
        ]
        keyboard_buttons.append([KeyboardButton(Label.BACK)])

        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True), durations

    @staticmethod
    def confirmation():
        keyboard_buttons = [
            [KeyboardButton(Label.CONFIRM_YES)],
            [KeyboardButton(Label.CONFIRM_NO)],
        ]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def retry():
        keyboard_buttons = [
            [
                KeyboardButton(Label.CURRENT_RESERVATIONS),
                KeyboardButton(Label.AVAILABLE_SLOTS),
            ],
            [KeyboardButton(Label.RETRY)],
            [KeyboardButton(Label.HISTORY)],
            [KeyboardButton(Label.CANCEL_RESERVATION)],
            [KeyboardButton(Label.FEEDBACK), KeyboardButton(Label.DONATE)],
        ]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def cancelation_options(reservations: list):
        keyboard_buttons = [[KeyboardButton(slot)] for slot in reservations]
        keyboard_buttons.append([KeyboardButton(Label.RESERVATION_TYPE_BACK)])
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def cancelation_confirm():
        keyboard_buttons = [
            [KeyboardButton(Label.CANCEL_CONFIRM_YES)],
            [KeyboardButton(Label.CONFIRM_NO)],
        ]
        return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)
