import discord
from discord.ext import commands, tasks
import logging
import asyncio
from datetime import datetime, timedelta
import os
from database import Database
from utils import create_embed, is_admin, RateLimitHandler

# Import command modules
from commands.admin import AdminCommands
from commands.club import ClubCommands
from commands.player import PlayerCommands
from commands.match import MatchCommands
from commands.stats import StatsCommands

logger = logging.getLogger(__name__)

class FootballBot(commands.Bot):
    def __init__(self):
        # Configure bot intents with enhanced rate limiting protection
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        self.db = Database()
        self.rate_limiter = RateLimitHandler()
        
        # Initialize command modules
        self.admin_commands = AdminCommands(self)
        self.club_commands = ClubCommands(self)
        self.player_commands = PlayerCommands(self)
        self.match_commands = MatchCommands(self)
        self.stats_commands = StatsCommands(self)
        
    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        try:
            # Initialize database
            self.db.initialize()
            logger.info("Database initialized")
            
            # Start background tasks
            self.match_reminder_task.start()
            
            # Sync slash commands
            await self.tree.sync()
            logger.info("Slash commands synced")
            
        except Exception as e:
            logger.error(f"Setup error: {e}")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Football Clubs ⚽"
        )
        await self.change_presence(activity=activity)

    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined guild: {guild.name} ({guild.id})")

    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("❌ You don't have permission to use this command!", ephemeral=True)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(f"⏰ Command is on cooldown. Try again in {error.retry_after:.2f} seconds", ephemeral=True)
        else:
            logger.error(f"Command error: {error}")
            await ctx.respond("❌ An error occurred while processing the command.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def match_reminder_task(self):
        """Background task to send match reminders"""
        try:
            upcoming_matches = self.db.get_upcoming_matches(minutes=5)
            
            for match in upcoming_matches:
                guild = self.get_guild(match['guild_id'])
                if not guild:
                    continue
                    
                # Get team roles
                team1_role = guild.get_role(match['team1_role_id'])
                team2_role = guild.get_role(match['team2_role_id'])
                
                if team1_role and team2_role:
                    # Send reminder to a designated channel or DM
                    embed = create_embed(
                        title="⚽ Match Reminder",
                        description=f"Match starting in 5 minutes!\n{team1_role.mention} vs {team2_role.mention}",
                        color=discord.Color.yellow()
                    )
                    
                    # Try to find a general channel to send reminder
                    channel = discord.utils.get(guild.text_channels, name='general') or guild.text_channels[0]
                    if channel:
                        try:
                            await self.rate_limiter.execute(channel.send, embed=embed)
                        except Exception as e:
                            logger.error(f"Failed to send match reminder: {e}")
                            
        except Exception as e:
            logger.error(f"Match reminder task error: {e}")

    @match_reminder_task.before_loop
    async def before_match_reminder_task(self):
        """Wait for bot to be ready before starting the task"""
        await self.wait_until_ready()

    async def close(self):
        """Cleanup when bot is closing"""
        logger.info("Bot shutting down...")
        if hasattr(self, 'match_reminder_task'):
            self.match_reminder_task.cancel()
        await super().close()
