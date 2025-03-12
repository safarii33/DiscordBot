import requests

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

    def get_standings(self):

        """get standings is a method that fetches the standings from Sleeper.
        It returns the standings in the form of a JSON object."""
        """Fetch standings from Sleeper."""
        url = f"{self.BASE_URL}/{self.league_id}/rosters"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch standings: {response.status_code}"}
        
    def get_team_name(self, team_id):
        """
        returns the team name from the team_id
        in the form of a string.
        get team name is a method that fetches the team name from Sleeper.
        So that our standings method can display the team name instead of the team ID."""
        """Fetch team name from Sleeper."""
        url = f"https://api.sleeper.app/v1/league/{self.league_id}/users"
        response = requests.get(url)

        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user["user_id"] == team_id:
                    return user.get("team_name") or user.get("metadata", {}).get("team_name", f"{user.get('display_name')}")
            return "Team not found"
        else:
            return "Failed to fetch team name"
