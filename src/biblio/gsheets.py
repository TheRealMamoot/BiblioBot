import logging
import os
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

import aiocron
import asyncpg
import pandas as pd
import pygsheets

from src.biblio.utils.utils import get_database_url

CREDENTIALS_PATH = Path(__file__).resolve().parents[1] / 'biblio' / 'config' / 'biblio.json'
DATABASE_URL = get_database_url()
print(DATABASE_URL)


@cache
def get_gsheet_client(auth_mode: str = 'prod'):
    if auth_mode == 'prod':
        return pygsheets.authorize(service_account_json=os.environ['GSHEETS'])
    elif auth_mode == 'local':
        return pygsheets.authorize(service_file=CREDENTIALS_PATH)
    else:
        raise ValueError('Wrong mode')


def get_wks(auth_mode: str = 'prod'):
    gc = get_gsheet_client(auth_mode)
    return gc.open('Biblio-logs').worksheet_by_title('backup')


async def fetch_all_reservations():
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    SELECT 
    r.id as id,
    user_id,
    chat_id,
    username,
    first_name,
    last_name,
    codice_fiscale,
    priority,
    name,
    email,
    selected_date,
    display_date,
    start_time,
    end_time,
    selected_duration,
    booking_code,
    retries,
    status,
    instant,
    status_change,
    notified,
    inserted_at AT TIME ZONE 'Europe/Rome' as inserted_at,
    updated_at AT TIME ZONE 'Europe/Rome' as updated_at,
    r.created_at AT TIME ZONE 'Europe/Rome' as created_at
    FROM reservations r
    JOIN users u ON r.user_id = u.id
    ORDER BY selected_date ASC, priority ASC, status ASC, selected_duration DESC, start_time ASC
    """
    rows = await conn.fetch(query)
    await conn.close()
    if not rows:
        return pd.DataFrame()

    data = [dict(row) for row in rows]
    return pd.DataFrame(data)


async def backup_reservations(auth_mode: str = 'prod'):
    df = await fetch_all_reservations()
    if df.empty:
        print('[GSHEET] No data to write to the sheet.')
        return

    wks = get_wks(auth_mode)
    wks.clear(start='A1')  # Optional: clear previous backup
    wks.set_dataframe(df, (1, 1))
    print('[GSHEET] Data written to Google Sheet successfully.')


def schedule_backup_job():
    @aiocron.crontab('*/5 * * * *', tz=ZoneInfo('Europe/Rome'))
    async def _backup_job():
        logging.info('[GSHEET] Starting Google Sheets backup')
        await backup_reservations()
        logging.info('[GSHEET] Backup complete.')


if __name__ == '__main__':
    # parser = get_parser()
    # args = parser.parse_args()
    import asyncio

    asyncio.run(backup_reservations(auth_mode='local'))
