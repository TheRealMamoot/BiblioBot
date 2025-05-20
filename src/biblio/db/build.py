import logging
from pathlib import Path

import asyncpg

from src.biblio.access import get_database_url
from src.biblio.utils.utils import load_env

SCHEMA_PATH = Path(__file__).parent / 'schema.sql'


async def build_db(db_env='staging'):
    load_env()
    DATABASE_URL = get_database_url(db_env)
    conn = await asyncpg.connect(DATABASE_URL)
    sql = SCHEMA_PATH.read_text()
    await conn.execute(sql)
    await conn.close()
    logging.info('[DB] Schema applied!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    import asyncio

    asyncio.run(build_db(env='staging'))
