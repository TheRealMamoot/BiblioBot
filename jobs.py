from datetime import datetime, timedelta, time as dt_time
from itertools import product
import logging
import time
import os
from zoneinfo import ZoneInfo

import pandas as pd
import pygsheets
from pygsheets import   Worksheet
import schedule
from telegram.ext import Application

from reservation import set_reservation, confirm_reservation
from slot_datetime import reserve_datetime
from utils import update_gsheet_data_point

def reserve_job():
    # gc = pygsheets.authorize(service_file=os.path.join(os.getcwd(),'biblio.json')) # Local - Must be commented by default.    
    gc = pygsheets.authorize(service_account_json=os.environ['GSHEETS'])    
    wks: Worksheet = gc.open('Biblio-logs').worksheet_by_title('logs')
    # wks = gc.open('Biblio-logs').worksheet_by_title('tests') # Commented by default - only for tests
    data = wks.get_as_df()
    data['temp_duration_int'] = pd.to_numeric(data['selected_dur'])
    data['temp_date'] = pd.to_datetime(data['selected_date'])
    data['temp_date'] = data['temp_date'].dt.tz_localize('UTC').dt.tz_convert('Europe/Rome')
    data['temp_start'] = pd.to_datetime(data['start'], format='%H:%M').dt.time
    data['temp_datetime'] = data.apply(
        lambda row: datetime.combine(
            row['temp_date'].date(), row['temp_start']
        ).replace(tzinfo=ZoneInfo('Europe/Rome')),
        axis=1
    )
    data['retries'] = data['retries'].astype(str)
    data: pd.DataFrame = data.sort_values(['temp_datetime','priority','temp_duration_int', 'temp_start'], ascending=[True, True, False, True])
    today = datetime.now(ZoneInfo('Europe/Rome')).today().strftime('%A, %Y-%m-%d')
    for _, row in data.iterrows():
        id = row['id']
        status_change = False
        old_status = row['status']
        if row['status_change']=='True':
            continue
        
        if row['selected_date'] != today:
            continue

        now = datetime.now(ZoneInfo('Europe/Rome'))
        print(f"{row['temp_datetime'] + timedelta(minutes=3)}")
        print(f'{now}')

        if row['temp_datetime'] + timedelta(minutes=8) < now and row['status']=='fail':
            update_gsheet_data_point(data, id, 'status', 'terminated', wks)
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
            update_gsheet_data_point(data, id, 'status', 'success', wks)
            update_gsheet_data_point(data, id, 'booking_code', reservation_response['codice_prenotazione'], wks)
            update_gsheet_data_point(data, id, 'updated_at', datetime.now(ZoneInfo('Europe/Rome')), wks)

        except Exception as e:
            logging.error(f'❌ Failed reservation for {user_data['cognome_nome']} — {e}')
            update_gsheet_data_point(data, id, 'retries', int(row['retries'])+1, wks)
            changed_status = 'terminated' if int(row['retries']) > 18 else 'fail'
            update_gsheet_data_point(data, id, 'status', changed_status, wks)
            update_gsheet_data_point(data, id, 'updated_at', datetime.now(ZoneInfo('Europe/Rome')), wks)

        new_data = wks.get_as_df()
        new_status = new_data.loc[new_data['id'] == id, 'status'].values[0]
        if (old_status=='fail' or old_status=='pending') and old_status!=new_status:
            status_change = True

        update_gsheet_data_point(data, id, 'status_change', status_change, wks)
        
    del data['temp_duration_int'], data['temp_date'], data['temp_start'], data['temp_datetime']
    logging.info(f'🔄 Data refreshed at {datetime.now(ZoneInfo('Europe/Rome'))}')

def run_reserve_job():  
    hours = range(7, 23)  # 7 to 18 inclusive
    minutes = [0,1,30,31,32]
    seconds = range(2, 30, 6)
    for hour, minute, second in product(hours, minutes, seconds):
        time_str = f'{hour:02d}:{minute:02d}:{second:02d}'  
        schedule.every().day.at(time_str, 'Europe/Rome').do(reserve_job)
    while True:
        schedule.run_pending()
        time.sleep(1)

def run_notify_job(application: Application, function):
    for hour in range(7, 23):
        for minute in [3,5,15,33,35,45]:
            job_time = dt_time(hour=hour, minute=minute, tzinfo=ZoneInfo('Europe/Rome'))
            application.job_queue.run_daily(
                function,
                time=job_time,
                name=f'Notification update job at {hour:02d}:{minute:02d}'
            )