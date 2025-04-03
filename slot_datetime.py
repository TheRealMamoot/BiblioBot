from datetime import datetime, timedelta

import pytz

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
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise ValueError('Invalid date format. Use YYYY-MM-DD.')

    # Validate day of the week (0 = Monday, 6 = Sunday)
    weekday = date_obj.weekday()
    if weekday == 6:
        raise ValueError('Reservations are not allowed on Sundays.')

    try:
        time_obj = datetime.strptime(start, '%H:%M')
    except ValueError:
        raise ValueError('Invalid time format. Use HH:MM (24-hour format).')

    time_obj = round_time_to_nearest_half_hour(time_obj)

    # Saturday rules
    max_duration = 14  # Default max duration
    closing_hour = 23  # Default closing hour

    if weekday == 5:  # Saturday
        max_duration = 5
        closing_hour = 14

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