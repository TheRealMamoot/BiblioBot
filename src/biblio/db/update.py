import logging
from typing import Any

import asyncpg

from src.biblio.access import get_database_url

DATABASE_URL = get_database_url()


async def update_cancel_status(reservation_id: str) -> None:
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


async def update_record(table: str, row_id: str, updates: dict[str, Any]) -> None:
    if not updates:
        raise ValueError('No columns provided to update.')

    conn = await asyncpg.connect(DATABASE_URL)

    # Dynamically build column assignments like col1 = $1, col2 = $2 ...
    columns = list(updates.keys())
    placeholders = [f'{col} = ${i + 1}' for i, col in enumerate(columns)]
    set_clause = ', '.join(placeholders)

    # The $N for the WHERE clause (after the update values)
    where_placeholder = f'${len(columns) + 1}'
    query = f"""
    UPDATE {table}
    SET {set_clause}
    WHERE id = {where_placeholder}
    """

    values = list(updates.values()) + [row_id]

    await conn.execute(query, *values)
    await conn.close()

    logging.info(f'[DB] Updated row in {table}, id={row_id}, columns={list(updates.keys())}')
