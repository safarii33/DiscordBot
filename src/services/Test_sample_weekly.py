import pandas as pd
import asyncpg
from src.db.connections import get_db_connection_pool, close_db_connection_pool

async def fetch_weekly_data():
    conn = await asyncpg.connect(get_db_connection_pool)
    rows = await conn.fetch("SELECT * FROM nfl_weekly_data_raw")
    await conn.close()
    df = pd.DataFrame(rows)
    return df