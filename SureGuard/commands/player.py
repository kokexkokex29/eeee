import discord
from discord.ext import commands
from utils import create_embed, is_admin, format_currency, format_player_info, assign_role_to_user, remove_role_from_user
import logging

logger = logging.getLogger(__name__)

class PlayerCommands:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.setup_commands()
    
    def setup_commands(self):
        """Setup all player management slash commands"""
        
        @self.bot.tree.command(name="add_player", description="👤 Add a new player to the system")
        @is_admin()
        async def add_player(interaction: discord.Interaction, name: str, value: float, position: str = "Unknown", age: int = 25, club: str = None, discord_user: discord.Member = None):
            """Add a new player"""
            try:
                # Check if player already exists
                existing_player = self.db.get_player_by_name(name, interaction.guild_id)
                if existing_player:
                    await interaction.response.send_message("❌ Player already exists!", ephemeral=True)
                    return
                
                club_id = None
                club_obj = None
                if club:
                    club_obj = self.db.get_club_by_name(club, interaction.guild_id)
                    if not club_obj:
                        await interaction.response.send_message("❌ Club not found!", ephemeral=True)
                        return
                    club_id = club_obj['id']
                
                # Create player
                discord_user_id = discord_user.id if discord_user else None
                player_id = self.db.create_player(name, value, interaction.guild_id, club_id, position, age, discord_user_id)
                
                # Assign Discord role if player has a club and Discord user
                if club_obj and discord_user and club_obj['role_id']:
                    role = interaction.guild.get_role(club_obj['role_id'])
                    if role:
                        await assign_role_to_user(discord_user, role)
                
                embed = create_embed(
                    title="👤 Player Added!",
                    description=f"**{name}** has joined the league!",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="💎 Value", value=format_currency(value), inline=True)
                embed.add_field(name="⚽ Position", value=position, inline=True)
                embed.add_field(name="🎂 Age", value=str(age), inline=True)
                
                if club_obj:
                    embed.add_field(name="🏆 Club", value=club_obj['name'], inline=True)
                
                if discord_user:
                    embed.add_field(name="👤 Discord User", value=discord_user.mention, inline=True)
                
                embed.add_field(name="🆔 Player ID", value=str(player_id), inline=True)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Add player command error: {e}")
                await interaction.response.send_message("❌ Error adding player.", ephemeral=True)

        @self.bot.tree.command(name="remove_player", description="🗑️ Remove a player from the system")
        @is_admin()
        async def remove_player(interaction: discord.Interaction, name: str):
            """Remove a player"""
            try:
                player = self.db.get_player_by_name(name, interaction.guild_id)
                if not player:
                    await interaction.response.send_message("❌ Player not found!", ephemeral=True)
                    return
                
                # Remove from Discord role if applicable
                if player['club_id'] and player['discord_user_id']:
                    club = self.db.get_club_by_name("", interaction.guild_id)  # Get by ID instead
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM clubs WHERE id = ?', (player['club_id'],))
                        club = cursor.fetchone()
                    
                    if club and club['role_id']:
                        role = interaction.guild.get_role(club['role_id'])
                        discord_user = interaction.guild.get_member(player['discord_user_id'])
                        if role and discord_user:
                            await remove_role_from_user(discord_user, role)
                
                success = self.db.delete_player(player['id'])
                
                if success:
                    embed = create_embed(
                        title="🗑️ Player Removed",
                        description=f"**{name}** has left the league.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("❌ Error removing player.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"Remove player command error: {e}")
                await interaction.response.send_message("❌ Error removing player.", ephemeral=True)

        @self.bot.tree.command(name="transfer_player", description="🔄 Transfer a player between clubs")
        @is_admin()
        async def transfer_player(interaction: discord.Interaction, player_name: str, to_club: str, transfer_fee: float):
            """Transfer a player between clubs"""
            try:
                player = self.db.get_player_by_name(player_name, interaction.guild_id)
                if not player:
                    await interaction.response.send_message("❌ Player not found!", ephemeral=True)
                    return
                
                to_club_obj = self.db.get_club_by_name(to_club, interaction.guild_id)
                if not to_club_obj:
                    await interaction.response.send_message("❌ Destination club not found!", ephemeral=True)
                    return
                
                # Get from club info
                from_club_obj = None
                if player['club_id']:
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM clubs WHERE id = ?', (player['club_id'],))
                        from_club_obj = cursor.fetchone()
                
                # Check if destination club has enough budget
                if to_club_obj['budget'] < transfer_fee:
                    await interaction.response.send_message("❌ Destination club doesn't have enough budget!", ephemeral=True)
                    return
                
                # Handle Discord roles
                discord_user = None
                if player['discord_user_id']:
                    discord_user = interaction.guild.get_member(player['discord_user_id'])
                
                if discord_user:
                    # Remove from old club role
                    if from_club_obj and from_club_obj['role_id']:
                        old_role = interaction.guild.get_role(from_club_obj['role_id'])
                        if old_role:
                            await remove_role_from_user(discord_user, old_role)
                    
                    # Add to new club role
                    if to_club_obj['role_id']:
                        new_role = interaction.guild.get_role(to_club_obj['role_id'])
                        if new_role:
                            await assign_role_to_user(discord_user, new_role)
                
                # Perform transfer
                success = self.db.transfer_player(player['id'], to_club_obj['id'], transfer_fee, interaction.guild_id)
                
                if success:
                    embed = create_embed(
                        title="🔄 Transfer Complete!",
                        description=f"**{player_name}** has been transferred!",
                        color=discord.Color.green()
                    )
                    
                    embed.add_field(
                        name="📍 From",
                        value=from_club_obj['name'] if from_club_obj else "Free Agent",
                        inline=True
                    )
                    embed.add_field(name="📍 To", value=to_club_obj['name'], inline=True)
                    embed.add_field(name="💰 Fee", value=format_currency(transfer_fee), inline=True)
                    
                    if discord_user:
                        embed.add_field(name="👤 Discord User", value=discord_user.mention, inline=False)
                    
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("❌ Error performing transfer.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"Transfer player command error: {e}")
                await interaction.response.send_message("❌ Error transferring player.", ephemeral=True)

        @self.bot.tree.command(name="update_player_value", description="💎 Update a player's market value")
        @is_admin()
        async def update_player_value(interaction: discord.Interaction, name: str, value: float):
            """Update player value"""
            try:
                player = self.db.get_player_by_name(name, interaction.guild_id)
                if not player:
                    await interaction.response.send_message("❌ Player not found!", ephemeral=True)
                    return
                
                old_value = player['value']
                success = self.db.update_player_value(player['id'], value)
                
                if success:
                    difference = value - old_value
                    embed = create_embed(
                        title="💎 Player Value Updated",
                        description=f"**{name}**'s value has been updated!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Previous", value=format_currency(old_value), inline=True)
                    embed.add_field(name="New", value=format_currency(value), inline=True)
                    embed.add_field(name="Change", value=f"{'+' if difference >= 0 else ''}{format_currency(difference)}", inline=True)
                    
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("❌ Error updating player value.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"Update player value command error: {e}")
                await interaction.response.send_message("❌ Error updating player value.", ephemeral=True)

        @self.bot.tree.command(name="player_info", description="ℹ️ Get detailed information about a player")
        async def player_info(interaction: discord.Interaction, name: str, image: discord.Attachment = None):
            """Get detailed player information"""
            try:
                player = self.db.get_player_by_name(name, interaction.guild_id)
                if not player:
                    await interaction.response.send_message("❌ Player not found!", ephemeral=True)
                    return
                
                embed = create_embed(
                    title=f"ℹ️ {player['name']} - Player Information",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="💎 Market Value", value=format_currency(player['value']), inline=True)
                embed.add_field(name="⚽ Position", value=player['position'], inline=True)
                embed.add_field(name="🎂 Age", value=str(player['age']), inline=True)
                
                # Club info
                if player['club_id']:
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM clubs WHERE id = ?', (player['club_id'],))
                        club = cursor.fetchone()
                    
                    if club:
                        embed.add_field(name="🏆 Current Club", value=club['name'], inline=True)
                        if club['role_id']:
                            role = interaction.guild.get_role(club['role_id'])
                            if role:
                                embed.add_field(name="👑 Club Role", value=role.mention, inline=True)
                else:
                    embed.add_field(name="🏆 Current Club", value="Free Agent", inline=True)
                
                # Discord user info
                if player['discord_user_id']:
                    discord_user = interaction.guild.get_member(player['discord_user_id'])
                    if discord_user:
                        embed.add_field(name="👤 Discord User", value=discord_user.mention, inline=True)
                
                # Contract info
                if player['contract_end']:
                    embed.add_field(name="📅 Contract End", value=player['contract_end'], inline=True)
                
                # Transfer history
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        '''SELECT COUNT(*) as transfer_count FROM transfers WHERE player_id = ?''',
                        (player['id'],)
                    )
                    transfer_count = cursor.fetchone()['transfer_count']
                
                embed.add_field(name="🔄 Career Transfers", value=str(transfer_count), inline=True)
                
                if image:
                    embed.set_image(url=image.url)
                
                embed.set_footer(text=f"Player ID: {player['id']} | Added: {player['created_at']}")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Player info command error: {e}")
                await interaction.response.send_message("❌ Error getting player information.", ephemeral=True)

        @self.bot.tree.command(name="list_players", description="📋 List all players or players from a specific club")
        async def list_players(interaction: discord.Interaction, club: str = None):
            """List players"""
            try:
                if club:
                    club_obj = self.db.get_club_by_name(club, interaction.guild_id)
                    if not club_obj:
                        await interaction.response.send_message("❌ Club not found!", ephemeral=True)
                        return
                    players = self.db.get_players_by_club(club_obj['id'])
                    title = f"⚽ {club} Squad"
                else:
                    players = self.db.get_all_players(interaction.guild_id)
                    title = "👥 All Players"
                
                if not players:
                    await interaction.response.send_message("📋 No players found!", ephemeral=True)
                    return
                
                embed = create_embed(
                    title=title,
                    description=f"Total players: {len(players)}",
                    color=discord.Color.blue()
                )
                
                for i, player in enumerate(players[:15]):  # Limit to 15 players
                    club_name = ""
                    if player['club_id'] and not club:
                        with self.db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT name FROM clubs WHERE id = ?', (player['club_id'],))
                            club_result = cursor.fetchone()
                            club_name = f" ({club_result['name']})" if club_result else ""
                    
                    value = f"{format_currency(player['value'])}\n{player['position']} • Age {player['age']}"
                    
                    embed.add_field(
                        name=f"👤 {player['name']}{club_name}",
                        value=value,
                        inline=True
                    )
                
                if len(players) > 15:
                    embed.set_footer(text=f"Showing first 15 of {len(players)} players")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"List players command error: {e}")
                await interaction.response.send_message("❌ Error listing players.", ephemeral=True)

        @self.bot.tree.command(name="free_agents", description="🆓 List all players without a club")
        async def free_agents(interaction: discord.Interaction):
            """List free agents"""
            try:
                all_players = self.db.get_all_players(interaction.guild_id)
                free_agents = [p for p in all_players if not p['club_id']]
                
                if not free_agents:
                    await interaction.response.send_message("🆓 No free agents available!", ephemeral=True)
                    return
                
                embed = create_embed(
                    title="🆓 Free Agents",
                    description=f"Players available for signing: {len(free_agents)}",
                    color=discord.Color.gold()
                )
                
                for player in free_agents[:10]:  # Limit to 10
                    value = f"{format_currency(player['value'])}\n{player['position']} • Age {player['age']}"
                    embed.add_field(
                        name=f"👤 {player['name']}",
                        value=value,
                        inline=True
                    )
                
                if len(free_agents) > 10:
                    embed.set_footer(text=f"Showing first 10 of {len(free_agents)} free agents")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Free agents command error: {e}")
                await interaction.response.send_message("❌ Error listing free agents.", ephemeral=True)
