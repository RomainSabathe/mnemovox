# ABOUTME: Tests for HTML recordings list page with pagination
# ABOUTME: Verifies GET /recordings returns proper HTML with pagination UI

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
            for i in range(7):  # Create 7 test recordings (3 pages with 3 per page)
                recording = Recording(
                    original_filename=f"test_recording_{i:02d}.wav",
                    internal_filename=f"1609459200_{i:02d}_abcd1234.wav",
                    storage_path=f"2021/01-01/1609459200_{i:02d}_abcd1234.wav",
                    import_timestamp=now,
                    duration_seconds=120.5 + i,
                    audio_format="wav",
                    sample_rate=44100,
                    channels=2,
                    file_size_bytes=1024 * 1024 * (i + 1),  # 1MB, 2MB, etc.
                    transcript_status="complete" if i % 2 == 0 else "pending",
                )
                session.add(recording)
            session.commit()
        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_recordings_list_page_loads(test_app_with_recordings):
    """Test that GET /recordings returns valid HTML."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")

    html = response.text

    # Check basic HTML structure
    assert "<!DOCTYPE html>" in html
    assert "<title>" in html
    assert "Audio Recording Manager" in html

    # Check for recordings table
    assert "<table>" in html
    assert "<th>Filename</th>" in html
    assert "<th>Duration</th>" in html
    assert "<th>Status</th>" in html

    # Should show recordings
    assert "test_recording_" in html


def test_recordings_list_page_pagination_ui(test_app_with_recordings):
    """Test that pagination UI elements are present."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings")

    assert response.status_code == 200
    html = response.text

    # Check pagination info
    assert "Page 1 of" in html
    assert "recordings total" in html
    assert "<strong>7</strong>" in html

    # Check pagination controls (should have Next link but no Previous on first page)
    assert "Next &raquo;" in html
    assert "&laquo; Previous" in html  # Should be disabled/grayed out

    # Check page numbers
    assert "?page=2" in html


def test_recordings_list_page_second_page(test_app_with_recordings):
    """Test navigation to second page."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings?page=2")

    assert response.status_code == 200
    html = response.text

    # Check pagination info
    assert "Page 2 of" in html

    # Check pagination controls (should have both Previous and Next)
    assert "Next &raquo;" in html
    assert "&laquo; Previous" in html
    assert "?page=1" in html  # Previous link
    assert "?page=3" in html  # Next link


def test_recordings_list_page_last_page(test_app_with_recordings):
    """Test last page pagination."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings?page=3")

    assert response.status_code == 200
    html = response.text

    # Check pagination info
    assert "Page 3 of" in html

    # Should have Previous but no Next
    assert "&laquo; Previous" in html
    assert "?page=2" in html  # Previous link

    # Should show only 1 recording on last page
    assert "Showing 1 of 7 recordings" in html


def test_recordings_list_page_empty_database():
    """Test recordings list page with no recordings."""
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

        response = client.get("/recordings")

        assert response.status_code == 200
        html = response.text

        # Should show empty state
        assert "No recordings found" in html
        assert "Upload Your First Recording" in html
        assert "/recordings/upload" in html


def test_recordings_list_page_recording_details(test_app_with_recordings):
    """Test that recording details are displayed correctly."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings")

    assert response.status_code == 200
    html = response.text

    # Check for recording details
    assert "test_recording_06.wav" in html  # Most recent should be first
    assert "WAV" in html  # Format should be uppercase
    assert "Complete" in html or "Pending" in html  # Status should be title case

    # Check for file sizes (should show MB for larger files)
    assert "MB" in html

    # Check for View Details links
    assert "View Details" in html
    assert "/recordings/" in html


def test_recordings_list_page_upload_button(test_app_with_recordings):
    """Test that upload button is present."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings")

    assert response.status_code == 200
    html = response.text

    # Check for upload button
    assert "Upload New Recording" in html
    assert "/recordings/upload" in html


def test_recordings_list_page_navigation_links(test_app_with_recordings):
    """Test that navigation links work correctly."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings")

    assert response.status_code == 200
    html = response.text

    # Check for navigation
    assert "All Recordings" in html


def test_recordings_list_page_status_styling(test_app_with_recordings):
    """Test that status indicators have proper CSS classes."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings")

    assert response.status_code == 200
    html = response.text

    # Check for status CSS classes
    assert 'class="status complete"' in html or 'class="status pending"' in html


def test_recordings_list_page_responsive_design(test_app_with_recordings):
    """Test that page includes responsive design elements."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings")

    assert response.status_code == 200
    html = response.text

    # Check for responsive viewport meta tag
    assert 'name="viewport"' in html
    assert "width=device-width" in html


def test_recordings_list_page_invalid_page_number(test_app_with_recordings):
    """Test page with invalid page number."""
    client, config, db_path = test_app_with_recordings

    # Test page 0 (should redirect to page 1)
    response = client.get("/recordings?page=0")
    assert response.status_code == 200
    html = response.text
    assert "Page 1 of" in html

    # Test negative page (should redirect to page 1)
    response = client.get("/recordings?page=-5")
    assert response.status_code == 200
    html = response.text
    assert "Page 1 of" in html

    # Test page beyond available (should show empty results but still be valid)
    response = client.get("/recordings?page=999")
    assert response.status_code == 200
    html = response.text
    # When no recordings are returned, template shows empty state
    assert "No recordings found" in html


def test_recordings_list_page_single_page():
    """Test recordings list when all recordings fit on one page."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config with large page size
        config = Config(
            storage_path=str(tmp_path / "storage"),
            items_per_page=20,  # Much larger than our test data
        )

        # Initialize database with few recordings
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        session = get_session(db_path)
        try:
            now = datetime.now()
            for i in range(3):  # Only 3 recordings
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

        response = client.get("/recordings")

        assert response.status_code == 200
        html = response.text

        # Should not show pagination controls when everything fits on one page
        assert "Page 1 of 1" in html
        assert "Next &raquo;" not in html
        assert "&laquo; Previous" not in html


def test_recordings_list_page_search_button(test_app_with_recordings):
    """Test that search button/link is present on recordings list page."""
    client, config, db_path = test_app_with_recordings

    response = client.get("/recordings")

    assert response.status_code == 200
    html = response.text

    # Check for search button/link
    assert "Search" in html
    assert "/search" in html
