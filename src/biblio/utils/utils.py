import argparse
import json
import os
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

import plotly.express as px
import plotly.io as pio
import pygsheets
from dotenv import load_dotenv
from pandas import DataFrame

from src.biblio.config.config import Schedule

CREDENTIALS_PATH = Path(__file__).resolve().parents[2] / 'biblio' / 'config' / 'biblio.json'
LIB_SCHEDULE = Schedule.weekly()


class ReservationConfirmationConflict(Exception):
    """
    Raised when the server returns a 401 Unauthorized during reservation confirmation.
    This indicates that the reservation is most likely already confirmed!
    """

    pass


def load_env():
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=project_root / '.env')


def generate_days(past: int = 0, future: int = 5) -> list:
    now = datetime.now(ZoneInfo('Europe/Rome'))
    today = now.date()
    days = []

    _, end_hour = LIB_SCHEDULE.get_hours(today.weekday())
    offset = 1 if now.hour == end_hour and now.minute >= 30 else 0  # * exclude today after closing hours

    start_offset = -past if past > 0 else 0
    end_offset = future + offset

    for i in range(start_offset, end_offset + 1):
        day = today + timedelta(days=i)
        library_hours = LIB_SCHEDULE.get_hours(day.weekday())
        if library_hours != (0, 0):
            day_name = day.strftime('%A')
            formatted_date = day.strftime('%Y-%m-%d')
            days.append(f'{day_name}, {formatted_date}')

    if past > 0 and future == 0:
        days.reverse()

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


def plot_slot_history(
    df: DataFrame, date: str, slot: str, start: str = None, end: str = None, output_path: str = 'slot_history.jpg'
):
    day_label = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %Y-%m-%d')
    title = f'{day_label} for Slot {slot}'
    if start and end:
        title += f' (Range: {start}–{end})'

    fig = px.line(
        df,
        x='time',
        y='available',
        title=title,
        markers=True,
    )

    fig.update_traces(line=dict(width=3))

    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Available Seats',
        template='plotly_white',
        title_font=dict(size=28),
        xaxis_title_font=dict(size=22),
        yaxis_title_font=dict(size=22),
        font=dict(size=18),
        yaxis=dict(
            dtick=10,
            tickmode='linear',
            range=[0, df['available'].max() + 5],
            zeroline=True,
            zerolinewidth=3,
            zerolinecolor='gray',
        ),
    )

    pio.write_image(fig, output_path, format='jpg', width=1200, height=900)


def utc_tuple_to_rome_time(hour_minute: tuple[int, int]) -> tuple[int, int]:
    hour, minute = hour_minute
    dt_utc = datetime(2000, 1, 1, hour, minute, tzinfo=ZoneInfo('UTC'))
    dt_rome = dt_utc.astimezone(ZoneInfo('Europe/Rome'))
    return dt_rome.hour, dt_rome.minute
