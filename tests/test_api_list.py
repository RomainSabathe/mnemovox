# ABOUTME: Tests for API listings endpoint with pagination
# ABOUTME: Verifies GET /api/recordings with page/per_page query parameters

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from mnemovox.app import create_app
from mnemovox.config import Config
from mnemovox.db import init_db, get_session, Recording
from datetime import datetime


@pytest.fixture
def test_app_with_recordings():
    """Create test app with sample recordings in database."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
            items_per_page=3,  # Small page size for testing
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
            for i in range(10):  # Create 10 test recordings
                recording = Recording(
                    original_filename=f"test_recording_{i:02d}.wav",
                    internal_filename=f"1609459200_{i:02d}_abcd1234.wav",
                    storage_path=f"2021/01-01/1609459200_{i:02d}_abcd1234.wav",
                    import_timestamp=now,
                    duration_seconds=120.5 + i,
                    audio_format="wav",
                    sample_rate=44100,
                    channels=2,
                    file_size_bytes=1024 * (i + 1),
                    transcript_status="pending",
                )
                session.add(recording)
            session.commit()
        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_api_recordings_list_default_pagination(test_app_with_recordings):
    """Test GET /api/recordings with default pagination."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/api/recordings")

    assert response.status_code == 200
    data = response.json()

    # Should return structure with pagination info
    assert "recordings" in data
    assert "pagination" in data

    # Check pagination metadata
    pagination = data["pagination"]
    assert pagination["page"] == 1
    assert pagination["per_page"] == config.items_per_page
    assert pagination["total"] == 10
    assert pagination["pages"] == 4  # 10 items / 3 per page = 4 pages
    assert pagination["has_prev"] is False
    assert pagination["has_next"] is True

    # Check recordings data
    recordings = data["recordings"]
    assert len(recordings) == config.items_per_page  # First page

    # Should be ordered by import_timestamp desc (most recent first)
    assert recordings[0]["original_filename"] == "test_recording_09.wav"
    assert recordings[1]["original_filename"] == "test_recording_08.wav"
    assert recordings[2]["original_filename"] == "test_recording_07.wav"


def test_api_recordings_list_custom_pagination(test_app_with_recordings):
    """Test GET /api/recordings with custom page and per_page parameters."""
    client, config, db_path = test_app_with_recordings

    # Request page 2 with 4 items per page
    response = client.get("/api/recordings?page=2&per_page=4")

    assert response.status_code == 200
    data = response.json()

    # Check pagination metadata
    pagination = data["pagination"]
    assert pagination["page"] == 2
    assert pagination["per_page"] == 4
    assert pagination["total"] == 10
    assert pagination["pages"] == 3  # 10 items / 4 per page = 3 pages
    assert pagination["has_prev"] is True
    assert pagination["has_next"] is True

    # Check recordings data (should be items 5-8, 0-indexed)
    recordings = data["recordings"]
    assert len(recordings) == 4
    assert recordings[0]["original_filename"] == "test_recording_05.wav"
    assert recordings[1]["original_filename"] == "test_recording_04.wav"
    assert recordings[2]["original_filename"] == "test_recording_03.wav"
    assert recordings[3]["original_filename"] == "test_recording_02.wav"


def test_api_recordings_list_last_page(test_app_with_recordings):
    """Test GET /api/recordings on the last page."""
    client, config, db_path = test_app_with_recordings

    # Request last page with default per_page (3)
    response = client.get("/api/recordings?page=4")

    assert response.status_code == 200
    data = response.json()

    # Check pagination metadata
    pagination = data["pagination"]
    assert pagination["page"] == 4
    assert pagination["per_page"] == config.items_per_page
    assert pagination["total"] == 10
    assert pagination["pages"] == 4
    assert pagination["has_prev"] is True
    assert pagination["has_next"] is False

    # Check recordings data (should be only 1 item on last page)
    recordings = data["recordings"]
    assert len(recordings) == 1
    assert recordings[0]["original_filename"] == "test_recording_00.wav"


def test_api_recordings_list_page_out_of_bounds(test_app_with_recordings):
    """Test GET /api/recordings with page number beyond available data."""
    client, config, db_path = test_app_with_recordings

    # Request page that doesn't exist
    response = client.get("/api/recordings?page=10")

    assert response.status_code == 200
    data = response.json()

    # Should return empty results but valid pagination
    recordings = data["recordings"]
    assert len(recordings) == 0

    pagination = data["pagination"]
    assert pagination["page"] == 10
    assert pagination["total"] == 10
    assert pagination["has_prev"] is True
    assert pagination["has_next"] is False


def test_api_recordings_list_invalid_parameters(test_app_with_recordings):
    """Test GET /api/recordings with invalid pagination parameters."""
    client, config, db_path = test_app_with_recordings

    # Test invalid page (negative)
    response = client.get("/api/recordings?page=-1")
    assert response.status_code == 400
    error_data = response.json()
    assert "error" in error_data["detail"]
    assert "page" in error_data["detail"]["error"].lower()

    # Test invalid per_page (negative)
    response = client.get("/api/recordings?per_page=-5")
    assert response.status_code == 400
    error_data = response.json()
    assert "error" in error_data["detail"]
    assert "per_page" in error_data["detail"]["error"].lower()

    # Test per_page too large
    response = client.get("/api/recordings?per_page=1000")
    assert response.status_code == 400
    error_data = response.json()
    assert "error" in error_data["detail"]
    assert "per_page" in error_data["detail"]["error"].lower()


def test_api_recordings_list_zero_page(test_app_with_recordings):
    """Test GET /api/recordings with page=0."""
    client, config, db_path = test_app_with_recordings

    # Page 0 should be treated as page 1
    response = client.get("/api/recordings?page=0")

    assert response.status_code == 200
    data = response.json()

    # Should return first page
    pagination = data["pagination"]
    assert pagination["page"] == 1
    assert pagination["has_prev"] is False
    assert pagination["has_next"] is True


def test_api_recordings_list_empty_database():
    """Test GET /api/recordings with no recordings in database."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            storage_path=str(tmp_path / "storage"),
            items_per_page=10,
        )

        # Initialize empty database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        response = client.get("/api/recordings")

        assert response.status_code == 200
        data = response.json()

        # Should return empty results
        assert data["recordings"] == []

        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["per_page"] == 10
        assert pagination["total"] == 0
        assert pagination["pages"] == 0
        assert pagination["has_prev"] is False
        assert pagination["has_next"] is False


def test_api_recordings_list_recording_fields(test_app_with_recordings):
    """Test that each recording in the list contains expected fields."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/api/recordings?per_page=1")

    assert response.status_code == 200
    data = response.json()

    recordings = data["recordings"]
    assert len(recordings) == 1

    recording = recordings[0]

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
        "created_at",
        "updated_at",
    ]

    for field in expected_fields:
        assert field in recording, f"Missing field: {field}"

    # Check field types and values
    assert isinstance(recording["id"], int)
    assert isinstance(recording["original_filename"], str)
    assert isinstance(recording["duration_seconds"], float)
    assert recording["transcript_status"] == "pending"


def test_api_recordings_list_consistent_ordering(test_app_with_recordings):
    """Test that pagination maintains consistent ordering across pages."""
    client, config, db_path = test_app_with_recordings

    # Get all recordings across multiple pages
    all_recordings = []

    # Get first 3 pages (should cover all 10 recordings)
    for page in [1, 2, 3, 4]:
        response = client.get(f"/api/recordings?page={page}&per_page=3")
        assert response.status_code == 200
        data = response.json()
        all_recordings.extend(data["recordings"])

    # Should have all 10 recordings
    assert len(all_recordings) == 10

    # Check ordering is consistent (by import_timestamp desc, then by id desc)
    filenames = [r["original_filename"] for r in all_recordings]
    expected_order = [f"test_recording_{i:02d}.wav" for i in range(9, -1, -1)]
    assert filenames == expected_order
