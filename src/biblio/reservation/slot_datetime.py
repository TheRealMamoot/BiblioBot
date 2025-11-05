from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytz

from src.biblio.config.config import Schedule

LIB_SCHEDULE = Schedule.weekly()


def round_time_to_nearest_half_hour(time_obj: datetime) -> datetime:
    minutes = time_obj.minute
    if minutes >= 30:
        time_obj += timedelta(minutes=(30 - minutes))
    else:
        time_obj -= timedelta(minutes=minutes)

    return time_obj


def reserve_datetime(date: str, start: str, duration: int) -> tuple[int, int, int]:
    """
    Converts user-provided date, start time, and duration into Unix timestamps.

    Parameters:
    - date (str): Date in 'YYYY-MM-DD' format.
    - start (str): Start time in 'HH:MM' format (24-hour).
    - duration (int): Duration in hours (max 14 on weekdays, max 5 on Saturdays).

    Returns:
    - tuple[int, int, int]: (start_time, end_time, duration in seconds)
    """
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=ZoneInfo('Europe/Rome'))
    except ValueError:
        raise ValueError('Invalid date format. Use YYYY-MM-DD.')

    # * Sundays are temporarily open
    # weekday = date_obj.weekday()
    # if weekday == 6:
    #     raise ValueError('Reservations are not allowed on Sundays.')

    try:
        time_obj = datetime.strptime(start, '%H:%M').replace(tzinfo=ZoneInfo('Europe/Rome'))
    except ValueError:
        raise ValueError('Invalid time format. Use HH:MM (24-hour format).')

    time_obj = round_time_to_nearest_half_hour(time_obj)

    opening_hour, closing_hour = LIB_SCHEDULE.get_hours(date_obj.weekday())
    closing_hour += 1
    max_duration = closing_hour - opening_hour

    if not isinstance(duration, int) or duration < 1 or duration > max_duration:
        raise ValueError(f'Duration must be an between 1 and {max_duration} hours.')

    # Convert GMT to CET
    italy_tz = pytz.timezone('Europe/Rome')
    start_time = datetime.combine(date_obj.date(), time_obj.time())
    start_time = italy_tz.localize(start_time)

    opening_time = start_time.replace(hour=9, minute=0)
    if start_time < opening_time:
        raise ValueError('Start time cannot be before 09:00 AM.')

    end_time = start_time + timedelta(hours=duration)
    closing_time = start_time.replace(hour=closing_hour, minute=0)
    if end_time > closing_time:
        raise ValueError(f'End time cannot be after {closing_hour}:00.')

    # Convert to Unix timestamps
    start_time = int(start_time.timestamp())
    end_time = int(end_time.timestamp())
    durata = duration * 3600

    return start_time, end_time, durata


def extract_available_seats(schedule: dict[str, dict], filter_past: bool = True) -> dict[str, int]:
    now = datetime.now(ZoneInfo('Europe/Rome'))
    now_minutes = 0 if now.minute < 30 else 30
    now_rounded = time(now.hour, now_minutes)

    result = {}
    for slot, info in schedule.items():
        start_time, _ = slot.split('-')
        start_time = datetime.strptime(start_time, '%H:%M').time()

        if not filter_past or start_time >= now_rounded:
            result[slot] = info['disponibili']

    return result
