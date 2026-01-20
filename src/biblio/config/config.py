import argparse
import json
import logging
import os
from dataclasses import dataclass
from enum import IntEnum, StrEnum, auto
from functools import cache
from pathlib import Path

import asyncpg
import pygsheets
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).resolve().parents[2] / "biblio" / "config"
DEFAULT_CREDENTIALS = CONFIG_DIR / "biblio.json"
DEFAULT_PRIORITY = 5
RAILWAY_SERVICES = {
    "BiblioBot": "🤖",
    "Postgres": "🗃️",
    "Reservation": "⏰",
    "Reservation Job": "⏰",
}


def _resolve_credentials_path() -> Path | None:
    if DEFAULT_CREDENTIALS.exists():
        return DEFAULT_CREDENTIALS

    path = next(CONFIG_DIR.glob("*.json"), None)
    if path is None:
        logging.warning(f"[GSHEETS] No credentials JSON file found in {CONFIG_DIR}")

    return path


CREDENTIALS_PATH = _resolve_credentials_path()


class State(IntEnum):
    AGREEMENT = auto()
    CREDENTIALS = auto()
    WELCOME_BACK = auto()
    RESERVE_TYPE = auto()
    ADMIN_PANEL = auto()
    ADMIN_NOTIF = auto()
    ADMIN_NOTIF_CONFIRM = auto()
    MAINTENANCE = auto()
    ADMIN_MAINTANANCE_CONFIRM = auto()
    ADMIN_MANAGE_SERVICES = auto()
    ADMIN_SERVICE_OPTIONS = auto()
    ADMIN_OPTION_CONFIRM = auto()
    CHOOSING_DATE = auto()
    CHOOSING_TIME = auto()
    CHOOSING_DUR = auto()
    CHOOSING_AVAILABLE = auto()
    CHOOSING_DATE_HISTORY = auto()
    CHOOSING_SLOT = auto()
    CHOOSING_FILTER_START = auto()
    CHOOSING_FILTER_END = auto()
    CONFIRMING = auto()
    CANCELATION_SLOT_CHOICE = auto()
    CANCELATION_CONFIRMING = auto()
    RETRY = auto()


class EmojiStrEnum(StrEnum):
    def __new__(cls, code: str, emoji: str):
        obj = str.__new__(cls, code)
        obj._value_ = code
        obj.emoji = emoji
        return obj


class Status(EmojiStrEnum):
    PENDING = ("pending", "🔄")
    PROCESSING = ("processing", "🛠️")
    AWAITING = ("awaiting", "⏳")
    FAIL = ("fail", "⚠️")
    SUCCESS = ("success", "✅")
    EXISTING = ("existing", "✴️")
    TERMINATED = ("terminated", "❌")
    CANCELED = ("canceled", "🛑")


class BookingCodeStatus(StrEnum):
    NA = "NA"
    TBD = "TBD"
    CLOSED = "CLOSED"


class UserDataKey(StrEnum):  # applies .lower() to next values
    IS_ADMIN = auto()
    AMDMIN_SERVICES = auto()
    ENV_ID = auto()
    CHOSEN_SERVICE_ID = auto()
    CHOSEN_SERVICE_NAME = auto()
    SERVICE_DEPLOYMENT_ID = auto()
    CHOSEN_SERVICE_OPTION = auto()
    MAINTANANCE_STATUS = auto()
    INSTANT = auto()
    STATE = auto()
    SELECTED_DATE = auto()
    SELECTED_DATE_HISTORY = auto()
    SELECTED_TIME = auto()
    SELECTED_DURATION = auto()
    SLOT = auto()
    SLOT_HISTORY = auto()
    FILTER_START = auto()
    FILTER_END = auto()
    CANCELATION_CHOICES = auto()
    CANCELATION_CHOSEN_SLOT_ID = auto()
    CODICE_FISCALE = auto()
    NAME = auto()
    EMAIL = auto()
    USERNAME = auto()
    FIRST_NAME = auto()
    LAST_NAME = auto()
    ID = auto()
    PRIORITY = auto()
    NOTIFICATION = auto()
    STATUS = auto()
    BOOKING_CODE = auto()
    RETRIES = auto()
    STATUS_CHANGE = auto()
    CREATED_AT = auto()
    UPDATED_AT = auto()
    SUCCESS_AT = auto()
    FAIL_AT = auto()


@dataclass
class Schedule:
    hours: dict

    @staticmethod
    def weekly():
        return Schedule(
            {
                0: (9, 22),
                1: (9, 22),
                2: (9, 22),
                3: (9, 22),
                4: (9, 22),
                5: (9, 13),
                6: (9, 13),
            }
        )

    @staticmethod
    def jobs(daylight_saving=False):
        adjustment = 1 if daylight_saving else 0  # hour
        return Schedule(
            {
                "weekday": (5 + adjustment, 20 + adjustment),
                "sat": (5 + adjustment, 11 + adjustment),
                "sun": (5 + adjustment, 11 + adjustment),
                "availability": (5 + adjustment, 18 + adjustment),
                "availability_sat": (5 + adjustment, 11 + adjustment),
            }
        )

    def get_hours(self, key):
        return self.hours.get(key, (0, 0))


class ReservationConfirmationConflict(Exception):
    """
    Raised when the server returns a 401 Unauthorized during reservation confirmation.
    This indicates that the reservation is most likely already confirmed!
    """

    pass


def load_env(name: str = "prod") -> None:
    global _CURRENT_ENV
    _CURRENT_ENV = name
    project_root = Path(__file__).resolve().parents[3]
    mapping = {
        "local": ".env",
        "staging": ".env.staging",
        "prod": ".env.production",
    }
    env_file = project_root / mapping.get(name)
    if env_file.exists():
        load_dotenv(env_file, override=True)


def get_parser():
    parser = argparse.ArgumentParser(description="Telegram Bot")
    parser.add_argument(
        "-env",
        type=str,
        default="local",
        choices=["prod", "staging", "local"],
        help="Environment to run",
    )
    return parser


def check_is_admin(chat_id: str) -> bool:
    is_admin = True if chat_id == int(os.getenv("BOTLORD_CHAT_ID")) else False
    return is_admin


@cache
def get_gsheet_client():
    gsheets = os.getenv("GSHEETS")
    if gsheets:
        return pygsheets.authorize(service_account_json=gsheets)
    else:
        return pygsheets.authorize(service_file=CREDENTIALS_PATH)


def get_wks():
    gc = get_gsheet_client()
    return gc.open(os.getenv("GSHEETS_NAME")).worksheet_by_title(
        os.getenv("GSHEETS_TAB")
    )


async def connect_db():
    url = os.getenv("DATABASE_URL")
    return await asyncpg.connect(url)


def get_priorities():
    priority_codes = os.getenv("PRIORITY_CODES")
    if not priority_codes:
        return {}
    try:
        return json.loads(priority_codes)
    except json.JSONDecodeError:
        logging.warning("[PRIORITY] Invalid PRIORITY_CODES JSON; using defaults.")
        return {}
