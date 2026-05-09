"""
Database layer using SQLite with persistent path.
On Railway: set DATABASE_URL=/data/archiq.db AND add a Volume at /data
On local: defaults to ./archiq.db
Upgradeable to PostgreSQL by changing DATABASE_URL
"""
import aiosqlite
import json
import os
from pathlib import Path

# On Railway, mount a volume at /data and set DATABASE_URL=/data/archiq.db
# This ensures data survives container restarts
DATABASE_URL = os.getenv("DATABASE_URL", "./archiq.db")

# Ensure parent directory exists
_db_path = Path(DATABASE_URL)
if _db_path.parent != Path("."):
    _db_path.parent.mkdir(parents=True, exist_ok=True)


async def get_db():
    db = await aiosqlite.connect(DATABASE_URL)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        # Enable WAL mode for better concurrent access
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")

        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                raw_text TEXT,
                source_type TEXT,
                parsed_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_skills (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                skill_name TEXT,
                depth_level TEXT,
                evidence_text TEXT,
                confidence REAL,
                domain_cluster TEXT,
                embedding TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                job_type TEXT,
                source_url TEXT UNIQUE,
                jd_text TEXT,
                skills_json TEXT,
                fetched_at TEXT DEFAULT (datetime('now')),
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                job_id TEXT,
                total_score REAL,
                tech_score REAL,
                arch_score REAL,
                depth_score REAL,
                growth_score REAL,
                explanation_json TEXT,
                computed_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS gaps (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                skill_name TEXT,
                priority TEXT,
                reason_text TEXT,
                suggested_resources TEXT,
                order_index INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS scrape_sessions (
                id TEXT PRIMARY KEY,
                status TEXT,
                jobs_found INTEGER DEFAULT 0,
                started_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT
            );
        """)
        await db.commit()
    print(f"✅ Database initialized at: {DATABASE_URL}")
