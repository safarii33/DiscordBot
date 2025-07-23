import requests
import json
import os
from datetime import datetime
import asyncio
import asyncpg

# Import the async connection pool functions
from src.db.connections import get_db_connection_pool, close_db_connection_pool

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# --- RapidAPI Configuration ---
# IMPORTANT: Updated for ESPN Core API Athletes endpoint.
# This endpoint provides all active athletes directly, no need to iterate by team.
RAPIDAPI_PLAYERS_BASE_URL = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"
RAPIDAPI_TEAMS_URL = "https://nfl-api-data.p.rapidapi.com/nfl-team-listing/v1/data" # This URL is for teams, keep as is if it works for teams
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST") # Keep these if ESPN API requires them, otherwise they might be ignored/irrelevant
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

# --- Database Configuration ---
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

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

# --- Player Data Ingestion ---

async def fetch_rapidapi_players():
    """
    Fetches all active player data from the ESPN Core API Athletes endpoint.
    Returns a list of all fetched player data.
    """
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        print("❌ RapidAPI Key or Host not found in environment variables. Please set them in your .env file.")
        # Note: ESPN's public APIs might not need these headers. If they don't, you can remove this check
        # and pass an empty headers dict or None to requests.get().
        return None

    all_players_data = []

    try:
        print(f"Attempting to fetch all active players from ESPN Core API URL: {RAPIDAPI_PLAYERS_BASE_URL}")
        response = requests.get(RAPIDAPI_PLAYERS_BASE_URL, headers=HEADERS, timeout=120) # Increased timeout for large response
        response.raise_for_status()
        full_players_response = response.json()
        
        # ESPN Core API for lists often nests items under an 'items' key
        if isinstance(full_players_response, dict) and 'items' in full_players_response:
            if isinstance(full_players_response['items'], list):
                all_players_data.extend(full_players_response['items'])
                print(f"✅ Fetched {len(full_players_response['items'])} active players from ESPN Core API.")
            else:
                print(f"⚠️ Unexpected 'items' format: Expected list, got {type(full_players_response['items'])}. Skipping.")
        else:
            # Fallback if 'items' key is not present, assume response is direct list or dict
            if isinstance(full_players_response, list):
                all_players_data.extend(full_players_response)
                print(f"✅ Fetched {len(full_players_response)} active players (direct list) from ESPN Core API.")
            elif isinstance(full_players_response, dict):
                all_players_data.extend(list(full_players_response.values()))
                print(f"✅ Fetched {len(full_players_response)} active players (dict values) from ESPN Core API.")
            else:
                print(f"⚠️ Unexpected top-level player data format: {type(full_players_response)}. Skipping.")

    except requests.exceptions.Timeout:
        print(f"❌ Failed to fetch players from ESPN Core API: Request timed out after 120 seconds.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch players from ESPN Core API: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to decode JSON response from ESPN Core API: {e}")
        print(f"Raw response content (first 500 chars): {response.text[:500]}")
    except Exception as e:
        print(f"❌ An unexpected error occurred while fetching players from ESPN Core API: {e}")

    print(f"✅ Total players fetched from ESPN Core API: {len(all_players_data)}")
    return all_players_data


async def process_and_store_rapidapi_players(players_data_from_api):
    """
    Processes and stores player data fetched from RapidAPI (ESPN Core API) into the PostgreSQL nfl_players table.
    """
    if not players_data_from_api:
        print("No RapidAPI player data to process.")
        return

    pool = await get_db_connection_pool(DATABASE_URL)
    if not pool:
        print("❌ Could not get a database connection pool. Aborting RapidAPI player processing.")
        return

    async with pool.acquire() as conn:
        async with conn.transaction(): 
            try:
                await conn.execute("""
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
                    years_exp TEXT,
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
                print("✅ nfl_players table schema checked/created for RapidAPI ingestion.")

                if not isinstance(players_data_from_api, list):
                    print("❌ Unexpected RapidAPI player response format. Expected a list of player dictionaries.")
                    return

                processed_count = 0
                for player_raw_data in players_data_from_api:
                    if not isinstance(player_raw_data, dict):
                        print(f"⚠️ Skipping player record: Not a dictionary ({type(player_raw_data)}).")
                        continue
                    if player_raw_data.get("active") is not True:
                        print(f"⚠️ Skipping inactive player: {player_raw_data.get('displayName', 'Unknown Player')}")
                        continue
                    # --- Data Mapping from ESPN Core API Athlete to nfl_players table ---
                    # Based on common ESPN athlete object structure
                    
                    player_id = player_raw_data.get("id") # ESPN's athlete ID
                    
                    if not player_id:
                        print(f"⚠️ Skipping player: No 'id' found in record: {player_raw_data.get('displayName', 'Unknown Player')}")
                        continue

                    player_id_str = str(player_id)

                    # Team abbreviation is usually nested under 'team' object
                    # team_abbr = player_raw_data.get("team", {}).get("abbreviation")
                    
                    # ESPN often has 'firstName' and 'lastName'
                    first_name = player_raw_data.get("firstName")
                    last_name = player_raw_data.get("lastName")
                    
                    # Position abbreviation is usually nested under 'position' object
                    position = player_raw_data.get("position", {}).get("abbreviation")
                    
                    jersey_number = clean_int(player_raw_data.get("jersey"))

                    # ESPN might have 'displayHeight' or 'height' (in inches)
                    height = player_raw_data.get("displayHeight") or player_raw_data.get("height")
                    weight = clean_int(player_raw_data.get("weight"))
                    
                    # College name from nested 'college' object
                    college = player_raw_data.get("college", {}).get("name")
                    
                    # Experience is often nested under 'experience' object
                    years_exp_raw = player_raw_data.get("experience", {}).get("years")
                    years_exp_str = str(years_exp_raw) if years_exp_raw is not None else None
                    
                    # Rookie year might be derived or explicitly provided
                    # ESPN Core API might have a 'rookieYear' or 'firstSeason' field, check API docs
                    rookie_year = clean_int(player_raw_data.get("rookieYear")) # Assuming a 'rookieYear' field
                    if rookie_year is None: # Fallback if not directly provided
                        # Try to infer from 'experience' if 'years' is 0 or 'R'
                        if years_exp_raw == 0 or years_exp_str == 'R':
                            # This is a guess, you might need to get current year or season from another API call
                            rookie_year = datetime.now().year # Or current NFL season year
                    
                    active = player_raw_data.get("active")
                    
                    # ESPN's own ID is typically the 'id' field for the athlete
                    espn_id_str = player_id_str 
                    
                    # Other IDs from Sleeper that ESPN might not have, default to None
                    fantasy_data_id = None
                    search_rank = None
                    age = clean_int(player_raw_data.get("age")) # Assuming 'age' field exists
                    high_school = None # Not commonly in this ESPN athlete endpoint
                    depth_chart_order = None
                    rotoworld_id = None
                    sportradar_id = None
                    number = jersey_number
                    rotowire_id = None

                    try:
                        await conn.execute("""
                            INSERT INTO nfl_players (
                                player_id, team, espn_id, fantasy_data_id, first_name, last_name, college, position, search_rank,
                                age, height, weight, high_school, rookie_year, years_exp, depth_chart_order, rotoworld_id,
                                active, sportradar_id, number, rotowire_id, created_at, last_updated
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
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
                                last_updated = NOW();
                        """, 
                        player_id_str,
                        team_abbr,
                        espn_id_str,
                        fantasy_data_id,
                        first_name,
                        last_name,
                        college,
                        position,
                        search_rank,
                        age,
                        height,
                        weight,
                        high_school,
                        rookie_year,
                        years_exp_str,
                        depth_chart_order,
                        rotoworld_id,
                        active,
                        sportradar_id,
                        number,
                        rotowire_id,
                        datetime.now(),
                        datetime.now()
                        )
                        processed_count += 1
                        
                    except asyncpg.PostgresError as e:
                        print(f"❌ Database error processing RapidAPI player {player_id_str}: {e}")
                    except Exception as e:
                        print(f"❌ Unexpected error processing RapidAPI player {player_id_str}: {e}")
                
                print(f"✅ Processed {processed_count} RapidAPI player records.")
                print(f"✅ All RapidAPI player data processed and stored successfully!")

            except Exception as e:
                print(f"❌ An error occurred during RapidAPI player data processing: {e}")
                raise

# --- Team Data Ingestion ---

def fetch_rapidapi_teams():
    """Fetches team data from RapidAPI and returns it as JSON."""
    if not RAPIDAPI_KEY or not RAPIDAPI_HOST:
        print("❌ RapidAPI Key or Host not found in environment variables. Please set them in your .env file.")
        return None

    try:
        print(f"Attempting to fetch team data from RapidAPI URL: {RAPIDAPI_TEAMS_URL}")
        response = requests.get(RAPIDAPI_TEAMS_URL, headers=HEADERS, timeout=60)
        response.raise_for_status()
        print("✅ Team data fetched successfully from RapidAPI.")
        return response.json()
    except requests.exceptions.Timeout:
        print(f"❌ Failed to fetch teams from RapidAPI: Request timed out after 60 seconds.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch teams from RapidAPI: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to decode JSON response from RapidAPI: {e}")
        print(f"Raw response content (first 500 chars): {response.text[:500]}")
        return None

async def process_and_store_rapidapi_teams(teams_data_from_api):
    """
    Processes and stores team data fetched from RapidAPI into the PostgreSQL nfl_teams table.
    """
    if not teams_data_from_api:
        print("No RapidAPI team data to process.")
        return

    pool = await get_db_connection_pool(DATABASE_URL)
    if not pool:
        print("❌ Could not get a database connection pool. Aborting RapidAPI team processing.")
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS nfl_teams (
                    team_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    short_display_name TEXT,
                    location TEXT,
                    abbreviation TEXT UNIQUE,
                    nickname TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """)
                print("✅ nfl_teams table schema checked/created.")

                teams_to_process = []
                if isinstance(teams_data_from_api, dict):
                    if 'team' in teams_data_from_api and isinstance(teams_data_from_api['team'], dict):
                        teams_to_process.append(teams_data_from_api['team'])
                    elif 'data' in teams_data_from_api and isinstance(teams_data_from_api['data'], list):
                        teams_to_process = teams_data_from_api['data']
                    else:
                        teams_to_process = list(teams_data_from_api.values())
                elif isinstance(teams_data_from_api, list):
                    teams_to_process = teams_data_from_api
                else:
                    print("❌ Unexpected RapidAPI team response format. Expected a list or dictionary of teams.")
                    return

                processed_count = 0
                for team_raw_data in teams_to_process:
                    if not isinstance(team_raw_data, dict):
                        print(f"⚠️ Skipping team record: Not a dictionary ({type(team_raw_data)}).")
                        continue

                    team_data = team_raw_data.get('team', team_raw_data)

                    team_id = clean_int(team_data.get("id"))
                    if team_id is None:
                        print(f"⚠️ Skipping team: No valid 'id' found in record: {team_data.get('displayName', 'Unknown Team')}")
                        continue

                    name = team_data.get("name")
                    display_name = team_data.get("displayName")
                    short_display_name = team_data.get("shortDisplayName")
                    location = team_data.get("location")
                    abbreviation = team_data.get("abbreviation")
                    nickname = team_data.get("nickname")

                    if not name or not display_name or not abbreviation:
                        print(f"⚠️ Skipping team {team_id}: Missing required fields (name, displayName, or abbreviation).")
                        continue

                    try:
                        await conn.execute("""
                            INSERT INTO nfl_teams (
                                team_id, name, display_name, short_display_name, location, abbreviation, nickname, created_at, last_updated
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            ON CONFLICT (team_id) DO UPDATE 
                            SET 
                                name = EXCLUDED.name,
                                display_name = EXCLUDED.display_name,
                                short_display_name = EXCLUDED.short_display_name,
                                location = EXCLUDED.location,
                                abbreviation = EXCLUDED.abbreviation,
                                nickname = EXCLUDED.nickname,
                                last_updated = NOW();
                        """, 
                        team_id,
                        name,
                        display_name,
                        short_display_name,
                        location,
                        abbreviation,
                        nickname,
                        datetime.now(),
                        datetime.now()
                        )
                        processed_count += 1
                        
                    except asyncpg.PostgresError as e:
                        print(f"❌ Database error processing RapidAPI team {team_id}: {e}")
                    except Exception as e:
                        print(f"❌ Unexpected error processing RapidAPI team {team_id}: {e}")
                
                print(f"✅ Processed {processed_count} RapidAPI team records.")
                print(f"✅ All RapidAPI team data processed and stored successfully!")

            except Exception as e:
                print(f"❌ An error occurred during RapidAPI team data processing: {e}")
                raise

# Main execution block
async def main():
    # --- Ingest Teams First ---
    # rapidapi_teams_data = fetch_rapidapi_teams()
    # if rapidapi_teams_data:
        # await process_and_store_rapidapi_teams(rapidapi_teams_data)
    
    # --- Then Ingest Players ---
    rapidapi_players_data = await fetch_rapidapi_players() # Await the async fetch_rapidapi_players
    print("stopping here to debug rapidapi_players_data")
    print(rapidapi_players_data)
    if rapidapi_players_data:
        await process_and_store_rapidapi_players(rapidapi_players_data)
    
    await close_db_connection_pool()

if __name__ == "__main__":
    asyncio.run(main())
