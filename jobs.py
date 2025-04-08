from datetime import datetime
import logging
import time
import os

import pygsheets
import schedule

from reservation import set_reservation, confirm_reservation
from slot_datetime import reserve_datetime

def job():

    if datetime.today().weekday() == 6: # Sunday
        logging.info("🟡 It's Sunday. Job skipped.")
        return
    
    # gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(),'biblio.json')) # Local    
    gc = pygsheets.authorize(service_account_json=os.environ['GSHEETS'])    
    wks = gc.open('Biblio-logs').worksheet_by_title('logs')
    reservations = wks.get_as_df()

    today = datetime.today().strftime('%A, %Y-%m-%d')
    data = reservations.drop_duplicates(['codice_fiscale','name','email','selected_date','start','end'])
    data = data[data['selected_date'] == today]

    for _, row in data.iterrows():
        date = row['selected_date'].split(' ')[-1]
        start_time = row['start']
        selected_dur = row['selected_dur']
        user_data = {'codice_fiscale':row['codice_fiscale'],
                    'cognome_nome':row['name'],
                    'email':row['email']
                    }
        try:
            start, end, duration = reserve_datetime(date, start_time, selected_dur)
            logging.info(f'✅ **1** Slot identified for {user_data['cognome_nome']}')
            reservation_response = set_reservation(start, end, duration, user_data)
            logging.info(f'✅ **2** Reservation set for {user_data['cognome_nome']}')
            confirm_reservation(reservation_response['entry'])
            logging.info(f'✅ **3** Reservation confirmed for {user_data['cognome_nome']}')
        except Exception as e:
            logging.error(f'❌ Failed reservation for {user_data['cognome_nome']} — {e}')

def run_job():  

    schedule.every().day.at('06:25').do(job) # UTC time
    # schedule.every(15).seconds.do(job) # UTC time
    # for minute in range(30, 36):  # 05:30 to 05:35
    #     schedule.every().day.at(f'5:{minute:02d}').do(job)

    # for hour in range(7, 17):  # 9 to 18 inclusive
    #     for minute in range(0,5):
    #         schedule.every().day.at(f'{hour:02d}:{minute:02d}').do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)