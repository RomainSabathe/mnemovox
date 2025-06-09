# ABOUTME: Tests for search API endpoint with FTS5 full-text search
# ABOUTME: Verifies GET /api/search endpoint functionality and query handling

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from src.audio_manager.app import create_app
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording, sync_fts
from datetime import datetime


@pytest.fixture
def test_app_with_searchable_recordings():
    """Create test app with recordings that have searchable content."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config with FTS enabled
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
            items_per_page=20,
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

            # Recording about meetings
            meeting_recording = Recording(
                original_filename="team_meeting_notes.wav",
                internal_filename="1609459200_meeting_abcd1234.wav",
                storage_path="2021/01-01/1609459200_meeting_abcd1234.wav",
                import_timestamp=now,
                duration_seconds=120.0,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=2048000,
                transcript_status="complete",
                transcript_language="en",
                transcript_text="This is a team meeting about project planning and budget allocation. We discussed quarterly goals and resource management.",
                transcript_segments=[
                    {
                        "start": 0.0,
                        "end": 10.0,
                        "text": "This is a team meeting about project planning.",
                        "confidence": 0.95,
                    },
                    {
                        "start": 10.0,
                        "end": 20.0,
                        "text": "We discussed quarterly goals and budget allocation.",
                        "confidence": 0.92,
                    },
                ],
            )
            session.add(meeting_recording)
            session.flush()  # Get ID for FTS sync

            # Recording about interviews
            interview_recording = Recording(
                original_filename="candidate_interview_session.mp3",
                internal_filename="1609459300_interview_efgh5678.mp3",
                storage_path="2021/01-01/1609459300_interview_efgh5678.mp3",
                import_timestamp=now,
                duration_seconds=1800.0,
                audio_format="mp3",
                sample_rate=22050,
                channels=1,
                file_size_bytes=1024000,
                transcript_status="complete",
                transcript_language="en",
                transcript_text="Candidate interview session discussing technical skills, experience with Python programming, and software development methodologies.",
                transcript_segments=[
                    {
                        "start": 0.0,
                        "end": 15.0,
                        "text": "Candidate interview session discussing technical skills.",
                        "confidence": 0.88,
                    }
                ],
            )
            session.add(interview_recording)
            session.flush()

            # Recording about training
            training_recording = Recording(
                original_filename="python_training_workshop.m4a",
                internal_filename="1609459400_training_ijkl9012.m4a",
                storage_path="2021/01-01/1609459400_training_ijkl9012.m4a",
                import_timestamp=now,
                duration_seconds=3600.0,
                audio_format="m4a",
                sample_rate=48000,
                channels=2,
                file_size_bytes=4096000,
                transcript_status="complete",
                transcript_language="en",
                transcript_text="Python training workshop covering advanced programming concepts, data structures, and algorithmic problem solving techniques.",
                transcript_segments=[
                    {
                        "start": 0.0,
                        "end": 20.0,
                        "text": "Python training workshop covering advanced programming concepts.",
                        "confidence": 0.93,
                    }
                ],
            )
            session.add(training_recording)
            session.flush()

            # Recording with no transcript (pending)
            pending_recording = Recording(
                original_filename="raw_audio_file.wav",
                internal_filename="1609459500_raw_mnop3456.wav",
                storage_path="2021/01-01/1609459500_raw_mnop3456.wav",
                import_timestamp=now,
                duration_seconds=600.0,
                audio_format="wav",
                sample_rate=16000,
                channels=1,
                file_size_bytes=512000,
                transcript_status="pending",
            )
            session.add(pending_recording)
            session.flush()

            session.commit()

            # Sync all recordings to FTS
            for recording in [
                meeting_recording,
                interview_recording,
                training_recording,
                pending_recording,
            ]:
                sync_fts(session, recording.id)

        finally:
            session.close()

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_search_valid_query_results(test_app_with_searchable_recordings):
    """Test search with valid query returns relevant results."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=python")

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "query" in data
    assert "results" in data
    assert "pagination" in data

    assert data["query"] == "python"

    # Should find the training recording
    results = data["results"]
    assert len(results) >= 1

    # Check result structure
    result = results[0]
    expected_fields = [
        "id",
        "original_filename",
        "transcript_text",
        "excerpt",
        "relevance_score",
    ]
    for field in expected_fields:
        assert field in result, f"Missing field: {field}"

    # Should match the training recording
    assert (
        "python" in result["original_filename"].lower()
        or "python" in result["transcript_text"].lower()
    )
    assert "python" in result["excerpt"].lower()


def test_search_multiple_matches(test_app_with_searchable_recordings):
    """Test search query that matches multiple recordings."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=programming")

    assert response.status_code == 200
    data = response.json()

    results = data["results"]

    # Should find both interview and training recordings
    assert len(results) >= 2

    # Results should be ordered by relevance
    for i in range(len(results) - 1):
        assert results[i]["relevance_score"] >= results[i + 1]["relevance_score"]


def test_search_filename_match(test_app_with_searchable_recordings):
    """Test search that matches filename content."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=meeting")

    assert response.status_code == 200
    data = response.json()

    results = data["results"]
    assert len(results) >= 1

    # Should find the meeting recording
    meeting_result = next(
        (r for r in results if "meeting" in r["original_filename"].lower()), None
    )
    assert meeting_result is not None


def test_search_transcript_content_match(test_app_with_searchable_recordings):
    """Test search that matches transcript content."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=budget")

    assert response.status_code == 200
    data = response.json()

    results = data["results"]
    assert len(results) >= 1

    # Should find recording with budget in transcript
    budget_result = next(
        (r for r in results if "budget" in r["transcript_text"].lower()), None
    )
    assert budget_result is not None
    assert "budget" in budget_result["excerpt"].lower()


def test_search_query_too_short(test_app_with_searchable_recordings):
    """Test search with query shorter than 3 characters."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=py")

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "at least 3 characters" in data["detail"].lower()


def test_search_empty_query(test_app_with_searchable_recordings):
    """Test search with empty query parameter."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=")

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_search_missing_query_parameter(test_app_with_searchable_recordings):
    """Test search without query parameter."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search")

    assert response.status_code == 422  # FastAPI validation error


def test_search_no_results(test_app_with_searchable_recordings):
    """Test search query that returns no results."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=nonexistent")

    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "nonexistent"
    assert data["results"] == []
    assert data["pagination"]["total"] == 0


def test_search_pagination(test_app_with_searchable_recordings):
    """Test search pagination parameters."""
    client, config, db_path = test_app_with_searchable_recordings

    # Test with custom page size
    response = client.get("/api/search?q=session&page=1&per_page=1")

    assert response.status_code == 200
    data = response.json()

    pagination = data["pagination"]
    assert "page" in pagination
    assert "per_page" in pagination
    assert "total" in pagination
    assert "pages" in pagination
    assert "has_prev" in pagination
    assert "has_next" in pagination

    assert pagination["page"] == 1
    assert pagination["per_page"] == 1

    # If there are results, should be limited to 1
    if data["results"]:
        assert len(data["results"]) <= 1


def test_search_invalid_pagination(test_app_with_searchable_recordings):
    """Test search with invalid pagination parameters."""
    client, config, db_path = test_app_with_searchable_recordings

    # Test negative page
    response = client.get("/api/search?q=test&page=-1")
    assert response.status_code == 400

    # Test zero page
    response = client.get("/api/search?q=test&page=0")
    assert response.status_code == 400

    # Test invalid per_page
    response = client.get("/api/search?q=test&per_page=0")
    assert response.status_code == 400

    # Test per_page too large
    response = client.get("/api/search?q=test&per_page=200")
    assert response.status_code == 400


def test_search_excerpt_generation(test_app_with_searchable_recordings):
    """Test that search results include relevant excerpts."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=quarterly")

    assert response.status_code == 200
    data = response.json()

    if data["results"]:
        result = data["results"][0]
        excerpt = result["excerpt"]

        # Excerpt should contain the search term
        assert "quarterly" in excerpt.lower()

        # Excerpt should be reasonably sized (not the entire transcript)
        assert len(excerpt) <= 200  # Reasonable excerpt length

        # Excerpt should contain some context around the search term
        assert len(excerpt.split()) >= 5  # At least a few words of context


def test_search_only_complete_transcripts(test_app_with_searchable_recordings):
    """Test that search only returns recordings with complete transcripts."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=raw")

    assert response.status_code == 200
    data = response.json()

    # Should not find the pending recording even though filename matches
    # because it has no transcript content to search
    for result in data["results"]:
        assert result["transcript_text"] is not None
        assert result["transcript_text"].strip() != ""


def test_search_case_insensitive(test_app_with_searchable_recordings):
    """Test that search is case insensitive."""
    client, config, db_path = test_app_with_searchable_recordings

    # Test lowercase
    response1 = client.get("/api/search?q=python")
    # Test uppercase
    response2 = client.get("/api/search?q=PYTHON")
    # Test mixed case
    response3 = client.get("/api/search?q=Python")

    for response in [response1, response2, response3]:
        assert response.status_code == 200
        data = response.json()
        # All should return the same results
        if response1.json()["results"]:
            assert len(data["results"]) > 0


def test_search_special_characters(test_app_with_searchable_recordings):
    """Test search with special characters and quotes."""
    client, config, db_path = test_app_with_searchable_recordings

    # Test with quotes (should still work)
    response = client.get('/api/search?q="project planning"')

    assert response.status_code == 200
    # Should handle gracefully even if FTS doesn't support exact phrase search


def test_search_response_format(test_app_with_searchable_recordings):
    """Test that search response has correct format."""
    client, config, db_path = test_app_with_searchable_recordings

    response = client.get("/api/search?q=test")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # Check top-level structure
    required_fields = ["query", "results", "pagination"]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    # Check pagination structure
    pagination = data["pagination"]
    pagination_fields = ["page", "per_page", "total", "pages", "has_prev", "has_next"]
    for field in pagination_fields:
        assert field in pagination, f"Missing pagination field: {field}"

    # Check result structure if results exist
    if data["results"]:
        result = data["results"][0]
        result_fields = [
            "id",
            "original_filename",
            "transcript_text",
            "excerpt",
            "relevance_score",
        ]
        for field in result_fields:
            assert field in result, f"Missing result field: {field}"

        # Check data types
        assert isinstance(result["id"], int)
        assert isinstance(result["original_filename"], str)
        assert isinstance(result["excerpt"], str)
        assert isinstance(result["relevance_score"], (int, float))
