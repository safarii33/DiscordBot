# src/bot/commands/trade.py
import discord
from discord.ext import commands
from src.core.trade_analyzer import TradeAnalyzer # Your Trade Analyzer logic

class TradeCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, trade_analyzer: TradeAnalyzer):
        self.bot = bot
        self.trade_analyzer = trade_analyzer

    @commands.command(name="gradetrade")
    async def grade_trade(self, ctx: commands.Context, trade_id: str):
        """Analyzes and grades a specific trade."""
        await ctx.defer()
        
        # Get the original trade data
        trade_data = await self.trade_analyzer.get_trade_by_id(trade_id)
        
        if not trade_data:
            await ctx.send(f"Could not find a completed trade with ID: `{trade_id}`.")
            return
        
        # Perform the grading
        grading_result = await self.trade_analyzer.analyze_and_grade_trade(trade_data)
        
        if grading_result:
            response_msg = f"**Trade Analysis for Trade ID: `{trade_id}`**\n"
            for roster_id, result in grading_result['team_grades'].items():
                response_msg += f"**{result['team_name']}**: Grade: **{result['grade']}** ({result['net_value_change']:.2f})\n"
                response_msg += f"  - Players Received Value: {result['received_players_value']:.2f}\n"
                response_msg += f"  - Players Gave Value: {result['gave_players_value']:.2f}\n"
                response_msg += f"  - Picks Received Value: {result['received_picks_value']:.2f}\n"
                response_msg += f"  - Picks Gave Value: {result['gave_picks_value']:.2f}\n"
            
            await ctx.send(response_msg)
        else:
            await ctx.send(f"Failed to grade trade ID: `{trade_id}`. An internal error occurred.")


    @commands.command(name="tradewins")
    async def display_trade_wins(self, ctx: commands.Context):
        """Displays current trade win/loss records for the league."""
        await ctx.defer()
        
        trade_wins_data = await self.trade_analyzer.get_league_trade_wins()
        
        if not trade_wins_data:
            await ctx.send("No trade win/loss data available yet. Start grading some trades!")
            return
        
        response_msg = "**League Trade Wins/Losses:**\n"
        # Sort by net wins for display
        sorted_data = sorted(trade_wins_data.items(), key=lambda item: item[1]['wins'] - item[1]['losses'], reverse=True)

        for roster_id, data in sorted_data:
            response_msg += (
                f"**{data['team_name']}**: {data['wins']} Wins - {data['losses']} Losses "
                f"(Net: {data['wins'] - data['losses']})\n"
            )
        
        await ctx.send(response_msg)

# This function is required by discord.py to load the cog
async def setup(bot: commands.Bot):
    # Pass the TradeAnalyzer instance from the bot's custom properties
    await bot.add_cog(TradeCommands(bot, bot.trade_analyzer))