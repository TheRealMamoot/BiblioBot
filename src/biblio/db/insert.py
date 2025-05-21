import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.db.fetch import fetch_existing_user_id
from src.biblio.utils.utils import get_database_url

DATABASE_URL = get_database_url()


async def writer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    start_time = datetime.strptime(context.user_data['selected_time'], '%H:%M').time()
    start_dt = datetime.combine(date.today(), start_time).replace(tzinfo=ZoneInfo('Europe/Rome'))
    end_dt = start_dt + timedelta(hours=int(context.user_data['selected_duration']))

    data = {
        'user_id': context.user_data['user_id'],
        'selected_date': datetime.strptime(context.user_data['selected_date'], '%A, %Y-%m-%d').date(),
        'display_date': context.user_data['selected_date'],
        'start_time': start_dt.time(),
        'end_time': end_dt.time(),
        'selected_duration': int(context.user_data['selected_duration']),
        'booking_code': context.user_data['booking_code'],
        'retries': int(context.user_data['retries']),
        'status': context.user_data['status'],
        'updated_at': context.user_data.get('updated_at', datetime.now(ZoneInfo('Europe/Rome'))),
        'created_at': context.user_data.get('created_at', datetime.now(ZoneInfo('Europe/Rome'))),
        'instant': bool(context.user_data.get('instant', False)),
        'status_change': bool(context.user_data.get('status_change', False)),
        'notified': bool(context.user_data.get('notified', False)),
        'inserted_at': datetime.now(ZoneInfo('Europe/Rome')),
    }

    await insert_reservation(data)
    logging.info(f'[DB] Reservation inserted for {update.effective_user}')


async def insert_reservation(data: dict):
    columns, placeholders, values = _prepare_insert_parts(data)
    conn = await asyncpg.connect(DATABASE_URL)
    query = f"""
    INSERT INTO reservations ({columns})
    VALUES ({placeholders})
    """
    await conn.execute(query, *values)
    await conn.close()
    logging.info('[DB] Reservation added')


async def insert_user(data: dict) -> str:
    columns, placeholders, values = _prepare_insert_parts(data)

    query = f"""
    INSERT INTO users ({columns})
    VALUES ({placeholders})
    ON CONFLICT DO NOTHING
    RETURNING id
    """
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow(query, *values)

    if row:
        user_id = row['id']
        logging.info(f'[DB] New user inserted: {user_id}')
    else:
        # Fetch the existing one
        user_id = await fetch_existing_user_id(data['codice_fiscale'], data['email'])
        logging.info(f'[DB] Existing user used: {user_id}')
    await conn.close()
    return user_id


def _prepare_insert_parts(data: dict):
    columns = ', '.join(data.keys())
    placeholders = ', '.join(f'${i}' for i in range(1, len(data) + 1))
    values = list(data.values())
    return columns, placeholders, values
