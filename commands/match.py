import discord
from discord.ext import commands
from utils import create_embed, is_admin, parse_datetime
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MatchCommands:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.setup_commands()
    
    def setup_commands(self):
        """Setup all match management slash commands"""
        
        @self.bot.tree.command(name="create_match", description="⚽ Schedule a match between two clubs")
        @is_admin()
        async def create_match(interaction: discord.Interaction, team1: str, team2: str, date: str, time: str, year: int, month: int):
            """Create a new match"""
            try:
                # Get clubs
                team1_obj = self.db.get_club_by_name(team1, interaction.guild_id)
                team2_obj = self.db.get_club_by_name(team2, interaction.guild_id)
                
                if not team1_obj or not team2_obj:
                    await interaction.response.send_message("❌ One or both clubs not found!", ephemeral=True)
                    return
                
                if team1_obj['id'] == team2_obj['id']:
                    await interaction.response.send_message("❌ A club cannot play against itself!", ephemeral=True)
                    return
                
                # Parse datetime
                try:
                    full_date = f"{year}-{month:02d}-{date}"
                    match_datetime = parse_datetime(full_date, time)
                except ValueError as e:
                    await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
                    return
                
                # Check if match is in the future
                if match_datetime <= datetime.now():
                    await interaction.response.send_message("❌ Match must be scheduled for the future!", ephemeral=True)
                    return
                
                # Get role IDs
                team1_role_id = team1_obj['role_id']
                team2_role_id = team2_obj['role_id']
                
                # Create match
                match_id = self.db.create_match(
                    team1_obj['id'], team2_obj['id'], match_datetime,
                    interaction.guild_id, interaction.user.id,
                    team1_role_id, team2_role_id
                )
                
                # Send confirmation
                embed = create_embed(
                    title="⚽ Match Scheduled!",
                    description=f"**{team1}** vs **{team2}**",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="📅 Date", value=match_datetime.strftime("%B %d, %Y"), inline=True)
                embed.add_field(name="⏰ Time", value=match_datetime.strftime("%H:%M"), inline=True)
                embed.add_field(name="🆔 Match ID", value=str(match_id), inline=True)
                
                # Add role mentions
                role_mentions = ""
                if team1_role_id:
                    role1 = interaction.guild.get_role(team1_role_id)
                    if role1:
                        role_mentions += f"Team 1: {role1.mention}\n"
                
                if team2_role_id:
                    role2 = interaction.guild.get_role(team2_role_id)
                    if role2:
                        role_mentions += f"Team 2: {role2.mention}"
                
                if role_mentions:
                    embed.add_field(name="👑 Team Roles", value=role_mentions, inline=False)
                
                embed.add_field(name="⏰ Reminder", value="5 minutes before kickoff", inline=False)
                
                await interaction.response.send_message(embed=embed)
                
                # Send DMs to role members
                await self.send_match_notifications(interaction.guild, team1_obj, team2_obj, match_datetime, "scheduled")
                
            except Exception as e:
                logger.error(f"Create match command error: {e}")
                await interaction.response.send_message("❌ Error creating match.", ephemeral=True)

        @self.bot.tree.command(name="list_matches", description="📋 List upcoming and recent matches")
        async def list_matches(interaction: discord.Interaction, upcoming_only: bool = True):
            """List matches"""
            try:
                matches = self.db.get_matches(interaction.guild_id)
                
                if upcoming_only:
                    now = datetime.now()
                    matches = [m for m in matches if datetime.fromisoformat(m['match_date']) > now]
                    title = "⚽ Upcoming Matches"
                else:
                    title = "📋 All Matches"
                
                if not matches:
                    message = "No upcoming matches!" if upcoming_only else "No matches found!"
                    await interaction.response.send_message(f"📋 {message}", ephemeral=True)
                    return
                
                embed = create_embed(
                    title=title,
                    description=f"Total matches: {len(matches)}",
                    color=discord.Color.blue()
                )
                
                for match in matches[:10]:  # Limit to 10 matches
                    match_date = datetime.fromisoformat(match['match_date'])
                    status = "🔴 Past" if match_date < datetime.now() else "🟢 Upcoming"
                    
                    embed.add_field(
                        name=f"⚽ {match['team1_name']} vs {match['team2_name']}",
                        value=f"{status}\n📅 {match_date.strftime('%B %d, %Y')}\n⏰ {match_date.strftime('%H:%M')}",
                        inline=True
                    )
                
                if len(matches) > 10:
                    embed.set_footer(text=f"Showing first 10 of {len(matches)} matches")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"List matches command error: {e}")
                await interaction.response.send_message("❌ Error listing matches.", ephemeral=True)

        @self.bot.tree.command(name="cancel_match", description="❌ Cancel a scheduled match")
        @is_admin()
        async def cancel_match(interaction: discord.Interaction, team1: str, team2: str):
            """Cancel a match"""
            try:
                # Find the match
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        '''SELECT m.*, c1.name as team1_name, c2.name as team2_name 
                           FROM matches m
                           JOIN clubs c1 ON m.team1_id = c1.id
                           JOIN clubs c2 ON m.team2_id = c2.id
                           WHERE m.guild_id = ? AND 
                                 ((c1.name = ? AND c2.name = ?) OR (c1.name = ? AND c2.name = ?))
                                 AND m.match_date > datetime('now')
                           ORDER BY m.match_date ASC LIMIT 1''',
                        (interaction.guild_id, team1, team2, team2, team1)
                    )
                    match = cursor.fetchone()
                
                if not match:
                    await interaction.response.send_message("❌ No upcoming match found between these teams!", ephemeral=True)
                    return
                
                # Delete the match
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM matches WHERE id = ?', (match['id'],))
                
                embed = create_embed(
                    title="❌ Match Cancelled",
                    description=f"**{match['team1_name']}** vs **{match['team2_name']}**",
                    color=discord.Color.red()
                )
                
                match_date = datetime.fromisoformat(match['match_date'])
                embed.add_field(name="📅 Was Scheduled For", value=match_date.strftime("%B %d, %Y at %H:%M"), inline=False)
                
                # Notify team roles
                role_mentions = ""
                if match['team1_role_id']:
                    role1 = interaction.guild.get_role(match['team1_role_id'])
                    if role1:
                        role_mentions += f"{role1.mention} "
                
                if match['team2_role_id']:
                    role2 = interaction.guild.get_role(match['team2_role_id'])
                    if role2:
                        role_mentions += f"{role2.mention}"
                
                if role_mentions:
                    embed.add_field(name="📢 Notification Sent To", value=role_mentions, inline=False)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Cancel match command error: {e}")
                await interaction.response.send_message("❌ Error cancelling match.", ephemeral=True)

        @self.bot.tree.command(name="match_reminder", description="📢 Send manual reminder for upcoming matches")
        @is_admin()
        async def match_reminder(interaction: discord.Interaction, hours: int = 1):
            """Send manual match reminders"""
            try:
                # Get upcoming matches within the specified hours
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    reminder_time = datetime.now() + timedelta(hours=hours)
                    
                    cursor.execute(
                        '''SELECT m.*, c1.name as team1_name, c2.name as team2_name 
                           FROM matches m
                           JOIN clubs c1 ON m.team1_id = c1.id
                           JOIN clubs c2 ON m.team2_id = c2.id
                           WHERE m.guild_id = ? AND m.match_date <= ? AND m.match_date > datetime('now')
                           ORDER BY m.match_date ASC''',
                        (interaction.guild_id, reminder_time.strftime('%Y-%m-%d %H:%M:%S'))
                    )
                    matches = cursor.fetchall()
                
                if not matches:
                    await interaction.response.send_message(f"📢 No matches found in the next {hours} hour(s)!", ephemeral=True)
                    return
                
                sent_count = 0
                for match in matches:
                    match_date = datetime.fromisoformat(match['match_date'])
                    time_until = match_date - datetime.now()
                    
                    embed = create_embed(
                        title="📢 Match Reminder",
                        description=f"**{match['team1_name']}** vs **{match['team2_name']}**",
                        color=discord.Color.yellow()
                    )
                    
                    embed.add_field(name="📅 Date", value=match_date.strftime("%B %d, %Y"), inline=True)
                    embed.add_field(name="⏰ Time", value=match_date.strftime("%H:%M"), inline=True)
                    embed.add_field(name="⏳ Time Until", value=f"{int(time_until.total_seconds() // 3600)}h {int((time_until.total_seconds() % 3600) // 60)}m", inline=True)
                    
                    # Send to channel with role mentions
                    role_mentions = ""
                    if match['team1_role_id']:
                        role1 = interaction.guild.get_role(match['team1_role_id'])
                        if role1:
                            role_mentions += f"{role1.mention} "
                    
                    if match['team2_role_id']:
                        role2 = interaction.guild.get_role(match['team2_role_id'])
                        if role2:
                            role_mentions += f"{role2.mention}"
                    
                    # Try to find a general channel
                    channel = discord.utils.get(interaction.guild.text_channels, name='general')
                    if not channel:
                        channel = interaction.guild.text_channels[0] if interaction.guild.text_channels else None
                    
                    if channel:
                        try:
                            content = f"📢 Match Reminder! {role_mentions}".strip()
                            await self.bot.rate_limiter.execute(channel.send, content=content, embed=embed)
                            sent_count += 1
                        except Exception as e:
                            logger.error(f"Failed to send match reminder: {e}")
                
                embed = create_embed(
                    title="📢 Reminders Sent",
                    description=f"Sent {sent_count} match reminder(s) for matches in the next {hours} hour(s)",
                    color=discord.Color.green()
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Match reminder command error: {e}")
                await interaction.response.send_message("❌ Error sending match reminders.", ephemeral=True)

    async def send_match_notifications(self, guild, team1_obj, team2_obj, match_datetime, notification_type):
        """Send match notifications to team members via DM"""
        try:
            message_title = "⚽ Match Scheduled!" if notification_type == "scheduled" else "📢 Match Reminder!"
            
            # Create notification embed
            embed = create_embed(
                title=message_title,
                description=f"**{team1_obj['name']}** vs **{team2_obj['name']}**",
                color=discord.Color.blue() if notification_type == "scheduled" else discord.Color.yellow()
            )
            
            embed.add_field(name="📅 Date", value=match_datetime.strftime("%B %d, %Y"), inline=True)
            embed.add_field(name="⏰ Time", value=match_datetime.strftime("%H:%M"), inline=True)
            
            if notification_type == "reminder":
                time_until = match_datetime - datetime.now()
                embed.add_field(name="⏳ Starting In", value=f"{int(time_until.total_seconds() // 60)} minutes", inline=True)
            
            # Send to team 1 members
            if team1_obj['role_id']:
                role1 = guild.get_role(team1_obj['role_id'])
                if role1:
                    for member in role1.members:
                        try:
                            await member.send(embed=embed)
                        except discord.Forbidden:
                            # User has DMs disabled
                            pass
                        except Exception as e:
                            logger.error(f"Failed to send DM to {member}: {e}")
            
            # Send to team 2 members
            if team2_obj['role_id']:
                role2 = guild.get_role(team2_obj['role_id'])
                if role2:
                    for member in role2.members:
                        try:
                            await member.send(embed=embed)
                        except discord.Forbidden:
                            # User has DMs disabled
                            pass
                        except Exception as e:
                            logger.error(f"Failed to send DM to {member}: {e}")
                            
        except Exception as e:
            logger.error(f"Error sending match notifications: {e}")
