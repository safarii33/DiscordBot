# src/db/connection.py
import asyncpg
import os

_db_pool = None

async def get_db_connection_pool(database_url: str):
    global _db_pool
    if _db_pool is None:
        try:
            # Min/Max connections can be tuned based on your needs
            _db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
            print("🗄️ Database connection pool established.")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            _db_pool = None
    return _db_pool

async def close_db_connection_pool():
    global _db_pool
    if _db_pool:
        print("Closing database connection pool...")
        await _db_pool.close()
        _db_pool = None
        print("Database connection pool closed.")