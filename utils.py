from datetime import datetime, timedelta
from math import ceil

from pygsheets import Worksheet
import pandas as pd
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import ContextTypes
import textwrap
from zoneinfo import ZoneInfo

# Keyboards
def generate_start_keyboard(edit_credential_stage: bool = False):
   keyboard_buttons = [[KeyboardButton("🤝 Reach out!")], [KeyboardButton('❓ Help')]]
   if edit_credential_stage:
       keyboard_buttons = [[KeyboardButton("➡️ Changed my mind.")]]
       
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_reservation_type_keyboard():
   keyboard_buttons = [
       [KeyboardButton('🫶 Donate'), KeyboardButton('❓ Help')],
       [KeyboardButton('🗓️ Current reservations')],
       [KeyboardButton('⏳ I need a slot for later.')], 
       [KeyboardButton('⚡️ I need a slot for now.')], 
       [KeyboardButton('🚫 Cancel reservation')], 
       [KeyboardButton('⬅️ Edit credentials')],
       ]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_date_keyboard():
    dates = generate_days()
    keyboard_buttons = []
    for i in range(0, len(dates), 3):
        row = [KeyboardButton(date) for date in dates[i:i+3]]
        keyboard_buttons.append(row)
    
    keyboard_buttons.insert(0, [KeyboardButton('🗓️ Current reservations')])
    keyboard_buttons.append([KeyboardButton('⬅️ Edit reservation type')])

    return ReplyKeyboardMarkup(keyboard_buttons)

def generate_time_keyboard(selected_date: str, instant: bool=False):
    now = datetime.now(ZoneInfo('Europe/Rome'))
    date_obj = datetime.strptime(selected_date.split(' ')[-1], '%Y-%m-%d')
    date_obj = date_obj.replace(tzinfo=ZoneInfo('Europe/Rome'))
    year = now.year if now.month <= date_obj.month else now.year + 1
    full_date = datetime(year, date_obj.month, date_obj.day, tzinfo=ZoneInfo('Europe/Rome'))
    end_hour = 13 if full_date.weekday() == 5 else 22 # Saturdays

    # Check starting time.
    current = datetime(year, date_obj.month, date_obj.day, 9, 0, tzinfo=ZoneInfo('Europe/Rome'))
    if full_date.date() == now.date():
        if now.hour < 9:
            current = datetime(year, date_obj.month, date_obj.day, 9, 0, tzinfo=ZoneInfo('Europe/Rome'))
        else:
            hour = now.hour
            minute = 0 if now.minute < 30 else 30
            current = datetime(year, date_obj.month, date_obj.day, hour, minute, tzinfo=ZoneInfo('Europe/Rome'))
    times = []
    while current.hour < end_hour or (current.hour == end_hour and current.minute == 0):
        times.append(current.strftime('%H:%M'))
        current += timedelta(minutes=30)

    keyboard_buttons = [
        [KeyboardButton(time) for time in times[i:i+5]]
        for i in range(0, len(times), 5)
    ]
    keyboard_buttons.append([KeyboardButton('⬅️')])

    if instant:
        keyboard_buttons.insert(0, [KeyboardButton('🗓️ Current reservations')])

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
   keyboard_buttons = [
       [KeyboardButton("🆕 Let's go again!")], 
       [KeyboardButton('🗓️ Current reservations')], 
       [KeyboardButton("💡 Feedback")],
       [KeyboardButton('🫶 Donate')],
       ]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_agreement_keyboard():
   keyboard_buttons = [[KeyboardButton("👍 Yes, I agree.")], [KeyboardButton("👎 No, I don't agree.")]]
   return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_cancelation_options_keyboard(reservations: list):
    keyboard_buttons = [[KeyboardButton(slot)] for slot in reservations]
    keyboard_buttons.append([KeyboardButton('⬅️ Back to reservation type')])
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

def generate_cancelation_confirm_keyboard():
    keyboard_buttons = [[KeyboardButton("📅❌ Yes, I'm sure.")], [KeyboardButton("⬅️ No, take me back.")]]
    return ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)

# Misc
def generate_days() -> list:
    today = datetime.now(ZoneInfo('Europe/Rome')).today()
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

def show_existing_reservations(update: Update, context: ContextTypes.DEFAULT_TYPE, history: pd.DataFrame, cancel_stage: bool=False) -> str:

    coidce = context.user_data['codice_fiscale']
    email = context.user_data['email']
    filtered: pd.DataFrame = history[(history['codice_fiscale'] == coidce) & 
                                     (history['email'] == email)
    ].copy()
    filtered['datetime'] = pd.to_datetime(filtered['selected_date'] + ' ' +filtered['end']) # ' ' acts as space
    filtered['datetime'] = filtered['datetime'].dt.tz_localize('UTC').dt.tz_convert('Europe/Rome')
    current = filtered[filtered['datetime'] > datetime.now(ZoneInfo('Europe/Rome'))]
    current = current.sort_values('datetime', ascending=True)
    name = update.effective_user.username if update.effective_user.username else update.effective_user.first_name
    message = textwrap.dedent(
        f"Reservations for *{name}*\n"
        f"Coidce Fiscale: *{coidce}*\n"
        f"Email: {email}\n"
        f"-----------------------\n"
        )   
    if len(current) != 0:
        if cancel_stage:
            return current

        idx = 1
        for _, row in current.iterrows():
            status = f'✅ {row['status']}' if row['status']=='success' \
                else f'🔄 {row['status']}' if row['status']=='pending' \
                else f'⚠️ {row['status']}' if row['status']=='fail' \
                else f'❌ {row['status']}' if row['status']=='terminated' \
                else 'undefined'
            booking_code: str = row['booking_code']
            res_type = 'Instant' if row['instant']=='True' else 'Regular'
            retry = f" - Retry at :00 and :30 of every hour." if row['status'] =='fail' else ''
            message += textwrap.dedent(
                f"Reservation NO: *{idx:02d}*\n"
                f"Date: *{row['selected_date']}*\n"
                f"Time: *{row['start']}* - *{row['end']}*\n"
                f"Duration: *{row['selected_dur']}* *hours*\n"
                f"Booking Code: *{booking_code.upper()}*\n"
                f"Reservation Type: *{res_type}*\n"
                f"Status: *{status.title()}*_{retry}_\n"
                f"-----------------------\n"
            )
            idx += 1
    else:
        message += "_You have no reservations at the moment._"
    return message

def show_support_message() -> str:
    text = f"""
            Thank you for using *Biblio*.
            Tell your friends, but not all of them!
            If anything was not to your liking, I don't really care. Blame this guy not me.

            [Linkedin](https://www.linkedin.com/in/alireza-mahmoudian-5b0276246/)
            [GitHub](https://github.com/TheRealMamoot)
            alireza.mahmoudian.am@gmail.com

            Cool person, check him out! 😏
    """
    return textwrap.dedent(text)

def show_donate_message() -> str:
    message = textwrap.dedent(
        f"""
        *🤝 Thanks for Helping Out!*
        Your support means the world! ❤️
        If you find the bot helpful and would like to contribute to its development, your donation would be truly appreciated.
        [Revolut](https://revolut.me/mamoot)
        [PayPal](https://www.paypal.com/paypalme/TheRealMamoot)
        Cheers! 🍻
        """
    )
    return message

def show_help() -> str:
    message = textwrap.dedent(
        f"""
        📖 *How it works*
        --------------------------
        You can reserve your slot at *BICF* either for *later* or *instantly*:

        ⏳ If you choose *"I need a slot for later"*, your requested slot will be queued and the bot will attempt to make your reservation at the next reset time, which occurs at *:00* and *:30* minute marks.

        ⚡️ If you choose *"I need a slot for now"*, the bot will try to reserve your slot *immediately*. If the slot is not available, it will automatically be queued for the next reset time — just like the "later" option. This option is only for the current day.
        
        ❗ You do not need to book multiple times. If your original reservation time hasn't passed, the bot will retry automatically. The maximum number of retries for a request is *18*. Afterwards the request will be *terminated*.

        🔔 You will be notified when your reservation is made or if it eventually fails.

        📅 You can see all your reservations and their states by choosing *"Current reservations"*.

        🚫 You can also *cancel* your request. Doing this *without* the bot might cause issues with your next slot request.
        
        📌 *Reservation Statuses*
        --------------------------
        🔄 *Pending*: Your request is in the queue and will be processed at the next slot opening at :00 or :30.

        ✅ *Success*: Your reservation was successful. You can now go to the library — you can check your email to be sure.

        ⚠️ *Fail*: The reservation was unsuccessful but will be retried several times. You don't need to request again yet.

        ❌ *Terminated*: Your request has either expired, exceeded the retry limit or canceled by you. You'll need to make a new reservation.

        ℹ️ You'll be notified if your reservation succeeds or fails permanently.
        
        💡 *Recommendation*
        --------------------------
        ❕ To increase your chances, it's highly recommended to use the *"I need a slot for later"* option and book in advance, before the day of your visit.

        ❕ Please avoid sharing the bot with a wide audience. Too many users may cause the system to slow down or fail, and it could reduce everyone's chances of getting a reservation.

        ❕ In case of any unforseen behaviour, please use /start to reset the bot. You can also use /help and /feedback at any time.

        🏹 Happy hunting...for slots!!!
        """
    )
    return message

def update_gsheet_data_point(data: pd.DataFrame, org_data_point_id: str, org_data_col_name: str, new_value, worksheet: Worksheet) -> None:
    row_idx = data.index[data['id'] == org_data_point_id].tolist()
    sheet_row = row_idx[0] + 2 # +2 because: 1 for zero-based index, 1 for header row
    sheet_col = data.columns.get_loc(org_data_col_name) + 1 # 1-based for pygsheets 
    worksheet.update_value((sheet_row, sheet_col), str(new_value))