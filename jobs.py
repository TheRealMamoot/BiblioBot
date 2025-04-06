# from datetime import datetime
# import logging
# import time
# import os

# import pandas as pd
# import pygsheets
# import schedule

# from reservation import set_reservation, confirm_reservation
# from slot_datetime import reserve_datetime

# def job(reservations: pd.DataFrame):

#     if datetime.today().weekday() == 6: # Sunday
#         logging.info("🟡 It's Sunday. Job skipped.")
#         return
    
#     gc = pygsheets.authorize(service_account_json=os.environ['GSHEETS'])    
#     wks = gc.open('Biblio-logs').worksheet_by_title('logs')
#     reservations = wks.get_as_df()

#     today = datetime.today().strftime('%A, %Y-%m-%d')
#     data = reservations.drop_duplicates(['codice_fiscale','name','email','selected_date','start','end'])
#     data = data[data['selected_date'] == today]

#     for _, row in data.iterrows():
#         date = row['selected_date'].split(' ')[-1]
#         start_time = row['start']
#         selected_dur = row['selected_dur']
#         user_data = {'codice_fiscale':f'{row['codice_fiscale']}',
#                     'cognome_nome':f'{row['name']}',
#                     'email':f'{row['email']}'
#                     }
#         try:
#             start, end, duration = reserve_datetime(date, start_time, selected_dur)
#             logging.info(f'✅ **1** Slot identified for {user_data['cognome_nome']}')
#             reservation_response = set_reservation(start, end, duration, user_data)
#             logging.info(f'✅ **2** Reservation set for {user_data['cognome_nome']}')
#             confirm_reservation(reservation_response['entry'])
#             logging.info(f'✅ **3** Reservation confirmed for {user_data['cognome_nome']}')
#         except Exception as e:
#             logging.error(f'❌ Failed reservation for {user_data['cognome_nome']} — {e}')

# def run_job():
#     schedule.every().day.at('07:32').do(job)

#     while True:
#         now = datetime.now()
#         if now.hour > 9 or (now.hour == 9 and now.minute >= 30):
#             print("⏱️ It's after 09:30. Running job manually")
#             job()
#             time.sleep(60 * 60 * 24)
#             continue

#         schedule.run_pending()
#         time.sleep(15 * 60)


from datetime import datetime
from zoneinfo import ZoneInfo
import schedule
import time

def test_job():
    utc_now = datetime.utcnow()
    italy_now = datetime.now(ZoneInfo('Europe/Rome'))

    print(f'⏰ UTC Now: {utc_now.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'🇮🇹 Italy Now: {italy_now.strftime("%Y-%m-%d %H:%M:%S")}')
    
def run_job():
    schedule.every(5).seconds.do(test_job)

    print("✅ Starting job...")

    while True:
        schedule.run_pending()
        time.sleep(1)