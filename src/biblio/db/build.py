import logging
from pathlib import Path

import asyncpg

from src.biblio.utils.utils import get_database_url

SCHEMA_PATH = Path(__file__).parent / 'schema.sql'
DATABASE_URL = get_database_url()


async def build_db():
    conn = await asyncpg.connect(DATABASE_URL)
    sql = SCHEMA_PATH.read_text()
    await conn.execute(sql)
    await conn.close()
    logging.info('[DB] Schema applied!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    import asyncio

    asyncio.run(build_db())
    