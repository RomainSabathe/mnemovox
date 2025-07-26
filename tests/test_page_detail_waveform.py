# ABOUTME: Tests for the waveform display on the recording detail page.
# ABOUTME: Verifies that necessary HTML elements and scripts are present.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime, timezone

from mnemovox.app import create_app
from mnemovox.config import get_config
from mnemovox.db import Recording, init_db


@pytest.fixture(scope="module")
def test_config():
    """Fixture for test configuration."""
    return get_config("config.yaml.sample")


@pytest.fixture(scope="module")
def db_session():
    """Fixture for a test database session."""
    db_path = "test_waveform_page.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    init_db(db_path, fts_enabled=False)
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = Session()
    try:
        # Add a sample recording
        recording = Recording(
            id=1,
            original_filename="test_waveform.wav",
            internal_filename="12345_abc.wav",
            storage_path="2023/2023-10-27/12345_abc.wav",
            import_timestamp=datetime.now(timezone.utc),
            duration_seconds=10.5,
            audio_format="wav",
            sample_rate=16000,
            channels=1,
            file_size_bytes=168000,
            transcript_status="complete",
            transcript_text="This is a test transcript.",
            transcript_segments=[
                {"start": 0, "end": 5, "text": "This is a test transcript."}
            ],
        )
        db.add(recording)
        db.commit()
        yield db
    finally:
        db.close()
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture(scope="module")
def client(test_config, db_session):
    """Fixture for the FastAPI TestClient."""
    # The db_session fixture is used to populate the DB,
    # but the app needs the path to create its own session pool.
    db_path = "test_waveform_page.db"
    app = create_app(config=test_config, db_path=db_path)
    with TestClient(app) as c:
        yield c


def test_get_recording_detail_page_with_waveform(client):
    """
    Tests that the recording detail page includes the necessary elements
    for the wavesurfer.js waveform display.
    """
    response = client.get("/recordings/1")
    assert response.status_code == 200
    html = response.text

    # 1. Check for the waveform container
    assert '<div id="waveform"></div>' in html, "Waveform container div is missing."

    # 2. Check for the wavesurfer.js library script
    assert (
        '<script src="https://unpkg.com/wavesurfer.js@7"></script>' in html
    ), "wavesurfer.js script from CDN is missing."

    # 3. Check for our custom waveform script
    assert (
        '<script src="/static/js/waveform.js"></script>' in html
    ), "Custom waveform.js script is missing."

    # 4. Check for play/pause controls
    assert '<button id="btn-play-pause"' in html, "Play/pause button is missing."
