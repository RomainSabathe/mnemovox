# ABOUTME: Tests for FastAPI web interface
# ABOUTME: Verifies web routes, templates, and audio serving functionality

import pytest
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording


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
def test_db_with_records(tmp_path, test_config):
    """Create a test database with sample recordings."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    
    session = get_session(str(db_path))
    
    # Create sample recordings
    recordings_data = [
        {
            "original_filename": "meeting_notes.wav",
            "internal_filename": "1609459200_abcd1234.wav",
            "storage_path": "2023/2023-12-01/1609459200_abcd1234.wav",
            "duration_seconds": 120.5,
            "audio_format": "wav",
            "transcript_status": "complete",
            "transcript_text": "This is a sample meeting transcript with multiple sentences.",
            "transcript_segments": [
                {"start": 0.0, "end": 2.0, "text": "This is a sample", "confidence": 0.95},
                {"start": 2.0, "end": 5.0, "text": "meeting transcript", "confidence": 0.87},
                {"start": 5.0, "end": 8.0, "text": "with multiple sentences.", "confidence": 0.92}
            ]
        },
        {
            "original_filename": "voice_memo.mp3",
            "internal_filename": "1609459300_efgh5678.mp3",
            "storage_path": "2023/2023-12-01/1609459300_efgh5678.mp3",
            "duration_seconds": 45.2,
            "audio_format": "mp3",
            "transcript_status": "pending",
            "transcript_text": None,
            "transcript_segments": None
        },
        {
            "original_filename": "interview.m4a",
            "internal_filename": "1609459400_ijkl9012.m4a",
            "storage_path": "2023/2023-12-02/1609459400_ijkl9012.m4a",
            "duration_seconds": 300.0,
            "audio_format": "m4a",
            "transcript_status": "error",
            "transcript_text": None,
            "transcript_segments": None
        }
    ]
    
    for data in recordings_data:
        # Create storage directory and dummy audio file
        full_storage_path = Path(test_config.storage_path) / data["storage_path"]
        full_storage_path.parent.mkdir(parents=True, exist_ok=True)
        full_storage_path.write_text("dummy audio content")
        
        recording = Recording(
            original_filename=data["original_filename"],
            internal_filename=data["internal_filename"],
            storage_path=data["storage_path"],
            import_timestamp=datetime.now(),
            duration_seconds=data["duration_seconds"],
            audio_format=data["audio_format"],
            sample_rate=16000,
            channels=1,
            file_size_bytes=1024,
            transcript_status=data["transcript_status"],
            transcript_text=data["transcript_text"],
            transcript_segments=data["transcript_segments"]
        )
        session.add(recording)
    
    session.commit()
    session.close()
    
    return str(db_path)


@pytest.fixture
def test_client(test_config, test_db_with_records):
    """Create a test client for the FastAPI app."""
    from src.audio_manager.app import create_app
    
    app = create_app(test_config, test_db_with_records)
    return TestClient(app)


def test_recordings_list_page(test_client):
    """Test that the recordings list page loads and displays recordings."""
    response = test_client.get("/recordings")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Check that recording filenames appear in the response
    content = response.text
    assert "meeting_notes.wav" in content
    assert "voice_memo.mp3" in content
    assert "interview.m4a" in content
    
    # Check that statuses are displayed
    assert "complete" in content
    assert "pending" in content
    assert "error" in content


def test_recordings_detail_page_complete(test_client):
    """Test the detail page for a completed recording."""
    response = test_client.get("/recordings/1")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    content = response.text
    # Check that original filename is displayed
    assert "meeting_notes.wav" in content
    
    # Check that transcript text is displayed
    assert "This is a sample meeting transcript" in content
    
    # Check that audio player is present
    assert "<audio" in content
    assert "controls" in content


def test_recordings_detail_page_pending(test_client):
    """Test the detail page for a pending recording."""
    response = test_client.get("/recordings/2")
    
    assert response.status_code == 200
    
    content = response.text
    assert "voice_memo.mp3" in content
    assert "Transcription in progress" in content or "pending" in content.lower()


def test_recordings_detail_page_error(test_client):
    """Test the detail page for a recording with transcription error."""
    response = test_client.get("/recordings/3")
    
    assert response.status_code == 200
    
    content = response.text
    assert "interview.m4a" in content
    assert "Transcription failed" in content or "error" in content.lower()


def test_recordings_detail_page_not_found(test_client):
    """Test the detail page for a non-existent recording."""
    response = test_client.get("/recordings/999")
    
    assert response.status_code == 404


def test_audio_file_serving(test_client):
    """Test that audio files are served correctly."""
    response = test_client.get("/audio/2023/2023-12-01/1609459200_abcd1234.wav")
    
    assert response.status_code == 200
    # Should serve the dummy audio content
    assert "dummy audio content" in response.text


def test_audio_file_not_found(test_client):
    """Test that missing audio files return 404."""
    response = test_client.get("/audio/nonexistent/file.wav")
    
    assert response.status_code == 404


def test_root_redirect(test_client):
    """Test that root path redirects to recordings list."""
    response = test_client.get("/", follow_redirects=False)
    
    assert response.status_code == 302
    assert "/recordings" in response.headers["location"]


def test_recordings_list_json_api(test_client):
    """Test the JSON API endpoint for recordings list."""
    response = test_client.get("/api/recordings")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    
    # Check that we have the expected recordings (order may vary)
    filenames = [r["original_filename"] for r in data]
    assert "meeting_notes.wav" in filenames
    assert "voice_memo.mp3" in filenames
    assert "interview.m4a" in filenames
    
    # Find and check the completed recording
    completed_recording = next(r for r in data if r["transcript_status"] == "complete")
    assert completed_recording["original_filename"] == "meeting_notes.wav"
    assert completed_recording["duration_seconds"] == 120.5


def test_recording_detail_json_api(test_client):
    """Test the JSON API endpoint for recording detail."""
    response = test_client.get("/api/recordings/1")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert data["original_filename"] == "meeting_notes.wav"
    assert data["transcript_text"] == "This is a sample meeting transcript with multiple sentences."
    assert len(data["transcript_segments"]) == 3


def test_recording_detail_json_api_not_found(test_client):
    """Test the JSON API endpoint for non-existent recording."""
    response = test_client.get("/api/recordings/999")
    
    assert response.status_code == 404
    
    data = response.json()
    assert "detail" in data