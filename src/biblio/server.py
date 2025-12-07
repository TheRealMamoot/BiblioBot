import os

import asyncpg
from fastapi import FastAPI

users_server = FastAPI()


@users_server.get("/stats")
async def stats():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    count = await conn.fetchval("SELECT COUNT(*) FROM users;")
    await conn.close()
    return {"users": count}


@users_server.get("/health")
async def health():
    return {"status": "ok"}
