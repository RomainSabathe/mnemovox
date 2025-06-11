# ABOUTME: Tests for database migration adding transcription overrides
import sqlite3
from migrations.migration_002_add_overrides import apply_migration


def test_migration_adds_columns(tmp_path):
    # Setup: Create a database with the initial schema
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE recordings (
            id INTEGER PRIMARY KEY,
            original_filename TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()

    # Apply the migration
    apply_migration(str(db_path))

    # Verify the columns were added
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(recordings)")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    assert "transcription_model" in columns
    assert "transcription_language" in columns


def test_migration_idempotent(tmp_path):
    # Setup: Create a database with the initial schema
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE recordings (
            id INTEGER PRIMARY KEY,
            original_filename TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()

    # Apply the migration twice
    apply_migration(str(db_path))
    apply_migration(str(db_path))

    # Verify columns only added once
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(recordings)")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    # Count occurrences of each column
    model_count = sum(1 for col in columns if col == "transcription_model")
    lang_count = sum(1 for col in columns if col == "transcription_language")

    assert model_count == 1
    assert lang_count == 1
