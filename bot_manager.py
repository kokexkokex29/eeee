import asyncio
import logging
import os
from datetime import datetime, timedelta
from bot import FootballBot

logger = logging.getLogger(__name__)

class BotManager:
    """Manages Discord bot with enhanced rate limiting and error recovery"""
    
    def __init__(self):
        self.bot = None
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.base_delay = 60  # Start with 1 minute delay
        
    async def start_bot(self):
        """Start the bot with comprehensive error handling"""
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN not found in environment variables")
            return False
            
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                if self.bot:
                    await self.bot.close()
                    
                # Create new bot instance
                self.bot = FootballBot()
                
                # Calculate delay based on reconnect attempts (exponential backoff)
                delay = self.base_delay * (2 ** self.reconnect_attempts)
                
                if self.reconnect_attempts > 0:
                    logger.info(f"Attempting to reconnect (attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts}) after {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.info("Starting Discord bot...")
                    await asyncio.sleep(5)  # Initial delay
                
                await self.bot.start(token)
                
                # If we reach here, bot started successfully
                self.is_running = True
                self.reconnect_attempts = 0
                logger.info("Bot started successfully!")
                return True
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Bot startup error (attempt {self.reconnect_attempts + 1}): {error_msg}")
                
                # Handle rate limiting specifically
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    wait_time = 900 + (300 * self.reconnect_attempts)  # 15+ minutes
                    logger.warning(f"Rate limited! Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                elif "401" in error_msg:
                    logger.error("Invalid token! Please check your DISCORD_TOKEN")
                    return False
                
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    logger.error("Max reconnection attempts reached. Bot will not restart.")
                    return False
                    
        return False
    
    async def stop_bot(self):
        """Safely stop the bot"""
        if self.bot:
            logger.info("Stopping bot...")
            await self.bot.close()
            self.is_running = False
    
    def is_bot_running(self):
        """Check if bot is running"""
        return self.is_running and self.bot and not self.bot.is_closed()

# Global bot manager instance
bot_manager = BotManager()
