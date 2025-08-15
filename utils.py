import discord
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

def create_embed(title: str, description: str = "", color: discord.Color = discord.Color.blue(), 
                footer: Optional[str] = None, thumbnail: Optional[str] = None, image: Optional[str] = None):
    """Create a Discord embed with common formatting"""
    embed = discord.Embed(title=title, description=description, color=color)
    
    if footer:
        embed.set_footer(text=footer)
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
        
    if image:
        embed.set_image(url=image)
    
    embed.timestamp = datetime.utcnow()
    return embed

def is_admin():
    """Decorator to check if user has administrator permissions"""
    def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        member = interaction.guild.get_member(interaction.user.id)
        return member is not None and member.guild_permissions.administrator
    return discord.app_commands.check(predicate)

def format_currency(amount: float) -> str:
    """Format amount as Euro currency"""
    return f"€{amount:,.2f}"

def format_player_info(player: dict, club_name: Optional[str] = None) -> str:
    """Format player information"""
    info = f"**{player['name']}** ({player['position']})\n"
    info += f"Value: {format_currency(player['value'])}\n"
    info += f"Age: {player['age']}\n"
    if club_name:
        info += f"Club: {club_name}\n"
    return info

def format_club_info(club: dict, stats: Optional[dict] = None) -> str:
    """Format club information"""
    info = f"**{club['name']}**\n"
    info += f"Budget: {format_currency(club['budget'])}\n"
    if stats:
        info += f"Players: {stats['player_count']}\n"
        info += f"Squad Value: {format_currency(stats['total_value'])}\n"
    return info

class RateLimitHandler:
    """Handle Discord API rate limiting"""
    def __init__(self):
        self.last_request = {}
        self.min_delay = 1  # Minimum delay between requests in seconds
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with rate limiting"""
        func_name = func.__name__
        now = datetime.now()
        
        # Check if we need to wait
        if func_name in self.last_request:
            time_since_last = (now - self.last_request[func_name]).total_seconds()
            if time_since_last < self.min_delay:
                wait_time = self.min_delay - time_since_last
                await asyncio.sleep(wait_time)
        
        # Update last request time
        self.last_request[func_name] = datetime.now()
        
        # Execute the function with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    retry_after = float(e.response.headers.get('Retry-After', 1))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    if attempt == max_retries - 1:
                        raise
                else:
                    raise
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

async def create_or_get_role(guild: discord.Guild, role_name: str, color: discord.Color = discord.Color.blue()) -> Optional[discord.Role]:
    """Create a role or get existing one"""
    try:
        # Check if role already exists
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            return existing_role
        
        # Create new role
        role = await guild.create_role(
            name=role_name,
            color=color,
            reason=f"Created by Football Bot for club: {role_name}"
        )
        logger.info(f"Created role: {role_name} in {guild.name}")
        return role
        
    except discord.Forbidden:
        logger.error(f"No permission to create role in {guild.name}")
        return None
    except discord.HTTPException as e:
        logger.error(f"Failed to create role {role_name}: {e}")
        return None

async def assign_role_to_user(member: discord.Member, role: discord.Role) -> bool:
    """Assign a role to a user"""
    try:
        if role not in member.roles:
            await member.add_roles(role, reason="Assigned by Football Bot")
            logger.info(f"Assigned role {role.name} to {member.display_name}")
            return True
        return True
    except discord.Forbidden:
        logger.error(f"No permission to assign role to {member.display_name}")
        return False
    except discord.HTTPException as e:
        logger.error(f"Failed to assign role: {e}")
        return False

async def remove_role_from_user(member: discord.Member, role: discord.Role) -> bool:
    """Remove a role from a user"""
    try:
        if role in member.roles:
            await member.remove_roles(role, reason="Removed by Football Bot")
            logger.info(f"Removed role {role.name} from {member.display_name}")
            return True
        return True
    except discord.Forbidden:
        logger.error(f"No permission to remove role from {member.display_name}")
        return False
    except discord.HTTPException as e:
        logger.error(f"Failed to remove role: {e}")
        return False

def validate_euro_amount(amount_str: str) -> float:
    """Validate and convert Euro amount string to float"""
    try:
        # Remove € symbol and commas if present
        cleaned = amount_str.replace('€', '').replace(',', '')
        amount = float(cleaned)
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        return amount
    except ValueError:
        raise ValueError("Invalid amount format")

def parse_datetime(date_str: str, time_str: str) -> datetime:
    """Parse date and time strings into datetime object"""
    try:
        datetime_str = f"{date_str} {time_str}"
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError("Invalid date/time format. Use YYYY-MM-DD and HH:MM")
