# ⚽ Football Club Discord Bot

A comprehensive Discord bot for managing football clubs with 20+ slash commands, Discord role integration, Euro-based budgets, player management, transfer systems, and match scheduling.

## ✨ Features

- **Club Management**: Create clubs with automatic Discord role creation
- **Player System**: Add players, manage positions, set market values
- **Transfer Market**: Transfer players between clubs with automatic role management
- **Match Scheduling**: Schedule matches with role-based notifications and reminders
- **Statistics**: Comprehensive stats, rankings, and analytics
- **Admin Controls**: Administrator-only access with backup and reset functionality

## 🚀 Setup Instructions

### 1. Discord Bot Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token
5. Under "OAuth2" → "URL Generator":
   - Select scopes: `bot` and `applications.commands`
   - Select permissions: `Manage Roles`, `Send Messages`, `Use Slash Commands`
6. Use the generated URL to invite the bot to your server

### 2. Running Locally (Replit)
1. Add your Discord bot token to Replit Secrets:
   ```
   DISCORD_TOKEN = your_bot_token_here
   ```
2. The bot will automatically start when you run the project

### 3. Deploy to Render
1. Connect your GitHub repository to Render
2. Choose "Web Service"
3. Use these settings:
   - **Build Command**: `pip install discord.py flask flask-sqlalchemy gunicorn pillow aiosqlite`
   - **Start Command**: `python main.py`
4. Add environment variable:
   - `DISCORD_TOKEN` = your_bot_token_here

## 🎮 Available Commands

### Club Management
- `/create_club` - Create a new football club with Discord role
- `/delete_club` - Delete a club and its role
- `/list_clubs` - List all clubs in the server
- `/update_budget` - Update a club's budget
- `/club_info` - Get detailed club information

### Player Management
- `/add_player` - Add a new player to a club
- `/transfer_player` - Transfer player between clubs
- `/list_players` - List players in a club
- `/player_info` - Get detailed player information
- `/free_agents` - List players without clubs

### Match System
- `/create_match` - Schedule a match between clubs
- `/list_matches` - List upcoming matches
- `/cancel_match` - Cancel a scheduled match
- `/match_reminder` - Send manual match reminder

### Statistics & Analytics
- `/club_stats` - Get club statistics
- `/player_stats` - Get player statistics
- `/top_clubs` - Show club rankings
- `/most_valuable_players` - Show top valued players
- `/transfer_history` - Show recent transfers

### Admin Commands
- `/admin_backup` - Backup all bot data
- `/admin_restore` - Restore bot data from backup
- `/admin_reset` - Reset all bot data (DANGEROUS!)
- `/admin_sync_roles` - Sync Discord roles with database

## 📊 Database Schema

The bot uses SQLite database with the following tables:
- **Clubs**: Store club information and Discord role IDs
- **Players**: Player data with club relationships
- **Matches**: Scheduled matches with notifications
- **Transfers**: Transfer history and audit trail

## 🛡️ Permissions Required

The bot requires these Discord permissions:
- **Manage Roles**: For automatic club role creation/management
- **Send Messages**: For sending notifications and responses
- **Use Slash Commands**: For command functionality

## 💰 Currency System

All financial transactions use Euro (€) currency with proper formatting and budget tracking.

## 🔧 Technical Details

- **Framework**: Discord.py with Flask web server
- **Database**: SQLite for data persistence
- **Threading**: Concurrent Discord bot and web server execution
- **Role Management**: Automatic Discord role synchronization
- **Error Handling**: Comprehensive error handling with user-friendly messages

## 📝 License

This project is open source and available under the MIT License.