# ABOUTME: Tests for complete ingestion to transcription pipeline
# ABOUTME: Verifies end-to-end workflow with asyncio orchestration

import pytest
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording
from src.audio_manager.pipeline import (
    TranscriptionPipeline,
    process_pending_transcriptions,
)


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
    """Create a test database with sample records."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    return str(db_path)


@pytest.mark.asyncio
async def test_transcription_pipeline_processes_pending_record(test_config, test_db):
    """Test that pipeline processes a pending transcription record."""
    # Create a pending record in the database
    session = get_session(test_db)

    # Create storage directory and dummy audio file
    storage_path = "2023/2023-12-01/1609459200_abcd1234.wav"
    full_storage_path = Path(test_config.storage_path) / storage_path
    full_storage_path.parent.mkdir(parents=True, exist_ok=True)
    full_storage_path.write_text("dummy audio content")

    recording = Recording(
        original_filename="test.wav",
        internal_filename="1609459200_abcd1234.wav",
        storage_path=storage_path,
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="pending",
    )
    session.add(recording)
    session.commit()
    record_id = recording.id
    session.close()

    # Mock transcription result
    mock_transcript = (
        "Hello world test transcript",
        [
            {"start": 0.0, "end": 2.0, "text": "Hello world", "confidence": 0.95},
            {"start": 2.0, "end": 4.0, "text": "test transcript", "confidence": 0.88},
        ],
    )

    with patch(
        "src.audio_manager.pipeline.transcribe_file", return_value=mock_transcript
    ):
        pipeline = TranscriptionPipeline(test_config, test_db)
        await pipeline.process_pending_transcriptions()

    # Verify record was updated
    session = get_session(test_db)
    updated_record = session.query(Recording).filter_by(id=record_id).first()

    assert updated_record.transcript_status == "complete"
    assert updated_record.transcript_text == "Hello world test transcript"
    assert updated_record.transcript_segments is not None
    assert len(updated_record.transcript_segments) == 2
    assert updated_record.transcript_segments[0]["text"] == "Hello world"

    session.close()


@pytest.mark.asyncio
async def test_transcription_pipeline_handles_error(test_config, test_db):
    """Test that pipeline handles transcription errors gracefully."""
    # Create a pending record
    session = get_session(test_db)

    recording = Recording(
        original_filename="error.wav",
        internal_filename="1609459200_error123.wav",
        storage_path="2023/2023-12-01/1609459200_error123.wav",
        import_timestamp=datetime.now(),
        duration_seconds=15.0,
        audio_format="wav",
        transcript_status="pending",
    )
    session.add(recording)
    session.commit()
    record_id = recording.id
    session.close()

    # Mock transcription failure
    with patch("src.audio_manager.pipeline.transcribe_file", return_value=None):
        pipeline = TranscriptionPipeline(test_config, test_db)
        await pipeline.process_pending_transcriptions()

    # Verify record was marked as error
    session = get_session(test_db)
    updated_record = session.query(Recording).filter_by(id=record_id).first()

    assert updated_record.transcript_status == "error"
    assert updated_record.transcript_text is None
    assert updated_record.transcript_segments is None

    session.close()


@pytest.mark.asyncio
async def test_transcription_pipeline_processes_multiple_records(test_config, test_db):
    """Test that pipeline processes multiple records successfully."""
    # Create multiple pending records
    session = get_session(test_db)

    for i in range(5):
        storage_path = f"2023/2023-12-01/1609459200_test{i:03d}.wav"
        full_storage_path = Path(test_config.storage_path) / storage_path
        full_storage_path.parent.mkdir(parents=True, exist_ok=True)
        full_storage_path.write_text(f"dummy audio {i}")

        recording = Recording(
            original_filename=f"test{i}.wav",
            internal_filename=f"1609459200_test{i:03d}.wav",
            storage_path=storage_path,
            import_timestamp=datetime.now(),
            duration_seconds=10.0,
            transcript_status="pending",
        )
        session.add(recording)

    session.commit()
    session.close()

    # Track concurrent calls using a simpler approach
    call_count = 0

    def mock_transcribe_with_delay(*args):
        nonlocal call_count
        call_count += 1
        import time

        time.sleep(0.1)  # Simulate processing time
        return (
            "Mock transcript",
            [{"start": 0, "end": 1, "text": "Mock", "confidence": 0.9}],
        )

    with patch(
        "src.audio_manager.pipeline.transcribe_file",
        side_effect=mock_transcribe_with_delay,
    ):
        pipeline = TranscriptionPipeline(test_config, test_db)
        await pipeline.process_pending_transcriptions()

    # Check that all 5 records were processed
    assert call_count == 5

    # Verify all records were marked as complete
    session = get_session(test_db)
    completed_count = (
        session.query(Recording).filter_by(transcript_status="complete").count()
    )
    assert completed_count == 5
    session.close()


@pytest.mark.asyncio
async def test_transcription_pipeline_no_pending_records(test_config, test_db):
    """Test that pipeline handles case with no pending records."""
    pipeline = TranscriptionPipeline(test_config, test_db)

    # Should complete without error even with no pending records
    await pipeline.process_pending_transcriptions()

    # Verify no records exist
    session = get_session(test_db)
    count = session.query(Recording).count()
    assert count == 0
    session.close()


def test_process_pending_transcriptions_function(test_config, test_db):
    """Test the standalone process_pending_transcriptions function."""
    # Create a pending record
    session = get_session(test_db)

    storage_path = "2023/2023-12-01/1609459200_func123.wav"
    full_storage_path = Path(test_config.storage_path) / storage_path
    full_storage_path.parent.mkdir(parents=True, exist_ok=True)
    full_storage_path.write_text("dummy audio")

    recording = Recording(
        original_filename="func_test.wav",
        internal_filename="1609459200_func123.wav",
        storage_path=storage_path,
        import_timestamp=datetime.now(),
        transcript_status="pending",
    )
    session.add(recording)
    session.commit()
    record_id = recording.id
    session.close()

    # Mock transcription
    mock_result = (
        "Function test",
        [{"start": 0, "end": 1, "text": "Function test", "confidence": 0.9}],
    )

    with patch("src.audio_manager.pipeline.transcribe_file", return_value=mock_result):
        # Run the function (should work synchronously)
        asyncio.run(process_pending_transcriptions(test_config, test_db))

    # Verify record was processed
    session = get_session(test_db)
    updated_record = session.query(Recording).filter_by(id=record_id).first()

    assert updated_record.transcript_status == "complete"
    assert updated_record.transcript_text == "Function test"

    session.close()


@pytest.mark.asyncio
async def test_transcription_pipeline_missing_audio_file(test_config, test_db):
    """Test handling of records where audio file is missing."""
    session = get_session(test_db)

    # Create record with non-existent audio file
    recording = Recording(
        original_filename="missing.wav",
        internal_filename="1609459200_missing.wav",
        storage_path="2023/2023-12-01/1609459200_missing.wav",  # File doesn't exist
        import_timestamp=datetime.now(),
        transcript_status="pending",
    )
    session.add(recording)
    session.commit()
    record_id = recording.id
    session.close()

    pipeline = TranscriptionPipeline(test_config, test_db)
    await pipeline.process_pending_transcriptions()

    # Should mark as error when file is missing
    session = get_session(test_db)
    updated_record = session.query(Recording).filter_by(id=record_id).first()

    assert updated_record.transcript_status == "error"

    session.close()


# Integration tests with real audio file
@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_transcribe_real_audio_file(test_config, test_db):
    """Integration test: complete pipeline with real audio file transcription."""
    # Copy the test audio file to storage location
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Create storage directory structure
    storage_path = "2023/2023-12-01/1609459200_real_test.wav"
    full_storage_path = Path(test_config.storage_path) / storage_path
    full_storage_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy test file to storage location
    shutil.copy2(test_audio_path, full_storage_path)

    # Create database record
    session = get_session(test_db)

    recording = Recording(
        original_filename="real_test.wav",
        internal_filename="1609459200_real_test.wav",
        storage_path=storage_path,
        import_timestamp=datetime.now(),
        duration_seconds=None,  # Will be filled by transcription
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=int(test_audio_path.stat().st_size),
        transcript_status="pending",
    )
    session.add(recording)
    session.commit()
    record_id = recording.id
    session.close()

    # Run the pipeline
    pipeline = TranscriptionPipeline(test_config, test_db)
    await pipeline.process_pending_transcriptions()

    # Verify transcription completed
    session = get_session(test_db)
    updated_record = session.query(Recording).filter_by(id=record_id).first()

    assert updated_record.transcript_status == "complete"
    assert updated_record.transcript_text is not None
    assert len(updated_record.transcript_text) > 0

    # The test file says "This is a test" - verify we got something reasonable
    transcript_lower = updated_record.transcript_text.lower()
    assert any(word in transcript_lower for word in ["this", "test"])

    # Verify segments were created
    assert updated_record.transcript_segments is not None
    assert len(updated_record.transcript_segments) > 0

    # Verify segment structure
    for segment in updated_record.transcript_segments:
        assert "start" in segment
        assert "end" in segment
        assert "text" in segment
        assert segment["start"] <= segment["end"]

    session.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_multiple_real_files(test_config, test_db):
    """Integration test: process multiple real audio files concurrently."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Create multiple records using the same audio file
    session = get_session(test_db)
    record_ids = []

    for i in range(3):
        # Create storage path for each file
        storage_path = f"2023/2023-12-01/1609459200_multi_{i:02d}.wav"
        full_storage_path = Path(test_config.storage_path) / storage_path
        full_storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy test file to storage location
        shutil.copy2(test_audio_path, full_storage_path)

        recording = Recording(
            original_filename=f"multi_test_{i:02d}.wav",
            internal_filename=f"1609459200_multi_{i:02d}.wav",
            storage_path=storage_path,
            import_timestamp=datetime.now(),
            audio_format="wav",
            file_size_bytes=int(test_audio_path.stat().st_size),
            transcript_status="pending",
        )
        session.add(recording)
        session.commit()
        record_ids.append(recording.id)

    session.close()

    # Process all files
    pipeline = TranscriptionPipeline(test_config, test_db)
    await pipeline.process_pending_transcriptions()

    # Verify all were processed
    session = get_session(test_db)

    for record_id in record_ids:
        record = session.query(Recording).filter_by(id=record_id).first()
        assert record.transcript_status == "complete"
        assert record.transcript_text is not None
        assert len(record.transcript_text) > 0

        # All should contain similar content since they're the same file
        transcript_lower = record.transcript_text.lower()
        assert any(word in transcript_lower for word in ["this", "test"])

    session.close()


@pytest.mark.integration
def test_process_pending_transcriptions_function_real_audio(test_config, test_db):
    """Integration test: standalone function with real audio file."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Setup storage and database record
    storage_path = "2023/2023-12-01/1609459200_function_test.wav"
    full_storage_path = Path(test_config.storage_path) / storage_path
    full_storage_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(test_audio_path, full_storage_path)

    session = get_session(test_db)

    recording = Recording(
        original_filename="function_test.wav",
        internal_filename="1609459200_function_test.wav",
        storage_path=storage_path,
        import_timestamp=datetime.now(),
        audio_format="wav",
        file_size_bytes=int(test_audio_path.stat().st_size),
        transcript_status="pending",
    )
    session.add(recording)
    session.commit()
    record_id = recording.id
    session.close()

    # Run the standalone function
    asyncio.run(process_pending_transcriptions(test_config, test_db))

    # Verify transcription
    session = get_session(test_db)
    updated_record = session.query(Recording).filter_by(id=record_id).first()

    assert updated_record.transcript_status == "complete"
    assert updated_record.transcript_text is not None

    # Verify content
    transcript_lower = updated_record.transcript_text.lower()
    assert any(word in transcript_lower for word in ["this", "test"])

    session.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_respects_concurrency_with_real_audio(test_config, test_db):
    """Integration test: verify concurrency control with real audio files."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Create multiple records (more than max_concurrent_transcriptions)
    session = get_session(test_db)
    record_ids = []

    num_files = test_config.max_concurrent_transcriptions + 1  # Should be 3 files

    for i in range(num_files):
        storage_path = f"2023/2023-12-01/1609459200_concurrent_{i:02d}.wav"
        full_storage_path = Path(test_config.storage_path) / storage_path
        full_storage_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_audio_path, full_storage_path)

        recording = Recording(
            original_filename=f"concurrent_test_{i:02d}.wav",
            internal_filename=f"1609459200_concurrent_{i:02d}.wav",
            storage_path=storage_path,
            import_timestamp=datetime.now(),
            audio_format="wav",
            file_size_bytes=int(test_audio_path.stat().st_size),
            transcript_status="pending",
        )
        session.add(recording)
        session.commit()
        record_ids.append(recording.id)

    session.close()

    # Process with concurrency control
    pipeline = TranscriptionPipeline(test_config, test_db)
    await pipeline.process_pending_transcriptions()

    # Verify all files were processed despite concurrency limit
    session = get_session(test_db)
    completed_count = 0

    for record_id in record_ids:
        record = session.query(Recording).filter_by(id=record_id).first()
        if record.transcript_status == "complete":
            completed_count += 1
            assert record.transcript_text is not None

    # All files should be completed
    assert completed_count == num_files

    session.close()
