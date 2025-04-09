from datetime import datetime, timedelta
from math import ceil

import pandas as pd
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import ContextTypes
import textwrap
from zoneinfo import ZoneInfo

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
       [KeyboardButton('⏳ I need a slot for later.')], 
       [KeyboardButton('⚡️ I need a slot now.')],
       [KeyboardButton('⬅️ Edit credentials')]
       ]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_date_keyboard():
    dates = generate_days()
    keyboard_buttons = []
    for i in range(0, len(dates), 3):
        row = [KeyboardButton(date) for date in dates[i:i+3]]
        keyboard_buttons.append(row)
    
    keyboard_buttons.insert(0, [KeyboardButton('🗓️ Show current reservations')])
    keyboard_buttons.append([KeyboardButton('⬅️ Edit reservation type')])

    return ReplyKeyboardMarkup(keyboard_buttons)

def generate_time_keyboard(selected_date: str):
    now = datetime.now(ZoneInfo('Europe/Rome'))
    date_obj = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')
    date_obj = date_obj.replace(tzinfo=ZoneInfo('Europe/Rome'))
    year = now.year if now.month <= date_obj.month else now.year + 1
    full_date = datetime(year, date_obj.month, date_obj.day, tzinfo=ZoneInfo('Europe/Rome'))
    end_hour = 13 if full_date.weekday() == 5 else 22 # Saturdays

    # Check starting time.
    if full_date.date() == now.date():
        hour = now.hour
        minute = 0 if now.minute < 30 else 30
        current = datetime(year, date_obj.month, date_obj.day, hour, minute, tzinfo=ZoneInfo('Europe/Rome'))
    else:
        current = datetime(year, date_obj.month, date_obj.day, 9, 0, tzinfo=ZoneInfo('Europe/Rome'))
    
    times = []
    while current.hour < end_hour or (current.hour == end_hour and current.minute == 0):
        times.append(current.strftime('%H:%M'))
        current += timedelta(minutes=30)

    keyboard_buttons = [
        [KeyboardButton(time) for time in times[i:i+5]]
        for i in range(0, len(times), 5)
    ]
    keyboard_buttons.append([KeyboardButton('⬅️')])

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
        [KeyboardButton(dur) for dur in durations[i:i+8]]
        for i in range(0, len(durations), 8)
    ]
    keyboard_buttons.append([KeyboardButton('⬅️')])

    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True), durations

def generate_confirmation_keyboard():
   keyboard_buttons = [[KeyboardButton('✅ Yes, all looks good.')], [KeyboardButton('⬅️ No, take me back.')]]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_retry_keyboard():
   keyboard_buttons = [[KeyboardButton("🆕 Let's go for another date.")], [KeyboardButton('🗓️ Show current reservations')], [KeyboardButton("💡 Feedback")]]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_start_keyboard(edit_credential_stage: bool = False):
   keyboard_buttons = [[KeyboardButton("🤝 Reach out!")]]
   if edit_credential_stage:
       keyboard_buttons = [[KeyboardButton("➡️ Changed my mind.")]]
       
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_agreement_keyboard():
   keyboard_buttons = [[KeyboardButton("👍 Yes, I agree.")], [KeyboardButton("👎 No, I don't agree.")]]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def support_message(name):
    text = f"""
            Thank you *{name}* for using *Biblio*.
            Tell your friends, but not all of them!
            If anything was not to your liking, I don't really care. Blame this guy not me.

            [Linkedin](https://www.linkedin.com/in/alireza-mahmoudian-5b0276246/)
            [GitHub](https://github.com/TheRealMamoot)
            alireza.mahmoudian.am@gmail.com

            Cool person, you should check him out.
            Don't you dare /start again! 😠
    """
    return textwrap.dedent(text)

def show_existing_reservations(update: Update, context: ContextTypes.DEFAULT_TYPE, history: pd.DataFrame) -> str:

    coidce = context.user_data['codice_fiscale']
    email = context.user_data['email']
    filtered = history[(history['codice_fiscale'] == coidce) & 
                       (history['email'] == email)
    ].copy()
    filtered['datetime'] = pd.to_datetime(filtered['selected_date'] + ' ' +filtered['end']) # ' ' acts as space
    current = filtered[filtered['datetime'] > datetime.now()]
    current = current.sort_values('datetime', ascending=True)
    name = update.effective_user.username if update.effective_user.username else update.effective_user.first_name
    message = textwrap.dedent(
        f"Reservations for *{name}*\n"
        f"Coidce Fiscale: *{coidce}*\n"
        f"Email: {email}\n"
        f"-----------------------\n"
        )   
    if len(current) != 0:
        for _, row in current.iterrows():
            status = f'✅ {row['status']}' if row['status']=='success' \
                else f'🔄 {row['status']}' if row['status']=='pending' \
                else f'⚠️ {row['status']}' if row['status']=='fail' \
                else f'❌ {row['status']}' if row['status']=='terminated' \
                else 'undefined'
            booking_code: str = row['booking_code']
            retry = f" - Will try again at ##:00 and ##:30 hours" if row['status'] =='fail' else ''
            message += textwrap.dedent(
                f"Date: *{row['selected_date']}*\n"
                f"Time: *{row['start']}* - *{row['end']}*\n"
                f"Duration: *{row['selected_dur']}* *hours*\n"
                f"Booking Code: *{booking_code.upper()}*\n"
                f"Status: *{status.title()}*_{retry}_\n"
                f"-----------------------\n"
            )
    else:
        message += "_No upcoming reservations._"
    return message