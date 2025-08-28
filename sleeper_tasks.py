import requests
import json
import os
import asyncio
import asyncpg
import pandas as pd
from dotenv import load_dotenv
from src.db.db_operations.connections import get_db_connection_pool, close_db_connection_pool
from src.db.db_operations.create_psg_table import generate_create_table_sql, execute_create_table_sql
load_dotenv()

# --- Database Configuration ---
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


class SleeperJob:
    BASE_URL = "https://api.sleeper.app/v1/"

    def __init__(self, league_id):
        self.league_id = league_id
    
    # --- Helper Method for API Calls (Recommended) ---
    def _make_request(self, endpoint):
        """Helper method to make Sleeper API requests and handle responses."""
        url = f"{self.BASE_URL}{endpoint}"
        print(url)
        try:
            response = requests.get(url, timeout=10) # Add a timeout for robustness
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            if response.status_code == 204:  # No content
                return {}
            elif response.status_code == 200:
                # Attempt to parse JSON response
                res = response.json()  # Clean the JSON data
                df = pd.DataFrame(res)  # Convert to DataFrame if needed
                print("Sleeper API response received successfully.")
                return df
            else:
                print(f"Unexpected status code {response.status_code} for URL: {url}")
        except requests.exceptions.HTTPError as http_err:
            print(f"Sleeper API HTTP error occurred: {http_err} - URL: {url} - Response: {response.text}")
            return None
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Sleeper API Connection error occurred: {conn_err} - URL: {url}")
            return None
        except requests.exceptions.Timeout as timeout_err:
            print(f"Sleeper API Request timed out: {timeout_err} - URL: {url}")
            return None
        except requests.exceptions.RequestException as req_err:
            print(f"An unexpected Sleeper API error occurred: {req_err} - URL: {url}")
            return None
        except json.JSONDecodeError as json_err:
            print(f"Error decoding JSON response from Sleeper API: {json_err} - Raw response: {response.text if response else 'No response'} - URL: {url}")
            return None

    # --- Existing Methods, Updated to use _make_request ---

    def get_users(self):
        """Fetch all users in the Sleeper league. Url: /{league_id}/users"""
        endpoint = f"league/{self.league_id}/users"
        return self._make_request(endpoint)

    def get_rosters(self):
        """Fetch rosters from Sleeper."""
        endpoint = f"league/{self.league_id}/rosters"
        return self._make_request(endpoint)
        
    def get_team_name(self, user_id): # Renamed 'team_id' to 'user_id' for clarity as it maps to Sleeper's user_id
        """
        Returns the team name (display name) from the user_id.
        Fetches users if not already cached.
        """
        # It's more efficient to fetch users once and then look up
        # For simplicity, fetching here. In a larger app, you'd cache this.
        users = self.get_users() 
        if users and not users.get("error"):
            for user in users:
                if user["user_id"] == user_id: # Use user_id as it's consistent
                    # Sleeper often stores team_name in metadata or display_name
                    return user.get("metadata", {}).get("team_name", user.get("display_name", f"User {user_id}"))
            return "Team not found"
        else:
            return "Failed to fetch users for team name"
            
    def get_player_data(self, player_id): # Renamed from get_player_stats for accuracy
        """Fetch individual player data from Sleeper."""
        # Using a direct player ID lookup might be better for individual requests
        # but for many players, `get_all_players` and caching is better.
        endpoint = f"players/nfl/{player_id}"
        return self._make_request(endpoint)
    
    # --- NEW METHODS FOR TRADES ---

    def get_league_transactions(self, round=None, week=None):
        """
        Fetches all transactions for a given league and week.
        Returns a list of transaction objects.
        """
        endpoint = f"league/{self.league_id}/transactions/{round}"
        return self._make_request(endpoint)
    
    # --- THE CORRECTED get_trades METHOD ---
    def get_trades(self, week=None): # Use a clear parameter name
        """
        Fetches all 'trade' transactions for a given league and week number.
        Returns a list of trade transaction objects.
        """
        # Call the general transaction fetching method
        all_transactions = self.get_league_transactions(week)
        
        if not all_transactions:
            return [] # Return an empty list if no transactions or error occurred

        trades_only = []
        for transaction in all_transactions:
            # Filter by type "trade" and ensure status is "complete"
            if transaction.get("type") == "trade" and transaction.get("status") == "complete":
                trades_only.append(transaction)
        
        return trades_only

    def get_nfl_state(self):
        """
        Fetches the current NFL state (current season, week, etc.).
        This is useful to know which week to query for transactions.
        """
        endpoint = "state/nfl"
        return self._make_request(endpoint)

    def get_all_players(self):
        """
        Fetches all NFL player data. This is a very large endpoint
        and should be cached if possible, updated periodically (e.g., once a day).
        """
        if self._player_cache:
            return self._player_cache
            
        endpoint = "players/nfl"
        players_data = self._make_request(endpoint)
        if players_data:
            self._player_cache = players_data # Cache it
        return players_data

    def get_player_name_from_id(self, player_id):
        """
        Helper to get a player's full name and position from their ID.
        Uses the internal player cache.
        """
        if not self._player_cache:
            print("Player cache not loaded. Attempting to load all players...")
            self.get_all_players() # Attempt to load cache

        if self._player_cache:
            player_info = self._player_cache.get(player_id)
            if player_info:
                full_name = player_info.get('full_name')
                position = player_info.get('position')
                return f"{full_name} ({position})" if full_name and position else f"Player_ID:{player_id}"
        return f"Player_ID:{player_id}"
    
    def get_users_leagues(self, user_id, years: list):
        """Fetch all leagues for a given user across multiple years and return as a single DataFrame."""
        all_leagues = []
        for year in years:
            if not isinstance(year, int) or year < 2000 or year > 2100:
                raise ValueError(f"Invalid year: {year}. Year must be a four-digit integer between 2000 and 2100.")
            endpoint = f"user/{user_id}/leagues/nfl/{year}"
            df = self._make_request(endpoint)
            if df is not None and not df.empty:
                all_leagues.append(df)
        if all_leagues:
            return pd.concat(all_leagues, ignore_index=True)
        else:
            return pd.DataFrame()  # Return empty DataFrame if nothing found
    
    def get_league_instances(self):
        """Fetch all league instances for the given league ID."""
        # TODO: Implement pagination if the API supports it and if there are many instances
        pass
        endpoint = f"{self.league_id}/instances"
        return self._make_request(endpoint)
    
    # --- ASYNC METHOD TO INSERT DATAFRAME INTO POSTGRESQL ---
    async def insert_dataframe_sync(self, df: pd.DataFrame, table_name: str, omit_columns: list = None, pk: list = None):
        """
        Bulk upserts all rows from a DataFrame into the specified PostgreSQL table.
        Uses (user_id, league_id) as the composite key.
        Allows omitting specified columns from insert.
        """
        if df.empty:
            print("❌ DataFrame is empty. No data to insert.")
            return False

        # Omit specified columns
        if omit_columns:
            for col in omit_columns:
                if col in df.columns:
                    df = df.drop(columns=[col])

        # Cast 'metadata' dicts to JSON strings if present
        # Define which columns should be treated as dicts and which as lists
        dict_columns = ['metadata', 'settings', 'scoring_settings', 'co_owners']
        list_columns = ['roster_positions', 'players', 'reserve', 'starters', 'taxi']

        for col in dict_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else str(x))

        for col in list_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else str(x))

        if 'owner_id' in df.columns:
            df = df.rename(columns={'owner_id': 'user_id'})

        pool = await get_db_connection_pool(DATABASE_URL)
        if not pool:
            print("❌ Could not get a database connection pool. Aborting insert.")
            return False
        async with pool.acquire() as conn:
            async with conn.transaction():
                columns = [ ''.join(c if c.isalnum() else '_' for c in col).lower() for col in df.columns ]
                values = [tuple(row) for row in df.values]
                placeholders = ', '.join([f"${i+1}" for i in range(len(columns))])
                update_assignments = ', '.join([f"{col}=EXCLUDED.{col}" for col in columns if col not in pk])
                upsert_sql = (
                    f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders}) "
                    f"ON CONFLICT ({', '.join(pk)}) DO UPDATE SET {update_assignments}"
                )
                try:
                    await conn.executemany(upsert_sql, values)
                    print(f"✅ Bulk upserted {len(values)} rows into {table_name}.")
                    return True
                except asyncpg.PostgresError as e:
                    print(f"❌ Database error during bulk upsert: {e}")
                    return False
                except Exception as e:
                    print(f"❌ Unexpected error during bulk upsert: {e}")
                    return False
    

# Then call it like this:
async def main():
    # Main method to run all ingestion jobs
    # Define columns to exclude from inserts for each table
    users_col_exclude = ['settings']
    league_col_exclude = []
    rosters_col_exclude = []
    league_id_from_env = os.getenv("LEAGUE_ID") 
    
    # Create an instance of the SleeperJob class
    sleeper_job_instance = SleeperJob(league_id=league_id_from_env)

    # Example usage: Fetch all users in the league
    users = sleeper_job_instance.get_users()
    if users is not None and not users.empty:
        print(f"Successfully fetched users from Sleeper.")
        sleeper_users_table_name = "SLEEPER.SLEEPER_USERS"  # Define your table name
        sql_output = generate_create_table_sql(users, sleeper_users_table_name, False)

        # Optionally, print the number of users fetched
        print(f"Total users fetched: {len(users)}")
    else:
        print("Failed to fetch users or no users found.")

    # Execute the generated SQL statement
    success = await execute_create_table_sql(sql_output)

    if success:
        print(f"Table '{sleeper_users_table_name}' is ready in your database.")
        await sleeper_job_instance.insert_dataframe_sync(users, sleeper_users_table_name, users_col_exclude, pk = ["user_id", "league_id"])
    else:
        print(f"Failed to create table '{sleeper_users_table_name}'. Check logs for errors.")

    # Fetch leagues for a user
    leagues = sleeper_job_instance.get_users_leagues(user_id=os.environ.get("SLEEPER_USER_ID"), years=[2022, 2023, 2024, 2025])

    if leagues is not None and not leagues.empty:
        print(f"Successfully fetched leagues for user.")
        leagues_table_name = "SLEEPER.LEAGUES"  # Define your table name        
        sql_output = generate_create_table_sql(leagues, leagues_table_name, True)
        # Optionally, print the number of leagues fetched
        print(f"Total leagues fetched: {len(leagues)}")
    else:
        print("Failed to fetch leagues or no leagues found.")

    # Execute the generated SQL statement
    success = await execute_create_table_sql(sql_output)
    if success:
        print(f"Table '{leagues_table_name}' is ready in your database.")
        await sleeper_job_instance.insert_dataframe_sync(leagues, leagues_table_name, league_col_exclude, pk = ["league_id"])

    # Fetch rosters for a user
    rosters = sleeper_job_instance.get_rosters()

    if rosters is not None and not rosters.empty:
        print(f"Successfully fetched rosters for user.")
        rosters_table_name = "SLEEPER.USER_ROSTERS"  # Define your table name        
        sql_output = generate_create_table_sql(rosters, rosters_table_name, True)

        # Optionally, print the number of rosters fetched
        print(f"Total rosters fetched: {len(rosters)}")
    else:
        print("Failed to fetch rosters or no rosters found.")

    # Execute the generated SQL statement
    success = await execute_create_table_sql(sql_output)

    if success:
        print(f"Table '{rosters_table_name}' is ready in your database.")
        await sleeper_job_instance.insert_dataframe_sync(rosters, rosters_table_name, rosters_col_exclude, pk = ["league_id", "user_id"])

if __name__ == "__main__":
    # This block ensures that run_all_ingestion_jobs() is called when the script is executed
    print("Executing data ingestion script...")
    asyncio.run(main())
    print("Data ingestion script finished.")