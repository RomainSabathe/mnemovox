# ABOUTME: Migration script to add transcription overrides columns
import sqlite3


def apply_migration(db_path: str) -> None:
    """Apply migration to add transcription overrides columns."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(recordings)")
    columns = [col[1] for col in cursor.fetchall()]

    if "transcription_model" not in columns:
        cursor.execute("ALTER TABLE recordings ADD COLUMN transcription_model TEXT")

    if "transcription_language" not in columns:
        cursor.execute("ALTER TABLE recordings ADD COLUMN transcription_language TEXT")

    conn.commit()
    conn.close()
