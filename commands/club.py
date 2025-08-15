import discord
from discord.ext import commands
from utils import create_embed, is_admin, format_currency, format_club_info, create_or_get_role
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ClubCommands:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.setup_commands()
    
    def setup_commands(self):
        """Setup all club management slash commands"""
        
        @self.bot.tree.command(name="create_club", description="⚽ Create a new football club with Discord role")
        @is_admin()
        async def create_club(interaction: discord.Interaction, name: str, budget: float, image: Optional[discord.Attachment] = None):
            """Create a new club"""
            try:
                # Check if club already exists
                existing_club = self.db.get_club_by_name(name, interaction.guild_id)
                if existing_club:
                    await interaction.response.send_message("❌ Club already exists!", ephemeral=True)
                    return
                
                # Create Discord role for the club
                if interaction.guild:
                    role = await create_or_get_role(interaction.guild, name, discord.Color.blue())
                    role_id = role.id if role else None
                else:
                    role = None
                    role_id = None
                
                # Create club in database
                club_id = self.db.create_club(name, budget, interaction.guild_id, role_id)
                
                embed = create_embed(
                    title="⚽ Club Created!",
                    description=f"**{name}** has been established!",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="💰 Initial Budget", value=format_currency(budget), inline=True)
                if role:
                    embed.add_field(name="👑 Discord Role", value=role.mention, inline=True)
                embed.add_field(name="🆔 Club ID", value=str(club_id), inline=True)
                
                if image:
                    embed.set_image(url=image.url)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Create club command error: {e}")
                await interaction.response.send_message("❌ Error creating club.", ephemeral=True)

        @self.bot.tree.command(name="delete_club", description="🗑️ Delete a club and its Discord role")
        @is_admin()
        async def delete_club(interaction: discord.Interaction, name: str):
            """Delete a club"""
            try:
                club = self.db.get_club_by_name(name, interaction.guild_id)
                if not club:
                    await interaction.response.send_message("❌ Club not found!", ephemeral=True)
                    return
                
                # Get role before deletion
                role = None
                if club['role_id']:
                    role = interaction.guild.get_role(club['role_id'])
                
                # Delete from database
                success = self.db.delete_club(club['id'])
                
                if success:
                    # Delete Discord role
                    if role:
                        try:
                            await role.delete(reason="Club deleted by admin")
                        except discord.HTTPException as e:
                            logger.error(f"Failed to delete role: {e}")
                    
                    embed = create_embed(
                        title="🗑️ Club Deleted",
                        description=f"**{name}** has been dissolved.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("❌ Error deleting club.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"Delete club command error: {e}")
                await interaction.response.send_message("❌ Error deleting club.", ephemeral=True)

        @self.bot.tree.command(name="list_clubs", description="📋 List all clubs with their information")
        async def list_clubs(interaction: discord.Interaction):
            """List all clubs"""
            try:
                clubs = self.db.get_all_clubs(interaction.guild_id)
                
                if not clubs:
                    await interaction.response.send_message("📋 No clubs found. Create one with `/create_club`!", ephemeral=True)
                    return
                
                embed = create_embed(
                    title="⚽ Football Clubs",
                    description=f"Total clubs: {len(clubs)}",
                    color=discord.Color.blue()
                )
                
                for club in clubs[:10]:  # Limit to 10 clubs to avoid embed limits
                    stats = self.db.get_club_stats(club['id'])
                    role_mention = ""
                    if club['role_id']:
                        role = interaction.guild.get_role(club['role_id'])
                        role_mention = f" {role.mention}" if role else ""
                    
                    value = f"{format_currency(club['budget'])}\n"
                    if stats:
                        value += f"Players: {stats['player_count']} | Squad Value: {format_currency(stats['total_value'])}"
                    
                    embed.add_field(
                        name=f"⚽ {club['name']}{role_mention}",
                        value=value,
                        inline=True
                    )
                
                if len(clubs) > 10:
                    embed.set_footer(text=f"Showing first 10 of {len(clubs)} clubs")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"List clubs command error: {e}")
                await interaction.response.send_message("❌ Error listing clubs.", ephemeral=True)

        @self.bot.tree.command(name="club_info", description="ℹ️ Get detailed information about a specific club")
        async def club_info(interaction: discord.Interaction, name: str, image: discord.Attachment = None):
            """Get detailed club information"""
            try:
                club = self.db.get_club_by_name(name, interaction.guild_id)
                if not club:
                    await interaction.response.send_message("❌ Club not found!", ephemeral=True)
                    return
                
                stats = self.db.get_club_stats(club['id'])
                players = self.db.get_players_by_club(club['id'])
                
                embed = create_embed(
                    title=f"ℹ️ {club['name']} - Club Information",
                    color=discord.Color.blue()
                )
                
                # Basic info
                embed.add_field(name="💰 Budget", value=format_currency(club['budget']), inline=True)
                embed.add_field(name="👥 Players", value=str(stats['player_count']) if stats else "0", inline=True)
                embed.add_field(name="💎 Squad Value", value=format_currency(stats['total_value']) if stats else "€0.00", inline=True)
                
                # Role info
                if club['role_id']:
                    role = interaction.guild.get_role(club['role_id'])
                    if role:
                        embed.add_field(name="👑 Discord Role", value=role.mention, inline=True)
                        embed.add_field(name="👤 Role Members", value=str(len(role.members)), inline=True)
                
                # Transfer activity
                if stats:
                    embed.add_field(name="📈 Transfers In", value=str(stats['transfers_in']), inline=True)
                    embed.add_field(name="📉 Transfers Out", value=str(stats['transfers_out']), inline=True)
                
                # Top players
                if players:
                    top_players = sorted(players, key=lambda x: x['value'], reverse=True)[:3]
                    players_text = "\n".join([f"• {p['name']} ({format_currency(p['value'])})" for p in top_players])
                    embed.add_field(name="⭐ Top Players", value=players_text, inline=False)
                
                if image:
                    embed.set_image(url=image.url)
                
                embed.set_footer(text=f"Club ID: {club['id']} | Created: {club['created_at']}")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Club info command error: {e}")
                await interaction.response.send_message("❌ Error getting club information.", ephemeral=True)

        @self.bot.tree.command(name="update_budget", description="💰 Update a club's budget")
        @is_admin()
        async def update_budget(interaction: discord.Interaction, name: str, amount: float):
            """Update club budget"""
            try:
                club = self.db.get_club_by_name(name, interaction.guild_id)
                if not club:
                    await interaction.response.send_message("❌ Club not found!", ephemeral=True)
                    return
                
                old_budget = club['budget']
                success = self.db.update_club_budget(club['id'], amount)
                
                if success:
                    difference = amount - old_budget
                    embed = create_embed(
                        title="💰 Budget Updated",
                        description=f"**{name}** budget updated!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Previous", value=format_currency(old_budget), inline=True)
                    embed.add_field(name="New", value=format_currency(amount), inline=True)
                    embed.add_field(name="Change", value=f"{'+' if difference >= 0 else ''}{format_currency(difference)}", inline=True)
                    
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("❌ Error updating budget.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"Update budget command error: {e}")
                await interaction.response.send_message("❌ Error updating budget.", ephemeral=True)

        @self.bot.tree.command(name="rename_club", description="✏️ Rename a club and update its Discord role")
        @is_admin()
        async def rename_club(interaction: discord.Interaction, old_name: str, new_name: str):
            """Rename a club"""
            try:
                club = self.db.get_club_by_name(old_name, interaction.guild_id)
                if not club:
                    await interaction.response.send_message("❌ Club not found!", ephemeral=True)
                    return
                
                # Check if new name already exists
                existing = self.db.get_club_by_name(new_name, interaction.guild_id)
                if existing:
                    await interaction.response.send_message("❌ A club with that name already exists!", ephemeral=True)
                    return
                
                # Update database
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE clubs SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                        (new_name, club['id'])
                    )
                
                # Update Discord role name
                if club['role_id']:
                    role = interaction.guild.get_role(club['role_id'])
                    if role:
                        try:
                            await role.edit(name=new_name, reason=f"Club renamed from {old_name}")
                        except discord.HTTPException as e:
                            logger.error(f"Failed to rename role: {e}")
                
                embed = create_embed(
                    title="✏️ Club Renamed",
                    description=f"**{old_name}** → **{new_name}**",
                    color=discord.Color.green()
                )
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Rename club command error: {e}")
                await interaction.response.send_message("❌ Error renaming club.", ephemeral=True)

        @self.bot.tree.command(name="compare_clubs", description="⚖️ Compare two clubs side by side")
        async def compare_clubs(interaction: discord.Interaction, club1: str, club2: str):
            """Compare two clubs"""
            try:
                c1 = self.db.get_club_by_name(club1, interaction.guild_id)
                c2 = self.db.get_club_by_name(club2, interaction.guild_id)
                
                if not c1 or not c2:
                    await interaction.response.send_message("❌ One or both clubs not found!", ephemeral=True)
                    return
                
                stats1 = self.db.get_club_stats(c1['id'])
                stats2 = self.db.get_club_stats(c2['id'])
                
                embed = create_embed(
                    title="⚖️ Club Comparison",
                    description=f"**{club1}** vs **{club2}**",
                    color=discord.Color.purple()
                )
                
                # Budget comparison
                embed.add_field(
                    name="💰 Budget",
                    value=f"{format_currency(c1['budget'])}\nvs\n{format_currency(c2['budget'])}",
                    inline=True
                )
                
                # Player count
                embed.add_field(
                    name="👥 Players",
                    value=f"{stats1['player_count'] if stats1 else 0}\nvs\n{stats2['player_count'] if stats2 else 0}",
                    inline=True
                )
                
                # Squad value
                embed.add_field(
                    name="💎 Squad Value",
                    value=f"{format_currency(stats1['total_value']) if stats1 else '€0.00'}\nvs\n{format_currency(stats2['total_value']) if stats2 else '€0.00'}",
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Compare clubs command error: {e}")
                await interaction.response.send_message("❌ Error comparing clubs.", ephemeral=True)
