import os
from flask import Flask, render_template
import logging

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask app"""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "football-bot-secret-key")
    
    @app.route('/')
    def index():
        """Main page showing bot status"""
        return render_template('index.html')
    
    @app.route('/health')
    def health():
        """Health check endpoint for monitoring"""
        return {'status': 'Bot is running', 'timestamp': '2025-08-15'}
    
    @app.route('/keep-alive')
    def keep_alive():
        """Keep alive endpoint"""
        return "Bot is alive!"
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
