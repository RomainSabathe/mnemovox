# ABOUTME: Tests for audio playback functionality in web interface
# ABOUTME: Verifies correct MIME types and audio player HTML generation

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
def test_db_with_audio_files(tmp_path, test_config):
    """Create a test database with sample recordings and actual audio files."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))

    # Get the test audio file
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    assert test_audio_path.exists(), f"Test audio file not found: {test_audio_path}"

    session = get_session(str(db_path))

    # Create sample recordings with different audio formats
    test_cases = [
        {
            "original_filename": "test_file.wav",
            "internal_filename": "1609459200_wav_test.wav",
            "storage_path": "2023/2023-12-01/1609459200_wav_test.wav",
            "audio_format": "pcm_s16le",  # This is the codec name from ffprobe
            "expected_mime_type": "audio/wav",
        },
        {
            "original_filename": "test_file.mp3",
            "internal_filename": "1609459300_mp3_test.mp3",
            "storage_path": "2023/2023-12-01/1609459300_mp3_test.mp3",
            "audio_format": "mp3",
            "expected_mime_type": "audio/mpeg",
        },
        {
            "original_filename": "test_file.m4a",
            "internal_filename": "1609459400_m4a_test.m4a",
            "storage_path": "2023/2023-12-01/1609459400_m4a_test.m4a",
            "audio_format": "aac",
            "expected_mime_type": "audio/mp4",
        },
    ]

    for i, test_case in enumerate(test_cases):
        # Create storage directory and copy test audio file
        full_storage_path = Path(test_config.storage_path) / test_case["storage_path"]
        full_storage_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_audio_path, full_storage_path)

        recording = Recording(
            original_filename=test_case["original_filename"],
            internal_filename=test_case["internal_filename"],
            storage_path=test_case["storage_path"],
            import_timestamp=datetime.now(),
            duration_seconds=2.5,
            audio_format=test_case["audio_format"],
            sample_rate=16000,
            channels=1,
            file_size_bytes=int(test_audio_path.stat().st_size),
            transcript_status="complete",
            transcript_text="This is a test",
            transcript_segments=[
                {"start": 0.0, "end": 2.5, "text": "This is a test", "confidence": 0.95}
            ],
        )
        session.add(recording)

    session.commit()
    session.close()

    return str(db_path)


@pytest.fixture
def test_client(test_config, test_db_with_audio_files):
    """Create a test client for the FastAPI app."""
    from src.audio_manager.app import create_app

    app = create_app(test_config, test_db_with_audio_files)
    return TestClient(app)


def test_audio_player_correct_mime_types(test_client):
    """Test that audio player uses correct MIME types for different formats."""
    # Test WAV file
    response = test_client.get("/recordings/1")
    assert response.status_code == 200
    content = response.text
    assert '<audio class="audio-player" controls>' in content
    assert 'type="audio/wav"' in content
    assert 'src="/audio/2023/2023-12-01/1609459200_wav_test.wav"' in content

    # Test MP3 file
    response = test_client.get("/recordings/2")
    assert response.status_code == 200
    content = response.text
    assert 'type="audio/mpeg"' in content
    assert 'src="/audio/2023/2023-12-01/1609459300_mp3_test.mp3"' in content

    # Test M4A file
    response = test_client.get("/recordings/3")
    assert response.status_code == 200
    content = response.text
    assert 'type="audio/mp4"' in content
    assert 'src="/audio/2023/2023-12-01/1609459400_m4a_test.m4a"' in content


def test_audio_files_are_servable(test_client):
    """Test that audio files can be downloaded correctly."""
    # Test each audio file endpoint
    test_cases = [
        ("/audio/2023/2023-12-01/1609459200_wav_test.wav", "audio/wav"),
        ("/audio/2023/2023-12-01/1609459300_mp3_test.mp3", "audio/mp3"),
        ("/audio/2023/2023-12-01/1609459400_m4a_test.m4a", "audio/m4a"),
    ]

    for url, expected_content_type in test_cases:
        response = test_client.get(url)
        assert response.status_code == 200
        assert response.headers["content-type"] == expected_content_type
        assert len(response.content) > 0  # File has content


def test_audio_player_html_structure(test_client):
    """Test that audio player HTML is correctly structured."""
    response = test_client.get("/recordings/1")
    assert response.status_code == 200
    content = response.text

    # Check for proper HTML structure
    assert "<h2>Audio Player</h2>" in content
    assert '<audio class="audio-player" controls>' in content
    assert '<source src="/audio/' in content
    assert 'type="audio/' in content
    assert "Your browser does not support the audio element." in content
    assert "</audio>" in content


def test_audio_player_fallback_message(test_client):
    """Test that fallback message is present for unsupported browsers."""
    response = test_client.get("/recordings/1")
    assert response.status_code == 200
    content = response.text

    # Check that fallback message is included
    assert "Your browser does not support the audio element." in content


@pytest.mark.integration
def test_audio_player_with_real_audio_file(test_client):
    """Integration test: verify audio player works with real audio file."""
    response = test_client.get("/recordings/1")
    assert response.status_code == 200
    content = response.text

    # Verify audio player is present
    assert '<audio class="audio-player" controls>' in content
    assert "controls" in content

    # Verify the audio file is actually downloadable
    response = test_client.get("/audio/2023/2023-12-01/1609459200_wav_test.wav")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"

    # Verify it's a real WAV file by checking the content
    content = response.content
    assert content.startswith(b"RIFF")  # WAV files start with RIFF header
    assert b"WAVE" in content[:12]  # WAVE format identifier


def test_audio_mime_type_edge_cases(test_client, test_config, test_db_with_audio_files):
    """Test MIME type handling for edge cases."""
    # Test file with no extension
    session = get_session(test_db_with_audio_files)

    # Add a file with no extension
    test_audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    storage_path = "2023/2023-12-01/no_extension_file"
    full_storage_path = Path(test_config.storage_path) / storage_path
    shutil.copy2(test_audio_path, full_storage_path)

    recording = Recording(
        original_filename="no_extension_file",
        internal_filename="no_extension_file",
        storage_path=storage_path,
        import_timestamp=datetime.now(),
        audio_format="unknown",
        transcript_status="complete",
    )
    session.add(recording)
    session.commit()
    record_id = recording.id
    session.close()

    response = test_client.get(f"/recordings/{record_id}")
    assert response.status_code == 200
    content = response.text

    # Should default to wav when no extension is found
    assert 'type="audio/wav"' in content
