import os
import asyncio
import logging
import threading
from bot import FootballBot
from web_server import create_app

# Configure logging with rate limiting protection
logging.basicConfig(
    level=logging.WARNING,  # Reduced to WARNING to avoid spam
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

# Start bot in background when app starts
bot_started = False
bot_thread = None

def start_bot_background():
    """Start bot in background thread"""
    global bot_started, bot_thread
    if not bot_started:
        bot_started = True
        bot_thread = threading.Thread(target=run_bot_sync, daemon=True)
        bot_thread.start()
        logger.info("Bot started in background thread")

async def run_bot():
    """Run the Discord bot with enhanced rate limiting protection"""
    try:
        bot = FootballBot()
        logger.info("Starting Discord bot...")
        
        # Get bot token from environment variable
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN environment variable not found!")
            return
            
        await bot.start(token)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        # Extended wait time to avoid rate limits
        await asyncio.sleep(300)  # Wait 5 minutes before retrying

def run_bot_sync():
    """Synchronous wrapper for bot"""
    asyncio.run(run_bot())

# Create Flask app for gunicorn
app = create_app()

# Start bot when app is created
start_bot_background()

def run_web_server():
    """Run the Flask web server in a separate thread"""
    try:
        logger.info("Web server started on port 5000")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Web server error: {e}")

def main():
    """Main function to start both web server and bot"""
    # Start web server in a separate thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Start bot with enhanced error handling and rate limit protection
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            logger.info("Bot shutting down...")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Unexpected error (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                wait_time = 300 * retry_count  # Exponential backoff: 5, 10, 15 minutes
                logger.info(f"Restarting bot in {wait_time} seconds...")
                asyncio.run(asyncio.sleep(wait_time))
            else:
                logger.error("Max retries reached. Bot will stop to avoid rate limits.")
                break

if __name__ == "__main__":
    main()
