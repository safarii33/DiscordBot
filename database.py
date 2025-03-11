import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

def get_db_connection():
    """Establish and return a database connection."""
    return psycopg2.connect(**DB_PARAMS)


def get_biggest_moves(time_period="daily"):
    """Fetch the biggest player moves from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT player_name, ktc_value, value_change FROM player_moves
        WHERE time_period = %s
        ORDER BY ABS(value_change) DESC
        LIMIT 5;
        """,
        (time_period,)
    )
    results = cur.fetchall()
    conn.close()
    return results
