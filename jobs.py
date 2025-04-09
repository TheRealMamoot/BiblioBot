from datetime import datetime
import logging
import time
import os
from zoneinfo import ZoneInfo

import pygsheets
import schedule

from reservation import set_reservation, confirm_reservation
from slot_datetime import reserve_datetime

def job():
    # gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(),'biblio.json')) # Local    
    gc = pygsheets.authorize(service_account_json=os.environ['GSHEETS'])    
    wks = gc.open('Biblio-logs').worksheet_by_title('logs')
    data = wks.get_as_df()
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
            data.loc[idx, 'status_timestamp'] = datetime.now(ZoneInfo('Europe/Rome'))
        except Exception as e:
            logging.error(f'❌ Failed reservation for {user_data['cognome_nome']} — {e}')
            data.loc[idx, 'retries'] = str(int(row['retries'])+1)
            data.loc[idx, 'status'] = 'fail' if int(row['retries']) <= 5 else 'terminated'
            data.loc[idx, 'status_timestamp'] = datetime.now(ZoneInfo('Europe/Rome'))
    data = data[data['status'] != 'terminated']
    wks.clear()
    wks.set_dataframe(data, start='A1', copy_head=True, copy_index=False)
    logging.info(f'🔄 Data refreshed at {datetime.now(ZoneInfo('Europe/Rome'))}')

def run_job():  

    for hour in range(7, 19):  # 9 to 18 inclusive
        for minute in [0,1,2,30,31,32]:
            schedule.every().day.at(f'{hour:02d}:{minute:02d}', 'Europe/Rome').do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)