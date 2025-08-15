import discord
from discord.ext import commands
from utils import create_embed, format_currency
import logging

logger = logging.getLogger(__name__)

class StatsCommands:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.setup_commands()
    
    def setup_commands(self):
        """Setup all statistics slash commands"""
        
        @self.bot.tree.command(name="top_players", description="⭐ Show top players by value")
        async def top_players(interaction: discord.Interaction, limit: int = 10, image: discord.Attachment = None):
            """Show top players by value"""
            try:
                if limit > 25:
                    limit = 25
                    
                players = self.db.get_top_players_by_value(interaction.guild_id, limit)
                
                if not players:
                    await interaction.response.send_message("⭐ No players found!", ephemeral=True)
                    return
                
                embed = create_embed(
                    title="⭐ Top Players by Value",
                    description=f"Top {len(players)} most valuable players",
                    color=discord.Color.gold()
                )
                
                for i, player in enumerate(players, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    club_name = player['club_name'] if player['club_name'] else "Free Agent"
                    
                    embed.add_field(
                        name=f"{medal} {player['name']}",
                        value=f"{format_currency(player['value'])}\n{player['position']} • {club_name}",
                        inline=True
                    )
                
                if image:
                    embed.set_image(url=image.url)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Top players command error: {e}")
                await interaction.response.send_message("❌ Error getting top players.", ephemeral=True)

        @self.bot.tree.command(name="richest_clubs", description="💰 Show richest clubs by budget")
        async def richest_clubs(interaction: discord.Interaction, limit: int = 10, image: discord.Attachment = None):
            """Show richest clubs"""
            try:
                if limit > 25:
                    limit = 25
                    
                clubs = self.db.get_richest_clubs(interaction.guild_id, limit)
                
                if not clubs:
                    await interaction.response.send_message("💰 No clubs found!", ephemeral=True)
                    return
                
                embed = create_embed(
                    title="💰 Richest Clubs",
                    description=f"Top {len(clubs)} wealthiest clubs",
                    color=discord.Color.gold()
                )
                
                for i, club in enumerate(clubs, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    
                    # Get additional stats
                    stats = self.db.get_club_stats(club['id'])
                    additional_info = ""
                    if stats:
                        additional_info = f"\nPlayers: {stats['player_count']} | Squad Value: {format_currency(stats['total_value'])}"
                    
                    embed.add_field(
                        name=f"{medal} {club['name']}",
                        value=f"{format_currency(club['budget'])}{additional_info}",
                        inline=True
                    )
                
                if image:
                    embed.set_image(url=image.url)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Richest clubs command error: {e}")
                await interaction.response.send_message("❌ Error getting richest clubs.", ephemeral=True)

        @self.bot.tree.command(name="league_overview", description="📊 Show complete league statistics")
        async def league_overview(interaction: discord.Interaction, image: discord.Attachment = None):
            """Show league overview"""
            try:
                clubs = self.db.get_all_clubs(interaction.guild_id)
                players = self.db.get_all_players(interaction.guild_id)
                matches = self.db.get_matches(interaction.guild_id)
                
                embed = create_embed(
                    title="📊 League Overview",
                    description=f"Complete statistics for {interaction.guild.name}",
                    color=discord.Color.blue()
                )
                
                # Basic stats
                embed.add_field(name="🏆 Total Clubs", value=str(len(clubs)), inline=True)
                embed.add_field(name="👥 Total Players", value=str(len(players)), inline=True)
                embed.add_field(name="⚽ Total Matches", value=str(len(matches)), inline=True)
                
                # Financial overview
                total_budget = sum(club['budget'] for club in clubs)
                total_player_value = sum(player['value'] for player in players)
                average_budget = total_budget / len(clubs) if clubs else 0
                average_player_value = total_player_value / len(players) if players else 0
                
                embed.add_field(name="💰 Total Club Budgets", value=format_currency(total_budget), inline=True)
                embed.add_field(name="💎 Total Player Values", value=format_currency(total_player_value), inline=True)
                embed.add_field(name="📈 League Market Value", value=format_currency(total_budget + total_player_value), inline=True)
                
                embed.add_field(name="📊 Average Club Budget", value=format_currency(average_budget), inline=True)
                embed.add_field(name="📊 Average Player Value", value=format_currency(average_player_value), inline=True)
                
                # Most active positions
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        '''SELECT position, COUNT(*) as count FROM players 
                           WHERE guild_id = ? GROUP BY position ORDER BY count DESC LIMIT 3''',
                        (interaction.guild_id,)
                    )
                    positions = cursor.fetchall()
                
                if positions:
                    position_text = "\n".join([f"{pos['position']}: {pos['count']}" for pos in positions])
                    embed.add_field(name="⚽ Most Common Positions", value=position_text, inline=True)
                
                if image:
                    embed.set_image(url=image.url)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"League overview command error: {e}")
                await interaction.response.send_message("❌ Error getting league overview.", ephemeral=True)

        @self.bot.tree.command(name="transfer_activity", description="🔄 Show recent transfer activity")
        async def transfer_activity(interaction: discord.Interaction, limit: int = 10):
            """Show transfer activity"""
            try:
                if limit > 20:
                    limit = 20
                    
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        '''SELECT t.*, p.name as player_name, 
                                  cf.name as from_club, ct.name as to_club
                           FROM transfers t
                           JOIN players p ON t.player_id = p.id
                           LEFT JOIN clubs cf ON t.from_club_id = cf.id
                           LEFT JOIN clubs ct ON t.to_club_id = ct.id
                           WHERE t.guild_id = ?
                           ORDER BY t.transfer_date DESC LIMIT ?''',
                        (interaction.guild_id, limit)
                    )
                    transfers = cursor.fetchall()
                
                if not transfers:
                    await interaction.response.send_message("🔄 No transfer activity found!", ephemeral=True)
                    return
                
                embed = create_embed(
                    title="🔄 Recent Transfer Activity",
                    description=f"Last {len(transfers)} transfers",
                    color=discord.Color.purple()
                )
                
                for transfer in transfers:
                    from_club = transfer['from_club'] if transfer['from_club'] else "Free Agent"
                    to_club = transfer['to_club'] if transfer['to_club'] else "Released"
                    
                    transfer_date = transfer['transfer_date'][:10]  # Get date part only
                    
                    embed.add_field(
                        name=f"🔄 {transfer['player_name']}",
                        value=f"{from_club} → {to_club}\n{format_currency(transfer['transfer_fee'])} • {transfer_date}",
                        inline=True
                    )
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Transfer activity command error: {e}")
                await interaction.response.send_message("❌ Error getting transfer activity.", ephemeral=True)

        @self.bot.tree.command(name="club_rankings", description="🏆 Show club rankings by squad value")
        async def club_rankings(interaction: discord.Interaction, image: discord.Attachment = None):
            """Show club rankings by total squad value"""
            try:
                clubs = self.db.get_all_clubs(interaction.guild_id)
                
                if not clubs:
                    await interaction.response.send_message("🏆 No clubs found!", ephemeral=True)
                    return
                
                # Calculate total value for each club (budget + squad value)
                club_rankings = []
                for club in clubs:
                    stats = self.db.get_club_stats(club['id'])
                    total_value = club['budget']
                    if stats:
                        total_value += stats['total_value']
                    
                    club_rankings.append({
                        'name': club['name'],
                        'budget': club['budget'],
                        'squad_value': stats['total_value'] if stats else 0,
                        'total_value': total_value,
                        'players': stats['player_count'] if stats else 0,
                        'role_id': club['role_id']
                    })
                
                # Sort by total value
                club_rankings.sort(key=lambda x: x['total_value'], reverse=True)
                
                embed = create_embed(
                    title="🏆 Club Rankings",
                    description="Clubs ranked by total value (budget + squad value)",
                    color=discord.Color.gold()
                )
                
                for i, club in enumerate(club_rankings[:15], 1):  # Limit to 15
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    
                    role_mention = ""
                    if club['role_id']:
                        role = interaction.guild.get_role(club['role_id'])
                        if role:
                            role_mention = f" {role.mention}"
                    
                    value_text = f"Total: {format_currency(club['total_value'])}\n"
                    value_text += f"Budget: {format_currency(club['budget'])} | Squad: {format_currency(club['squad_value'])}"
                    
                    embed.add_field(
                        name=f"{medal} {club['name']}{role_mention}",
                        value=value_text,
                        inline=True
                    )
                
                if image:
                    embed.set_image(url=image.url)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Club rankings command error: {e}")
                await interaction.response.send_message("❌ Error getting club rankings.", ephemeral=True)

        @self.bot.tree.command(name="player_search", description="🔍 Search for players by various criteria")
        async def player_search(interaction: discord.Interaction, position: str = None, min_value: float = None, max_value: float = None, club: str = None):
            """Search for players with filters"""
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    query = '''SELECT p.*, c.name as club_name FROM players p
                              LEFT JOIN clubs c ON p.club_id = c.id
                              WHERE p.guild_id = ?'''
                    params = [interaction.guild_id]
                    
                    if position:
                        query += ' AND p.position LIKE ?'
                        params.append(f'%{position}%')
                    
                    if min_value is not None:
                        query += ' AND p.value >= ?'
                        params.append(min_value)
                    
                    if max_value is not None:
                        query += ' AND p.value <= ?'
                        params.append(max_value)
                    
                    if club:
                        query += ' AND c.name LIKE ?'
                        params.append(f'%{club}%')
                    
                    query += ' ORDER BY p.value DESC LIMIT 15'
                    
                    cursor.execute(query, params)
                    players = cursor.fetchall()
                
                if not players:
                    await interaction.response.send_message("🔍 No players found matching your criteria!", ephemeral=True)
                    return
                
                # Build search criteria description
                criteria = []
                if position:
                    criteria.append(f"Position: {position}")
                if min_value is not None:
                    criteria.append(f"Min Value: {format_currency(min_value)}")
                if max_value is not None:
                    criteria.append(f"Max Value: {format_currency(max_value)}")
                if club:
                    criteria.append(f"Club: {club}")
                
                search_desc = " | ".join(criteria) if criteria else "All players"
                
                embed = create_embed(
                    title="🔍 Player Search Results",
                    description=f"{search_desc}\nFound {len(players)} player(s)",
                    color=discord.Color.blue()
                )
                
                for player in players:
                    club_name = player['club_name'] if player['club_name'] else "Free Agent"
                    value_text = f"{format_currency(player['value'])}\n{player['position']} • Age {player['age']} • {club_name}"
                    
                    embed.add_field(
                        name=f"👤 {player['name']}",
                        value=value_text,
                        inline=True
                    )
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Player search command error: {e}")
                await interaction.response.send_message("❌ Error searching players.", ephemeral=True)

        @self.bot.tree.command(name="age_analysis", description="📈 Analyze player ages across the league")
        async def age_analysis(interaction: discord.Interaction):
            """Show age analysis of players"""
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Age statistics
                    cursor.execute(
                        '''SELECT AVG(age) as avg_age, MIN(age) as min_age, MAX(age) as max_age,
                                  COUNT(*) as total_players FROM players WHERE guild_id = ?''',
                        (interaction.guild_id,)
                    )
                    stats = cursor.fetchone()
                    
                    # Age distribution
                    cursor.execute(
                        '''SELECT 
                           CASE 
                               WHEN age < 20 THEN 'Under 20'
                               WHEN age < 25 THEN '20-24'
                               WHEN age < 30 THEN '25-29'
                               WHEN age < 35 THEN '30-34'
                               ELSE '35+'
                           END as age_group,
                           COUNT(*) as count
                           FROM players WHERE guild_id = ?
                           GROUP BY age_group ORDER BY 
                           CASE 
                               WHEN age < 20 THEN 1
                               WHEN age < 25 THEN 2
                               WHEN age < 30 THEN 3
                               WHEN age < 35 THEN 4
                               ELSE 5
                           END''',
                        (interaction.guild_id,)
                    )
                    age_groups = cursor.fetchall()
                
                if not stats or stats['total_players'] == 0:
                    await interaction.response.send_message("📈 No players found for age analysis!", ephemeral=True)
                    return
                
                embed = create_embed(
                    title="📈 League Age Analysis",
                    description=f"Analysis of {stats['total_players']} players",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="📊 Average Age", value=f"{stats['avg_age']:.1f} years", inline=True)
                embed.add_field(name="👶 Youngest", value=f"{stats['min_age']} years", inline=True)
                embed.add_field(name="👴 Oldest", value=f"{stats['max_age']} years", inline=True)
                
                # Age distribution
                if age_groups:
                    distribution_text = "\n".join([f"{group['age_group']}: {group['count']} players" for group in age_groups])
                    embed.add_field(name="📊 Age Distribution", value=distribution_text, inline=False)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Age analysis command error: {e}")
                await interaction.response.send_message("❌ Error performing age analysis.", ephemeral=True)
