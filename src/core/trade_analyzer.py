# src/core/trade_analyzer.py
import json
from src.api.sleeper import SleeperClient
from src.core.player_data_manager import PlayerDataManager
from src.db.repositories.trade_repo import TradeRepository

class TradeAnalyzer:
    def __init__(self, sleeper_client: SleeperClient, player_data_manager: PlayerDataManager, trade_repository: TradeRepository):
        self.sleeper_client = sleeper_client
        self.player_data_manager = player_data_manager
        self.trade_repository = trade_repository

    async def get_trade_by_id(self, trade_id: str):
        """Fetches a specific trade by ID (from API or DB cache)."""
        # First, try to get from the DB if you've saved it
        trade_from_db = await self.trade_repository.get_trade(trade_id)
        if trade_from_db:
            return trade_from_db

        # Fallback: fetch from Sleeper API (might be slow as it iterates weeks)
        trade_data = self.sleeper_client.get_trade_by_id(trade_id)
        return trade_data

    async def parse_trade_data(self, trade_data: dict, get_team_name_func):
        """
        Parses a raw Sleeper trade transaction into a more digestible format.
        Takes get_team_name_func as a callable to resolve roster_ids to names.
        """
        trade_id = trade_data.get('transaction_id')
        adds = trade_data.get('adds', {})  # Players added: {player_id: roster_id}
        drops = trade_data.get('drops', {}) # Players dropped: {player_id: roster_id}
        draft_picks = trade_data.get('draft_picks', []) # Draft picks traded

        trade_summary = {
            'trade_id': trade_id,
            'teams': {}, # {roster_id: {name, received_players, gave_players, received_picks, gave_picks}}
            'raw_data': trade_data # Keep raw data for debugging/storage
        }

        # Identify all roster IDs involved in the trade
        all_roster_ids = set()
        for player_id, roster_id in adds.items():
            all_roster_ids.add(roster_id)
        for player_id, roster_id in drops.items():
            all_roster_ids.add(roster_id)
        for pick in draft_picks:
            all_roster_ids.add(pick.get('owner_id')) # Original owner of pick
            all_roster_ids.add(pick.get('roster_id')) # New owner of pick in this trade
            all_roster_ids.add(pick.get('previous_owner_id')) # Who gave it up in THIS trade

        # Initialize trade summary for each involved team
        for rid in all_roster_ids:
            trade_summary['teams'][rid] = {
                'name': get_team_name_func(rid),
                'received_players': [],
                'gave_players': [],
                'received_picks': [],
                'gave_picks': []
            }
        
        # Process player additions (who received which player)
        for player_id, receiving_roster_id in adds.items():
            player_info = await self.player_data_manager.get_player_info_by_id(player_id)
            player_name = player_info.get('full_name', f"Player_ID:{player_id}") if player_info else f"Player_ID:{player_id}"
            
            if receiving_roster_id in trade_summary['teams']:
                trade_summary['teams'][receiving_roster_id]['received_players'].append(player_name)
            
            # Find which team dropped this player *in this specific trade*
            # This requires matching the player_id from 'adds' to the player_id in 'drops'
            # and ensuring the roster_id dropping is *not* the roster_id adding.
            for dropped_player_id, dropping_roster_id in drops.items():
                if dropped_player_id == player_id and dropping_roster_id != receiving_roster_id:
                    if dropping_roster_id in trade_summary['teams']:
                        trade_summary['teams'][dropping_roster_id]['gave_players'].append(player_name)
                    break # Found the dropper for this player

        # Process draft picks
        for pick in draft_picks:
            season = pick.get('season')
            round_num = pick.get('round')
            original_owner_roster_id = pick.get('owner_id') # Roster ID of team that originally owned the pick
            receiving_roster_id_in_trade = pick.get('roster_id') # Roster ID of team receiving the pick in THIS trade
            giving_roster_id_in_trade = pick.get('previous_owner_id') # Roster ID of team giving the pick in THIS trade

            pick_str = f"{season} R{round_num} ({get_team_name_func(original_owner_roster_id)}'s Pick)"
            
            if receiving_roster_id_in_trade in trade_summary['teams']:
                trade_summary['teams'][receiving_roster_id_in_trade]['received_picks'].append(pick_str)
            
            if giving_roster_id_in_trade in trade_summary['teams']:
                trade_summary['teams'][giving_roster_id_in_trade]['gave_picks'].append(pick_str)

        return trade_summary

    async def analyze_and_grade_trade(self, trade_data: dict):
        """
        Analyzes a trade based on player values and assigns grades.
        Also determines trade 'wins'/'losses' and updates the database.
        """
        trade_summary = await self.parse_trade_data(trade_data, self._get_team_name_for_analysis)

        # Initialize results for each team
        team_grades = {}
        for roster_id, details in trade_summary['teams'].items():
            team_grades[roster_id] = {
                'team_name': details['name'],
                'received_players_value': 0.0,
                'gave_players_value': 0.0,
                'received_picks_value': 0.0,
                'gave_picks_value': 0.0,
                'net_value_change': 0.0,
                'grade': 'N/A' # A+, B, C, F, etc.
            }

        # Calculate player values
        for roster_id, details in trade_summary['teams'].items():
            # Received Players Value
            for player_name in details['received_players']:
                # Need to map player_name back to player_id for value lookup
                player_info = await self.player_data_manager.get_player_info_by_name(player_name)
                if player_info:
                    value = await self.player_data_manager.get_player_value(player_info['player_id'])
                    team_grades[roster_id]['received_players_value'] += value

            # Gave Players Value
            for player_name in details['gave_players']:
                player_info = await self.player_data_manager.get_player_info_by_name(player_name)
                if player_info:
                    value = await self.player_data_manager.get_player_value(player_info['player_id'])
                    team_grades[roster_id]['gave_players_value'] += value

            # Draft Picks Value (simplified, you'll need a pick value chart)
            # For simplicity, assign dummy values for picks (e.g., 1st round = 100, 2nd = 50 etc.)
            for pick_str in details['received_picks']:
                # Example: Parse '2025 R1'
                if "R1" in pick_str:
                    team_grades[roster_id]['received_picks_value'] += 100
                elif "R2" in pick_str:
                    team_grades[roster_id]['received_picks_value'] += 50
                # ... more sophisticated pick valuation needed here
            for pick_str in details['gave_picks']:
                if "R1" in pick_str:
                    team_grades[roster_id]['gave_picks_value'] += 100
                elif "R2" in pick_str:
                    team_grades[roster_id]['gave_picks_value'] += 50
                # ...

            # Calculate net value change
            net_value_received = team_grades[roster_id]['received_players_value'] + team_grades[roster_id]['received_picks_value']
            net_value_gave = team_grades[roster_id]['gave_players_value'] + team_grades[roster_id]['gave_picks_value']
            team_grades[roster_id]['net_value_change'] = net_value_received - net_value_gave
            
            # Assign a simple grade (this is the AI part you'll refine)
            if team_grades[roster_id]['net_value_change'] > 200:
                team_grades[roster_id]['grade'] = 'A+'
            elif team_grades[roster_id]['net_value_change'] > 100:
                team_grades[roster_id]['grade'] = 'A'
            elif team_grades[roster_id]['net_value_change'] > 0:
                team_grades[roster_id]['grade'] = 'B'
            elif team_grades[roster_id]['net_value_change'] > -100:
                team_grades[roster_id]['grade'] = 'C'
            else:
                team_grades[roster_id]['grade'] = 'F'

        # Determine trade winner(s) and loser(s)
        sorted_teams = sorted(team_grades.items(), key=lambda item: item[1]['net_value_change'], reverse=True)
        
        # This is a simplified way to determine "wins". You might want a threshold.
        winning_roster_id = sorted_teams[0][0]
        losing_roster_id = sorted_teams[1][0] # Assuming 2 teams involved

        if team_grades[winning_roster_id]['net_value_change'] > team_grades[losing_roster_id]['net_value_change']:
            # Store trade win/loss in DB
            await self.trade_repository.record_trade_outcome(
                trade_id=trade_data['transaction_id'],
                winning_roster_id=winning_roster_id,
                losing_roster_id=losing_roster_id,
                winner_grade=team_grades[winning_roster_id]['grade'],
                loser_grade=team_grades[losing_roster_id]['grade']
            )

        return {'trade_summary': trade_summary, 'team_grades': team_grades}

    async def get_league_trade_wins(self):
        """Fetches and aggregates trade wins/losses from the database."""
        # This will query your trade_repository to get aggregated wins/losses per team
        return await self.trade_repository.get_aggregated_trade_wins_losses()

    async def _get_team_name_for_analysis(self, roster_id: str):
        """Helper to get team names for trade analysis context."""
        # You'll need to fetch rosters and users from SleeperClient
        # or have PlayerDataManager manage a lookup.
        users = self.sleeper_client.get_users()
        rosters = self.sleeper_client.get_rosters()

        user_display_names = {u['user_id']: u.get('display_name') for u in users}
        roster_to_owner = {r['roster_id']: r['owner_id'] for r in rosters}
        
        owner_id = roster_to_owner.get(roster_id)
        return user_display_names.get(owner_id, f"Roster {roster_id}")