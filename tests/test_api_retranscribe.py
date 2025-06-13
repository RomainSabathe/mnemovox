# ABOUTME: Tests for re-transcription API endpoint
# ABOUTME: Verifies POST /api/recordings/{id}/transcribe endpoint functionality

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.audio_manager.app import create_app
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording
from datetime import datetime


@pytest.fixture
def test_app_with_recordings():
    """Create test app with sample recordings for re-transcription testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
            items_per_page=20,
        )

        # Create directories
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create sample recordings
        session = get_session(db_path)
        try:
            now = datetime.now()

            # Recording with complete transcript
            complete_recording = Recording(
                original_filename="completed_recording.wav",
                internal_filename="1609459200_complete_abcd1234.wav",
                storage_path="2021/01-01/1609459200_complete_abcd1234.wav",
                import_timestamp=now,
                duration_seconds=30.0,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=1536000,
                transcript_status="complete",
                transcript_language="en",
                transcript_text="This is a completed transcript.",
                transcript_segments=[
                    {
                        "start": 0.0,
                        "end": 5.0,
                        "text": "This is a completed transcript.",
                        "confidence": 0.95,
                    }
                ],
            )
            session.add(complete_recording)

            # Recording with error status
            error_recording = Recording(
                original_filename="error_recording.mp3",
                internal_filename="1609459200_error_efgh5678.mp3",
                storage_path="2021/01-01/1609459200_error_efgh5678.mp3",
                import_timestamp=now,
                duration_seconds=45.0,
                audio_format="mp3",
                sample_rate=22050,
                channels=1,
                file_size_bytes=1024000,
                transcript_status="error",
            )
            session.add(error_recording)

            # Recording with pending status
            pending_recording = Recording(
                original_filename="pending_recording.m4a",
                internal_filename="1609459200_pending_ijkl9012.m4a",
                storage_path="2021/01-01/1609459200_pending_ijkl9012.m4a",
                import_timestamp=now,
                duration_seconds=60.0,
                audio_format="m4a",
                sample_rate=48000,
                channels=2,
                file_size_bytes=2048000,
                transcript_status="pending",
            )
            session.add(pending_recording)

            session.commit()
        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_retranscribe_completed_recording(test_app_with_recordings):
    """Test re-transcription of a completed recording."""
    client, config, db_path = test_app_with_recordings

    # Verify initial state
    session = get_session(db_path)
    try:
        recording = session.query(Recording).filter_by(id=1).first()
        assert recording.transcript_status == "complete"
        assert recording.transcript_text == "This is a completed transcript."
    finally:
        session.close()

    # Request re-transcription
    response = client.post("/api/recordings/1/transcribe")

    assert response.status_code == 200
    data = response.json()

    # Check response format
    assert "id" in data
    assert "status" in data
    assert "message" in data

    assert data["id"] == 1
    assert data["status"] == "pending"
    assert "queued for re-transcription" in data["message"]

    # Verify database was updated initially (transcript data cleared)
    session = get_session(db_path)
    try:
        recording = session.query(Recording).filter_by(id=1).first()
        # The API should have cleared the transcript data and set to pending
        assert recording.transcript_text is None
        assert recording.transcript_segments is None
        assert recording.transcript_language is None

        # After the background task runs, it will try to transcribe but fail
        # due to missing file, so status will be "error" instead of "pending"
        # This is expected behavior with the new implementation
        assert recording.transcript_status in ["pending", "error"]

    finally:
        session.close()


def test_retranscribe_error_recording(test_app_with_recordings):
    """Test re-transcription of a recording with error status."""
    client, config, db_path = test_app_with_recordings

    # Verify initial state
    session = get_session(db_path)
    try:
        recording = session.query(Recording).filter_by(id=2).first()
        assert recording.transcript_status == "error"
    finally:
        session.close()

    # Request re-transcription
    response = client.post("/api/recordings/2/transcribe")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == 2
    assert data["status"] == "pending"

    # Verify database was updated
    session = get_session(db_path)
    try:
        recording = session.query(Recording).filter_by(id=2).first()
        # After background task runs, transcription will fail due to missing file
        assert recording.transcript_status in ["pending", "error"]
    finally:
        session.close()


def test_retranscribe_pending_recording(test_app_with_recordings):
    """Test re-transcription of a recording that's already pending."""
    client, config, db_path = test_app_with_recordings

    # Request re-transcription of already pending recording
    response = client.post("/api/recordings/3/transcribe")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == 3
    assert data["status"] == "pending"
    assert (
        "already pending" in data["message"].lower()
        or "queued for re-transcription" in data["message"]
    )


def test_retranscribe_nonexistent_recording(test_app_with_recordings):
    """Test re-transcription of non-existent recording."""
    client, config, db_path = test_app_with_recordings

    response = client.post("/api/recordings/999/transcribe")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_retranscribe_invalid_id_format(test_app_with_recordings):
    """Test re-transcription with invalid ID format."""
    client, config, db_path = test_app_with_recordings

    response = client.post("/api/recordings/invalid/transcribe")

    assert response.status_code == 422  # Validation error for invalid int


def test_retranscribe_background_task_integration(test_app_with_recordings):
    """Test that background task is properly queued for transcription."""
    client, config, db_path = test_app_with_recordings

    # Mock the background task function directly to prevent actual execution
    with patch("src.audio_manager.app.run_transcription_task") as mock_task:
        response = client.post("/api/recordings/1/transcribe")

        assert response.status_code == 200

        # Verify background task was called with correct arguments
        # Note: FastAPI's BackgroundTasks runs the task immediately in tests
        # so we should see it called once
        mock_task.assert_called_once_with(1, db_path)


def test_retranscribe_response_format(test_app_with_recordings):
    """Test that response has correct format and content."""
    client, config, db_path = test_app_with_recordings

    response = client.post("/api/recordings/1/transcribe")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # Check required fields
    required_fields = ["id", "status", "message"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Check data types
    assert isinstance(data["id"], int)
    assert isinstance(data["status"], str)
    assert isinstance(data["message"], str)

    # Check status value
    assert data["status"] in ["pending", "complete", "error"]


def test_retranscribe_database_transaction_consistency(test_app_with_recordings):
    """Test that database updates are consistent and atomic."""
    client, config, db_path = test_app_with_recordings

    # Get initial state
    session = get_session(db_path)
    try:
        initial_recording = session.query(Recording).filter_by(id=1).first()
        initial_status = initial_recording.transcript_status
        initial_text = initial_recording.transcript_text
        initial_updated_at = initial_recording.updated_at
    finally:
        session.close()

    # Request re-transcription
    response = client.post("/api/recordings/1/transcribe")
    assert response.status_code == 200

    # Verify consistent state change
    session = get_session(db_path)
    try:
        updated_recording = session.query(Recording).filter_by(id=1).first()

        # Status should be updated
        assert updated_recording.transcript_status in ["pending", "error"]
        assert updated_recording.transcript_status != initial_status

        # Transcript data should be cleared for re-processing
        if initial_text is not None:
            assert updated_recording.transcript_text is None
            assert updated_recording.transcript_segments is None
            assert updated_recording.transcript_language is None

        # updated_at should be changed
        assert updated_recording.updated_at != initial_updated_at

        # Other metadata should remain unchanged
        assert (
            updated_recording.original_filename == initial_recording.original_filename
        )
        assert updated_recording.storage_path == initial_recording.storage_path
        assert updated_recording.duration_seconds == initial_recording.duration_seconds
    finally:
        session.close()


def test_retranscribe_concurrent_requests(test_app_with_recordings):
    """Test handling of concurrent re-transcription requests."""
    client, config, db_path = test_app_with_recordings

    # Send multiple requests for the same recording
    responses = []
    for _ in range(3):
        response = client.post("/api/recordings/1/transcribe")
        responses.append(response)

    # All requests should succeed
    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"

    # Final state should be consistent
    session = get_session(db_path)
    try:
        recording = session.query(Recording).filter_by(id=1).first()
        # After background task runs, transcription will fail due to missing file
        assert recording.transcript_status in ["pending", "error"]
    finally:
        session.close()


def test_retranscribe_preserves_metadata(test_app_with_recordings):
    """Test that re-transcription preserves audio metadata."""
    client, config, db_path = test_app_with_recordings

    # Get initial metadata
    session = get_session(db_path)
    try:
        initial_recording = session.query(Recording).filter_by(id=1).first()
        initial_metadata = {
            "original_filename": initial_recording.original_filename,
            "internal_filename": initial_recording.internal_filename,
            "storage_path": initial_recording.storage_path,
            "import_timestamp": initial_recording.import_timestamp,
            "duration_seconds": initial_recording.duration_seconds,
            "audio_format": initial_recording.audio_format,
            "sample_rate": initial_recording.sample_rate,
            "channels": initial_recording.channels,
            "file_size_bytes": initial_recording.file_size_bytes,
        }
    finally:
        session.close()

    # Request re-transcription
    response = client.post("/api/recordings/1/transcribe")
    assert response.status_code == 200

    # Verify metadata is preserved
    session = get_session(db_path)
    try:
        updated_recording = session.query(Recording).filter_by(id=1).first()

        for field, expected_value in initial_metadata.items():
            actual_value = getattr(updated_recording, field)
            assert actual_value == expected_value, (
                f"Metadata field {field} changed during re-transcription"
            )
    finally:
        session.close()
