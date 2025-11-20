import argparse
import json
import os
from dataclasses import dataclass
from enum import IntEnum, auto
from functools import cache
from pathlib import Path

import asyncpg
import pygsheets
from dotenv import load_dotenv

CREDENTIALS_PATH = Path(__file__).resolve().parents[2] / 'biblio' / 'config' / 'biblio.json'


class States(IntEnum):
    AGREEMENT = auto()
    CREDENTIALS = auto()
    WELCOME_BACK = auto()
    RESERVE_TYPE = auto()
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
                'weekday': (5 + adjustment, 20 + adjustment),
                'sat': (5 + adjustment, 11 + adjustment),
                'sun': (5 + adjustment, 11 + adjustment),
                'availability': (5 + adjustment, 18 + adjustment),
                'availability_sat': (5 + adjustment, 11 + adjustment),
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


def load_env(name: str = 'prod') -> None:
    global _CURRENT_ENV
    _CURRENT_ENV = name
    project_root = Path(__file__).resolve().parents[3]
    mapping = {
        'local': '.env',
        'staging': '.env.staging',
        'prod': '.env.production',
    }
    env_file = project_root / mapping.get(name)
    if env_file.exists():
        load_dotenv(env_file, override=False)


def get_parser():
    parser = argparse.ArgumentParser(description='Telegram Bot')
    parser.add_argument(
        '-env',
        type=str,
        default='local',
        choices=['prod', 'staging', 'local'],
        help='Environment to run',
    )
    return parser


@cache
def get_gsheet_client():
    gsheets = os.getenv('GSHEETS')
    if gsheets:
        return pygsheets.authorize(service_account_json=gsheets)
    else:
        return pygsheets.authorize(service_file=CREDENTIALS_PATH)


def get_wks():
    gc = get_gsheet_client()
    return gc.open('Biblio-logs').worksheet_by_title('backup')


async def connect_db():
    url = os.getenv('DATABASE_URL')
    return await asyncpg.connect(url)


def get_priorities():
    priority_codes: dict = os.getenv('PRIORITY_CODES')
    priority_codes = json.loads(priority_codes)
    return priority_codes
