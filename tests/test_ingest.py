# ABOUTME: Tests for ingestion pipeline and file watcher
# ABOUTME: Verifies file monitoring, moving, and database integration

import pytest
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from mnemovox.config import Config
from mnemovox.db import init_db, get_session, Recording
from mnemovox.watcher import IngestHandler, setup_watcher


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
        max_concurrent_transcriptions=2,
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
        "duration": 120.5,
        "sample_rate": 44100,
        "channels": 2,
        "format": "wav",
        "file_size": 1024,
    }

    with (
        patch("mnemovox.watcher.probe_metadata", return_value=mock_metadata),
        patch(
            "mnemovox.watcher.generate_internal_filename",
            return_value="1609459200_abcd1234.wav",
        ),
    ):
        handler = IngestHandler(test_config, test_db)

        # Simulate file creation event
        from watchdog.events import FileCreatedEvent

        event = FileCreatedEvent(str(audio_file))
        handler.on_created(event)

        # Check that file was moved to storage
        expected_date_dir = datetime.now().strftime("%Y/%Y-%m-%d")
        expected_storage_path = (
            Path(test_config.storage_path)
            / expected_date_dir
            / "1609459200_abcd1234.wav"
        )

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
    with patch("mnemovox.watcher.probe_metadata", return_value=None):
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
        "duration": 60.0,
        "sample_rate": 16000,
        "channels": 1,
        "format": "m4a",
        "file_size": 512,
    }

    with (
        patch("mnemovox.watcher.probe_metadata", return_value=mock_metadata),
        patch(
            "mnemovox.watcher.generate_internal_filename",
            return_value="1609459200_efgh5678.m4a",
        ),
    ):
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
        "duration": 30.0,
        "sample_rate": 22050,
        "channels": 1,
        "format": "wav",
        "file_size": 256,
    }

    with (
        patch("mnemovox.watcher.probe_metadata", return_value=mock_metadata),
        patch(
            "mnemovox.watcher.generate_internal_filename",
            return_value="1609459200_ijkl9012.wav",
        ),
    ):
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


# Integration tests with real audio file
@pytest.mark.integration
def test_ingest_handler_real_audio_file(test_config, test_db):
    """Integration test: ingest real audio file with actual metadata extraction."""
    # Copy test audio file to monitored directory
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Copy file to monitored directory
    monitored_file = Path(test_config.monitored_directory) / "real_audio_test.wav"
    shutil.copy2(test_audio_path, monitored_file)

    # Create handler and process the file
    handler = IngestHandler(test_config, test_db)

    # Simulate file creation event
    from watchdog.events import FileCreatedEvent

    event = FileCreatedEvent(str(monitored_file))
    handler.on_created(event)

    # Verify file was moved to storage with correct structure
    # Should be moved to storage_path/YYYY/YYYY-MM-DD/timestamp_uuid.wav
    today = datetime.now()
    expected_date_dir = f"{today.year}/{today.strftime('%Y-%m-%d')}"
    storage_date_dir = Path(test_config.storage_path) / expected_date_dir

    assert storage_date_dir.exists()

    # Find the moved file (should be only one .wav file)
    wav_files = list(storage_date_dir.glob("*.wav"))
    assert len(wav_files) == 1
    moved_file = wav_files[0]

    # Verify filename pattern: timestamp_uuid.wav
    filename_parts = moved_file.stem.split("_")
    assert len(filename_parts) == 2
    assert filename_parts[0].isdigit()  # timestamp
    assert len(filename_parts[1]) == 8  # UUID

    # Verify original file was moved (not copied)
    assert not monitored_file.exists()

    # Verify database record was created with real metadata
    session = get_session(test_db)
    recording = session.query(Recording).first()

    assert recording is not None
    assert recording.original_filename == "real_audio_test.wav"
    assert recording.internal_filename == moved_file.name
    assert recording.transcript_status == "pending"

    # Verify real metadata was extracted
    assert recording.duration_seconds is not None
    assert recording.duration_seconds > 0
    assert recording.audio_format is not None
    assert recording.sample_rate is not None
    assert recording.channels is not None
    assert recording.file_size_bytes is not None
    assert recording.file_size_bytes > 0

    # Verify reasonable values for the test audio file
    assert 0.5 <= recording.duration_seconds <= 10.0
    assert recording.channels in [1, 2]  # mono or stereo
    assert 8000 <= recording.sample_rate <= 96000

    session.close()


@pytest.mark.integration
def test_ingest_handler_multiple_real_audio_files(test_config, test_db):
    """Integration test: ingest multiple real audio files sequentially."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    handler = IngestHandler(test_config, test_db)

    # Process multiple copies of the same file with different names
    for i in range(3):
        monitored_file = (
            Path(test_config.monitored_directory) / f"multi_audio_test_{i:02d}.wav"
        )
        shutil.copy2(test_audio_path, monitored_file)

        # Simulate file creation event
        from watchdog.events import FileCreatedEvent

        event = FileCreatedEvent(str(monitored_file))
        handler.on_created(event)

        # Verify file was moved
        assert not monitored_file.exists()

    # Verify all files were processed
    session = get_session(test_db)
    recordings = session.query(Recording).all()

    assert len(recordings) == 3

    # Verify each recording has unique internal filename but similar metadata
    internal_filenames = set()
    for i, recording in enumerate(recordings):
        assert recording.original_filename == f"multi_audio_test_{i:02d}.wav"
        assert recording.internal_filename not in internal_filenames
        internal_filenames.add(recording.internal_filename)

        # All should have similar metadata since they're the same file
        assert recording.duration_seconds is not None
        assert recording.duration_seconds > 0
        assert recording.transcript_status == "pending"

    session.close()


@pytest.mark.integration
def test_ingest_handler_real_audio_file_different_extensions(test_config, test_db):
    """Integration test: test ingestion with different file extensions."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    handler = IngestHandler(test_config, test_db)

    # Test with different extensions (same content, different names)
    extensions = [".wav", ".mp3", ".m4a"]

    for ext in extensions:
        # Copy with different extension
        monitored_file = Path(test_config.monitored_directory) / f"test_audio{ext}"
        shutil.copy2(test_audio_path, monitored_file)

        # Simulate file creation event
        from watchdog.events import FileCreatedEvent

        event = FileCreatedEvent(str(monitored_file))
        handler.on_created(event)

        # Verify file was processed (moved)
        assert not monitored_file.exists()

    # Verify all files were processed
    session = get_session(test_db)
    recordings = session.query(Recording).all()

    assert len(recordings) == len(extensions)

    # Verify each has the correct extension preserved
    for recording in recordings:
        assert recording.internal_filename.endswith((".wav", ".mp3", ".m4a"))
        assert recording.transcript_status == "pending"

    session.close()


@pytest.mark.integration
def test_ingest_handler_real_audio_file_storage_organization(test_config, test_db):
    """Integration test: verify proper storage directory organization."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Copy file to monitored directory
    monitored_file = Path(test_config.monitored_directory) / "storage_test.wav"
    shutil.copy2(test_audio_path, monitored_file)

    handler = IngestHandler(test_config, test_db)

    # Process the file
    from watchdog.events import FileCreatedEvent

    event = FileCreatedEvent(str(monitored_file))
    handler.on_created(event)

    # Verify storage directory structure
    today = datetime.now()
    year_dir = Path(test_config.storage_path) / str(today.year)
    date_dir = year_dir / today.strftime("%Y-%m-%d")

    assert year_dir.exists()
    assert date_dir.exists()

    # Verify file is in the correct location
    audio_files = list(date_dir.glob("*.wav"))
    assert len(audio_files) == 1

    stored_file = audio_files[0]

    # Verify file content is preserved
    assert stored_file.stat().st_size == test_audio_path.stat().st_size

    # Verify database record has correct storage path
    session = get_session(test_db)
    recording = session.query(Recording).first()

    expected_storage_path = (
        f"{today.year}/{today.strftime('%Y-%m-%d')}/{stored_file.name}"
    )
    assert recording.storage_path == expected_storage_path

    session.close()


@pytest.mark.integration
def test_ingest_handler_ignores_non_audio_files_real(test_config, test_db):
    """Integration test: verify non-audio files are ignored with real file system."""
    # Create a text file in monitored directory
    text_file = Path(test_config.monitored_directory) / "not_audio.txt"
    text_file.write_text("This is not an audio file")

    handler = IngestHandler(test_config, test_db)

    # Simulate file creation event
    from watchdog.events import FileCreatedEvent

    event = FileCreatedEvent(str(text_file))
    handler.on_created(event)

    # Verify file was not processed (still exists)
    assert text_file.exists()

    # Verify no database record was created
    session = get_session(test_db)
    count = session.query(Recording).count()
    assert count == 0
    session.close()


@pytest.mark.integration
def test_ingest_handler_concurrent_file_processing(test_config, test_db):
    """Integration test: verify handler can process files concurrently."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    handler = IngestHandler(test_config, test_db)

    # Create multiple files quickly
    monitored_files = []
    for i in range(5):
        monitored_file = (
            Path(test_config.monitored_directory) / f"concurrent_test_{i:02d}.wav"
        )
        shutil.copy2(test_audio_path, monitored_file)
        monitored_files.append(monitored_file)

    # Process all files
    from watchdog.events import FileCreatedEvent

    for monitored_file in monitored_files:
        event = FileCreatedEvent(str(monitored_file))
        handler.on_created(event)

    # Verify all files were processed
    for monitored_file in monitored_files:
        assert not monitored_file.exists()

    # Verify all database records were created
    session = get_session(test_db)
    recordings = session.query(Recording).all()

    assert len(recordings) == 5

    # Verify each has unique internal filename
    internal_filenames = {r.internal_filename for r in recordings}
    assert len(internal_filenames) == 5  # All unique

    session.close()
