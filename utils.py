from datetime import datetime, timedelta
from math import ceil

from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

def generate_days():
    today = datetime.today()
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

def generate_reservation_type_keyboard():
   keyboard_buttons = [
       [KeyboardButton('⬅️ Edit credentials')], 
       [KeyboardButton('⏳ I need a slot for later.')], 
       [KeyboardButton('⚡️ I need a slot for today.')]
       ]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_date_keyboard():
    dates = generate_days()
    keyboard_buttons = []
    for i in range(0, len(dates), 3):
        row = [KeyboardButton(date) for date in dates[i:i+3]]
        keyboard_buttons.append(row)
    
    keyboard_buttons.insert(0, [KeyboardButton('⬅️ Edit reservation')])

    return ReplyKeyboardMarkup(keyboard_buttons)

def generate_time_keyboard(selected_date: str):
    date_obj = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')
    today = datetime.today()
    year = today.year if today.month <= date_obj.month else today.year + 1
    full_date = datetime(year, date_obj.month, date_obj.day)

    end_hour = 13 if full_date.weekday() == 5 else 22 # Saturdays

    # Check starting time.
    if full_date.date() == today.date():
        hour = today.hour
        minute = 0 if today.minute < 30 else 30
        current = datetime(year, date_obj.month, date_obj.day, hour, minute)
    else:
        current = datetime(year, date_obj.month, date_obj.day, 9, 0)
    
    times = []
    while current.hour < end_hour or (current.hour == end_hour and current.minute == 0):
        times.append(current.strftime('%H:%M'))
        current += timedelta(minutes=30)

    keyboard_buttons = [
        [KeyboardButton(time) for time in times[i:i+5]]
        for i in range(0, len(times), 5)
    ]
    keyboard_buttons.insert(0, [KeyboardButton('⬅️')])

    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_duration_keyboard(selected_time: str, context: ContextTypes.DEFAULT_TYPE):
    selected_date = context.user_data.get('selected_date')
    selected_date = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')

    time_obj = datetime.strptime(selected_time, '%H:%M')
    date_obj = datetime(selected_date.year, selected_date.month, selected_date.day, time_obj.hour, time_obj.minute)

    end_hour = 14 if selected_date.weekday() == 5 else 23 # Saturdays
    selected_date = selected_date + timedelta(hours=end_hour)

    durations = ceil((selected_date - date_obj + timedelta(minutes=30)).seconds / 3600) # ceil in case of **:30 start time formats
    durations = list(range(1, durations))

    keyboard_buttons = [
        [KeyboardButton(dur) for dur in durations[i:i+10]]
        for i in range(0, len(durations), 10)
    ]
    keyboard_buttons.insert(0, [KeyboardButton('⬅️')])

    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True), durations

def generate_confirmation_keyboard():
   keyboard_buttons = [[KeyboardButton('⬅️ No, take me back.')], [KeyboardButton('✅ Yes, all looks good.')]]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)