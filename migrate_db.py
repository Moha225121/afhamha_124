"""
Database migration script to add missing columns to production database.
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

def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table."""
    if is_postgres:
        result = conn.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='{table_name}' AND column_name='{column_name}';
        """))
        return result.fetchone() is not None
    else:
        result = conn.execute(text(f"PRAGMA table_info({table_name});"))
        columns = [row[1] for row in result.fetchall()]
        return column_name in columns

try:
    with engine.connect() as conn:
        migrations_run = 0
        
        # Migration 1: Add joined_at to user table
        if not column_exists(conn, 'user', 'joined_at'):
            print("Adding 'joined_at' column to user table...")
            conn.execute(text("""
                ALTER TABLE "user" 
                ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """))
            conn.commit()
            print("✓ Added joined_at column")
            migrations_run += 1
        else:
            print("✓ Column 'joined_at' already exists in user table")
        
        # Migration 2: Add subject to explanation table
        if not column_exists(conn, 'explanation', 'subject'):
            print("Adding 'subject' column to explanation table...")
            conn.execute(text("""
                ALTER TABLE explanation 
                ADD COLUMN subject VARCHAR(100);
            """))
            conn.commit()
            print("✓ Added subject column")
            migrations_run += 1
        else:
            print("✓ Column 'subject' already exists in explanation table")
        
        # Migration 3: Add created_at to explanation table
        if not column_exists(conn, 'explanation', 'created_at'):
            print("Adding 'created_at' column to explanation table...")
            conn.execute(text("""
                ALTER TABLE explanation 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """))
            conn.commit()
            print("✓ Added created_at column")
            migrations_run += 1
        else:
            print("✓ Column 'created_at' already exists in explanation table")
        
        # Migration 4: Create lesson table if it doesn't exist
        if is_postgres:
            table_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'lesson'
                );
            """))
            table_exists = table_check.scalar()
        else:
            table_check = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='lesson';
            """))
            table_exists = table_check.fetchone() is not None
        
        if not table_exists:
            print("Creating 'lesson' table...")
            conn.execute(text("""
                CREATE TABLE lesson (
                    id SERIAL PRIMARY KEY,
                    study_year VARCHAR(50) NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    category VARCHAR(100),
                    lesson_name VARCHAR(255) NOT NULL,
                    description TEXT
                );
            """))
            conn.commit()
            print("✓ Created lesson table")
            migrations_run += 1
        else:
            print("✓ Table 'lesson' already exists")
        
        if migrations_run > 0:
            print(f"\n✓ Migration completed! {migrations_run} column(s) added.")
        else:
            print("\n✓ Database is up to date. No migrations needed.")
            
except Exception as e:
    print(f"\n✗ Migration failed: {e}")
    raise

print("\nDone!")
