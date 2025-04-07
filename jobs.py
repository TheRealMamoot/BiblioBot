from datetime import datetime
import logging
import time
import os
from zoneinfo import ZoneInfo

import pandas as pd
import pygsheets
import schedule

from reservation import set_reservation, confirm_reservation
from slot_datetime import reserve_datetime

def job():

    if datetime.now(ZoneInfo('Europe/Rome')).today().weekday() == 6: # Sunday
        logging.info("🟡 It's Sunday. Job skipped.")
        return
    
    gc = pygsheets.authorize(service_account_json=os.environ['GSHEETS'])    
    wks = gc.open('Biblio-logs').worksheet_by_title('logs')
    reservations = wks.get_as_df()

    today = datetime.now(ZoneInfo('Europe/Rome')).today().strftime('%A, %Y-%m-%d')
    data = reservations.drop_duplicates(['codice_fiscale','name','email','selected_date','start','end'])
    data = data[data['selected_date'] == today]

    for _, row in data.iterrows():
        date = row['selected_date'].split(' ')[-1]
        start_time = row['start']
        selected_dur = row['selected_dur']
        user_data = {'codice_fiscale':f'{row['codice_fiscale']}',
                    'cognome_nome':f'{row['name']}',
                    'email':f'{row['email']}'
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
    schedule.every().day.at('05:33').do(job()) # UTC time

    while True:
        now = datetime.now(ZoneInfo('Europe/Rome'))
        if now.hour > 9 or now.hour == 9 and now.minute >= 30:
            print("⏱️ It's after 09:30. Running job manually")
            job()
            time.sleep(60 * 60 * 24)
            continue

        schedule.run_pending()
        time.sleep(15 * 60)