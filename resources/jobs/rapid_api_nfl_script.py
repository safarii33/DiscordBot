import requests
import json

class RapidApiNFL:
    BASE_URL = "https://nfl-api-data.p.rapidapi.com"

    def __init__(self):
        self.headers = {
            "x-rapidapi-key": "6d00c23a97mshacfcd10ecd38be6p12fd9cjsn51e5d102a15e",
            "x-rapidapi-host": "nfl-api-data.p.rapidapi.com"
        }
    def get_nfl_news(self):
        """Fetch NFL news from the API."""
        url = f"{self.BASE_URL}/nfl-news"
        response = requests.get(url, headers=self.headers)
        with open("nfl_data.json", "w") as f:
            json.dump(response.json(), f, indent=4)
    
    def get_nfl_player_info(self, player_id):
        """Fetch NFL player information from the API."""
        url = f"{self.BASE_URL}/nfl-player-info/v1/data"
        querystring = {"id": player_id}
        response = requests.get(url, headers=self.headers, params=querystring)
        with open("nfl_data.json", "w") as f:
            json.dump(response.json(), f, indent=4)

    def get_nfl_team_listings(self):    
        """Fetch NFL team listings from the API."""
        url = f"{self.BASE_URL}/nfl-team-listing/v1/data"
        response = requests.get(url, headers=self.headers)

        # Print debug info
        print("Status Code:", response.status_code)
        print("Response Text:", response.text[:500])  # Print first 500 chars

        # Check if the response is valid JSON
        if response.status_code == 200:
            try:
                data = response.json()
                with open("nfl_data.json", "w") as f:
                    json.dump(data, f, indent=4)
                print("Data successfully saved to nfl_data.json")
            except requests.exceptions.JSONDecodeError:
                print("Error: Response is not valid JSON")
        else:
            print(f"Error: API request failed with status {response.status_code}")
    
    # def get_nfl_team_listings(self):    
    #     """Fetch NFL team listings from the API."""
    #     url = f"{self.BASE_URL}/nfl-team-listing/v1/data"
    #     response = requests.get(url, headers=self.headers)
    #     # res = json.dump(response.json(), f, indent=4)
    #     # for team in res:
    #     #     print(team["id"])
    #     with open("nfl_data.json", "w") as f:
    #         json.dump(response.json(), f, indent=4)
    #     # return response.json()
    
    def get_nfl_athlete_statistics(self, year, player_id):
        """Fetch NFL athlete statistics from the API."""
        url = f"{self.BASE_URL}/nfl-ath-statistics"
        querystring = {"year": year, "id": player_id}
        response = requests.get(url, headers=self.headers, params=querystring)
        with open("nfl_data.json", "w") as f:
            json.dump(response.json(), f, indent=4)

        # response = requests.get(url, headers=headers) # NFL News
        response = requests.get(url, headers=headers, params=querystring) # NFL Player Info
        print(response.json())
if __name__ == "__main__":
    api = RapidApiNFL()
    # api.get_nfl_news()
    # api.get_nfl_player_info("2532952")
    api.get_nfl_team_listings()
    # api.get_nfl_athlete_statistics(2023, "2532952")