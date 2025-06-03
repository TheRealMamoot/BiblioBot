import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import asyncpg
import pandas as pd

from src.biblio.utils.utils import get_database_url

DATABASE_URL = get_database_url()


async def fetch_user_reservations(*user_details, include_date: bool = True) -> pd.DataFrame:
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    SELECT
        r.id AS id,
        r.selected_date,
        r.display_date,
        r.start_time,
        r.end_time,
        r.selected_duration,
        r.display_date,
        r.status,
        r.instant,
        r.booking_code,
        u.codice_fiscale,
        u.email
    FROM reservations r
    JOIN users u ON r.user_id = u.id
    WHERE u.codice_fiscale = $1
      AND u.email = $2
    """
    if include_date:
        query += ' AND r.display_date::TEXT = $3\n'
    query += 'ORDER BY r.selected_date DESC;'

    rows = await conn.fetch(query, *user_details)
    await conn.close()
    if not rows:
        return pd.DataFrame()

    # Convert asyncpg.Record to list of dicts
    data = [dict(row) for row in rows]
    logging.info('[DB] *user* reservations fetched')
    return pd.DataFrame(data)


async def fetch_reservations(statuses: list[str], date: datetime.date = None) -> list[dict]:
    if date is None:
        date = datetime.now(ZoneInfo('Europe/Rome')).date()

    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    SELECT r.*,
    u.codice_fiscale,
    u.priority,
    u.email,
    u.name,
    u.chat_id
    FROM reservations r
    JOIN users u ON r.user_id = u.id
    WHERE r.selected_date = $2
    AND r.status = ANY($1)
    ORDER BY u.priority, r.selected_date, r.selected_duration DESC, r.start_time;
    """
    rows = await conn.fetch(query, statuses, date)
    await conn.close()
    logging.info(f'[DB] *pending* reservations fetched - {len(rows)} results')
    return [dict(row) for row in rows] if rows else []


async def fetch_all_reservations() -> pd.DataFrame:
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    SELECT 
    r.id as id,
    user_id,
    chat_id,
    username,
    first_name,
    last_name,
    codice_fiscale as codice,
    email,
    name,
    priority,
    selected_date,
    display_date,
    start_time,
    end_time,
    selected_duration as dur,
    booking_code as code,
    retries,
    status,

    CASE 
    WHEN status = 'existing' THEN 0  
    WHEN status = 'fail' THEN 1  
    WHEN status = 'pending' THEN 2  
    WHEN status = 'success' THEN 3
    WHEN status = 'terminated' THEN 4
    ELSE 5
    END AS status_label,

    instant,
    status_change as change,
    notified,
    inserted_at AT TIME ZONE 'Europe/Rome' as inserted_at,
    updated_at AT TIME ZONE 'Europe/Rome' as updated_at,
    r.created_at AT TIME ZONE 'Europe/Rome' as created_at
    FROM reservations r
    JOIN users u ON r.user_id = u.id
    ORDER BY selected_date DESC, status_label ASC, priority ASC, selected_duration DESC, start_time ASC
    """
    rows = await conn.fetch(query)
    await conn.close()
    if not rows:
        return pd.DataFrame()

    data = [dict(row) for row in rows]
    return pd.DataFrame(data)


async def fetch_reservation_by_id(reservation_id: str) -> dict | None:
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    SELECT r.booking_code
    FROM reservations r
    WHERE r.id = $1
    """
    row = await conn.fetchrow(query, reservation_id)
    await conn.close()
    return dict(row) if row else None


async def fetch_all_user_chat_ids() -> list[str]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch('SELECT DISTINCT chat_id FROM users')
        return [row['chat_id'] for row in rows]
    finally:
        await conn.close()


async def fetch_existing_user(chat_id: str) -> dict | None:
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    SELECT 
    id,
    codice_fiscale,
    name,
    email,
    priority
    FROM users
    WHERE chat_id = $1
    """
    row = await conn.fetchrow(query, chat_id)
    await conn.close()
    return row
