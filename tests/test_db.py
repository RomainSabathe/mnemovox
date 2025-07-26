# ABOUTME: Tests for database module
# ABOUTME: Verifies database initialization and schema creation

import sqlite3
from mnemovox.db import init_db, get_session
from sqlalchemy import inspect


def test_init_db_creates_database_file(tmp_path):
    """Test that init_db creates the database file."""
    db_path = tmp_path / "test_metadata.db"
    init_db(str(db_path))

    assert db_path.exists()


def test_init_db_creates_recordings_table(tmp_path):
    """Test that init_db creates the recordings table with correct schema."""
    db_path = tmp_path / "test_metadata.db"
    init_db(str(db_path))

    # Connect directly to verify table structure
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='recordings'"
    )
    result = cursor.fetchone()
    assert result is not None

    # Check column names and types
    cursor.execute("PRAGMA table_info(recordings)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]

    expected_columns = [
        "id",
        "original_filename",
        "internal_filename",
        "storage_path",
        "import_timestamp",
        "duration_seconds",
        "audio_format",
        "sample_rate",
        "channels",
        "file_size_bytes",
        "transcript_status",
        "transcript_language",
        "transcript_text",
        "transcript_segments",
        "created_at",
        "updated_at",
    ]

    for col in expected_columns:
        assert col in column_names, f"Column {col} missing from recordings table"

    conn.close()


def test_get_session_returns_valid_session(tmp_path):
    """Test that get_session returns a working SQLAlchemy session."""
    db_path = tmp_path / "test_metadata.db"
    init_db(str(db_path))

    session = get_session(str(db_path))

    # Verify we can query the database
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()

    assert "recordings" in tables

    session.close()


def test_init_db_idempotent(tmp_path):
    """Test that calling init_db multiple times doesn't break anything."""
    db_path = tmp_path / "test_metadata.db"

    # Call init_db twice
    init_db(str(db_path))
    init_db(str(db_path))

    # Should still work
    session = get_session(str(db_path))
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()

    assert "recordings" in tables
    session.close()


def test_database_with_config_path(tmp_path):
    """Test database creation using storage path from config pattern."""
    storage_path = tmp_path / "data" / "audio"
    storage_path.mkdir(parents=True)

    db_path = storage_path / "metadata.db"
    init_db(str(db_path))

    assert db_path.exists()

    session = get_session(str(db_path))
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()

    assert "recordings" in tables
    session.close()
