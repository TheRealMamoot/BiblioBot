import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


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


def load_env():
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=project_root / '.env')


def generate_days() -> list:
    today = datetime.now(ZoneInfo('Europe/Rome')).date()
    days = []
    for i in range(7):
        next_day = today + timedelta(days=i)
        if next_day.weekday() != 6:  # Skip Sunday
            day_name = next_day.strftime('%A')
            formatted_date = next_day.strftime('%Y-%m-%d')
            days.append(f'{day_name}, {formatted_date}')
        if len(days) == 6:
            break
    return days


def get_parser():
    parser = argparse.ArgumentParser(description='Telegram Bot')
    parser.add_argument(
        '--token-env',
        type=str,
        default='prod',
        choices=['prod', 'staging'],
        help='Which .env key to use for Telegram bot token',
    )
    return parser


def get_priorities():
    priority_codes: dict = os.environ['PRIORITY_CODES']
    priority_codes = json.loads(priority_codes)
    return priority_codes
