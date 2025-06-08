# ABOUTME: Tests for audio utilities module
# ABOUTME: Verifies audio metadata probing and filename generation

import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.audio_manager.audio_utils import probe_metadata, generate_internal_filename


def test_probe_metadata_success():
    """Test that probe_metadata parses ffprobe output correctly."""
    mock_ffprobe_output = {
        "streams": [
            {
                "codec_type": "audio",
                "duration": "123.456",
                "sample_rate": "44100",
                "channels": 2,
                "codec_name": "mp3"
            }
        ],
        "format": {
            "size": "5678901"
        }
    }
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_ffprobe_output),
            stderr="",
            returncode=0
        )
        
        result = probe_metadata("/fake/path/test.mp3")
        
        assert result["duration"] == 123.456
        assert result["sample_rate"] == 44100
        assert result["channels"] == 2
        assert result["format"] == "mp3"
        assert result["file_size"] == 5678901
        
        # Verify ffprobe was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffprobe" in args
        assert "-v" in args and "quiet" in args
        assert "-print_format" in args and "json" in args
        assert "/fake/path/test.mp3" in args


def test_probe_metadata_handles_ffprobe_error():
    """Test that probe_metadata handles ffprobe errors gracefully."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="ffprobe: error message",
            returncode=1
        )
        
        result = probe_metadata("/fake/path/bad.mp3")
        
        assert result is None


def test_probe_metadata_handles_malformed_json():
    """Test that probe_metadata handles malformed JSON output."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            stdout="invalid json {",
            stderr="",
            returncode=0
        )
        
        result = probe_metadata("/fake/path/test.mp3")
        
        assert result is None


def test_probe_metadata_missing_stream_data():
    """Test that probe_metadata handles missing stream data."""
    mock_ffprobe_output = {
        "streams": [],
        "format": {"size": "1000"}
    }
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_ffprobe_output),
            stderr="",
            returncode=0
        )
        
        result = probe_metadata("/fake/path/test.mp3")
        
        assert result is None


def test_generate_internal_filename_format():
    """Test that generated filename follows the correct format."""
    original_name = "my recording.mp3"
    
    # Mock time to get predictable timestamp
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        filename = generate_internal_filename(original_name)
    
    # Should be: <timestamp>_<8-char-uuid>.mp3
    parts = filename.split('.')
    assert len(parts) == 2
    assert parts[1] == "mp3"  # extension preserved
    
    name_parts = parts[0].split('_')
    assert len(name_parts) == 2
    assert name_parts[0] == "1609459200"  # epoch timestamp
    assert len(name_parts[1]) == 8  # short UUID


def test_generate_internal_filename_uniqueness():
    """Test that generated filenames are unique."""
    original_name = "test.wav"
    
    filename1 = generate_internal_filename(original_name)
    filename2 = generate_internal_filename(original_name)
    
    assert filename1 != filename2
    
    # Both should have same extension
    assert filename1.endswith(".wav")
    assert filename2.endswith(".wav")


def test_generate_internal_filename_preserves_extension():
    """Test that file extensions are preserved correctly."""
    test_cases = [
        ("file.mp3", "mp3"),
        ("recording.wav", "wav"),
        ("audio.m4a", "m4a"),
        ("no_extension", ""),
        ("multiple.dots.mp3", "mp3")
    ]
    
    for original, expected_ext in test_cases:
        filename = generate_internal_filename(original)
        if expected_ext:
            assert filename.endswith(f".{expected_ext}")
        else:
            assert "." not in filename


def test_generate_internal_filename_timestamp_increases():
    """Test that timestamps in filenames increase over time."""
    filename1 = generate_internal_filename("test.mp3")
    time.sleep(0.01)  # Small delay
    filename2 = generate_internal_filename("test.mp3")
    
    timestamp1 = int(filename1.split('_')[0])
    timestamp2 = int(filename2.split('_')[0])
    
    assert timestamp2 >= timestamp1


# Integration tests with real audio file
@pytest.mark.integration
def test_probe_metadata_real_audio_file():
    """Integration test: probe metadata from actual audio file using ffprobe."""
    audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    
    # Verify the test file exists
    assert audio_path.exists(), f"Test audio file not found: {audio_path}"
    
    # Probe metadata using actual ffprobe
    metadata = probe_metadata(str(audio_path))
    
    assert metadata is not None
    
    # Check that we get reasonable metadata for a WAV file
    assert metadata["format"] == "pcm_s16le"  # Common WAV format
    assert metadata["duration"] > 0  # Should have some duration
    assert metadata["sample_rate"] > 0  # Should have a sample rate
    assert metadata["channels"] > 0  # Should have at least one channel
    assert metadata["file_size"] > 0  # File should have some size
    
    # Reasonable bounds for a short test audio file
    assert 0.5 <= metadata["duration"] <= 10.0  # Between 0.5 and 10 seconds
    assert 8000 <= metadata["sample_rate"] <= 96000  # Common sample rates
    assert 1 <= metadata["channels"] <= 2  # Mono or stereo


@pytest.mark.integration
def test_probe_metadata_real_audio_file_detailed():
    """Integration test: verify specific metadata fields from real audio file."""
    audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    
    # Verify the test file exists
    assert audio_path.exists(), f"Test audio file not found: {audio_path}"
    
    metadata = probe_metadata(str(audio_path))
    
    assert metadata is not None
    
    # Check all required fields are present
    required_fields = ["duration", "sample_rate", "channels", "format", "file_size"]
    for field in required_fields:
        assert field in metadata, f"Missing field: {field}"
        assert metadata[field] is not None, f"Field {field} is None"
    
    # Check data types
    assert isinstance(metadata["duration"], float)
    assert isinstance(metadata["sample_rate"], int)
    assert isinstance(metadata["channels"], int)
    assert isinstance(metadata["format"], str)
    assert isinstance(metadata["file_size"], int)


@pytest.mark.integration  
def test_probe_metadata_real_audio_consistency():
    """Integration test: verify metadata is consistent across multiple calls."""
    audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    
    # Verify the test file exists
    assert audio_path.exists(), f"Test audio file not found: {audio_path}"
    
    # Probe metadata multiple times
    metadata1 = probe_metadata(str(audio_path))
    metadata2 = probe_metadata(str(audio_path))
    
    assert metadata1 is not None
    assert metadata2 is not None
    
    # Results should be identical
    assert metadata1 == metadata2


@pytest.mark.integration
def test_generate_internal_filename_with_real_file():
    """Integration test: generate filenames based on real audio file."""
    audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"
    original_filename = audio_path.name
    
    # Generate multiple filenames
    filename1 = generate_internal_filename(original_filename)
    time.sleep(0.01)  # Small delay to ensure different timestamps
    filename2 = generate_internal_filename(original_filename)
    
    # Both should preserve the .wav extension
    assert filename1.endswith(".wav")
    assert filename2.endswith(".wav")
    
    # Filenames should be different due to timestamp and UUID
    assert filename1 != filename2
    
    # Both should follow the pattern: timestamp_uuid.wav
    parts1 = filename1.replace(".wav", "").split("_")
    parts2 = filename2.replace(".wav", "").split("_")
    
    assert len(parts1) == 2
    assert len(parts2) == 2
    
    # Timestamps should be integers
    timestamp1 = int(parts1[0])
    timestamp2 = int(parts2[0])
    assert timestamp2 >= timestamp1
    
    # UUIDs should be 8 characters each
    assert len(parts1[1]) == 8
    assert len(parts2[1]) == 8
    assert parts1[1] != parts2[1]  # Different UUIDs