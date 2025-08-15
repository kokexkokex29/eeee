# Overview

A comprehensive Discord bot designed for managing football clubs, players, transfers, and matches with complete Discord role integration. The system provides administrator controls for creating and managing virtual football leagues within Discord servers, featuring automated role management, financial tracking with Euro currency, player valuations, transfer systems, and match scheduling with notifications.

# User Preferences

- Preferred communication style: Simple, everyday language
- Language: Arabic support for setup instructions and documentation
- Deployment preference: Render.com platform for hosting

# System Architecture

## Core Technologies
- **Discord.py Framework**: Primary bot framework for Discord interactions using slash commands
- **SQLite Database**: Local database storage for clubs, players, matches, and transfer data
- **Flask Web Server**: Simple HTTP server for health checks and keep-alive functionality
- **Threading Model**: Concurrent execution of Discord bot and web server using Python threading

## Database Design
- **Relational Schema**: Clubs, players, matches, and transfers with foreign key relationships
- **Discord Integration**: Role IDs and user IDs stored for automatic Discord role management
- **Guild Isolation**: All data scoped by Discord guild ID for multi-server support
- **Timestamping**: Created/updated timestamps for audit trails

## Bot Architecture
- **Modular Command Structure**: Commands organized into separate modules (admin, club, player, match, stats)
- **Permission System**: Administrator-only access with decorator-based authorization
- **Rate Limiting**: Built-in rate limiting to prevent Discord API abuse
- **Error Handling**: Comprehensive error handling with user-friendly messages

## Discord Role Management
- **Automatic Role Creation**: Creates Discord roles when clubs are established
- **Dynamic Role Assignment**: Automatically assigns/removes roles during player transfers
- **Role Synchronization**: Maintains consistency between database and Discord roles
- **Bulk Operations**: Administrative commands for role cleanup and synchronization

## Financial System
- **Euro Currency**: All financial transactions handled in Euros with formatting
- **Budget Tracking**: Club budgets with administrative controls
- **Player Valuations**: Individual player market values
- **Transfer Logic**: Automated budget calculations during player transfers

## Match System
- **Scheduling Engine**: Match scheduling with date/time validation
- **Notification System**: Automated DM notifications to team members
- **Role-based Alerts**: Mentions club roles for match announcements
- **Reminder System**: 5-minute pre-match reminders

## Data Management
- **Backup/Restore**: Complete data export/import functionality
- **Reset Operations**: Comprehensive system reset with Discord role cleanup
- **Audit Trails**: Transfer history and activity tracking
- **Data Validation**: Input validation for dates, finances, and relationships

# External Dependencies

## Discord API
- **discord.py**: Main Discord library for bot interactions
- **Bot Permissions**: Requires manage roles, send messages, and slash command permissions
- **OAuth2 Scopes**: Bot and applications.commands scopes required

## Web Server
- **Flask**: Lightweight web framework for status endpoints
- **Keep-Alive Endpoints**: Health check and monitoring endpoints for uptime services
- **Static File Serving**: Basic HTML templates and CSS for status page

## Database
- **SQLite3**: Embedded database with no external dependencies
- **File-based Storage**: Single database file for portability
- **Connection Pooling**: Row factory for dictionary-like access

## Environment Configuration
- **DISCORD_TOKEN**: Required environment variable for bot authentication
- **Optional Secrets**: Session secrets for Flask web server
- **Logging**: File and console logging with configurable levels

## Deployment Dependencies
- **Threading Support**: Python threading for concurrent Flask and Discord bot execution
- **Process Management**: Daemon threads for web server lifecycle
- **Error Recovery**: Automatic retry logic for Discord connection failures