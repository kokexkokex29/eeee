import os
import asyncio
import logging
import threading
from bot_manager import bot_manager
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

# Bot management is now handled by bot_manager.py

def run_bot_sync():
    """Synchronous wrapper for bot manager"""
    asyncio.run(bot_manager.start_bot())

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
    
    # Start bot manager
    try:
        asyncio.run(bot_manager.start_bot())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
        asyncio.run(bot_manager.stop_bot())

if __name__ == "__main__":
    main()
