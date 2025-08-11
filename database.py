# database.py
import os
import sqlite3
from urllib.parse import urlparse

try:
    import psycopg2
except Exception:
    psycopg2 = None

def get_connection():
    """
    Returns a DB connection:
      - If DATABASE_URL is present, connect to Postgres.
      - Else, fall back to SQLite local.db
    """
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Use psycopg2 to connect
        if not psycopg2:
            raise RuntimeError("psycopg2 is required to connect to a Postgres DATABASE_URL. Install psycopg2-binary.")
        url = urlparse(database_url)
        conn = psycopg2.connect(
            dbname=(url.path or "").lstrip("/"),
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        return conn, "postgres"
    else:
        conn = sqlite3.connect("local.db", check_same_thread=False)
        return conn, "sqlite"

def init_db():
    """
    Create messages table with a SQL compatible command for both DBs.
    """
    conn, kind = get_connection()
    cur = conn.cursor()
    if kind == "postgres":
        # Postgres schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL
            );
        """)
    else:
        # SQLite schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL
            );
        """)
    conn.commit()
    cur.close()
    conn.close()

def add_message(content: str):
    conn, kind = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO messages (content) VALUES (%s)" if kind == "postgres" else "INSERT INTO messages (content) VALUES (?)", (content,))
    conn.commit()
    cur.close()
    conn.close()

def fetch_messages(limit=100):
    conn, kind = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, content FROM messages ORDER BY id DESC LIMIT %s" if kind == "postgres" else "SELECT id, content FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
