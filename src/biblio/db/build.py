import logging
from pathlib import Path

# import asyncpg
from src.biblio.utils.utils import connect_db

SCHEMA_PATH = Path(__file__).parent / 'schema.sql'


async def build_db():
    conn = await connect_db()
    sql = SCHEMA_PATH.read_text()
    await conn.execute(sql)
    await conn.close()
    logging.info('[DB] Schema applied!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    import asyncio

    asyncio.run(build_db())
