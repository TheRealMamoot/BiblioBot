import logging
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg
from telegram import Update
from telegram.ext import ContextTypes

from src.biblio.db.insert import insert_reservation
from src.biblio.utils.utils import load_env

load_env()
DATABASE_URL = os.getenv('DATABASE_URL_S')


async def writer(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        'updated_at': context.user_data.get('updated_at', datetime.now()),
        'created_at': datetime.now(),
        'instant': bool(context.user_data.get('instant', False)),
        'status_change': bool(context.user_data.get('status_change', False)),
        'notified': bool(context.user_data.get('notified', False)),
    }

    await insert_reservation(data)
    logging.info(f'[DB] Reservation inserted for {update.effective_user}')


async def update_cancel_status(reservation_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    UPDATE reservations
    SET status = 'terminated',
        notified = TRUE,
        status_change = TRUE,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = $1
    """
    await conn.execute(query, reservation_id)
    await conn.close()
    logging.info(f'[DB] Reservation {reservation_id} marked as terminated')
