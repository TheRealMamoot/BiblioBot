import logging
import os
from pathlib import Path

import asyncpg

from src.biblio.utils.utils import load_env

SCHEMA_PATH = Path(__file__).parent / 'schema.sql'


async def build_db(env='staging'):
    load_env()
    DATABASE_URL = os.getenv('DATABASE_URL_S') if env == 'staging' else os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(DATABASE_URL)
    sql = SCHEMA_PATH.read_text()
    await conn.execute(sql)
    await conn.close()
    logging.info('[DB] Schema applied!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    import asyncio

    asyncio.run(build_db(env='staging'))
