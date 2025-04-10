from datetime import datetime
from itertools import product
import logging
import time
import os
from zoneinfo import ZoneInfo

import pygsheets
import pandas as pd
import schedule

from reservation import set_reservation, confirm_reservation
from slot_datetime import reserve_datetime

def job():
    gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(),'biblio.json')) # Local    
    # gc = pygsheets.authorize(service_account_json=os.environ['GSHEETS'])    
    wks = gc.open('Biblio-logs').worksheet_by_title('tests')
    data = wks.get_as_df()
    data['temp_duration_int'] = pd.to_numeric(data['selected_dur'])
    data['temp_datetime'] = pd.to_datetime(data['selected_date'])
    data['temp_datetime'] = data['temp_datetime'].dt.tz_localize('UTC').dt.tz_convert('Europe/Rome')
    data['temp_start'] = pd.to_datetime(data['start'], format='%H:%M').dt.time
    data['retries'] = data['retries'].astype(str)

    data: pd.DataFrame = data.sort_values(['temp_datetime','priority','temp_duration_int', 'temp_start'], ascending=[True, True, False, True])
    today = datetime.now(ZoneInfo('Europe/Rome')).today().strftime('%A, %Y-%m-%d')
    for idx, row in data.iterrows():
        if row['selected_date'] != today:
            continue
        if row['status']=='success' or row['status']=='terminated':
            continue

        logging.info(f'⏳ Job started at {datetime.now(ZoneInfo('Europe/Rome'))}')
        user_data = {
            'codice_fiscale': row['codice_fiscale'],
            'cognome_nome': row['name'],
            'email': row['email']
        }
        date = row['selected_date'].split(' ')[-1]
        start_time = row['start']
        selected_dur = row['selected_dur']
        try:
            start, end, duration = reserve_datetime(date, start_time, selected_dur)
            logging.info(f'✅ **1** Slot identified for {user_data['cognome_nome']}')
            reservation_response = set_reservation(start, end, duration, user_data)
            logging.info(f'✅ **2** Reservation set for {user_data['cognome_nome']}')
            confirm_reservation(reservation_response['entry'])
            logging.info(f'✅ **3** Reservation confirmed for {user_data['cognome_nome']}')
            data.loc[idx, 'status'] = 'success'
            data.loc[idx, 'booking_code'] = reservation_response['codice_prenotazione']
            data.loc[idx, 'updated_at'] = datetime.now(ZoneInfo('Europe/Rome'))
        except Exception as e:
            logging.error(f'❌ Failed reservation for {user_data['cognome_nome']} — {e}')
            data.loc[idx, 'retries'] = str(int(row['retries'])+1)
            data.loc[idx, 'status'] = 'terminated' if int(row['retries']) > 18 else 'fail'
            data.loc[idx, 'updated_at'] = datetime.now(ZoneInfo('Europe/Rome'))
    del data['temp_duration_int'], data['temp_datetime'], data['temp_start']
    wks.clear()
    wks.set_dataframe(data, start='A1', copy_head=True, copy_index=False)
    logging.info(f'🔄 Data refreshed at {datetime.now(ZoneInfo('Europe/Rome'))}')

def run_job():  
    hours = range(7, 23)  # 7 to 18 inclusive
    minutes = [0,1,2,3,30,31,32,33]
    seconds = range(2, 30, 6)
    for hour, minute, second in product(hours, minutes, seconds):
        time_str = f'{hour:02d}:{minute:02d}:{second:02d}'
        schedule.every().day.at(time_str, 'Europe/Rome').do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)