# src/utils/formatting.py

import discord

def format_movers_embed(risers: list, fallers: list) -> discord.Embed:
    """Creates a Discord embed for KTC movers."""
    embed = discord.Embed(
        title="📈 KTC Market Movers (30 Days)",
        color=0x00FF00, # Green color
        description="Here are the biggest risers and fallers in dynasty value."
    )
    
    risers_text = "\n".join([f"🔼 {r['name']} - {r['value']}" for r in risers]) if risers else "No risers."
    fallers_text = "\n".join([f"🔽 {f['name']} - {f['value']}" for f in fallers]) if fallers else "No fallers."

    embed.add_field(name="🔥 Top Risers", value=risers_text, inline=False)
    embed.add_field(name="❄️ Top Fallers", value=fallers_text, inline=False)
    
    embed.set_footer(text="Data from KeepTradeCut.com")
    return embed

def format_trade_summary_embed(trade_summary: dict, team_grades: dict) -> discord.Embed:
    """
    Creates an embed to display a trade summary and its grades.
    """
    embed = discord.Embed(
        title=f"🏈 Trade Analysis: {trade_summary['trade_id']}",
        color=discord.Color.blue()
    )

    for roster_id, details in trade_summary['teams'].items():
        grade_info = team_grades.get(roster_id, {})
        grade_text = f"Grade: **{grade_info.get('grade', 'N/A')}** (Net Value: {grade_info.get('net_value_change', 0.0):.2f})"
        
        field_value = ""
        if details['received_players']:
            field_value += f"**Received Players:** {', '.join(details['received_players'])}\n"
        if details['gave_players']:
            field_value += f"**Gave Players:** {', '.join(details['gave_players'])}\n"
        if details['received_picks']:
            field_value += f"**Received Picks:** {', '.join(details['received_picks'])}\n"
        if details['gave_picks']:
            field_value += f"**Gave Picks:** {', '.join(details['gave_picks'])}\n"
        
        field_value += f"\n*{grade_text}*"

        embed.add_field(name=details['name'], value=field_value, inline=False)
    
    embed.set_footer(text="Trade graded by Fantasy Football Fellowship Bot AI")
    return embed

# Add other formatting functions as needed (e.g., for standings)