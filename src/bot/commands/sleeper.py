# src/bot/commands/sleeper.py
import discord
from discord.ext import commands
from src.api.sleeper import SleeperClient # Your Sleeper API client

class SleeperCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, sleeper_client: SleeperClient):
        self.bot = bot
        self.sleeper_client = sleeper_client

    @commands.command(name="standings")
    async def standings(self, ctx: commands.Context):
        """Command to fetch and display standings from Sleeper."""
        await ctx.defer() # Acknowledge the command quickly

        rosters = self.sleeper_client.get_rosters()
        users = self.sleeper_client.get_users()

        if not rosters or not users or "error" in rosters or "error" in users:
            await ctx.send("Could not retrieve standings data from Sleeper. Please try again later.")
            return

        # Create a mapping for owner_id to display_name
        user_map = {user['user_id']: user.get('metadata', {}).get('team_name', user.get('display_name', 'Unknown Owner')) 
                    for user in users}
        
        standings_msg = "**Sleeper Standings:**\n"
        for team in sorted(rosters, key=lambda x: x['settings']['wins'], reverse=True): # Sort by wins
            wins = team["settings"]["wins"]
            losses = team["settings"]["losses"]
            total_games = wins + losses
            
            calculated_win_percentage = (wins / total_games) * 100 if total_games > 0 else 0 

            team_name = user_map.get(team["owner_id"], f"Roster {team['roster_id']}")
            standings_msg += f"**{team_name}** | **{wins}W - {losses}L** (Win %: **{calculated_win_percentage:.2f}%**)\n"

        await ctx.send(standings_msg)

    @commands.command(name="playerinfo")
    async def playerinfo(self, ctx: commands.Context, *, player_name: str):
        """Fetches and displays basic info for a given player."""
        await ctx.defer()
        
        # The PlayerDataManager should handle searching and caching
        player_data = await self.bot.player_data_manager.get_player_info_by_name(player_name)

        if player_data:
            response = (
                f"**{player_data['full_name']}** ({player_data['position']}, Team: {player_data['team']})\n"
                f"Status: {player_data.get('injury_status', 'Healthy')}\n"
                f"Age: {player_data.get('age', 'N/A')}\n"
                f"Player ID: `{player_data['player_id']}`"
            )
        else:
            response = f"Could not find player: `{player_name}`. Please check spelling."
        
        await ctx.send(response)


    @commands.command(name="trades")
    async def trades(self, ctx: commands.Context, week: int = None):
        """Command to fetch and display league trades for a given week."""
        await ctx.defer()

        # Determine week if not provided
        if week is None:
            nfl_state = self.sleeper_client.get_nfl_state()
            if not nfl_state or "error" in nfl_state:
                await ctx.send("Could not determine current NFL week. Please provide a week number (e.g., `!trades 5`).")
                return
            week = nfl_state.get("leg", 1) # 'leg' is the current week, default to 1 for offseason

        trades_data = self.sleeper_client.get_trades(week)

        if not trades_data:
            await ctx.send(f"No completed trades found for week {week}.")
            return

        response_messages = []
        response_messages.append(f"Recent Trades for Week {week}:")
        
        # Get user display names for the league to make output readable
        users = self.sleeper_client.get_users()
        rosters = self.sleeper_client.get_rosters()
        
        user_display_names = {u['user_id']: u.get('display_name') for u in users}
        roster_to_owner = {r['roster_id']: r['owner_id'] for r in rosters}
        
        def get_team_name_for_trade(roster_id):
            owner_id = roster_to_owner.get(roster_id)
            return user_display_names.get(owner_id, f"Roster {roster_id}")

        for i, trade in enumerate(trades_data):
            # Use the TradeAnalyzer's parse method (or a similar method)
            # This is a simplified example, your TradeAnalyzer will have more sophisticated parsing
            trade_summary = self.bot.trade_analyzer.parse_trade_data(trade, get_team_name_for_trade)
            
            msg = f"\n--- Trade {i+1} (ID: `{trade_summary['trade_id']}`) ---\n"
            for roster_id, details in trade_summary['teams'].items():
                msg += f"**{details['name']}**:\n"
                if details['received_players']:
                    msg += f"  Received: {', '.join(details['received_players'])}\n"
                if details['gave_players']:
                    msg += f"  Gave: {', '.join(details['gave_players'])}\n"
                if details['received_picks']:
                    msg += f"  Received Picks: {', '.join(details['received_picks'])}\n"
                if details['gave_picks']:
                    msg += f"  Gave Picks: {', '.join(details['gave_picks'])}\n"
            
            # Check length before appending to avoid hitting Discord's message limit
            if len("\n".join(response_messages) + msg) > 1900: # Discord max is 2000 chars
                await ctx.send("\n".join(response_messages))
                response_messages = [msg] # Start a new message
            else:
                response_messages.append(msg)
        
        if response_messages:
            await ctx.send("\n".join(response_messages))

# This function is required by discord.py to load the cog
async def setup(bot: commands.Bot):
    # Pass the SleeperClient instance from the bot's custom properties
    await bot.add_cog(SleeperCommands(bot, bot.sleeper_client))