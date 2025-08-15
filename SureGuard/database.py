import sqlite3
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="football_bot.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def initialize(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clubs table with Discord role integration
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS clubs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        budget REAL DEFAULT 0.0,
                        guild_id INTEGER NOT NULL,
                        role_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Players table with role tracking
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        value REAL DEFAULT 0.0,
                        club_id INTEGER,
                        position TEXT DEFAULT 'Unknown',
                        age INTEGER DEFAULT 25,
                        contract_end DATE,
                        discord_user_id INTEGER,
                        guild_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (club_id) REFERENCES clubs (id) ON DELETE SET NULL
                    )
                ''')
                
                # Transfers table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transfers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        player_id INTEGER NOT NULL,
                        from_club_id INTEGER,
                        to_club_id INTEGER,
                        transfer_fee REAL DEFAULT 0.0,
                        transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        guild_id INTEGER NOT NULL,
                        FOREIGN KEY (player_id) REFERENCES players (id),
                        FOREIGN KEY (from_club_id) REFERENCES clubs (id),
                        FOREIGN KEY (to_club_id) REFERENCES clubs (id)
                    )
                ''')
                
                # Matches table with role integration
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        team1_id INTEGER NOT NULL,
                        team2_id INTEGER NOT NULL,
                        team1_role_id INTEGER,
                        team2_role_id INTEGER,
                        match_date TIMESTAMP NOT NULL,
                        guild_id INTEGER NOT NULL,
                        created_by INTEGER,
                        reminded BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (team1_id) REFERENCES clubs (id),
                        FOREIGN KEY (team2_id) REFERENCES clubs (id)
                    )
                ''')
                
                # Settings table for guild-specific configurations
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER UNIQUE NOT NULL,
                        admin_role_id INTEGER,
                        match_channel_id INTEGER,
                        settings_json TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Database tables initialized")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    # Club management methods
    def create_club(self, name, budget, guild_id, role_id=None):
        """Create a new club"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO clubs (name, budget, guild_id, role_id) VALUES (?, ?, ?, ?)',
                (name, budget, guild_id, role_id)
            )
            return cursor.lastrowid

    def get_club_by_name(self, name, guild_id):
        """Get club by name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM clubs WHERE name = ? AND guild_id = ?',
                (name, guild_id)
            )
            return cursor.fetchone()

    def get_all_clubs(self, guild_id):
        """Get all clubs in a guild"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM clubs WHERE guild_id = ? ORDER BY name',
                (guild_id,)
            )
            return cursor.fetchall()

    def update_club_budget(self, club_id, budget):
        """Update club budget"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE clubs SET budget = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (budget, club_id)
            )
            return cursor.rowcount > 0

    def delete_club(self, club_id):
        """Delete a club"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM clubs WHERE id = ?', (club_id,))
            return cursor.rowcount > 0

    # Player management methods
    def create_player(self, name, value, guild_id, club_id=None, position="Unknown", age=25, discord_user_id=None):
        """Create a new player"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO players (name, value, club_id, position, age, discord_user_id, guild_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (name, value, club_id, position, age, discord_user_id, guild_id)
            )
            return cursor.lastrowid

    def get_player_by_name(self, name, guild_id):
        """Get player by name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM players WHERE name = ? AND guild_id = ?',
                (name, guild_id)
            )
            return cursor.fetchone()

    def get_players_by_club(self, club_id):
        """Get all players in a club"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM players WHERE club_id = ? ORDER BY value DESC',
                (club_id,)
            )
            return cursor.fetchall()

    def get_all_players(self, guild_id):
        """Get all players in a guild"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM players WHERE guild_id = ? ORDER BY value DESC',
                (guild_id,)
            )
            return cursor.fetchall()

    def update_player_value(self, player_id, value):
        """Update player value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE players SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (value, player_id)
            )
            return cursor.rowcount > 0

    def transfer_player(self, player_id, to_club_id, transfer_fee, guild_id):
        """Transfer a player to another club"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current club
            cursor.execute('SELECT club_id FROM players WHERE id = ?', (player_id,))
            result = cursor.fetchone()
            from_club_id = result['club_id'] if result else None
            
            # Update player club
            cursor.execute(
                'UPDATE players SET club_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (to_club_id, player_id)
            )
            
            # Record transfer
            cursor.execute(
                '''INSERT INTO transfers (player_id, from_club_id, to_club_id, transfer_fee, guild_id) 
                   VALUES (?, ?, ?, ?, ?)''',
                (player_id, from_club_id, to_club_id, transfer_fee, guild_id)
            )
            
            # Update club budgets
            if from_club_id:
                cursor.execute(
                    'UPDATE clubs SET budget = budget + ? WHERE id = ?',
                    (transfer_fee, from_club_id)
                )
            
            if to_club_id:
                cursor.execute(
                    'UPDATE clubs SET budget = budget - ? WHERE id = ?',
                    (transfer_fee, to_club_id)
                )
            
            return True

    def delete_player(self, player_id):
        """Delete a player"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM players WHERE id = ?', (player_id,))
            return cursor.rowcount > 0

    # Match management methods
    def create_match(self, team1_id, team2_id, match_date, guild_id, created_by, team1_role_id=None, team2_role_id=None):
        """Create a new match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO matches (team1_id, team2_id, team1_role_id, team2_role_id, match_date, guild_id, created_by) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (team1_id, team2_id, team1_role_id, team2_role_id, match_date, guild_id, created_by)
            )
            return cursor.lastrowid

    def get_upcoming_matches(self, guild_id=None, minutes=5):
        """Get matches that need reminders"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            reminder_time = datetime.now() + timedelta(minutes=minutes)
            
            if guild_id:
                cursor.execute(
                    '''SELECT * FROM matches 
                       WHERE guild_id = ? AND match_date <= ? AND match_date > datetime('now') AND reminded = FALSE''',
                    (guild_id, reminder_time.strftime('%Y-%m-%d %H:%M:%S'))
                )
            else:
                cursor.execute(
                    '''SELECT * FROM matches 
                       WHERE match_date <= ? AND match_date > datetime('now') AND reminded = FALSE''',
                    (reminder_time.strftime('%Y-%m-%d %H:%M:%S'),)
                )
            
            matches = cursor.fetchall()
            
            # Mark as reminded
            for match in matches:
                cursor.execute(
                    'UPDATE matches SET reminded = TRUE WHERE id = ?',
                    (match['id'],)
                )
            
            return matches

    def get_matches(self, guild_id):
        """Get all matches for a guild"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT m.*, c1.name as team1_name, c2.name as team2_name 
                   FROM matches m
                   JOIN clubs c1 ON m.team1_id = c1.id
                   JOIN clubs c2 ON m.team2_id = c2.id
                   WHERE m.guild_id = ?
                   ORDER BY m.match_date DESC''',
                (guild_id,)
            )
            return cursor.fetchall()

    # Statistics methods
    def get_top_players_by_value(self, guild_id, limit=10):
        """Get top players by value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT p.*, c.name as club_name FROM players p
                   LEFT JOIN clubs c ON p.club_id = c.id
                   WHERE p.guild_id = ?
                   ORDER BY p.value DESC LIMIT ?''',
                (guild_id, limit)
            )
            return cursor.fetchall()

    def get_richest_clubs(self, guild_id, limit=10):
        """Get richest clubs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM clubs WHERE guild_id = ? ORDER BY budget DESC LIMIT ?',
                (guild_id, limit)
            )
            return cursor.fetchall()

    def get_club_stats(self, club_id):
        """Get comprehensive club statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Basic club info
            cursor.execute('SELECT * FROM clubs WHERE id = ?', (club_id,))
            club = cursor.fetchone()
            
            if not club:
                return None
                
            # Player count and total value
            cursor.execute(
                'SELECT COUNT(*) as player_count, COALESCE(SUM(value), 0) as total_value FROM players WHERE club_id = ?',
                (club_id,)
            )
            stats = cursor.fetchone()
            
            # Transfer activity
            cursor.execute(
                'SELECT COUNT(*) as transfers_in FROM transfers WHERE to_club_id = ?',
                (club_id,)
            )
            transfers_in = cursor.fetchone()['transfers_in']
            
            cursor.execute(
                'SELECT COUNT(*) as transfers_out FROM transfers WHERE from_club_id = ?',
                (club_id,)
            )
            transfers_out = cursor.fetchone()['transfers_out']
            
            return {
                'club': dict(club),
                'player_count': stats['player_count'],
                'total_value': stats['total_value'],
                'transfers_in': transfers_in,
                'transfers_out': transfers_out
            }

    # Utility methods
    def reset_all_data(self, guild_id):
        """Reset all data for a guild"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM transfers WHERE guild_id = ?', (guild_id,))
            cursor.execute('DELETE FROM matches WHERE guild_id = ?', (guild_id,))
            cursor.execute('DELETE FROM players WHERE guild_id = ?', (guild_id,))
            cursor.execute('DELETE FROM clubs WHERE guild_id = ?', (guild_id,))
            cursor.execute('DELETE FROM settings WHERE guild_id = ?', (guild_id,))
            return True

    def backup_data(self, guild_id):
        """Create a backup of guild data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            backup = {
                'timestamp': datetime.now().isoformat(),
                'guild_id': guild_id,
                'clubs': [],
                'players': [],
                'transfers': [],
                'matches': []
            }
            
            # Backup clubs
            cursor.execute('SELECT * FROM clubs WHERE guild_id = ?', (guild_id,))
            backup['clubs'] = [dict(row) for row in cursor.fetchall()]
            
            # Backup players
            cursor.execute('SELECT * FROM players WHERE guild_id = ?', (guild_id,))
            backup['players'] = [dict(row) for row in cursor.fetchall()]
            
            # Backup transfers
            cursor.execute('SELECT * FROM transfers WHERE guild_id = ?', (guild_id,))
            backup['transfers'] = [dict(row) for row in cursor.fetchall()]
            
            # Backup matches
            cursor.execute('SELECT * FROM matches WHERE guild_id = ?', (guild_id,))
            backup['matches'] = [dict(row) for row in cursor.fetchall()]
            
            return backup
