import requests

class SleeperJob:
    BASE_URL = "https://api.sleeper.app/v1/league/1180277339947143168"

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

    def get_standings(self):
        """Fetch standings from Sleeper."""
        url = f"{self.BASE_URL}/{self.league_id}/rosters"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch standings: {response.status_code}"}
