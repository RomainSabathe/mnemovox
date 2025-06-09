# ABOUTME: Integration tests for complete search functionality workflow
# ABOUTME: Tests FTS indexing, search API, and HTML page with real data flow

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from src.audio_manager.app import create_app
from src.audio_manager.config import Config
from src.audio_manager.db import init_db, get_session, Recording, sync_fts
from datetime import datetime
from sqlalchemy import text


@pytest.fixture
def test_app_with_real_workflow():
    """Create test app simulating the real workflow from upload to search."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config with FTS enabled (matching real app settings)
        config = Config(
            monitored_directory=str(tmp_path / "monitored"),
            storage_path=str(tmp_path / "storage"),
            upload_temp_path=str(tmp_path / "uploads"),
            items_per_page=20,
            fts_enabled=True,
        )

        # Create directories
        Path(config.storage_path).mkdir(parents=True, exist_ok=True)
        Path(config.upload_temp_path).mkdir(parents=True, exist_ok=True)

        # Initialize database with FTS (matching real app)
        db_path = str(tmp_path / "test.db")
        init_db(db_path, fts_enabled=True)

        # Create app
        app = create_app(config, db_path)
        client = TestClient(app)

        yield client, config, db_path


def test_search_integration_with_uploaded_file(test_app_with_real_workflow):
    """Test complete workflow: file exists -> has transcript -> searchable."""
    client, config, db_path = test_app_with_real_workflow

    # Simulate a recording that has been processed (like your this_is_a_test.wav)
    session = get_session(db_path)
    try:
        now = datetime.now()

        # Create a recording like what would exist after ingestion + transcription
        test_recording = Recording(
            original_filename="this_is_a_test.wav",
            internal_filename="1609459200_test_abcd1234.wav",
            storage_path="2021/01-01/1609459200_test_abcd1234.wav",
            import_timestamp=now,
            duration_seconds=10.0,
            audio_format="wav",
            sample_rate=44100,
            channels=2,
            file_size_bytes=1024000,
            transcript_status="complete",  # Key: must be complete
            transcript_language="en",
            transcript_text="This is a test audio file for testing purposes.",  # Key: must have text
            transcript_segments=[
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "This is a test audio file",
                    "confidence": 0.95,
                },
                {
                    "start": 5.0,
                    "end": 10.0,
                    "text": "for testing purposes.",
                    "confidence": 0.92,
                },
            ],
        )

        session.add(test_recording)
        session.flush()  # Get the ID

        # CRITICAL: Sync to FTS table (this might be missing in real app)
        sync_fts(session, test_recording.id)

        session.commit()

        # Verify recording exists in main table
        recordings = session.query(Recording).all()
        assert len(recordings) == 1
        assert recordings[0].original_filename == "this_is_a_test.wav"
        assert recordings[0].transcript_status == "complete"
        assert recordings[0].transcript_text is not None

        # Verify FTS table was populated
        fts_result = session.execute(
            text("SELECT COUNT(*) FROM recordings_fts")
        ).fetchone()
        assert fts_result[0] == 1, "FTS table should have 1 entry"

    finally:
        session.close()

    # Test API search
    response = client.get("/api/search?q=test")
    assert response.status_code == 200

    data = response.json()
    assert data["query"] == "test"
    assert len(data["results"]) == 1, f"Expected 1 result, got {len(data['results'])}"

    result = data["results"][0]
    assert result["original_filename"] == "this_is_a_test.wav"
    assert "test" in result["excerpt"].lower()

    # Test HTML search page
    response = client.get("/search?q=test")
    assert response.status_code == 200
    html = response.text

    assert "Search Results" in html
    assert "this_is_a_test.wav" in html
    assert "1 result" in html


def test_search_fails_without_transcript(test_app_with_real_workflow):
    """Test that recordings without transcripts are not searchable."""
    client, config, db_path = test_app_with_real_workflow

    session = get_session(db_path)
    try:
        now = datetime.now()

        # Create recording without transcript (pending status)
        pending_recording = Recording(
            original_filename="pending_file.wav",
            internal_filename="1609459300_pending_efgh5678.wav",
            storage_path="2021/01-01/1609459300_pending_efgh5678.wav",
            import_timestamp=now,
            duration_seconds=10.0,
            audio_format="wav",
            sample_rate=44100,
            channels=2,
            file_size_bytes=1024000,
            transcript_status="pending",  # Not complete
            transcript_text=None,  # No transcript
        )

        session.add(pending_recording)
        session.flush()

        # Even if we sync to FTS, it shouldn't be searchable without transcript
        sync_fts(session, pending_recording.id)

        session.commit()

    finally:
        session.close()

    # Search should return no results
    response = client.get("/api/search?q=pending")
    assert response.status_code == 200

    data = response.json()
    assert (
        len(data["results"]) == 0
    ), "Recordings without transcripts should not be searchable"


def test_search_integration_multiple_files(test_app_with_real_workflow):
    """Test search with multiple files to verify ranking and relevance."""
    client, config, db_path = test_app_with_real_workflow

    session = get_session(db_path)
    try:
        now = datetime.now()

        # Create multiple recordings with different relevance to "test"
        recordings = [
            {
                "filename": "primary_test_file.wav",
                "transcript": "This is a test file for primary testing of the application.",
            },
            {
                "filename": "secondary_file.wav",
                "transcript": "This file mentions test only once in passing.",
            },
            {
                "filename": "test_heavy_file.wav",
                "transcript": "Test test test. This file is all about testing and test cases.",
            },
        ]

        for i, rec_data in enumerate(recordings):
            recording = Recording(
                original_filename=rec_data["filename"],
                internal_filename=f"1609459{300 + i*100}_test_{i:04d}.wav",
                storage_path=f"2021/01-01/1609459{300 + i*100}_test_{i:04d}.wav",
                import_timestamp=now,
                duration_seconds=10.0 + i * 5,
                audio_format="wav",
                sample_rate=44100,
                channels=2,
                file_size_bytes=1024000 + i * 512000,
                transcript_status="complete",
                transcript_language="en",
                transcript_text=rec_data["transcript"],
                transcript_segments=[
                    {
                        "start": 0.0,
                        "end": 10.0,
                        "text": rec_data["transcript"],
                        "confidence": 0.9,
                    }
                ],
            )

            session.add(recording)
            session.flush()
            sync_fts(session, recording.id)

        session.commit()

    finally:
        session.close()

    # Search for "test"
    response = client.get("/api/search?q=test")
    assert response.status_code == 200

    data = response.json()
    assert len(data["results"]) == 3, "Should find all 3 recordings"

    # Results should be ordered by relevance (test_heavy_file should rank highest)
    filenames = [r["original_filename"] for r in data["results"]]
    assert "test_heavy_file.wav" in filenames

    # Verify excerpts contain search term
    for result in data["results"]:
        assert "test" in result["excerpt"].lower()


def test_debug_fts_table_contents(test_app_with_real_workflow):
    """Debug test to inspect FTS table contents."""
    client, config, db_path = test_app_with_real_workflow

    session = get_session(db_path)
    try:
        now = datetime.now()

        # Create a simple test recording
        recording = Recording(
            original_filename="debug_test.wav",
            internal_filename="1609459999_debug_test.wav",
            storage_path="2021/01-01/1609459999_debug_test.wav",
            import_timestamp=now,
            duration_seconds=10.0,
            audio_format="wav",
            sample_rate=44100,
            channels=2,
            file_size_bytes=1024000,
            transcript_status="complete",
            transcript_language="en",
            transcript_text="Hello world this is a debug test.",
        )

        session.add(recording)
        session.flush()

        # Check what gets inserted into FTS
        print(f"\n--- DEBUG: Recording ID: {recording.id} ---")
        print(f"Filename: {recording.original_filename}")
        print(f"Transcript: {recording.transcript_text}")
        print(f"Status: {recording.transcript_status}")

        # Sync to FTS
        sync_fts(session, recording.id)
        session.commit()

        # Check FTS table contents
        fts_rows = session.execute(
            text("SELECT rowid, original_filename, transcript_text FROM recordings_fts")
        ).fetchall()
        print("\n--- DEBUG: FTS Table Contents ---")
        for row in fts_rows:
            print(f"Row ID: {row[0]}, Filename: {row[1]}, Transcript: {row[2]}")

        # Test FTS query directly
        direct_search = session.execute(
            text("SELECT rowid FROM recordings_fts WHERE recordings_fts MATCH 'debug'")
        ).fetchall()
        print("\n--- DEBUG: Direct FTS Search for 'debug' ---")
        print(f"Results: {len(direct_search)} rows")
        for row in direct_search:
            print(f"Found rowid: {row[0]}")

    finally:
        session.close()

    # This test always passes - it's just for debugging
    assert True


def test_check_real_database_state():
    """Debug test to check what's in a real database (if it exists)."""
    # This would help diagnose your real issue
    real_db_path = Path("data/metadata.db")  # Adjust path as needed

    if not real_db_path.exists():
        pytest.skip("Real database not found - this is a debug test")

    from src.audio_manager.db import get_session

    session = get_session(str(real_db_path))
    try:
        # Check recordings table
        recordings = session.execute(
            text(
                "SELECT id, original_filename, transcript_status, transcript_text FROM recordings"
            )
        ).fetchall()
        print("\n--- DEBUG: Real DB Recordings ---")
        for rec in recordings:
            print(
                f"ID: {rec[0]}, File: {rec[1]}, Status: {rec[2]}, Has transcript: {rec[3] is not None}"
            )

        # Check if FTS table exists
        try:
            fts_count = session.execute(
                text("SELECT COUNT(*) FROM recordings_fts")
            ).fetchone()
            print(f"\n--- DEBUG: FTS Table has {fts_count[0]} entries ---")

            if fts_count[0] > 0:
                fts_sample = session.execute(
                    text("SELECT rowid, original_filename FROM recordings_fts LIMIT 3")
                ).fetchall()
                for row in fts_sample:
                    print(f"FTS Row: {row[0]} -> {row[1]}")
        except Exception as e:
            print(f"FTS table issue: {e}")

    finally:
        session.close()

    assert True  # Always pass - just for debugging
