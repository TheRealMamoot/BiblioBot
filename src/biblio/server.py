import os

import asyncpg
from fastapi import FastAPI

users_server = FastAPI()


@users_server.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "ok"}


@users_server.get("/stats")
async def stats():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    count = await conn.fetchval("SELECT COUNT(*) FROM users;")
    res_count = await conn.fetchval("SELECT COUNT(*) FROM reservations")
    await conn.close()
    return {"users": count, "reservations": res_count}
