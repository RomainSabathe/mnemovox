# ABOUTME: Diagnostic test to debug the current search issue
# ABOUTME: Checks database state and search functionality in your real deployment

import pytest
import requests
from pathlib import Path
from src.audio_manager.db import get_session
from sqlalchemy import text


def test_diagnose_real_app_search_issue():
    """Diagnostic test to check what's wrong with search in the real app."""

    # This test assumes your server is running on localhost:8000
    base_url = "http://localhost:8000"

    try:
        # Test 1: Check if server is running
        response = requests.get(base_url)
        print(f"✅ Server is running: {response.status_code}")

        # Test 2: Check recordings list
        response = requests.get(f"{base_url}/api/recordings")
        assert response.status_code == 200
        recordings_data = response.json()
        print(f"📋 Total recordings: {recordings_data['pagination']['total']}")

        if recordings_data["recordings"]:
            print("📁 Sample recordings:")
            for rec in recordings_data["recordings"][:3]:
                print(
                    f"   ID: {rec['id']}, File: {rec['original_filename']}, Status: {rec['transcript_status']}"
                )

        # Test 3: Check database directly (if database file exists)
        db_path = Path("data/metadata.db")  # Adjust path as needed
        if db_path.exists():
            print(f"💾 Found database at: {db_path}")

            session = get_session(str(db_path))
            try:
                # Check recordings
                recordings = session.execute(
                    text(
                        "SELECT id, original_filename, transcript_status, transcript_text IS NOT NULL as has_text FROM recordings"
                    )
                ).fetchall()

                print("📊 Database recordings:")
                for rec in recordings:
                    print(
                        f"   ID: {rec[0]}, File: {rec[1]}, Status: {rec[2]}, Has text: {rec[3]}"
                    )

                # Check FTS table
                try:
                    fts_count = session.execute(
                        text("SELECT COUNT(*) FROM recordings_fts")
                    ).fetchone()
                    print(f"🔍 FTS table entries: {fts_count[0]}")

                    if fts_count[0] > 0:
                        fts_entries = session.execute(
                            text("SELECT rowid, original_filename FROM recordings_fts")
                        ).fetchall()
                        print("🔍 FTS indexed files:")
                        for entry in fts_entries:
                            print(f"   Row {entry[0]}: {entry[1]}")
                    else:
                        print("❌ FTS table is empty - this is the problem!")

                        # Check if there are completed recordings not in FTS
                        completed_not_in_fts = session.execute(
                            text(
                                """
                                SELECT r.id, r.original_filename 
                                FROM recordings r 
                                LEFT JOIN recordings_fts fts ON r.id = fts.rowid 
                                WHERE r.transcript_status = 'complete' 
                                AND r.transcript_text IS NOT NULL 
                                AND fts.rowid IS NULL
                            """
                            )
                        ).fetchall()

                        if completed_not_in_fts:
                            print("❌ Found completed recordings not indexed in FTS:")
                            for rec in completed_not_in_fts:
                                print(
                                    f"   ID: {rec[0]}, File: {rec[1]} - needs FTS indexing"
                                )

                except Exception as e:
                    print(f"❌ FTS table error: {e}")

            finally:
                session.close()
        else:
            print(f"❌ Database not found at: {db_path}")

        # Test 4: Try search API
        response = requests.get(f"{base_url}/api/search?q=test")
        if response.status_code == 200:
            search_data = response.json()
            print(f"🔍 Search API works, found {len(search_data['results'])} results")
            if search_data["results"]:
                print("🔍 Search results:")
                for result in search_data["results"]:
                    print(
                        f"   {result['original_filename']}: {result['excerpt'][:50]}..."
                    )
        else:
            print(f"❌ Search API failed: {response.status_code}")

        # Test 5: Try search HTML page
        response = requests.get(f"{base_url}/search?q=test")
        if response.status_code == 200:
            print("✅ Search HTML page loads")
            if "No results found" in response.text:
                print("❌ Search page shows 'No results found'")
            elif "search-result-item" in response.text:
                print("✅ Search page shows results")
        else:
            print(f"❌ Search HTML page failed: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server - make sure it's running on localhost:8000")
        pytest.skip("Server not running")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    test_diagnose_real_app_search_issue()
