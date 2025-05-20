import logging
import os

import asyncpg
import pandas as pd

from src.biblio.utils.utils import load_env

load_env()
DATABASE_URL = os.getenv('DATABASE_URL_S')


async def fetch_reservations(*values, include_date: bool = True) -> pd.DataFrame:
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

    rows = await conn.fetch(query, *values)
    await conn.close()
    if not rows:
        return pd.DataFrame()

    # Convert asyncpg.Record to list of dicts
    data = [dict(row) for row in rows]
    logging.info('[DB] history fetched')
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


async def fetch_existing_user_id(codice: str, email: str) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    query = 'SELECT id FROM users WHERE codice_fiscale = $1 AND email = $2'
    row = await conn.fetchrow(query, codice, email)
    await conn.close()
    return row['id'] if row else None
