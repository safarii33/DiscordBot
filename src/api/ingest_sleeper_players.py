import requests
import json
import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime

# Assuming src.resources.db.database exists and contains get_db_connection
# If you moved this script, ensure your Python path is set correctly
# to resolve 'src' (e.g., by running from the project root with `python -m`)
from src.db.connections import get_db_connection

# Load environment variables from .env file
load_dotenv()

def fetch_players():
    """Fetches player data from Sleeper API and returns it as JSON."""
    url = "https://api.sleeper.app/v1/players/nfl"
    
    try:
        response = requests.get(url, timeout=30) # Add a timeout for robustness
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print("✅ Player data fetched successfully from Sleeper API.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch players from Sleeper API: {e}")
        # It's better to return None or raise a custom exception here
        # so the calling code can handle it gracefully.
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to decode JSON response from Sleeper API: {e}")
        return None

def clean_int(value):
    """
    Converts a value to an integer if possible, otherwise returns None.
    Handles strings that might contain non-digit characters or be empty.
    """
    if value is None:
        return None
    s_value = str(value).strip()
    if s_value.isdigit() or (s_value.startswith('-') and s_value[1:].isdigit()):
        return int(s_value)
    return None

def process_and_store_players(players):
    """
    Inserts or updates player data into the PostgreSQL nfl_players table.
    Uses ON CONFLICT (UPSERT) for efficient updates.
    """
    if not players:
        print("No player data to process.")
        return

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Create table if not exists
        # Added 'last_updated' column and adjusted 'years_exp' to TEXT
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
            years_exp TEXT, -- Changed to TEXT to accommodate 'R' for Rookie
            depth_chart_order INTEGER,
            rotoworld_id INTEGER,
            active BOOLEAN,
            sportradar_id TEXT,
            number INTEGER,
            rotowire_id INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit() # Commit table creation

        # Prepare for batch insertion/update if many players
        # Using a list of tuples for executemany, or individual executes for clarity
        
        insert_count = 0
        update_count = 0

        for player_id, data in players.items():
            # Safely get metadata and then rookie_year from it
            metadata = data.get("metadata", {})
            rookie_year = clean_int(metadata.get("rookie_year"))
            
            # Clean integer values for other fields
            search_rank = clean_int(data.get("search_rank"))
            age = clean_int(data.get("age"))
            depth_chart_order = clean_int(data.get("depth_chart_order"))
            rotoworld_id = clean_int(data.get("rotoworld_id"))
            number = clean_int(data.get("number"))
            rotowire_id = clean_int(data.get("rotowire_id"))
            fantasy_data_id = clean_int(data.get("fantasy_data_id"))
            
            # years_exp can be 'R' for rookie, so keep as TEXT
            years_exp = data.get("years_exp") 

            try:
                cur.execute("""
                    INSERT INTO nfl_players (
                        player_id, team, espn_id, fantasy_data_id, first_name, last_name, college, position, search_rank,
                        age, height, weight, high_school, rookie_year, years_exp, depth_chart_order, rotoworld_id,
                        active, sportradar_id, number, rotowire_id, created_at, last_updated
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (player_id) DO UPDATE 
                    SET 
                        team = EXCLUDED.team,
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
                        rotowire_id = EXCLUDED.rotowire_id,
                        last_updated = NOW(); -- Update the last_updated timestamp
                """, (
                    player_id,
                    data.get("team"),
                    data.get("espn_id"),
                    fantasy_data_id,
                    data.get("first_name"),
                    data.get("last_name"),
                    data.get("college"),
                    data.get("position"),
                    search_rank,
                    age,
                    data.get("height"),
                    data.get("weight"),
                    data.get("high_school"),
                    rookie_year,
                    years_exp, # Use the TEXT value
                    depth_chart_order,
                    rotoworld_id,
                    data.get("active"),
                    data.get("sportradar_id"),
                    number,
                    rotowire_id,
                    datetime.now(), # created_at for initial insert, not updated on conflict
                    datetime.now()  # last_updated will always be updated
                ))
                # Check if it was an insert or update (requires checking rowcount or a RETURNING clause)
                # For simplicity, we'll just count total operations for now.
                if cur.rowcount > 0:
                    # rowcount is 1 for insert, 0 for no change, 1 for update if data changed
                    # To distinguish, you'd need a more complex query or check before insert
                    pass # We'll just commit at the end for efficiency
                
            except psycopg2.Error as e:
                print(f"❌ Database error processing player {player_id}: {e}")
                conn.rollback() # Rollback on individual error to prevent data corruption
            except Exception as e:
                print(f"❌ Unexpected error processing player {player_id}: {e}")
                conn.rollback()
        
        conn.commit() # Commit all changes at once after the loop
        print(f"✅ All player data processed and stored successfully!")

    except psycopg2.Error as e:
        print(f"❌ Database connection or initial table creation error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ An unexpected error occurred during database operations: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# Main execution block
if __name__ == "__main__":
    players_data = fetch_players()
    if players_data:
        process_and_store_players(players_data)
