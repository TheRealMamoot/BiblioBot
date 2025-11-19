import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.config.config import connect_db


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
        'inserted_at': datetime.now(ZoneInfo('Europe/Rome')),
    }

    await insert_reservation(data)
    logging.info(f'[DB] Reservation inserted for {update.effective_user}')


async def insert_reservation(data: dict):
    columns, placeholders, values = _prepare_insert_parts(data)
    conn = await connect_db()
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
    ON CONFLICT (codice_fiscale, email, name) DO NOTHING
    RETURNING id
    """

    conn = await connect_db()
    try:
        row = await conn.fetchrow(query, *values)
        if row:
            logging.info('[DB] new user inserted.')
            return row['id']
        # insert didn't happen, so fetch the correct user_id
        fallback_query = """
        SELECT id FROM users
        WHERE codice_fiscale = $1 AND email = $2 AND name = $3
        """
        fallback_row = await conn.fetchrow(fallback_query, data['codice_fiscale'], data['email'], data['name'])
        if fallback_row:
            logging.info('[DB] Insert skipped due to conflict (user already exists).')
            return fallback_row['id']
        else:
            raise ValueError('[DB] Failed to insert or retrieve existing user.')
    finally:
        await conn.close()


async def insert_slots(slots: dict[str, int]) -> None:
    conn = await connect_db()
    try:
        async with conn.transaction():
            for slot, available in slots.items():
                query = """
                INSERT INTO slots (slot, available)
                VALUES ($1, $2)
                """
                await conn.execute(query, slot, available)
        logging.info(f'[DB] Inserted {len(slots)} slot records in batch.')
    finally:
        await conn.close()


def _prepare_insert_parts(data: dict):
    columns = ', '.join(data.keys())
    placeholders = ', '.join(f'${i}' for i in range(1, len(data) + 1))
    values = list(data.values())
    return columns, placeholders, values
