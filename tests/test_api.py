# ABOUTME: Tests for FastAPI web interface
# ABOUTME: Verifies web routes, templates, and audio serving functionality

import pytest
import shutil
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
        max_concurrent_transcriptions=2,
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
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "This is a sample",
                    "confidence": 0.95,
                },
                {
                    "start": 2.0,
                    "end": 5.0,
                    "text": "meeting transcript",
                    "confidence": 0.87,
                },
                {
                    "start": 5.0,
                    "end": 8.0,
                    "text": "with multiple sentences.",
                    "confidence": 0.92,
                },
            ],
        },
        {
            "original_filename": "voice_memo.mp3",
            "internal_filename": "1609459300_efgh5678.mp3",
            "storage_path": "2023/2023-12-01/1609459300_efgh5678.mp3",
            "duration_seconds": 45.2,
            "audio_format": "mp3",
            "transcript_status": "pending",
            "transcript_text": None,
            "transcript_segments": None,
        },
        {
            "original_filename": "interview.m4a",
            "internal_filename": "1609459400_ijkl9012.m4a",
            "storage_path": "2023/2023-12-02/1609459400_ijkl9012.m4a",
            "duration_seconds": 300.0,
            "audio_format": "m4a",
            "transcript_status": "error",
            "transcript_text": None,
            "transcript_segments": None,
        },
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
            transcript_segments=data["transcript_segments"],
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

    # Check that transcript text is displayed (either directly or in segments)
    assert "This is a sample meeting transcript" in content or (
        "This is a sample" in content and "meeting transcript" in content
    )

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
    assert isinstance(data, dict)
    assert "recordings" in data
    assert "pagination" in data

    recordings = data["recordings"]
    assert len(recordings) == 3

    # Check that we have the expected recordings (order may vary)
    filenames = [r["original_filename"] for r in recordings]
    assert "meeting_notes.wav" in filenames
    assert "voice_memo.mp3" in filenames
    assert "interview.m4a" in filenames

    # Find and check the completed recording
    completed_recording = next(
        r for r in recordings if r["transcript_status"] == "complete"
    )
    assert completed_recording["original_filename"] == "meeting_notes.wav"
    assert completed_recording["duration_seconds"] == 120.5


def test_recording_detail_json_api(test_client):
    """Test the JSON API endpoint for recording detail."""
    response = test_client.get("/api/recordings/1")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert data["original_filename"] == "meeting_notes.wav"
    assert (
        data["transcript_text"]
        == "This is a sample meeting transcript with multiple sentences."
    )
    assert len(data["transcript_segments"]) == 3


def test_recording_detail_json_api_not_found(test_client):
    """Test the JSON API endpoint for non-existent recording."""
    response = test_client.get("/api/recordings/999")

    assert response.status_code == 404

    data = response.json()
    assert "detail" in data


# Integration tests with real audio file
@pytest.mark.integration
def test_api_with_real_audio_file_complete_workflow(test_config, test_db_with_records):
    """Integration test: complete API workflow with real audio file."""
    # Get the real test audio file
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Create storage directory and copy real audio file
    storage_path = "2023/2023-12-01/1609459200_real_api_test.wav"
    full_storage_path = Path(test_config.storage_path) / storage_path
    full_storage_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(test_audio_path, full_storage_path)

    # Create a real database record with actual transcription
    session = get_session(test_db_with_records)

    # Add a record with real transcription data
    real_recording = Recording(
        original_filename="real_api_test.wav",
        internal_filename="1609459200_real_api_test.wav",
        storage_path=storage_path,
        import_timestamp=datetime.now(),
        duration_seconds=2.5,  # Approximate duration of test file
        audio_format="wav",
        sample_rate=16000,
        channels=1,
        file_size_bytes=int(test_audio_path.stat().st_size),
        transcript_status="complete",
        transcript_language="en",
        transcript_text="This is a test of the audio recording system.",
        transcript_segments=[
            {"start": 0.0, "end": 1.0, "text": "This is a test", "confidence": 0.95},
            {
                "start": 1.0,
                "end": 2.5,
                "text": "of the audio recording system.",
                "confidence": 0.87,
            },
        ],
    )
    session.add(real_recording)
    session.commit()
    real_record_id = real_recording.id
    session.close()

    # Create test client
    from src.audio_manager.app import create_app

    app = create_app(test_config, test_db_with_records)
    client = TestClient(app)

    # Test recordings list includes real recording
    response = client.get("/recordings")
    assert response.status_code == 200
    assert "real_api_test.wav" in response.text
    assert "complete" in response.text

    # Test individual recording detail page
    response = client.get(f"/recordings/{real_record_id}")
    assert response.status_code == 200
    assert "real_api_test.wav" in response.text
    # Check that transcript text is displayed (either directly or in segments)
    assert (
        "This is a test of the audio recording system." in response.text
        or "This is a test" in response.text
    )
    assert "controls" in response.text.lower()

    # Test audio file serving
    response = client.get(f"/audio/{storage_path}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/")

    # Verify actual audio content is served (check file size)
    content_length = len(response.content)
    expected_size = test_audio_path.stat().st_size
    assert content_length == expected_size

    # Test JSON API endpoints
    response = client.get("/api/recordings")
    assert response.status_code == 200
    data = response.json()
    recordings = data["recordings"]
    real_recordings = [
        r for r in recordings if r["original_filename"] == "real_api_test.wav"
    ]
    assert len(real_recordings) == 1

    real_record = real_recordings[0]
    assert real_record["transcript_status"] == "complete"

    # Test detail API endpoint for full transcript data
    response = client.get(f"/api/recordings/{real_record_id}")
    assert response.status_code == 200
    detail_data = response.json()
    assert (
        detail_data["transcript_text"]
        == "This is a test of the audio recording system."
    )
    assert len(detail_data["transcript_segments"]) == 2


@pytest.mark.integration
def test_api_audio_serving_real_file_security(test_config, test_db_with_records):
    """Integration test: verify audio serving security with real files."""
    # Create real audio file in storage
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    storage_path = "2023/2023-12-01/1609459200_security_test.wav"
    full_storage_path = Path(test_config.storage_path) / storage_path
    full_storage_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(test_audio_path, full_storage_path)

    # Create test client
    from src.audio_manager.app import create_app

    app = create_app(test_config, test_db_with_records)
    client = TestClient(app)

    # Test valid audio file serving
    response = client.get(f"/audio/{storage_path}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"

    # Test path traversal attack prevention
    response = client.get("/audio/../../../etc/passwd")
    assert response.status_code == 404 or response.status_code == 403

    # Test non-existent file
    response = client.get("/audio/2023/2023-12-01/nonexistent.wav")
    assert response.status_code == 404


@pytest.mark.integration
def test_api_transcription_workflow_integration(test_config, test_db_with_records):
    """Integration test: API display of transcription workflow stages."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Create multiple recordings in different states
    session = get_session(test_db_with_records)

    # Pending transcription
    pending_storage_path = "2023/2023-12-01/pending_test.wav"
    pending_full_path = Path(test_config.storage_path) / pending_storage_path
    pending_full_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(test_audio_path, pending_full_path)

    pending_record = Recording(
        original_filename="pending_test.wav",
        internal_filename="pending_test.wav",
        storage_path=pending_storage_path,
        import_timestamp=datetime.now(),
        audio_format="wav",
        file_size_bytes=int(test_audio_path.stat().st_size),
        transcript_status="pending",
    )
    session.add(pending_record)

    # Error transcription
    error_storage_path = "2023/2023-12-01/error_test.wav"
    error_full_path = Path(test_config.storage_path) / error_storage_path
    error_full_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(test_audio_path, error_full_path)

    error_record = Recording(
        original_filename="error_test.wav",
        internal_filename="error_test.wav",
        storage_path=error_storage_path,
        import_timestamp=datetime.now(),
        audio_format="wav",
        file_size_bytes=int(test_audio_path.stat().st_size),
        transcript_status="error",
    )
    session.add(error_record)

    session.commit()
    pending_id = pending_record.id
    error_id = error_record.id
    session.close()

    # Create test client
    from src.audio_manager.app import create_app

    app = create_app(test_config, test_db_with_records)
    client = TestClient(app)

    # Test recordings list shows different statuses
    response = client.get("/recordings")
    assert response.status_code == 200
    assert "pending_test.wav" in response.text
    assert "error_test.wav" in response.text
    assert "pending" in response.text
    assert "error" in response.text

    # Test pending recording detail page
    response = client.get(f"/recordings/{pending_id}")
    assert response.status_code == 200
    assert "pending_test.wav" in response.text
    assert (
        "Transcription in progress" in response.text
        or "pending" in response.text.lower()
    )

    # Test error recording detail page
    response = client.get(f"/recordings/{error_id}")
    assert response.status_code == 200
    assert "error_test.wav" in response.text
    assert "Transcription failed" in response.text or "error" in response.text.lower()

    # Both should still serve audio files
    response = client.get(f"/audio/{pending_storage_path}")
    assert response.status_code == 200

    response = client.get(f"/audio/{error_storage_path}")
    assert response.status_code == 200


@pytest.mark.integration
def test_api_large_audio_file_handling(test_config, test_db_with_records):
    """Integration test: API handling of larger audio file metadata."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Simulate a larger file by creating a record with larger metadata
    storage_path = "2023/2023-12-01/large_test.wav"
    full_storage_path = Path(test_config.storage_path) / storage_path
    full_storage_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(test_audio_path, full_storage_path)

    session = get_session(test_db_with_records)

    # Create very long transcript to test display
    long_transcript = "This is a test. " * 100  # 1600 characters
    many_segments = [
        {
            "start": i * 2.0,
            "end": (i + 1) * 2.0,
            "text": f"Segment {i + 1} content",
            "confidence": 0.9,
        }
        for i in range(50)  # 50 segments
    ]

    large_record = Recording(
        original_filename="large_test.wav",
        internal_filename="large_test.wav",
        storage_path=storage_path,
        import_timestamp=datetime.now(),
        duration_seconds=100.0,  # Long duration
        audio_format="wav",
        sample_rate=44100,  # High quality
        channels=2,  # Stereo
        file_size_bytes=int(test_audio_path.stat().st_size),
        transcript_status="complete",
        transcript_language="en",
        transcript_text=long_transcript,
        transcript_segments=many_segments,
    )
    session.add(large_record)
    session.commit()
    record_id = large_record.id
    session.close()

    # Create test client
    from src.audio_manager.app import create_app

    app = create_app(test_config, test_db_with_records)
    client = TestClient(app)

    # Test recordings list handles large metadata
    response = client.get("/recordings")
    assert response.status_code == 200
    assert "large_test.wav" in response.text
    assert "100.0s" in response.text  # Duration display

    # Test detail page handles long transcript
    response = client.get(f"/recordings/{record_id}")
    assert response.status_code == 200
    assert "large_test.wav" in response.text
    # Check that transcript text is displayed (either directly or through segments)
    assert (
        long_transcript in response.text
        or "This is a test" in response.text
        or "Segment 1 content" in response.text
    )

    # Should display segment table
    assert "Segment Details" in response.text
    assert "Segment 1 content" in response.text
    assert "Segment 50 content" in response.text

    # Test JSON API handles large data
    response = client.get(f"/api/recordings/{record_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["transcript_text"] == long_transcript
    assert len(data["transcript_segments"]) == 50
    assert data["duration_seconds"] == 100.0
    assert data["sample_rate"] == 44100
    assert data["channels"] == 2


@pytest.mark.integration
def test_api_file_serving_content_types(test_config, test_db_with_records):
    """Integration test: verify proper content types for different audio formats."""
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    # Test different file extensions with same content
    test_files = [
        ("test.wav", "audio/wav"),
        ("test.mp3", "audio/mp3"),
        ("test.m4a", "audio/m4a"),
    ]

    session = get_session(test_db_with_records)

    for filename, expected_content_type in test_files:
        storage_path = f"2023/2023-12-01/{filename}"
        full_storage_path = Path(test_config.storage_path) / storage_path
        full_storage_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_audio_path, full_storage_path)

        record = Recording(
            original_filename=filename,
            internal_filename=filename,
            storage_path=storage_path,
            import_timestamp=datetime.now(),
            audio_format=filename.split(".")[-1],
            file_size_bytes=int(test_audio_path.stat().st_size),
            transcript_status="pending",
        )
        session.add(record)

    session.commit()
    session.close()

    # Create test client
    from src.audio_manager.app import create_app

    app = create_app(test_config, test_db_with_records)
    client = TestClient(app)

    # Test each file serves with correct content type
    for filename, expected_content_type in test_files:
        storage_path = f"2023/2023-12-01/{filename}"
        response = client.get(f"/audio/{storage_path}")
        assert response.status_code == 200
        assert response.headers["content-type"] == expected_content_type
