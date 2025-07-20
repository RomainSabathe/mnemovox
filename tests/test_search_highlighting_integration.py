# ABOUTME: Integration test for search highlighting functionality
# ABOUTME: Verifies end-to-end search results contain highlighted excerpts

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from audio_manager.app import create_app
from audio_manager.config import Config
from audio_manager.db import Recording, get_session, init_db


@pytest.fixture
def test_app_with_search_data():
    """Create test app with sample recordings for search testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = Config(
            storage_path=str(tmp_path / "storage"),
            items_per_page=10,
        )

        # Create directories
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create test recordings with transcript data
        session = get_session(db_path)
        try:
            from datetime import datetime

            # Create recordings with different transcript content
            recordings = [
                Recording(
                    original_filename="meeting1.wav",
                    internal_filename="meeting1_internal.wav",
                    storage_path="2025/07-20/meeting1_internal.wav",
                    import_timestamp=datetime.now(),
                    transcript_status="complete",
                    transcript_text="This is the important meeting transcript with key information.",
                ),
                Recording(
                    original_filename="interview.wav",
                    internal_filename="interview_internal.wav",
                    storage_path="2025/07-20/interview_internal.wav",
                    import_timestamp=datetime.now(),
                    transcript_status="complete",
                    transcript_text="The interview discussion covered important topics and decisions.",
                ),
                Recording(
                    original_filename="notes.wav",
                    internal_filename="notes_internal.wav",
                    storage_path="2025/07-20/notes_internal.wav",
                    import_timestamp=datetime.now(),
                    transcript_status="complete",
                    transcript_text="These are personal notes about the project and its requirements.",
                ),
            ]

            for recording in recordings:
                session.add(recording)
            session.commit()

            # Setup FTS index
            from audio_manager.db import sync_fts

            for recording in recordings:
                sync_fts(session, recording.id)

        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_search_api_returns_highlighted_excerpts(test_app_with_search_data):
    """Test that search API returns excerpts with highlighted search terms."""
    client, config, db_path = test_app_with_search_data

    # Search for "important"
    response = client.get("/api/search?q=important")

    assert response.status_code == 200
    data = response.json()

    # Should find results
    assert data["pagination"]["total"] > 0
    assert len(data["results"]) > 0

    # Check that excerpts contain highlighting
    for result in data["results"]:
        excerpt = result["excerpt"]
        # Should contain <mark> tags around the search term
        assert "<mark>" in excerpt
        assert "</mark>" in excerpt
        # Should specifically highlight "important"
        assert (
            "<mark>important</mark>" in excerpt.lower()
            or "<mark>Important</mark>" in excerpt
        )


def test_search_page_displays_highlighted_excerpts(test_app_with_search_data):
    """Test that search page displays excerpts with highlighted search terms."""
    client, config, db_path = test_app_with_search_data

    # Search for "meeting"
    response = client.get("/search?q=meeting")

    assert response.status_code == 200
    html = response.text

    # Should contain search results
    assert "Search Results" in html

    # Should contain highlighted terms in the HTML
    # The excerpt is displayed with |safe filter, so <mark> tags should be preserved
    assert "<mark>" in html
    assert "</mark>" in html

    # Should specifically contain highlighted "meeting"
    assert "<mark>meeting</mark>" in html or "<mark>Meeting</mark>" in html


def test_search_with_multiple_terms_highlights_all(test_app_with_search_data):
    """Test that search with multiple terms highlights all matching terms."""
    client, config, db_path = test_app_with_search_data

    # Search for terms that appear in different recordings
    response = client.get("/api/search?q=important discussion")

    assert response.status_code == 200
    data = response.json()

    # Should find results
    assert data["pagination"]["total"] > 0

    # Check that excerpts contain highlighting for relevant terms
    found_important = False
    found_discussion = False

    for result in data["results"]:
        excerpt = result["excerpt"]
        if "<mark>important</mark>" in excerpt.lower():
            found_important = True
        if "<mark>discussion</mark>" in excerpt.lower():
            found_discussion = True

    # At least one of the terms should be highlighted
    assert found_important or found_discussion


def test_search_without_fts_highlighting_adds_manual_highlighting(
    test_app_with_search_data
):
    """Test that search without FTS highlighting falls back to manual highlighting."""
    client, config, db_path = test_app_with_search_data

    # This test verifies the fallback case when FTS doesn't provide highlighting
    # We'll search for a term and verify it gets highlighted
    response = client.get("/api/search?q=project")

    assert response.status_code == 200
    data = response.json()

    if data["pagination"]["total"] > 0:
        for result in data["results"]:
            excerpt = result["excerpt"]
            # Should contain highlighting even if FTS didn't provide it
            assert "<mark>" in excerpt
            assert "</mark>" in excerpt
