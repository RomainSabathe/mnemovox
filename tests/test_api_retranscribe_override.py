# ABOUTME: Tests for API endpoint that accepts transcription model and language overrides
# ABOUTME: Verifies POST /api/recordings/{id}/transcribe with override parameters

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from src.audio_manager.app import create_app
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create test client with temporary database and config."""
    # Create test config
    config = Config(
        monitored_directory=str(tmp_path / "incoming"),
        storage_path=str(tmp_path / "storage"),
        upload_temp_path=str(tmp_path / "uploads"),
        whisper_model="base.en",
        default_language="en",
        sample_rate=16000,
        max_concurrent_transcriptions=2,
        fts_enabled=True,
        items_per_page=20,
    )

    # Create directories
    (tmp_path / "incoming").mkdir()
    (tmp_path / "storage").mkdir()
    (tmp_path / "uploads").mkdir()

    # Initialize database
    db_path = str(tmp_path / "test.db")
    init_db(db_path, fts_enabled=True)

    # Create test app
    app = create_app(config, db_path)

    return TestClient(app)


def test_retranscribe_with_valid_overrides(client, tmp_path, monkeypatch):
    """Test POST with valid model and language overrides updates DB columns."""

    # Mock the background task to prevent actual transcription
    def mock_background_task(*args, **kwargs):
        pass

    monkeypatch.setattr(
        "src.audio_manager.app.run_transcription_task", mock_background_task
    )

    # Create a test recording
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Old transcript",
        transcript_language="en",
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Send POST request with overrides
    response = client.post(
        f"/api/recordings/{recording_id}/transcribe",
        json={"model": "small", "language": "fr"},
    )

    assert response.status_code in [200, 202]
    data = response.json()
    assert data["id"] == recording_id
    assert data["status"] == "pending"

    # Verify DB columns were updated
    session = get_session(db_path)
    updated_recording = session.query(Recording).filter_by(id=recording_id).first()
    assert updated_recording.transcription_model == "small"
    assert updated_recording.transcription_language == "fr"
    assert updated_recording.transcript_status == "pending"
    session.close()


def test_retranscribe_with_invalid_model(client, tmp_path):
    """Test POST with invalid model returns 400 error."""
    # Create a test recording
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Old transcript",
        transcript_language="en",
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Send POST request with invalid model
    response = client.post(
        f"/api/recordings/{recording_id}/transcribe",
        json={"model": "invalid_model", "language": "en"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "Invalid model" in data["detail"]


def test_retranscribe_with_invalid_language(client, tmp_path):
    """Test POST with invalid language returns 400 error."""
    # Create a test recording
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Old transcript",
        transcript_language="en",
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Send POST request with invalid language
    response = client.post(
        f"/api/recordings/{recording_id}/transcribe",
        json={"model": "base", "language": "invalid_lang"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "Invalid language" in data["detail"]


def test_retranscribe_nonexistent_recording(client, tmp_path):
    """Test POST to non-existent recording returns 404."""
    response = client.post(
        "/api/recordings/99999/transcribe", json={"model": "base", "language": "en"}
    )

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Recording not found"


def test_retranscribe_without_overrides_uses_defaults(client, tmp_path, monkeypatch):
    """Test POST without overrides uses global defaults."""

    # Mock the background task to prevent actual transcription
    def mock_background_task(*args, **kwargs):
        pass

    monkeypatch.setattr(
        "src.audio_manager.app.run_transcription_task", mock_background_task
    )

    # Create a test recording
    db_path = str(tmp_path / "test.db")
    session = get_session(db_path)

    recording = Recording(
        original_filename="test.wav",
        internal_filename="20231201_12345678.wav",
        storage_path="2023/12-01/20231201_12345678.wav",
        import_timestamp=datetime.now(),
        duration_seconds=30.0,
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=1024,
        transcript_status="complete",
        transcript_text="Old transcript",
        transcript_language="en",
    )

    session.add(recording)
    session.commit()
    recording_id = recording.id
    session.close()

    # Send POST request without overrides (empty JSON)
    response = client.post(f"/api/recordings/{recording_id}/transcribe", json={})

    assert response.status_code in [200, 202]
    data = response.json()
    assert data["id"] == recording_id
    assert data["status"] == "pending"

    # Verify DB columns remain null (use global defaults)
    session = get_session(db_path)
    updated_recording = session.query(Recording).filter_by(id=recording_id).first()
    assert updated_recording.transcription_model is None
    assert updated_recording.transcription_language is None
    assert updated_recording.transcript_status == "pending"
    session.close()
