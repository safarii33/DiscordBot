import requests
import json
from datetime import datetime
import psycopg2
from resources.db.database import get_db_connection

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
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            print("✅ Data fetched successfully")
        for team in res:
            self.store_team_data(team)

        with open("nfl_data.json", "w") as f:
            json.dump(res.json(), f, indent=4)
        # return response.json()
    
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
    
    def store_team_data(self, team_data):
        """Insert team data into the database"""
        # todo: check if team_data is a valid JSON object before processing
        if isinstance(team_data, bytes):
            team_data = json.loads(team_data.decode("utf-8"))
        team = team_data.get("team", {})

        # Extract required fields
        team_id = int(team.get("id", 0))
        uid = team.get("uid", "")
        slug = team.get("slug", "")
        abbreviation = team.get("abbreviation", "")
        display_name = team.get("displayName", "")
        short_display_name = team.get("shortDisplayName", "")
        name = team.get("name", "")
        nickname = team.get("nickname", "")
        location = team.get("location", "")
        color = team.get("color", "")
        alternate_color = team.get("alternateColor", "")
        is_active = team.get("isActive", False)

        # Extract the "roster" and "statistics" links
        links = team.get("links", [])
        roster_link = ""
        stats_link = ""

        for link in links:
            if "roster" in link.get("rel", []):
                roster_link = link.get("href", "")
            elif "stats" in link.get("rel", []):
                stats_link = link.get("href", "")
        conn = get_db_connection()
        query = """
            MERGE INTO teams AS target
            USING (VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s))
            AS source (team_id, uid, slug, abbreviation, display_name, short_display_name, name, nickname, 
                    location, roster_link, stats_link)
            ON target.team_id = source.team_id
            WHEN MATCHED THEN 
                UPDATE SET 
                    uid = source.uid,
                    slug = source.slug,
                    abbreviation = source.abbreviation,
                    display_name = source.display_name,
                    short_display_name = source.short_display_name,
                    name = source.name,
                    nickname = source.nickname,
                    location = source.location,
                    roster_link = source.roster_link,
                    stats_link = source.stats_link
            WHEN NOT MATCHED THEN 
                INSERT (team_id, uid, slug, abbreviation, display_name, short_display_name, name, nickname, 
                        location, roster_link, stats_link)
                VALUES (source.team_id, source.uid, source.slug, source.abbreviation, source.display_name, source.short_display_name, 
                        source.name, source.nickname, source.location, source.roster_link, source.stats_link);
            """

        try:
            with conn.cursor() as cur:
                cur.execute(query, (
                    team_id, uid, slug, abbreviation, display_name, short_display_name, 
                    name, nickname, location, roster_link, stats_link
                ))
                conn.commit()
                print(f"Merged team: {display_name}")
        except Exception as e:
            conn.rollback()
            print(f"Error merging {display_name}: {e}")
if __name__ == "__main__":
    api = RapidApiNFL()
    # api.get_nfl_news()
    # api.get_nfl_player_info("2532952")
    api.get_nfl_team_listings()
    # api.get_nfl_athlete_statistics(2023, "2532952")