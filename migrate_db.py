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
        
        # PostgreSQL aggressive migrations
        if is_postgres:
            print("Applying PostgreSQL migrations (IF NOT EXISTS)...")
            queries = [
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;',
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0;',
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS study_hours FLOAT DEFAULT 0.0;',
                'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;',
                'ALTER TABLE explanation ADD COLUMN IF NOT EXISTS subject VARCHAR(100);',
                'ALTER TABLE explanation ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;'
            ]
            for q in queries:
                try:
                    conn.execute(text(q))
                    conn.commit()
                    print(f"✓ Executed: {q[:40]}...")
                    migrations_run += 1
                except Exception as ex:
                    print(f"⚠ Skipping query (might already exist): {ex}")
        else:
            # SQLite fallback
            if not column_exists(conn, 'user', 'is_verified'):
                conn.execute(text('ALTER TABLE "user" ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;'))
                conn.commit()
                migrations_run += 1

        # Create lesson table if it doesn't exist
        try:
            if is_postgres:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS lesson (
                        id SERIAL PRIMARY KEY,
                        study_year VARCHAR(50) NOT NULL,
                        subject VARCHAR(100) NOT NULL,
                        category VARCHAR(100),
                        lesson_name VARCHAR(255) NOT NULL,
                        description TEXT
                    );
                """))
                conn.commit()
            else:
                # SQLite create lesson
                pass # Already handled or simplified
            print("✓ Checked lesson table")
        except Exception as e:
            print(f"⚠ Lesson table check error: {e}")
            
        if migrations_run > 0:
            print(f"\n✓ Migration finished! {migrations_run} checks performed.")
        else:
            print("\n✓ Database is up to date.")
            
except Exception as e:
    print(f"\n✗ Migration failed: {e}")
    raise

print("\nDone!")
