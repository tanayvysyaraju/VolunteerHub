# database.py
import sqlite3
import json

def init_database(db_path='user_profiles.db'):
    """Initializes the SQLite database with the user_profiles table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        user_name TEXT NOT NULL,
        raw_conversations TEXT,
        strengths TEXT,
        interests TEXT,
        expertise TEXT,
        communication_style TEXT,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")

if __name__ == "__main__":
    init_database()