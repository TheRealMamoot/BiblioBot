from datetime import datetime, timedelta

from pygsheets import Worksheet
import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes
import textwrap
from zoneinfo import ZoneInfo

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
            booking_code: str = str(row['booking_code'])
            booking_code = booking_code.replace('.','').replace('+','').replace('-','')
            if len(booking_code) < 6 and booking_code not in ['TBD','NA','INF','inf']:
                booking_code = booking_code.zfill(6)
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

def update_gsheet_data_point(data: pd.DataFrame, 
                             org_data_point_id: str, 
                             org_data_col_name: str, 
                             new_value, worksheet: Worksheet) -> None:
    row_idx = data.index[data['id'] == org_data_point_id].tolist()
    sheet_row = row_idx[0] + 2 # +2 because: 1 for zero-based index, 1 for header row
    sheet_col = data.columns.get_loc(org_data_col_name) + 1 # 1-based for pygsheets 
    worksheet.update_value((sheet_row, sheet_col), str(new_value))