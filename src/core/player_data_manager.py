# src/core/player_data_manager.py
import json
import os
import asyncio
from src.api.sleeper import SleeperClient
from src.api.rapidapi_nfl import RapidApiNFLClient

class PlayerDataManager:
    def __init__(self, sleeper_client: SleeperClient, rapidapi_nfl_client: RapidApiNFLClient):
        self.sleeper_client = sleeper_client
        self.rapidapi_nfl_client = rapidapi_nfl_client
        self._player_id_cache = {} # Map Sleeper Player ID to full data
        self._player_name_to_id_map = {} # Map common name to Sleeper Player ID
        self._player_values = {} # Placeholder for player values (from KTC or other source)

        # File paths for caching
        self.player_cache_file = 'data/player_data_cache.json'
        self.player_values_file = 'data/player_values_cache.json'
        os.makedirs(os.path.dirname(self.player_cache_file), exist_ok=True)


    async def warm_cache(self):
        """Fetches all player data from Sleeper and populates caches."""
        print("Starting player data cache warm-up...")
        all_sleeper_players = self.sleeper_client.get_all_players() # This uses the SleeperClient's internal cache
        
        if all_sleeper_players:
            for player_id, player_data in all_sleeper_players.items():
                self._player_id_cache[player_id] = player_data
                full_name = player_data.get('full_name')
                if full_name:
                    self._player_name_to_id_map[full_name.lower()] = player_id
            
            self._save_cache_to_file()
            print(f"Player data cache warmed with {len(self._player_id_cache)} players.")
        else:
            print("Failed to warm player data cache from Sleeper.")

        # Load player values (e.g., from KTC or other source)
        await self.load_player_values() # Or trigger an update from KTCScraper here


    def _save_cache_to_file(self):
        """Saves the player ID cache to a JSON file."""
        try:
            with open(self.player_cache_file, 'w') as f:
                json.dump(self._player_id_cache, f, indent=4)
            print(f"Player cache saved to {self.player_cache_file}")
        except Exception as e:
            print(f"Error saving player cache to file: {e}")

    def _load_cache_from_file(self):
        """Loads the player ID cache from a JSON file."""
        if os.path.exists(self.player_cache_file):
            try:
                with open(self.player_cache_file, 'r') as f:
                    self._player_id_cache = json.load(f)
                print(f"Player cache loaded from {self.player_cache_file}")
                # Rebuild name map after loading
                self._player_name_to_id_map = {v.get('full_name', '').lower(): k 
                                                for k, v in self._player_id_cache.items() 
                                                if v.get('full_name')}
            except Exception as e:
                print(f"Error loading player cache from file: {e}")
                self._player_id_cache = {} # Reset on error

    async def get_player_info_by_id(self, player_id: str):
        """Get player data by Sleeper ID from cache, fallback to API."""
        if player_id in self._player_id_cache:
            return self._player_id_cache[player_id]
        
        # Fallback to fetching single player info if not in cache (less efficient)
        player_data = self.sleeper_client.get_player_data(player_id)
        if player_data:
            self._player_id_cache[player_id] = player_data # Add to cache
            full_name = player_data.get('full_name')
            if full_name:
                self._player_name_to_id_map[full_name.lower()] = player_id
            return player_data
        return None

    async def get_player_info_by_name(self, player_name: str):
        """Searches for a player by name and returns their info."""
        # First, try exact match on lowercase name
        player_id = self._player_name_to_id_map.get(player_name.lower())
        if player_id:
            return self._player_id_cache.get(player_id)

        # If not found, try partial matching (can be slow for large caches)
        for p_id, p_data in self._player_id_cache.items():
            if player_name.lower() in p_data.get('full_name', '').lower() or \
               player_name.lower() in p_data.get('first_name', '').lower() or \
               player_name.lower() in p_data.get('last_name', '').lower():
                return p_data
        
        return None

    async def load_player_values(self):
        """
        Loads player values (e.g., from a CSV, KTC scraper, or another API).
        This method needs to be implemented based on your value source.
        For KTC, you'd call self.ktc_scraper.get_ktc_values() if it exists.
        """
        # Example: Simulating loading values
        # In a real scenario, you would fetch this from KTCScraper or a dedicated player value API
        # For KTC, the KTCScraper would need a method to return values for all players, not just movers.
        print("Loading player values (placeholder)...")
        # For now, let's assume some dummy values
        self._player_values = {
            "2505": 1000, # Example: Josh Allen
            "1234": 800,  # Example: Patrick Mahomes
            # ... and so on
        }
        print("Player values loaded.")

    async def get_player_value(self, player_id: str):
        """Returns the numerical value of a player."""
        # You'll need to define how player values are sourced and stored.
        # This is a placeholder.
        return self._player_values.get(player_id, 0) # Default to 0 if no value found

    # You might add methods to update player values from a source regularly