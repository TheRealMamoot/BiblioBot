import logging
from typing import Any

from src.biblio.config.config import (
    DEFAULT_PRIORITY,
    Status,
    connect_db,
    get_priorities,
)


async def upsert_setting(key: str, value: str) -> None:
    conn = await connect_db()
    try:
        await conn.execute(
            """
            INSERT INTO settings (key, value)
            VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
            """,
            key,
            value,
        )
    finally:
        await conn.close()


async def update_cancel_status(reservation_id: str) -> None:
    conn = await connect_db()
    query = """
    UPDATE reservations
    SET status = $1,
        canceled_at = CURRENT_TIMESTAMP,
        notified = TRUE,
        status_change = TRUE,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = $2
    """
    await conn.execute(query, Status.CANCELED, reservation_id)
    await conn.close()
    logging.info(f"[DB] Reservation {reservation_id} marked as {Status.CANCELED}")


async def update_record(table: str, row_id: str, updates: dict[str, Any]) -> None:
    if not updates:
        raise ValueError("No columns provided to update.")

    conn = await connect_db()

    # Dynamically build column assignments like col1 = $1, col2 = $2 ...
    columns = list(updates.keys())
    placeholders = [f"{col} = ${i + 1}" for i, col in enumerate(columns)]
    set_clause = ", ".join(placeholders)

    # The $N for the WHERE clause (after the update values)
    where_placeholder = f"${len(columns) + 1}"
    query = f"""
    UPDATE {table}
    SET {set_clause}
    WHERE id = {where_placeholder}
    """

    values = list(updates.values()) + [row_id]

    await conn.execute(query, *values)
    await conn.close()

    logging.info(
        f"[DB] Updated row in {table}, id={row_id}, columns={list(updates.keys())}"
    )


async def sync_user_priorities() -> int:
    priorities = get_priorities()
    conn = await connect_db()
    try:
        rows = await conn.fetch("SELECT id, codice_fiscale FROM users")
        updates = []
        for row in rows:
            codice = row["codice_fiscale"].upper()
            priority = int(priorities.get(codice, DEFAULT_PRIORITY))
            updates.append((priority, row["id"]))
        if not updates:
            return 0
        async with conn.transaction():
            await conn.executemany(
                "UPDATE users SET priority = $1 WHERE id = $2",
                updates,
            )
        logging.info(f"[DB] Synced priorities for {len(updates)} users")
        return len(updates)
    finally:
        await conn.close()


async def sweep_stuck_reservations(
    stale_minutes: int = 5,
    activation_grace_minutes: int = 30,
) -> list[dict]:
    """
    Reset reservations stuck in processing/awaiting_confirmation beyond stale_minutes.
    If the slot start + activation_grace_minutes has passed, terminate; otherwise mark fail. normal processing will pick them up.
    """
    conn = await connect_db()
    query = """
    UPDATE reservations r
    SET status = CASE
        WHEN (r.selected_date || ' ' || r.start_time)::timestamp
             AT TIME ZONE 'Europe/Rome' + make_interval(mins => $2) < now() AT TIME ZONE 'Europe/Rome'
          THEN $3
        ELSE $4
    END,
        retries = r.retries + 1,
        status_change = TRUE,
        updated_at = CURRENT_TIMESTAMP,
        fail_at = CASE
            WHEN (r.selected_date || ' ' || r.start_time)::timestamp
                 AT TIME ZONE 'Europe/Rome' + make_interval(mins => $2) < now() AT TIME ZONE 'Europe/Rome'
              THEN r.fail_at
            ELSE CURRENT_TIMESTAMP
        END,
        terminated_at = CASE
            WHEN (r.selected_date || ' ' || r.start_time)::timestamp
                 AT TIME ZONE 'Europe/Rome' + make_interval(mins => $2) < now() AT TIME ZONE 'Europe/Rome'
              THEN CURRENT_TIMESTAMP
            ELSE r.terminated_at
        END
    WHERE r.status IN ($5, $6)
      AND r.updated_at < now() - make_interval(mins => $1)
    RETURNING id, status, retries
    """
    rows = await conn.fetch(
        query,
        stale_minutes,
        activation_grace_minutes,
        Status.TERMINATED,
        Status.FAIL,
        Status.PROCESSING,
        Status.AWAITING,
    )
    await conn.close()
    if rows:
        logging.info(f"[DB] Swept {len(rows)} stuck reservations")
    return [dict(row) for row in rows] if rows else []
