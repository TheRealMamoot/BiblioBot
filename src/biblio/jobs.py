import asyncio
import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiocron
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pygsheets import Worksheet
from telegram import Bot

from src.biblio.bot.messages import show_notification
from src.biblio.db.fetch import fetch_all_reservations, fetch_reservations
from src.biblio.db.update import update_record
from src.biblio.reservation.reservation import calculate_timeout, confirm_reservation, set_reservation
from src.biblio.reservation.slot_datetime import reserve_datetime
from src.biblio.utils.notif import notify_donation, notify_reminder, notify_reservation_activation
from src.biblio.utils.utils import ReservationConfirmationConflict, get_wks

SEMAPHORE_LIMIT = 3
semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)


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
        status = 'terminated'
        result = {
            'id': record['id'],
            'status': status,
            'booking_code': 'CLOSED',
            'retries': int(record['retries']),
            'status_change': True,
            'updated_at': datetime.now(ZoneInfo('Europe/Rome')),
        }
        return result

    process_start = time.perf_counter()
    timeout = calculate_timeout(record['retries'])
    try:
        start, end, duration = reserve_datetime(date, start_time, selected_duration)
        logging.info(f'[JOB] ✅ **1** Slot IDENTIFIED for {user_data["cognome_nome"]} - ID {record["id"]}')
        response = await set_reservation(start, end, duration, user_data, timeout)
        logging.info(f'[JOB] ✅ **2** Reservation SET for {user_data["cognome_nome"]} - ID {record["id"]}')
        await confirm_reservation(response['entry'])
        logging.info(f'[JOB] ✅ **3** Reservation CONFIRMED for {user_data["cognome_nome"]} - ID {record["id"]}')

        if chat_id:
            notif = show_notification(status='success', record=record, booking_code=response['codice_prenotazione'])
            await bot.send_message(chat_id=chat_id, text=notif, parse_mode='Markdown')
        status = 'success'
        result = {
            'id': record['id'],
            'status': status,
            'booking_code': response['codice_prenotazione'],
            'retries': int(record['retries']),
            'status_change': record['status'] in ['fail', 'pending'],
            'updated_at': datetime.now(ZoneInfo('Europe/Rome')),
        }

        retries = result['retries']

    except ReservationConfirmationConflict as e:
        logging.error(
            f'[JOB] 🚫 Reservation ALREADY CONFIRMED for {user_data["cognome_nome"]} - ID {record["id"]}: {e}'
        )
        retries = int(record['retries'])
        status = 'existing'
        booking_code = 'UNKNOWN'
        if chat_id:
            notif = show_notification(status, record, booking_code)
            await bot.send_message(chat_id=chat_id, text=notif, parse_mode='Markdown')

        result = {
            'id': record['id'],
            'status': status,
            'booking_code': booking_code,
            'retries': retries,
            'status_change': True,
            'updated_at': datetime.now(ZoneInfo('Europe/Rome')),
        }

    except Exception as e:
        logging.error(f'[JOB] ❌ Reservation FAILED for {user_data["cognome_nome"]} - ID {record["id"]}: {e}')
        retries = int(record['retries']) + 1
        status = 'terminated' if retries > 20 else 'fail'
        booking_code = record['booking_code'] if status == 'fail' else 'CLOSED'
        chat_id = record.get('chat_id')
        if chat_id and (retries % 11 == 0 or status == 'terminated'):
            notif = show_notification(status, record, booking_code)
            await bot.send_message(chat_id=chat_id, text=notif, parse_mode='Markdown')

        result = {
            'id': record['id'],
            'status': status,
            'booking_code': booking_code,
            'retries': retries,
            'status_change': record['status'] in ['pending', 'fail'],
            'updated_at': datetime.now(ZoneInfo('Europe/Rome')),
        }

    process_end = time.perf_counter()
    elapsed = process_end - process_start
    logging.info(f'[JOB] 🕒 Process for {user_data["cognome_nome"]} - ID {result["id"]} took {elapsed:.2f}s')
    logging.info(f'[JOB] Retry {retries} → Delay {timeout.read:.1f}s for ID {record["id"]} in case of timeout')

    return result


async def throttled_process_reservation(record: dict, bot: Bot) -> dict:
    async with semaphore:
        return await process_reservation(record, bot)


async def execute_reservations(bot: Bot) -> None:
    records: list[dict] = await fetch_reservations(statuses=['pending', 'fail'])
    if not records:
        logging.info('[DB-JOB] No pending reservations to process')
        return
    tasks = [throttled_process_reservation(record, bot) for record in records]
    updates = await asyncio.gather(*tasks)
    await asyncio.gather(
        *(update_record('reservations', r['id'], {k: v for k, v in r.items() if k != 'id'}) for r in updates)
    )  # Skip the first value since it is an ID
    logging.info(f'[DB-JOB] Reservation job completed: {len(updates)} updated')


async def backup_reservations(auth_mode: str = 'cloud'):
    df = await fetch_all_reservations()
    if df.empty:
        logging.info('[GSHEET] No data to write to the sheet')
        return

    wks: Worksheet = get_wks(auth_mode)
    wks.clear(start='A1')
    wks.set_dataframe(df, (1, 1))
    logging.info('[GSHEET] Data written to Google Sheet successfully')


def schedule_reserve_job(bot: Bot) -> None:
    scheduler = AsyncIOScheduler(timezone='Europe/Rome')
    trigger = CronTrigger(second='*/10', minute='0,1,2,3,30,31,32,33', hour='5-20', day_of_week='mon-fri')  # UTC
    scheduler.add_job(execute_reservations, trigger, args=[bot])

    trigger = CronTrigger(second='*/20', minute='5,7,10,12,15,17,20', hour='5', day_of_week='mon-fri')  # UTC
    scheduler.add_job(execute_reservations, trigger, args=[bot])

    trigger_sat = CronTrigger(second='*/10', minute='0,1,2,3,30,31,32,33', hour='5-11', day_of_week='sat')  # UTC
    scheduler.add_job(execute_reservations, trigger_sat, args=[bot])

    scheduler.start()


def schedule_backup_job(auth_mode: str = 'cloud') -> None:
    @aiocron.crontab('*/1 * * * *', tz=ZoneInfo('Europe/Rome'))
    async def _backup_job():
        logging.info('[GSHEET] Starting Google Sheets backup')
        await backup_reservations(auth_mode)


def schedule_reminder_job(bot: Bot) -> None:
    @aiocron.crontab('30 23 * * 0-5', tz=ZoneInfo('Europe/Rome'))
    async def _reminder_job():
        logging.info('[NOTIF] Sending reminder notification')
        await notify_reminder(bot)


def schedule_activation_reminder_job(bot: Bot) -> None:
    @aiocron.crontab('15,45 8-21 * * 0-5', tz=ZoneInfo('Europe/Rome'))  # Sun - Fri
    async def _reminder_activation_job():
        logging.info('[NOTIF] Sending slot activation reminder notification')
        await notify_reservation_activation(bot)


def schedule_donation_reminder_job(bot: Bot) -> None:
    @aiocron.crontab('0 18 * * 1,4', tz=ZoneInfo('Europe/Rome'))  # Mon & Thu
    async def _reminder_donation_job():
        logging.info('[NOTIF] Sending donation reminder notification')
        await notify_donation(bot)
