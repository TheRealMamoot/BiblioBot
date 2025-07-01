import argparse
import json
import os
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

import pygsheets
from dotenv import load_dotenv

from src.biblio.config.config import Schedule

CREDENTIALS_PATH = Path(__file__).resolve().parents[2] / 'biblio' / 'config' / 'biblio.json'
LIB_SCHEDULE = Schedule.default()


class ReservationConfirmationConflict(Exception):
    """
    Raised when the server returns a 401 Unauthorized during reservation confirmation.
    This indicates that the reservation is most likely already confirmed!
    """

    pass


def load_env():
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=project_root / '.env')


def generate_days() -> list:
    now = datetime.now(ZoneInfo('Europe/Rome'))
    today = now.date()
    days = []

    _, end_hour = LIB_SCHEDULE.get_hours(today.weekday())
    offset = 1 if now.hour == end_hour and now.minute >= 30 else 0  # * exclude today after closing hours

    for i in range(offset, 7 + offset):
        next_day = today + timedelta(days=i)
        library_hours = LIB_SCHEDULE.get_hours(next_day.weekday())
        if library_hours != (0, 0):
            day_name = next_day.strftime('%A')
            formatted_date = next_day.strftime('%Y-%m-%d')
            days.append(f'{day_name}, {formatted_date}')
        if len(days) == 6:
            break
    return days


def get_token(token_env: str = 'prod'):
    load_env()
    if token_env == 'prod':
        token: str = os.getenv('TELEGRAM_TOKEN')
    elif token_env == 'staging':
        token: str = os.getenv('TELEGRAM_TOKEN_S')
    else:
        raise ValueError('Wrong mode')
    return token


def get_database_url() -> str:
    load_env()
    return os.getenv('DATABASE_URL')


def get_parser():
    parser = argparse.ArgumentParser(description='Telegram Bot')
    parser.add_argument(
        '-t',
        '--token-env',
        type=str,
        default='prod',
        choices=['prod', 'staging'],
        help='Which .env key to use for Telegram bot token',
    )
    parser.add_argument(
        '-g',
        '--gsheet-auth',
        type=str,
        default='cloud',
        choices=['cloud', 'local'],
        help='Which .env key to use for Telegram bot token',
    )
    return parser


def get_priorities():
    priority_codes: dict = os.environ['PRIORITY_CODES']
    priority_codes = json.loads(priority_codes)
    return priority_codes


@cache
def get_gsheet_client(auth_mode: str = 'cloud'):
    if auth_mode == 'cloud':
        return pygsheets.authorize(service_account_json=os.environ['GSHEETS'])
    elif auth_mode == 'local':
        return pygsheets.authorize(service_file=CREDENTIALS_PATH)
    else:
        raise ValueError('Wrong mode')


def get_wks(auth_mode: str = 'cloud'):
    gc = get_gsheet_client(auth_mode)
    return gc.open('Biblio-logs').worksheet_by_title('backup')
