"""
Database migration script to add joined_at column to user table.
Run this once on your production database.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Get database URL and fix postgres:// prefix
database_url = os.getenv("DATABASE_URL", "sqlite:///afhamha.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

print(f"Connecting to database...")
engine = create_engine(database_url)
is_postgres = database_url.startswith("postgresql://")

try:
    with engine.connect() as conn:
        # Check if column exists
        if is_postgres:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user' AND column_name='joined_at';
            """))
            column_exists = result.fetchone() is not None
        else:
            # SQLite: check using PRAGMA
            result = conn.execute(text("PRAGMA table_info(user);"))
            columns = [row[1] for row in result.fetchall()]
            column_exists = 'joined_at' in columns
        
        if column_exists:
            print("✓ Column 'joined_at' already exists. No migration needed.")
        else:
            print("Adding 'joined_at' column to user table...")
            if is_postgres:
                conn.execute(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """))
            else:
                conn.execute(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """))
            conn.commit()
            print("✓ Migration completed successfully!")
            
except Exception as e:
    print(f"✗ Migration failed: {e}")
    raise

print("\nDone!")
