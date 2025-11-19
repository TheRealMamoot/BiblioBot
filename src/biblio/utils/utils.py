from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from dateutil.parser import parse
from pandas import DataFrame

from src.biblio.config.config import Schedule

LIB_SCHEDULE = Schedule.weekly()


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


# !TODO: fix for edge case: only one point!
def plot_slot_history(df: DataFrame, date: str, slot: str, start: str = None, end: str = None) -> BytesIO:
    parsed_date = parse(date)
    day_label = parsed_date.strftime('%A, %Y-%m-%d')
    title = f'{day_label} for Slot {slot}'
    if start and end:
        title += f' (Range: {start}–{end})'

    df['time'] = pd.to_datetime(df['time'])
    y_min = df['available'].min()
    y_max = df['available'].max()

    y_padding_top = max(int(0.05 * (y_max - y_min)), 1)
    y_range_max = min(300, y_max + y_padding_top)

    y_padding_bottom = min(max(1, int(0.05 * y_max)), 10)
    y_range_min = -y_padding_bottom

    y_range_span = y_range_max
    dtick = 1 if y_range_span <= 5 else 2 if y_range_span <= 10 else 5 if y_range_span <= 30 else 10
    tickvals = list(range(y_range_min, y_range_max + 1, dtick))
    ticktext = [str(val) if val >= 0 else '' for val in tickvals]

    fig, ax = plt.subplots(figsize=(15, 8))
    ax.plot(df['time'], df['available'], marker='o', linewidth=3)

    ax.set_title(title, fontsize=22, weight='bold', pad=20)
    ax.set_xlabel('Time', fontsize=16)
    ax.set_ylabel('Available Seats', fontsize=16)
    ax.set_ylim(y_range_min, y_range_max)
    ax.set_yticks(tickvals)
    ax.set_yticklabels(ticktext)
    ax.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.5)

    time_span_minutes = (df['time'].max() - df['time'].min()).total_seconds() / 60
    base_minutes = 20
    interval = max(1, int(time_span_minutes // base_minutes))

    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=interval))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    fig.autofmt_xdate(rotation=45)

    ax.axhline(0, color='gray', linewidth=2)

    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format='jpg', dpi=150)
    plt.close(fig)
    buffer.seek(0)

    return buffer


def utc_tuple_to_rome_time(hour_minute: tuple[int, int]) -> tuple[int, int]:
    hour, minute = hour_minute
    dt_utc = datetime(2000, 1, 1, hour, minute, tzinfo=ZoneInfo('UTC'))
    dt_rome = dt_utc.astimezone(ZoneInfo('Europe/Rome'))
    return dt_rome.hour, dt_rome.minute
