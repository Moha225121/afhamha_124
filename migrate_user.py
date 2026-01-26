import sqlite3
import os
from datetime import datetime

db_path = "instance/afhamha.db"
if not os.path.exists(db_path):
    db_path = "afhamha.db"

def migrate_user():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if joined_at column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'joined_at' not in columns:
            print("Adding 'joined_at' column to 'user' table...")
            cursor.execute("ALTER TABLE user ADD COLUMN joined_at DATETIME")
            # Set a default date for existing users
            cursor.execute("UPDATE user SET joined_at = ?", (datetime.utcnow().isoformat(),))
            conn.commit()
            print("Successfully added 'joined_at' column and updated existing users.")
        else:
            print("'joined_at' column already exists.")
            
    except Exception as e:
        print(f"Error migrating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_user()
