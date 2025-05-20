import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from src.biblio.bot.messages import show_notification
from src.biblio.db.fetch import fetch_pending_reservations
from src.biblio.db.update import update_record
from src.biblio.reservation.reservation import confirm_reservation, set_reservation
from src.biblio.reservation.slot_datetime import reserve_datetime

ALLOWED_MINUTES = {0, 1, 30, 31, 32}
ALLOWED_WEEKDAYS = set(range(0, 5))  # Monday to Friday
SATURDAY = 5


async def process_reservation(record: dict, bot: Bot) -> dict:
    chat_id = record.get('chat_id')
    date = record['selected_date'].strftime('%Y-%m-%d')
    start_time = record['start_time'].strftime('%H:%M')
    selected_duration = int(record['selected_duration'])
    user_data = {
        'codice_fiscale': record['codice_fiscale'],
        'cognome_nome': record['name'],
        'email': record['email'],
    }

    now = datetime.now(ZoneInfo('Europe/Rome'))
    scheduled_dt = datetime.combine(record['selected_date'], record['start_time']).replace(
        tzinfo=ZoneInfo('Europe/Rome')
    )

    if record['status'] == 'fail' and scheduled_dt + timedelta(minutes=8) < now:
        logging.info(f'[JOB] ⏰ Reservation too old for ID {record["id"]} — marked as terminated')
        if chat_id:
            notif = show_notification(status='terminated', record=record, booking_code=record['booking_code'])
            await bot.send_message(chat_id=chat_id, text=notif, parse_mode='Markdown')
        result = {
            'id': record['id'],
            'status': 'terminated',
            'booking_code': 'CLOSED',
            'retries': int(record['retries']),
            'status_change': True,
            'notified': True,
            'updated_at': datetime.now(ZoneInfo('Europe/Rome')),
        }
        return result

    try:
        start, end, duration = reserve_datetime(date, start_time, selected_duration)
        logging.info(f'[JOB] ✅ **1** Slot identified for {user_data["cognome_nome"]} - ID {record["id"]}')
        response = await set_reservation(start, end, duration, user_data)
        logging.info(f'[JOB] ✅ **2** Reservation set for {user_data["cognome_nome"]} - ID {record["id"]}')
        await confirm_reservation(response['entry'])
        logging.info(f'[JOB] ✅ **3** Reservation confirmed for {user_data["cognome_nome"]} - ID {record["id"]}')

        if chat_id:
            notif = show_notification(status='success', record=record, booking_code=response['codice_prenotazione'])
            await bot.send_message(chat_id=chat_id, text=notif, parse_mode='Markdown')

        result = {
            'id': record['id'],
            'status': 'success',
            'booking_code': response['codice_prenotazione'],
            'retries': int(record['retries']),
            'status_change': record['status'] in ['fail', 'pending'],
            'notified': True,
            'updated_at': datetime.now(ZoneInfo('Europe/Rome')),
        }

    except Exception as e:
        logging.warning(f'[JOB] ❌ Reservation failed for {user_data["cognome_nome"]} - ID {record["id"]}: {e}')
        retries = int(record['retries']) + 1
        status = 'terminated' if retries > 18 else 'fail'
        booking_code = record['booking_code'] if status == 'fail' else 'CLOSED'
        chat_id = record.get('chat_id')
        if chat_id and (retries % 6 == 0 or status == 'terminated'):
            notif = show_notification(status, record, booking_code)
            await bot.send_message(chat_id=chat_id, text=notif, parse_mode='Markdown')

        result = {
            'id': record['id'],
            'status': status,
            'booking_code': booking_code,
            'retries': retries,
            'status_change': record['status'] in ['pending', 'fail'],
            'notified': True,
            'updated_at': datetime.now(ZoneInfo('Europe/Rome')),
        }

    return result


async def excecute_reservations(bot: Bot, db_env: str = 'staging'):
    records: list[dict] = await fetch_pending_reservations(db_env)
    if not records:
        logging.info('[DB-JOB] No pending reservations to process.')
        return
    tasks = [process_reservation(record, bot) for record in records]
    updates = await asyncio.gather(*tasks)
    await asyncio.gather(
        *(update_record('reservations', r['id'], {k: v for k, v in r.items() if k != 'id'}) for r in updates)
    )  # Skip the first value since it is an ID
    logging.info(f'[DB-JOB] Reservation job completed: {len(updates)} updated')


def schedule_jobs(bot: Bot, db_env='staging'):
    scheduler = AsyncIOScheduler(timezone='Europe/Rome')
    trigger = CronTrigger(second='*/10', minute='0,1,30,31,32', hour='7-22', day_of_week='mon-fri')
    scheduler.add_job(excecute_reservations, trigger, args=[bot, db_env])

    trigger_sat = CronTrigger(second='*/10', minute='0,1,30,31,32', hour='7-13', day_of_week='sat')
    scheduler.add_job(excecute_reservations, trigger_sat, args=[bot, db_env])
    scheduler.start()
