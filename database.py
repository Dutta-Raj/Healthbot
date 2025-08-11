import os
import sqlite3
import psycopg2
from urllib.parse import urlparse

def get_connection():
    """
    Returns a database connection.
    Uses DATABASE_URL if set (for Railway/PostgreSQL),
    otherwise falls back to local SQLite.
    """
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        # Railway will give a PostgreSQL URL in DATABASE_URL
        url = urlparse(database_url)
        conn = psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        return conn
    else:
        # Local SQLite database
        conn = sqlite3.connect("local.db")
        return conn

def init_db():
    """
    Creates a sample table if it doesn't exist.
    """
    conn = get_connection()
    cur = conn.cursor()

    # For PostgreSQL and SQLite compatibility
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
