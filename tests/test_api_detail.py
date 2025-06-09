# ABOUTME: Tests for API detail endpoints for recordings
# ABOUTME: Verifies GET /api/recordings/{id} and GET /api/recordings/{id}/segments

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from src.audio_manager.app import create_app
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording
from datetime import datetime


@pytest.fixture
def test_app_with_detailed_recordings():
    """Create test app with recordings that have detailed transcript data."""
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

        # Create sample recordings with transcript data
        session = get_session(db_path)
        try:
            now = datetime.now()

            # Recording with complete transcript
            complete_recording = Recording(
                original_filename="complete_transcript.wav",
                internal_filename="1609459200_complete_abcd1234.wav",
                storage_path="2021/01-01/1609459200_complete_abcd1234.wav",
                import_timestamp=now,
                duration_seconds=180.5,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=2048000,
                transcript_status="complete",
                transcript_language="en",
                transcript_text="Hello world. This is a test transcript. It has multiple sentences.",
                transcript_segments=[
                    {
                        "start": 0.0,
                        "end": 2.5,
                        "text": "Hello world.",
                        "confidence": 0.95,
                    },
                    {
                        "start": 2.5,
                        "end": 8.0,
                        "text": "This is a test transcript.",
                        "confidence": 0.92,
                    },
                    {
                        "start": 8.0,
                        "end": 12.0,
                        "text": "It has multiple sentences.",
                        "confidence": 0.88,
                    },
                ],
            )
            session.add(complete_recording)

            # Recording with pending transcript
            pending_recording = Recording(
                original_filename="pending_transcript.mp3",
                internal_filename="1609459200_pending_efgh5678.mp3",
                storage_path="2021/01-01/1609459200_pending_efgh5678.mp3",
                import_timestamp=now,
                duration_seconds=90.0,
                audio_format="mp3",
                sample_rate=22050,
                channels=1,
                file_size_bytes=1024000,
                transcript_status="pending",
            )
            session.add(pending_recording)

            # Recording with error status
            error_recording = Recording(
                original_filename="error_transcript.m4a",
                internal_filename="1609459200_error_ijkl9012.m4a",
                storage_path="2021/01-01/1609459200_error_ijkl9012.m4a",
                import_timestamp=now,
                duration_seconds=45.0,
                audio_format="m4a",
                sample_rate=48000,
                channels=2,
                file_size_bytes=512000,
                transcript_status="error",
            )
            session.add(error_recording)

            session.commit()
        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_api_recording_detail_complete(test_app_with_detailed_recordings):
    """Test GET /api/recordings/{id} for recording with complete transcript."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/1")

    assert response.status_code == 200
    data = response.json()

    # Check all expected fields are present
    expected_fields = [
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

    for field in expected_fields:
        assert field in data, f"Missing field: {field}"

    # Check specific values
    assert data["id"] == 1
    assert data["original_filename"] == "complete_transcript.wav"
    assert data["transcript_status"] == "complete"
    assert data["transcript_language"] == "en"
    assert (
        data["transcript_text"]
        == "Hello world. This is a test transcript. It has multiple sentences."
    )
    assert data["transcript_segments"] is not None
    assert len(data["transcript_segments"]) == 3

    # Check segments structure
    segment = data["transcript_segments"][0]
    assert segment["start"] == 0.0
    assert segment["end"] == 2.5
    assert segment["text"] == "Hello world."
    assert segment["confidence"] == 0.95


def test_api_recording_detail_pending(test_app_with_detailed_recordings):
    """Test GET /api/recordings/{id} for recording with pending transcript."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/2")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == 2
    assert data["original_filename"] == "pending_transcript.mp3"
    assert data["transcript_status"] == "pending"
    assert data["transcript_language"] is None
    assert data["transcript_text"] is None
    assert data["transcript_segments"] is None


def test_api_recording_detail_error(test_app_with_detailed_recordings):
    """Test GET /api/recordings/{id} for recording with error status."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/3")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == 3
    assert data["original_filename"] == "error_transcript.m4a"
    assert data["transcript_status"] == "error"
    assert data["transcript_language"] is None
    assert data["transcript_text"] is None
    assert data["transcript_segments"] is None


def test_api_recording_detail_not_found(test_app_with_detailed_recordings):
    """Test GET /api/recordings/{id} for non-existent recording."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/999")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_api_recording_segments_complete(test_app_with_detailed_recordings):
    """Test GET /api/recordings/{id}/segments for recording with segments."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/1/segments")

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "segments" in data
    assert "recording_id" in data
    assert "total_segments" in data

    assert data["recording_id"] == 1
    assert data["total_segments"] == 3

    segments = data["segments"]
    assert len(segments) == 3

    # Check first segment details
    segment = segments[0]
    expected_segment_fields = ["start", "end", "text", "confidence"]
    for field in expected_segment_fields:
        assert field in segment, f"Missing segment field: {field}"

    assert segment["start"] == 0.0
    assert segment["end"] == 2.5
    assert segment["text"] == "Hello world."
    assert segment["confidence"] == 0.95

    # Check segments are ordered by start time
    for i in range(len(segments) - 1):
        assert segments[i]["start"] <= segments[i + 1]["start"]


def test_api_recording_segments_no_transcript(test_app_with_detailed_recordings):
    """Test GET /api/recordings/{id}/segments for recording without transcript."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/2/segments")

    assert response.status_code == 200
    data = response.json()

    assert data["recording_id"] == 2
    assert data["total_segments"] == 0
    assert data["segments"] == []


def test_api_recording_segments_not_found(test_app_with_detailed_recordings):
    """Test GET /api/recordings/{id}/segments for non-existent recording."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/999/segments")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_api_recording_segments_invalid_id(test_app_with_detailed_recordings):
    """Test GET /api/recordings/{id}/segments with invalid ID format."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/invalid/segments")

    assert response.status_code == 422  # Validation error for invalid int


def test_api_recording_detail_field_types(test_app_with_detailed_recordings):
    """Test that API returns proper field types."""
    client, config, db_path = test_app_with_detailed_recordings

    response = client.get("/api/recordings/1")

    assert response.status_code == 200
    data = response.json()

    # Check field types
    assert isinstance(data["id"], int)
    assert isinstance(data["original_filename"], str)
    assert isinstance(data["duration_seconds"], float)
    assert isinstance(data["sample_rate"], int)
    assert isinstance(data["channels"], int)
    assert isinstance(data["file_size_bytes"], int)
    assert isinstance(data["transcript_status"], str)
    assert isinstance(data["transcript_text"], str)
    assert isinstance(data["transcript_segments"], list)

    # Check timestamp strings are ISO format
    assert "T" in data["import_timestamp"]
    assert "T" in data["created_at"]
    assert "T" in data["updated_at"]


def test_api_segments_response_format(test_app_with_detailed_recordings):
    """Test segments endpoint response format and data consistency."""
    client, config, db_path = test_app_with_detailed_recordings

    # Get recording detail first
    detail_response = client.get("/api/recordings/1")
    detail_data = detail_response.json()

    # Get segments
    segments_response = client.get("/api/recordings/1/segments")
    segments_data = segments_response.json()

    # Segments should match between detail and segments endpoints
    assert detail_data["transcript_segments"] == segments_data["segments"]
    assert len(detail_data["transcript_segments"]) == segments_data["total_segments"]


def test_api_recording_detail_metadata_consistency(test_app_with_detailed_recordings):
    """Test that detail endpoint metadata is consistent with list endpoint."""
    client, config, db_path = test_app_with_detailed_recordings

    # Get from list endpoint
    list_response = client.get("/api/recordings")
    list_data = list_response.json()
    recording_from_list = next(r for r in list_data["recordings"] if r["id"] == 1)

    # Get from detail endpoint
    detail_response = client.get("/api/recordings/1")
    detail_data = detail_response.json()

    # Common fields should match
    common_fields = [
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
        "created_at",
        "updated_at",
    ]

    for field in common_fields:
        assert recording_from_list[field] == detail_data[field], (
            f"Mismatch in field: {field}"
        )


def test_api_segments_empty_confidence_handling(test_app_with_detailed_recordings):
    """Test segments endpoint handles missing confidence values gracefully."""
    client, config, db_path = test_app_with_detailed_recordings

    # Add a recording with segments missing confidence
    session = get_session(db_path)
    try:
        recording = Recording(
            original_filename="no_confidence.wav",
            internal_filename="1609459200_noconf_xyz123.wav",
            storage_path="2021/01-01/1609459200_noconf_xyz123.wav",
            import_timestamp=datetime.now(),
            duration_seconds=30.0,
            audio_format="wav",
            sample_rate=16000,
            channels=1,
            file_size_bytes=256000,
            transcript_status="complete",
            transcript_segments=[
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Test without confidence.",
                    # No confidence field
                }
            ],
        )
        session.add(recording)
        session.commit()
        recording_id = recording.id
    finally:
        session.close()

    response = client.get(f"/api/recordings/{recording_id}/segments")

    assert response.status_code == 200
    data = response.json()

    segments = data["segments"]
    assert len(segments) == 1

    segment = segments[0]
    assert segment["start"] == 0.0
    assert segment["end"] == 5.0
    assert segment["text"] == "Test without confidence."
    # Confidence should be None or not present if missing
    assert segment.get("confidence") is None or "confidence" not in segment
