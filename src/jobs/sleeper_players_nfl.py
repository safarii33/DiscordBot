import requests
import json
import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime

# Load DB credentials from .env file
load_dotenv()

DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

def fetch_players():
    """Fetches player data from Sleeper API and returns it as JSON."""
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)

    if response.status_code == 200:
        print("✅ Data fetched successfully")
        return response.json()  # Return JSON data
    else:
        print(f"❌ Failed to fetch players: {response.status_code}")
        exit(1)

def clean_int(value):
    """Convert value to integer if possible, otherwise return None."""
    return int(value) if str(value).strip().isdigit() else None

def process_and_store_players(players):
    """Inserts player data into PostgreSQL safely."""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS nfl_players (
        player_id TEXT PRIMARY KEY,
        team TEXT,
        espn_id TEXT,
        fantasy_data_id INTEGER,
        first_name TEXT,
        last_name TEXT,
        college TEXT,
        position TEXT,
        search_rank INTEGER,
        age INTEGER,
        height TEXT,
        weight TEXT,
        high_school TEXT,
        rookie_year INTEGER,
        years_exp INTEGER,
        depth_chart_order INTEGER,
        rotoworld_id INTEGER,
        active BOOLEAN,
        sportradar_id TEXT,
        number INTEGER,
        rotowire_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Insert or update all players
    for player_id, data in players.items():
        # clean integer values
        metadata = data.get("metadata")  # Get metadata safely
        rookie_year = clean_int(metadata["rookie_year"]) if isinstance(metadata, dict) and "rookie_year" in metadata else None
        search_rank = clean_int(data.get("search_rank"))
        age = clean_int(data.get("age"))
        depth_chart_order = clean_int(data.get("depth_chart_order"))
        rotoworld_id = clean_int(data.get("rotoworld_id"))
        number = clean_int(data.get("number"))
        rotowire_id = clean_int(data.get("rotowire_id"))
        fantasy_data_id = clean_int(data.get("fantasy_data_id"))
        years_exp = clean_int(data.get("years_exp"))
        try:
            cur.execute("""
                INSERT INTO nfl_players (
                    player_id, team, espn_id, fantasy_data_id, first_name, last_name, college, position, search_rank,
                    age, height, weight, high_school, rookie_year, years_exp, depth_chart_order, rotoworld_id,
                    active, sportradar_id, number, rotowire_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (player_id) DO UPDATE 
                SET team = EXCLUDED.team,
                    espn_id = EXCLUDED.espn_id,
                    fantasy_data_id = EXCLUDED.fantasy_data_id,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    college = EXCLUDED.college,
                    position = EXCLUDED.position,
                    search_rank = EXCLUDED.search_rank,
                    age = EXCLUDED.age,
                    height = EXCLUDED.height,
                    weight = EXCLUDED.weight,
                    high_school = EXCLUDED.high_school,
                    rookie_year = EXCLUDED.rookie_year,
                    years_exp = EXCLUDED.years_exp,
                    depth_chart_order = EXCLUDED.depth_chart_order,
                    rotoworld_id = EXCLUDED.rotoworld_id,
                    active = EXCLUDED.active,
                    sportradar_id = EXCLUDED.sportradar_id,
                    number = EXCLUDED.number,
                    rotowire_id = EXCLUDED.rotowire_id
            """, (
                player_id,
                data.get("team"),
                data.get("espn_id"),
                fantasy_data_id,  # Using cleaned version
                data.get("first_name"),
                data.get("last_name"),
                data.get("college"),
                data.get("position"),
                search_rank,  # Using cleaned version
                age,  # Using cleaned version
                data.get("height"),
                data.get("weight"),
                data.get("high_school"),
                rookie_year,  # Using cleaned version
                years_exp,  # Using cleaned version
                depth_chart_order,  # Using cleaned version
                rotoworld_id,  # Using cleaned version
                data.get("active"),
                data.get("sportradar_id"),
                number,  # Using cleaned version
                rotowire_id,  # Using cleaned version
                datetime.now()
            ))
        except Exception as e:
            print(f"❌ Error inserting player {player_id}: {e}")
    # Commit and close
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Player data successfully inserted!")

# Run both functions safely
players_data = fetch_players()  # Step 1: Fetch data from API
process_and_store_players(players_data)  # Step 2: Process and insert data from JSON
