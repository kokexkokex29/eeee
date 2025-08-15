import discord
from discord.ext import commands
from utils import create_embed, is_admin, format_currency
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class AdminCommands:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.setup_commands()
    
    def setup_commands(self):
        """Setup all admin slash commands"""
        
        @self.bot.tree.command(name="reset_all", description="🗑️ Reset ALL data (clubs, players, matches, transfers)")
        @is_admin()
        async def reset_all(interaction: discord.Interaction):
            """Reset all bot data for this guild"""
            try:
                # Create confirmation embed
                embed = create_embed(
                    title="⚠️ DANGER ZONE ⚠️",
                    description="This will **PERMANENTLY DELETE** all:\n• Clubs and their roles\n• Players\n• Matches\n• Transfer history\n\n**This action cannot be undone!**",
                    color=discord.Color.red()
                )
                
                class ConfirmView(discord.ui.View):
                    def __init__(self, db, guild):
                        super().__init__(timeout=30)
                        self.db = db
                        self.guild = guild
                    
                    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        embed = create_embed("✅ Reset Cancelled", "No data was deleted.", discord.Color.green())
                        await button_interaction.response.edit_message(embed=embed, view=None)
                    
                    @discord.ui.button(label="🗑️ CONFIRM RESET", style=discord.ButtonStyle.danger)
                    async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        # Delete all Discord roles created by the bot
                        deleted_roles = 0
                        clubs = self.db.get_all_clubs(self.guild.id)
                        
                        for club in clubs:
                            if club['role_id'] and self.guild:
                                role = self.guild.get_role(club['role_id'])
                                if role:
                                    try:
                                        await role.delete(reason="Bot reset - cleaning up roles")
                                        deleted_roles += 1
                                    except discord.HTTPException as e:
                                        logger.error(f"Failed to delete role {role.name}: {e}")
                        
                        # Reset database
                        self.db.reset_all_data(self.guild.id)
                        
                        embed = create_embed(
                            title="🗑️ Reset Complete",
                            description=f"All data has been reset!\n• Deleted {len(clubs)} clubs\n• Deleted {deleted_roles} Discord roles\n• Cleared all players, matches, and transfers",
                            color=discord.Color.green()
                        )
                        await button_interaction.response.edit_message(embed=embed, view=None)
                
                await interaction.response.send_message(embed=embed, view=ConfirmView(self.db, interaction.guild), ephemeral=True)
                
            except Exception as e:
                logger.error(f"Reset command error: {e}")
                await interaction.response.send_message("❌ Error during reset operation.", ephemeral=True)

        @self.bot.tree.command(name="backup_data", description="💾 Create a backup of all bot data")
        @is_admin()
        async def backup_data(interaction: discord.Interaction):
            """Create a backup of all guild data"""
            try:
                backup = self.db.backup_data(interaction.guild_id)
                
                # Create backup file
                filename = f"backup_{interaction.guild.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                # Convert to JSON string
                backup_json = json.dumps(backup, indent=2, default=str)
                
                # Create file and send
                with open(filename, 'w') as f:
                    f.write(backup_json)
                
                embed = create_embed(
                    title="💾 Backup Created",
                    description=f"Backup contains:\n• {len(backup['clubs'])} clubs\n• {len(backup['players'])} players\n• {len(backup['matches'])} matches\n• {len(backup['transfers'])} transfers",
                    color=discord.Color.green()
                )
                
                file = discord.File(filename, filename=filename)
                await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
                
                # Clean up file
                import os
                os.remove(filename)
                
            except Exception as e:
                logger.error(f"Backup command error: {e}")
                await interaction.response.send_message("❌ Error creating backup.", ephemeral=True)

        @self.bot.tree.command(name="system_info", description="ℹ️ Show bot system information and statistics")
        @is_admin()
        async def system_info(interaction: discord.Interaction):
            """Show system information"""
            try:
                clubs = self.db.get_all_clubs(interaction.guild_id)
                players = self.db.get_all_players(interaction.guild_id)
                matches = self.db.get_matches(interaction.guild_id)
                
                embed = create_embed(
                    title="🤖 Bot System Information",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="📊 Database Statistics",
                    value=f"Clubs: {len(clubs)}\nPlayers: {len(players)}\nMatches: {len(matches)}",
                    inline=True
                )
                
                # Calculate total values
                total_budget = sum(club['budget'] for club in clubs)
                total_player_value = sum(player['value'] for player in players)
                
                embed.add_field(
                    name="💰 Financial Overview",
                    value=f"Total Club Budgets: {format_currency(total_budget)}\nTotal Player Values: {format_currency(total_player_value)}",
                    inline=True
                )
                
                embed.add_field(
                    name="🛠️ Bot Status",
                    value=f"Guilds: {len(self.bot.guilds)}\nLatency: {round(self.bot.latency * 1000)}ms\nUptime: Since restart",
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"System info command error: {e}")
                await interaction.response.send_message("❌ Error retrieving system information.", ephemeral=True)

        @self.bot.tree.command(name="manage_roles", description="👑 Manage Discord roles for clubs")
        @is_admin()
        async def manage_roles(interaction: discord.Interaction, action: str, club_name: str = None, user: discord.Member = None):
            """Manage Discord roles for clubs"""
            try:
                if action.lower() == "sync":
                    # Sync all club roles
                    clubs = self.db.get_all_clubs(interaction.guild_id)
                    synced = 0
                    
                    for club in clubs:
                        if not club['role_id']:
                            from utils import create_or_get_role
                            role = await create_or_get_role(interaction.guild, club['name'])
                            if role:
                                # Update database with role ID
                                with self.db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        'UPDATE clubs SET role_id = ? WHERE id = ?',
                                        (role.id, club['id'])
                                    )
                                synced += 1
                    
                    embed = create_embed(
                        title="👑 Roles Synchronized",
                        description=f"Synced {synced} club roles",
                        color=discord.Color.green()
                    )
                    
                elif action.lower() == "assign" and club_name and user:
                    # Assign user to club role
                    club = self.db.get_club_by_name(club_name, interaction.guild_id)
                    if not club:
                        await interaction.response.send_message("❌ Club not found!", ephemeral=True)
                        return
                    
                    if club['role_id']:
                        role = interaction.guild.get_role(club['role_id'])
                        if role:
                            from utils import assign_role_to_user
                            success = await assign_role_to_user(user, role)
                            if success:
                                embed = create_embed(
                                    title="👑 Role Assigned",
                                    description=f"{user.mention} assigned to {club['name']} role",
                                    color=discord.Color.green()
                                )
                            else:
                                await interaction.response.send_message("❌ Failed to assign role!", ephemeral=True)
                                return
                        else:
                            await interaction.response.send_message("❌ Club role not found!", ephemeral=True)
                            return
                    else:
                        await interaction.response.send_message("❌ Club has no associated role!", ephemeral=True)
                        return
                
                else:
                    embed = create_embed(
                        title="❌ Invalid Action",
                        description="Available actions:\n• `sync` - Sync all club roles\n• `assign` - Assign user to club role (requires club_name and user)",
                        color=discord.Color.red()
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Manage roles command error: {e}")
                await interaction.response.send_message("❌ Error managing roles.", ephemeral=True)

        @self.bot.tree.command(name="set_budgets_bulk", description="💰 Set budgets for multiple clubs at once")
        @is_admin()
        async def set_budgets_bulk(interaction: discord.Interaction, amount: float):
            """Set the same budget for all clubs"""
            try:
                clubs = self.db.get_all_clubs(interaction.guild_id)
                updated = 0
                
                for club in clubs:
                    if self.db.update_club_budget(club['id'], amount):
                        updated += 1
                
                embed = create_embed(
                    title="💰 Bulk Budget Update",
                    description=f"Set budget to {format_currency(amount)} for {updated} clubs",
                    color=discord.Color.green()
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Bulk budget command error: {e}")
                await interaction.response.send_message("❌ Error updating budgets.", ephemeral=True)
