import logging
import os

import asyncpg

from src.biblio.db.fetch import fetch_existing_user_id
from src.biblio.utils.utils import load_env

load_env()
DATABASE_URL = os.getenv('DATABASE_URL_S')


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
