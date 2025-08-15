# src/api/sleeper.py
import requests
import json
import os

class SleeperClient: # Renamed from SleeperJob
    BASE_URL = "https://api.sleeper.app/v1"

    def __init__(self, league_id: str):
        self.league_id = league_id
        self._player_cache = None 

    def _make_request(self, endpoint: str):
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status() 
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
            # Handle cases where response might not be valid JSON, especially if API returns an error page
            print(f"Error decoding JSON response from Sleeper API: {json_err} - Raw response: {response.text if response else 'No response'} - URL: {url}")
            return None

    def get_users(self):
        endpoint = f"league/{self.league_id}/users"
        return self._make_request(endpoint)

    def get_rosters(self):
        endpoint = f"league/{self.league_id}/rosters"
        return self._make_request(endpoint)
        
    def get_league_transactions(self, week_number: int):
        endpoint = f"league/{self.league_id}/transactions/{week_number}"
        return self._make_request(endpoint)

    def get_nfl_state(self):
        endpoint = "state/nfl"
        return self._make_request(endpoint)

    def get_all_players(self):
        if self._player_cache:
            return self._player_cache
        endpoint = "players/nfl"
        players_data = self._make_request(endpoint)
        if players_data:
            self._player_cache = players_data
        return players_data

    def get_trades(self, week_number: int):
        all_transactions = self.get_league_transactions(week_number)
        if not all_transactions:
            return [] 
        trades_only = []
        for transaction in all_transactions:
            if transaction.get("type") == "trade" and transaction.get("status") == "complete":
                trades_only.append(transaction)
        return trades_only

    def get_trade_by_id(self, trade_id: str):
        # Sleeper API doesn't have a direct endpoint for a single trade by ID easily.
        # You'd have to iterate through weeks to find it.
        # For simplicity in this example, let's assume we fetch recent weeks or from a database.
        # In a real scenario, you might store trades in your DB.
        
        # A more robust solution: iterate through recent weeks
        # Or, if trades are stored in your DB, fetch from there
        
        # For demonstration, let's assume it's in the current or previous week
        nfl_state = self.get_nfl_state()
        weeks_to_check = []
        if nfl_state and nfl_state.get('leg'):
            weeks_to_check.append(nfl_state['leg'])
            if nfl_state['leg'] > 1:
                weeks_to_check.append(nfl_state['leg'] - 1)
        weeks_to_check.append(1) # Always check week 1 for offseason trades

        for week in weeks_to_check:
            transactions = self.get_league_transactions(week)
            if transactions:
                for trans in transactions:
                    if trans.get('transaction_id') == trade_id and trans.get('type') == 'trade' and trans.get('status') == 'complete':
                        return trans
        return None