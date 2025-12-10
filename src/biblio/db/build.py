import logging
from pathlib import Path

from src.biblio.config.config import connect_db

SCHEMA_PATH = Path(__file__).parent / 'schema.sql'
MIGRATIONS_DIR = Path(__file__).parent / 'migrations'


async def build_db():
    conn = await connect_db()
    schema_sql = SCHEMA_PATH.read_text()
    await conn.execute(schema_sql)

    if MIGRATIONS_DIR.exists():
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            migration_sql = migration.read_text()
            await conn.execute(migration_sql)
            logging.info(f"[DB] Migration applied: {migration.name}")

    await conn.close()
    logging.info('[DB] Schema applied!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    import asyncio

    asyncio.run(build_db())
