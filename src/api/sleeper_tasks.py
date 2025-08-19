import requests
import json
import os

class SleeperJob:
    BASE_URL = "https://api.sleeper.app/v1/league"

    def __init__(self, league_id):
        self.league_id = league_id

    def get_users(self):
        """Fetch all users in the Sleeper league."""
        url = f"{self.BASE_URL}/{self.league_id}/users"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch users: {response.status_code}"}
    
    # --- Helper Method for API Calls (Recommended) ---
    def _make_request(self, endpoint):
        """Helper method to make Sleeper API requests and handle responses."""
        url = f"{self.BASE_URL}/{endpoint}"
        print(url)
        try:
            response = requests.get(url, timeout=10) # Add a timeout for robustness
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
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
        """Fetch all users in the Sleeper league."""
        endpoint = f"{self.league_id}/users"
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
        endpoint = f"{self.league_id}/transactions/{round}"
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

# First, instantiate the class
# You need to provide the league_id when creating the SleeperJob object
my_league_id = "YOUR_SLEEPER_LEAGUE_ID" # Replace with your actual league ID
sleeper_api_instance = SleeperJob(league_id=my_league_id)


# Your method definition:
# def get_league_transactions(self, round=None, week=None)
# This allows either 'round' or 'week' keyword argument.

# If you prefer to stick to 'week' as the primary parameter:
# def get_league_transactions(self, week):
#     """
#     Fetches all transactions for a given league and week.
#     Returns a list of transaction objects.
#     """
#     endpoint = f"league/{self.league_id}/transactions/{week}"
#     return self._make_request(endpoint)

# Then call it like this:
if __name__ == "__main__":
    # It's good practice to get the league ID from an environment variable
    # For testing, you can hardcode it temporarily, but remove before deployment.
    league_id_from_env = os.getenv("LEAGUE_ID") 
    
    # Create an instance of the SleeperJob class
    sleeper_job_instance = SleeperJob(league_id=league_id_from_env)
    # Example usage: Fetch all users in the league
    users = sleeper_job_instance.get_users()

    # Now call the method on that instance, passing the 'week' argument
    # trades = sleeper_job_instance.get_league_transactions(round=1)
    # trades = sleeper_job_instance.get_trades(week=1)  
    
    # if trades:
    #     print(f"Successfully fetched {len(trades)} transactions for week 1.")
        # You can now iterate through 'trades' and process them
    #     for trade in trades[:5]: # Print first 5 for brevity
    #         print(json.dumps(trade, indent=2))
    #         print("")
    # else:
    #     print("Failed to fetch transactions or no transactions found.")