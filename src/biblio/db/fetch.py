import logging

import asyncpg
import pandas as pd

from src.biblio.access import get_database_url


async def fetch_user_reservations(*user_details, include_date: bool = True, db_env='staging') -> pd.DataFrame:
    DATABASE_URL = get_database_url(db_env)
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


async def fetch_pending_reservations(db_env='staging') -> list[dict]:
    DATABASE_URL = get_database_url(db_env)
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    SELECT r.*,
    u.codice_fiscale,
    u.priority,
    u.email,
    u.name ,
    u.chat_id
    FROM reservations r
    JOIN users u ON r.user_id = u.id
    WHERE r.selected_date = CURRENT_DATE
    AND r.status IN ('pending', 'fail')
    ORDER BY u.priority, r.selected_date, r.selected_duration DESC, r.start_time;
    """
    rows = await conn.fetch(query)
    await conn.close()
    logging.info(f'[DB] *pending* reservations fetched - {len(rows)} results')
    return [dict(row) for row in rows] if rows else []


async def fetch_reservation_by_id(reservation_id: str, db_env='staging') -> dict | None:
    DATABASE_URL = get_database_url(db_env)
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    SELECT r.booking_code
    FROM reservations r
    WHERE r.id = $1
    """
    row = await conn.fetchrow(query, reservation_id)
    await conn.close()
    return dict(row) if row else None


async def fetch_existing_user_id(codice: str, email: str, db_env='staging') -> str:
    DATABASE_URL = get_database_url(db_env)
    conn = await asyncpg.connect(DATABASE_URL)
    query = 'SELECT id FROM users WHERE codice_fiscale = $1 AND email = $2'
    row = await conn.fetchrow(query, codice, email)
    await conn.close()
    return row['id'] if row else None
