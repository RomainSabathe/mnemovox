# ABOUTME: Tests for FTS5 full-text search functionality
# ABOUTME: Verifies FTS table creation and sync functionality for text search

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from src.audio_manager.db import init_db, get_session, Recording
from src.audio_manager.config import get_config


def test_init_db_creates_fts_table_when_enabled(tmp_path):
    """Test that init_db creates FTS5 table when fts_enabled is True."""
    # Create a config file with FTS enabled
    config_file = tmp_path / "config.yaml"
    config_data = {
        "storage_path": str(tmp_path / "storage"),
        "fts_enabled": True
    }
    
    with open(config_file, 'w') as f:
        import yaml
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    db_path = str(tmp_path / "test.db")
    
    # Initialize database with FTS enabled
    init_db(db_path, fts_enabled=config.fts_enabled)
    
    # Check that FTS table exists
    session = get_session(db_path)
    try:
        # Query sqlite_master to check if FTS table exists
        from sqlalchemy import text
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='recordings_fts'")
        ).fetchone()
        assert result is not None
        assert result[0] == "recordings_fts"
        
        # Verify FTS table structure by checking its definition
        table_info = session.execute(
            text("SELECT sql FROM sqlite_master WHERE name='recordings_fts'")
        ).fetchone()
        
        # Should be a virtual table using FTS5
        assert "CREATE VIRTUAL TABLE" in table_info[0]
        assert "fts5" in table_info[0].lower()
        assert "original_filename" in table_info[0]
        assert "transcript_text" in table_info[0]
        
    finally:
        session.close()


def test_init_db_skips_fts_table_when_disabled(tmp_path):
    """Test that init_db skips FTS5 table when fts_enabled is False."""
    # Create a config file with FTS disabled
    config_file = tmp_path / "config.yaml"
    config_data = {
        "storage_path": str(tmp_path / "storage"),
        "fts_enabled": False
    }
    
    with open(config_file, 'w') as f:
        import yaml
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    db_path = str(tmp_path / "test.db")
    
    # Initialize database with FTS disabled
    init_db(db_path, fts_enabled=config.fts_enabled)
    
    # Check that FTS table does not exist
    session = get_session(db_path)
    try:
        from sqlalchemy import text
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='recordings_fts'")
        ).fetchone()
        assert result is None
        
    finally:
        session.close()


def test_sync_fts_populates_search_data(tmp_path):
    """Test that sync_fts populates FTS table for a recording."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "storage_path": str(tmp_path / "storage"),
        "fts_enabled": True
    }
    
    with open(config_file, 'w') as f:
        import yaml
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    db_path = str(tmp_path / "test.db")
    
    # Initialize database with FTS
    init_db(db_path, fts_enabled=config.fts_enabled)
    
    session = get_session(db_path)
    try:
        # Create a test recording
        recording = Recording(
            original_filename="test_audio.wav",
            internal_filename="123456_abcdef.wav",
            storage_path="/storage/path/test.wav",
            import_timestamp=datetime.now(),
            duration_seconds=45.5,
            transcript_status="complete",
            transcript_text="Hello world this is a test transcript",
            transcript_language="en"
        )
        session.add(recording)
        session.commit()
        
        # Sync FTS
        from src.audio_manager.db import sync_fts
        sync_fts(session, recording.id)
        
        # Verify FTS data exists
        from sqlalchemy import text
        result = session.execute(
            text("SELECT rowid, original_filename, transcript_text FROM recordings_fts WHERE rowid = :recording_id"),
            {"recording_id": recording.id}
        ).fetchone()
        
        assert result is not None
        assert result[0] == recording.id
        assert result[1] == "test_audio.wav"
        assert result[2] == "Hello world this is a test transcript"
        
    finally:
        session.close()


def test_sync_fts_handles_null_transcript(tmp_path):
    """Test that sync_fts handles recordings with null transcript text."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "storage_path": str(tmp_path / "storage"),
        "fts_enabled": True
    }
    
    with open(config_file, 'w') as f:
        import yaml
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    db_path = str(tmp_path / "test.db")
    
    # Initialize database with FTS
    init_db(db_path, fts_enabled=config.fts_enabled)
    
    session = get_session(db_path)
    try:
        # Create a test recording with no transcript
        recording = Recording(
            original_filename="pending_audio.wav",
            internal_filename="789012_defghi.wav",
            storage_path="/storage/path/pending.wav",
            import_timestamp=datetime.now(),
            duration_seconds=30.0,
            transcript_status="pending",
            transcript_text=None,
            transcript_language=None
        )
        session.add(recording)
        session.commit()
        
        # Sync FTS - should not fail
        from src.audio_manager.db import sync_fts
        sync_fts(session, recording.id)
        
        # Verify FTS data exists with empty transcript
        from sqlalchemy import text
        result = session.execute(
            text("SELECT rowid, original_filename, transcript_text FROM recordings_fts WHERE rowid = :recording_id"),
            {"recording_id": recording.id}
        ).fetchone()
        
        assert result is not None
        assert result[0] == recording.id
        assert result[1] == "pending_audio.wav"
        assert result[2] == "" or result[2] is None
        
    finally:
        session.close()


def test_sync_fts_updates_existing_entry(tmp_path):
    """Test that sync_fts updates existing FTS entry when called multiple times."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "storage_path": str(tmp_path / "storage"),
        "fts_enabled": True
    }
    
    with open(config_file, 'w') as f:
        import yaml
        yaml.dump(config_data, f)
    
    config = get_config(str(config_file))
    db_path = str(tmp_path / "test.db")
    
    # Initialize database with FTS
    init_db(db_path, fts_enabled=config.fts_enabled)
    
    session = get_session(db_path)
    try:
        # Create a test recording
        recording = Recording(
            original_filename="update_test.wav",
            internal_filename="345678_jklmno.wav",
            storage_path="/storage/path/update.wav",
            import_timestamp=datetime.now(),
            duration_seconds=60.0,
            transcript_status="pending",
            transcript_text=None
        )
        session.add(recording)
        session.commit()
        
        # Initial sync with no transcript
        from src.audio_manager.db import sync_fts
        sync_fts(session, recording.id)
        
        # Update transcript and sync again
        recording.transcript_text = "Updated transcript content"
        recording.transcript_status = "complete"
        session.commit()
        
        sync_fts(session, recording.id)
        
        # Verify updated FTS data
        from sqlalchemy import text
        result = session.execute(
            text("SELECT rowid, original_filename, transcript_text FROM recordings_fts WHERE rowid = :recording_id"),
            {"recording_id": recording.id}
        ).fetchone()
        
        assert result is not None
        assert result[0] == recording.id
        assert result[1] == "update_test.wav"
        assert result[2] == "Updated transcript content"
        
        # Verify only one FTS entry exists for this recording
        count_result = session.execute(
            text("SELECT COUNT(*) FROM recordings_fts WHERE rowid = :recording_id"),
            {"recording_id": recording.id}
        ).fetchone()
        
        assert count_result[0] == 1
        
    finally:
        session.close()