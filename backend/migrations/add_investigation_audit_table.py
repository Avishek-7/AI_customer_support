"""
Migration: create investigation_audit table for admin copilot runs.
Run this script:
    python -m backend.migrations.add_investigation_audit_table
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from core.config import settings


def _to_sync_db_url(db_url: str) -> str:
    """Normalize async-style SQLAlchemy URLs for sync migration scripts."""
    if db_url.startswith("sqlite+aiosqlite://"):
        return db_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    if db_url.startswith("postgresql+asyncpg://"):
        return db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return db_url


def migrate():
    engine = create_engine(_to_sync_db_url(settings.DATABASE_URL))

    with engine.connect() as conn:
        if inspect(engine).has_table("investigation_audit"):
            print("investigation_audit table already exists")
            return

        if engine.dialect.name == "sqlite":
            conn.execute(text("""
                CREATE TABLE investigation_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigator_user_id INTEGER NOT NULL,
                    conversation_id INTEGER NOT NULL,
                    instruction_intent VARCHAR(64) NOT NULL,
                    tools_called TEXT NOT NULL DEFAULT '[]',
                    status VARCHAR(32) NOT NULL DEFAULT 'completed',
                    latency_ms INTEGER NOT NULL DEFAULT 0,
                    confidence_score REAL,
                    hallucination_score REAL,
                    alignment_score REAL,
                    diagnosis_summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY(investigator_user_id) REFERENCES users(id),
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
            """))
        else:
            conn.execute(text("""
                CREATE TABLE investigation_audit (
                    id SERIAL PRIMARY KEY,
                    investigator_user_id INTEGER NOT NULL REFERENCES users(id),
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    instruction_intent VARCHAR(64) NOT NULL,
                    tools_called TEXT NOT NULL DEFAULT '[]',
                    status VARCHAR(32) NOT NULL DEFAULT 'completed',
                    latency_ms INTEGER NOT NULL DEFAULT 0,
                    confidence_score DOUBLE PRECISION,
                    hallucination_score DOUBLE PRECISION,
                    alignment_score DOUBLE PRECISION,
                    diagnosis_summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """))

        conn.execute(text("""
            CREATE INDEX idx_investigation_audit_conversation_id
            ON investigation_audit(conversation_id);
        """))
        conn.execute(text("""
            CREATE INDEX idx_investigation_audit_created_at
            ON investigation_audit(created_at DESC);
        """))
        conn.commit()

    print("investigation_audit table created")


if __name__ == "__main__":
    migrate()
