# ABOUTME: Tests for ingestion pipeline and file watcher
# ABOUTME: Verifies file monitoring, moving, and database integration

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from config import Config
from db import init_db, get_session, Recording
from watcher import IngestHandler, setup_watcher


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration with temporary directories."""
    monitored_dir = tmp_path / "monitored"
    storage_dir = tmp_path / "storage"
    
    monitored_dir.mkdir()
    storage_dir.mkdir()
    
    config = Config(
        monitored_directory=str(monitored_dir),
        storage_path=str(storage_dir),
        whisper_model="base.en",
        sample_rate=16000,
        max_concurrent_transcriptions=2
    )
    return config


@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    return str(db_path)


def test_ingest_handler_processes_valid_audio_file(test_config, test_db):
    """Test that IngestHandler correctly processes a valid audio file."""
    # Create a dummy audio file
    audio_file = Path(test_config.monitored_directory) / "test_recording.wav"
    audio_file.write_text("dummy audio content")
    
    # Mock audio metadata
    mock_metadata = {
        'duration': 120.5,
        'sample_rate': 44100,
        'channels': 2,
        'format': 'wav',
        'file_size': 1024
    }
    
    with patch('watcher.probe_metadata', return_value=mock_metadata), \
         patch('watcher.generate_internal_filename', return_value='1609459200_abcd1234.wav'):
        
        handler = IngestHandler(test_config, test_db)
        
        # Simulate file creation event
        from watchdog.events import FileCreatedEvent
        event = FileCreatedEvent(str(audio_file))
        handler.on_created(event)
        
        # Check that file was moved to storage
        expected_date_dir = datetime.now().strftime("%Y/%Y-%m-%d")
        expected_storage_path = Path(test_config.storage_path) / expected_date_dir / "1609459200_abcd1234.wav"
        
        assert expected_storage_path.exists()
        assert not audio_file.exists()  # Original should be moved
        
        # Check database record was created
        session = get_session(test_db)
        recording = session.query(Recording).first()
        
        assert recording is not None
        assert recording.original_filename == "test_recording.wav"
        assert recording.internal_filename == "1609459200_abcd1234.wav"
        assert recording.transcript_status == "pending"
        assert recording.duration_seconds == 120.5
        assert recording.sample_rate == 44100
        assert recording.channels == 2
        assert recording.audio_format == "wav"
        assert recording.file_size_bytes == 1024
        
        session.close()


def test_ingest_handler_ignores_non_audio_files(test_config, test_db):
    """Test that IngestHandler ignores non-audio file extensions."""
    # Create a non-audio file
    text_file = Path(test_config.monitored_directory) / "document.txt"
    text_file.write_text("not audio")
    
    handler = IngestHandler(test_config, test_db)
    
    # Simulate file creation event
    from watchdog.events import FileCreatedEvent
    event = FileCreatedEvent(str(text_file))
    handler.on_created(event)
    
    # File should still exist (not processed)
    assert text_file.exists()
    
    # No database record should be created
    session = get_session(test_db)
    count = session.query(Recording).count()
    assert count == 0
    session.close()


def test_ingest_handler_handles_invalid_audio_metadata(test_config, test_db):
    """Test that IngestHandler handles files with invalid metadata gracefully."""
    # Create a dummy audio file
    audio_file = Path(test_config.monitored_directory) / "corrupt.mp3"
    audio_file.write_text("corrupt audio")
    
    # Mock failed metadata extraction
    with patch('watcher.probe_metadata', return_value=None):
        handler = IngestHandler(test_config, test_db)
        
        # Simulate file creation event
        from watchdog.events import FileCreatedEvent
        event = FileCreatedEvent(str(audio_file))
        handler.on_created(event)
        
        # File should still exist (not processed)
        assert audio_file.exists()
        
        # No database record should be created
        session = get_session(test_db)
        count = session.query(Recording).count()
        assert count == 0
        session.close()


def test_ingest_handler_creates_storage_directories(test_config, test_db):
    """Test that IngestHandler creates necessary storage directories."""
    # Create a dummy audio file
    audio_file = Path(test_config.monitored_directory) / "test.m4a"
    audio_file.write_text("dummy audio")
    
    mock_metadata = {
        'duration': 60.0,
        'sample_rate': 16000,
        'channels': 1,
        'format': 'm4a',
        'file_size': 512
    }
    
    with patch('watcher.probe_metadata', return_value=mock_metadata), \
         patch('watcher.generate_internal_filename', return_value='1609459200_efgh5678.m4a'):
        
        handler = IngestHandler(test_config, test_db)
        
        # Simulate file creation event
        from watchdog.events import FileCreatedEvent
        event = FileCreatedEvent(str(audio_file))
        handler.on_created(event)
        
        # Check that date directory was created
        expected_date_dir = datetime.now().strftime("%Y/%Y-%m-%d")
        date_path = Path(test_config.storage_path) / expected_date_dir
        
        assert date_path.exists()
        assert date_path.is_dir()


def test_ingest_handler_idempotent_processing(test_config, test_db):
    """Test that processing the same file multiple times doesn't cause issues."""
    # Create a dummy audio file
    audio_file = Path(test_config.monitored_directory) / "duplicate.wav"
    audio_file.write_text("dummy audio")
    
    mock_metadata = {
        'duration': 30.0,
        'sample_rate': 22050,
        'channels': 1,
        'format': 'wav',
        'file_size': 256
    }
    
    with patch('watcher.probe_metadata', return_value=mock_metadata), \
         patch('watcher.generate_internal_filename', return_value='1609459200_ijkl9012.wav'):
        
        handler = IngestHandler(test_config, test_db)
        
        # Process the same event twice
        from watchdog.events import FileCreatedEvent
        event = FileCreatedEvent(str(audio_file))
        
        handler.on_created(event)
        # File is moved, so second call should do nothing
        handler.on_created(event)
        
        # Should have only one database record
        session = get_session(test_db)
        count = session.query(Recording).count()
        assert count == 1
        session.close()


def test_setup_watcher_returns_observer(test_config, test_db):
    """Test that setup_watcher returns a configured observer."""
    observer = setup_watcher(test_config, test_db)
    
    assert observer is not None
    # Observer should be configured but not started
    assert not observer.is_alive()