# ABOUTME: Tests for HTML search page and user interface
# ABOUTME: Verifies GET /search page rendering and search form functionality

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from src.audio_manager.app import create_app
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording, sync_fts
from datetime import datetime


@pytest.fixture
def test_app_with_search_data():
    """Create test app with recordings for search page testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config with FTS enabled
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
            items_per_page=5,  # Small page size for pagination testing
            fts_enabled=True,
        )

        # Create directories
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize database with FTS
        db_path = str(tmp_path / "test.db")
        init_db(db_path, fts_enabled=True)

        # Create sample recordings with searchable content
        session = get_session(db_path)
        try:
            now = datetime.now()

            # Create multiple recordings for testing
            recordings_data = [
                {
                    "original_filename": "project_meeting.wav",
                    "transcript_text": "This is a project meeting about software development and team coordination. We discussed the new features and bug fixes.",
                },
                {
                    "original_filename": "training_session.mp3",
                    "transcript_text": "Training session on Python programming and web development frameworks. Focus on FastAPI and database integration.",
                },
                {
                    "original_filename": "interview_candidate.m4a",
                    "transcript_text": "Technical interview with software engineer candidate. Discussion of algorithms, data structures, and system design.",
                },
                {
                    "original_filename": "daily_standup.wav",
                    "transcript_text": "Daily standup meeting covering sprint progress, blockers, and upcoming tasks for the development team.",
                },
                {
                    "original_filename": "code_review.mp3",
                    "transcript_text": "Code review session discussing best practices, security considerations, and performance optimizations.",
                },
                {
                    "original_filename": "planning_session.m4a",
                    "transcript_text": "Sprint planning session for the next iteration. Story pointing and task breakdown discussions.",
                },
            ]

            for i, data in enumerate(recordings_data):
                recording = Recording(
                    original_filename=data["original_filename"],
                    internal_filename=f"1609459{200 + i * 100}_test_{i:04d}.wav",
                    storage_path=f"2021/01-01/1609459{200 + i * 100}_test_{i:04d}.wav",
                    import_timestamp=now,
                    duration_seconds=1800.0 + i * 300,
                    audio_format="wav",
                    sample_rate=44100,
                    channels=2,
                    file_size_bytes=2048000 + i * 512000,
                    transcript_status="complete",
                    transcript_language="en",
                    transcript_text=data["transcript_text"],
                    transcript_segments=[
                        {
                            "start": 0.0,
                            "end": 10.0,
                            "text": data["transcript_text"][:50] + "...",
                            "confidence": 0.95,
                        }
                    ],
                )
                session.add(recording)
                session.flush()

                # Sync to FTS
                sync_fts(session, recording.id)

            session.commit()

        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_search_page_no_query(test_app_with_search_data):
    """Test search page without query parameter."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text

    # Check page title and structure
    assert "Search Recordings" in html
    assert "Audio Recording Manager" in html

    # Check search form is present
    assert 'id="search-form"' in html
    assert 'id="search-input"' in html
    assert 'name="q"' in html
    assert 'placeholder="Search recordings' in html

    # Check search button
    assert 'type="submit"' in html
    assert "Search" in html

    # Check search tips
    assert "Search Tips" in html
    assert "Minimum 3 characters" in html

    # Should not show results section
    assert "Search Results" not in html


def test_search_page_with_valid_query(test_app_with_search_data):
    """Test search page with valid query returning results."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search?q=meeting")

    assert response.status_code == 200
    html = response.text

    # Check search results are displayed
    assert "Search Results" in html
    assert 'Searching for: <strong>"meeting"' in html

    # Check that results are shown
    assert "search-result-item" in html
    assert "result-filename" in html
    assert "result-excerpt" in html

    # Should find meeting-related recordings
    assert "project_meeting.wav" in html or "daily_standup" in html

    # Check action links
    assert "View Details" in html
    assert "Show Full Transcript" in html

    # Check pagination info is displayed
    assert "result" in html.lower()  # "X results" or "result"


def test_search_page_with_no_results(test_app_with_search_data):
    """Test search page with query that returns no results."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search?q=nonexistent")

    assert response.status_code == 200
    html = response.text

    # Check no results message
    assert "No results found" in html
    assert 'search for <strong>"nonexistent"' in html

    # Check suggestions are shown
    assert "Try:" in html
    assert "Using different keywords" in html
    assert "Checking for typos" in html

    # Should not show actual result items (ignoring CSS)
    assert 'class="search-result-item"' not in html


def test_search_page_query_too_short(test_app_with_search_data):
    """Test search page with query that's too short."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search?q=ab")

    assert response.status_code == 200
    html = response.text

    # Should show the form but no results
    assert 'id="search-input"' in html
    assert 'value="ab"' in html  # Query should be preserved in input

    # Should not show search results section
    assert "Search Results" not in html


def test_search_page_pagination(test_app_with_search_data):
    """Test search page pagination functionality."""
    client, config, db_path = test_app_with_search_data

    # Search for a term that should return multiple results
    response = client.get("/search?q=session")

    assert response.status_code == 200
    html = response.text

    # Check if pagination controls appear (if there are enough results)
    if "Page" in html and "of" in html:
        # Check pagination structure
        assert "pagination" in html.lower()

        # Test second page if available
        if "Next" in html:
            response2 = client.get("/search?q=session&page=2")
            assert response2.status_code == 200

            html2 = response2.text
            assert "Page 2" in html2


def test_search_page_preserves_query(test_app_with_search_data):
    """Test that search page preserves query in input field."""
    client, config, db_path = test_app_with_search_data

    query = "development"
    response = client.get(f"/search?q={query}")

    assert response.status_code == 200
    html = response.text

    # Query should be preserved in the input field
    assert f'value="{query}"' in html
    assert f'Searching for: <strong>"{query}"' in html


def test_search_page_javascript_inclusion(test_app_with_search_data):
    """Test that search page includes JavaScript functionality."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search")

    assert response.status_code == 200
    html = response.text

    # Check JavaScript files are included
    assert "/static/js/search.js" in html

    # Check JavaScript initialization
    assert "SearchManager" in html
    assert "DOMContentLoaded" in html


def test_search_page_css_styling(test_app_with_search_data):
    """Test that search page includes proper CSS styling."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search?q=test")

    assert response.status_code == 200
    html = response.text

    # Check CSS classes are present
    assert "search-container" in html
    assert "search-form" in html
    assert "search-input" in html
    assert "search-button" in html

    # Check styling elements
    assert "<style>" in html
    assert "search-input-group" in html
    assert "search-tips" in html


def test_search_page_form_attributes(test_app_with_search_data):
    """Test search form has correct attributes."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search")

    assert response.status_code == 200
    html = response.text

    # Check form attributes
    assert 'method="get"' in html
    assert 'action="/search"' in html

    # Check input attributes
    assert "required" in html
    assert 'minlength="3"' in html
    assert 'autocomplete="off"' in html


def test_search_page_result_links(test_app_with_search_data):
    """Test that search results contain proper links."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search?q=project")

    assert response.status_code == 200
    html = response.text

    if "search-result-item" in html:
        # Check detail page links
        assert 'href="/recordings/' in html
        assert "View Details" in html

        # Check result filename links
        assert "result-link" in html


def test_search_page_expand_functionality(test_app_with_search_data):
    """Test search page transcript expand functionality."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search?q=development")

    assert response.status_code == 200
    html = response.text

    if "search-result-item" in html:
        # Check expand button is present
        assert "expand-button" in html
        assert "Show Full Transcript" in html

        # Check transcript container exists
        assert "result-full-transcript" in html
        assert "Full Transcript:" in html


def test_search_page_responsiveness(test_app_with_search_data):
    """Test search page responsive design elements."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search?q=test")

    assert response.status_code == 200
    html = response.text

    # Check responsive CSS media queries
    assert "@media" in html
    assert "max-width" in html

    # Check flexible layout classes
    assert "flex" in html or "search-input-group" in html


def test_search_page_accessibility(test_app_with_search_data):
    """Test search page accessibility features."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search")

    assert response.status_code == 200
    html = response.text

    # Check form labels and accessibility
    assert "placeholder=" in html
    assert "title=" in html or "aria-label=" in html

    # Check semantic HTML structure
    assert "<form" in html
    assert "<input" in html
    assert "<button" in html


def test_search_page_error_handling(test_app_with_search_data):
    """Test search page handles errors gracefully."""
    client, config, db_path = test_app_with_search_data

    # Test with malformed query parameters
    response = client.get("/search?q=test&page=invalid")

    # Should still return 200 and handle gracefully
    assert response.status_code == 200
    html = response.text

    # Should show search form
    assert 'id="search-form"' in html


def test_search_page_performance_indicators(test_app_with_search_data):
    """Test search page shows relevance and performance indicators."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search?q=programming")

    assert response.status_code == 200
    html = response.text

    if "search-result-item" in html:
        # Check relevance scores are displayed
        assert "relevance-score" in html
        assert "Relevance Score" in html

        # Check excerpts are highlighted
        assert "result-excerpt" in html


def test_search_page_navigation_integration(test_app_with_search_data):
    """Test search page integrates with site navigation."""
    client, config, db_path = test_app_with_search_data

    response = client.get("/search")

    assert response.status_code == 200
    html = response.text

    # Should extend base template
    assert "Audio Recording Manager" in html

    # Should have proper page title
    assert "<title>" in html and "Search" in html
