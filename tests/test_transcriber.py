# ABOUTME: Tests for transcription module
# ABOUTME: Verifies faster-whisper integration and transcription functionality

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from mnemovox.transcriber import transcribe_file


def test_transcribe_file_success():
    """Test successful transcription with faster-whisper."""
    # Mock transcription segments
    mock_segments = [
        MagicMock(start=0.0, end=2.5, text="Hello, this is a test.", confidence=0.95),
        MagicMock(
            start=2.5, end=5.0, text="This is the second segment.", confidence=0.87
        ),
    ]

    # Mock whisper model and transcribe method
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, mock_info)

    with patch("mnemovox.transcriber.WhisperModel", return_value=mock_model):
        result = transcribe_file("/fake/path/audio.wav", "base.en")
        assert result is not None
        full_text, segments, detected_language = result

        # Check full text concatenation
        expected_text = "Hello, this is a test. This is the second segment."
        assert full_text == expected_text

        # Check segments structure
        assert len(segments) == 2

        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 2.5
        assert segments[0]["text"] == "Hello, this is a test."
        assert segments[0]["confidence"] == 0.95

        assert segments[1]["start"] == 2.5
        assert segments[1]["end"] == 5.0
        assert segments[1]["text"] == "This is the second segment."
        assert segments[1]["confidence"] == 0.87

        assert detected_language == "en"

        # Verify model was created with correct parameters
        from mnemovox.transcriber import WhisperModel

        WhisperModel.assert_called_once_with("base.en", device="cpu")

        # Verify transcribe was called with correct path
        mock_model.transcribe.assert_called_once_with("/fake/path/audio.wav")


def test_transcribe_file_empty_segments():
    """Test transcription with no segments returned."""
    mock_segments = []

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, mock_info)

    with patch("mnemovox.transcriber.WhisperModel", return_value=mock_model):
        result = transcribe_file("/fake/path/empty.wav", "base.en")
        assert result is not None
        full_text, segments, detected_language = result

        assert full_text == ""
        assert segments == []
        assert detected_language == "en"


def test_transcribe_file_single_segment():
    """Test transcription with single segment."""
    mock_segments = [
        MagicMock(
            start=0.0, end=3.2, text="Single segment audio file.", confidence=0.92
        )
    ]

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, mock_info)

    with patch("mnemovox.transcriber.WhisperModel", return_value=mock_model):
        result = transcribe_file("/fake/path/single.wav", "small")
        assert result is not None
        full_text, segments, detected_language = result

        assert full_text == "Single segment audio file."
        assert len(segments) == 1
        assert segments[0]["text"] == "Single segment audio file."
        assert segments[0]["confidence"] == 0.92
        assert detected_language == "en"


def test_transcribe_file_handles_whisper_exception():
    """Test that transcription handles faster-whisper exceptions gracefully."""
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = Exception("Whisper model error")

    with patch("mnemovox.transcriber.WhisperModel", return_value=mock_model):
        result = transcribe_file("/fake/path/error.wav", "base.en")

        assert result is None


def test_transcribe_file_handles_model_creation_error():
    """Test that transcription handles model creation errors gracefully."""
    with patch(
        "mnemovox.transcriber.WhisperModel",
        side_effect=Exception("Model load error"),
    ):
        result = transcribe_file("/fake/path/audio.wav", "invalid-model")

        assert result is None


def test_transcribe_file_with_different_models():
    """Test transcription with different whisper models."""
    mock_segments_data = [MagicMock(start=0.0, end=1.0, text="Test", confidence=0.9)]

    mock_info = MagicMock()
    mock_info.language = "fr"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments_data, mock_info)

    # Test with different model sizes
    for model_name in ["tiny", "base", "small", "medium", "large-v2"]:
        with patch(
            "mnemovox.transcriber.WhisperModel", return_value=mock_model
        ) as mock_whisper_model_constructor:
            result = transcribe_file("/fake/path/audio.wav", model_name)
            assert result is not None
            full_text, segments, detected_language = result

            assert full_text == "Test"
            assert len(segments) == 1
            assert detected_language == "fr"
            mock_whisper_model_constructor.assert_called_with(model_name, device="cpu")


def test_transcribe_file_preserves_segment_timing():
    """Test that segment timing information is preserved correctly."""
    mock_segments = [
        MagicMock(start=1.25, end=3.75, text="First", confidence=0.88),
        MagicMock(start=4.0, end=7.33, text="Second", confidence=0.93),
        MagicMock(start=8.1, end=10.5, text="Third", confidence=0.91),
    ]

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, mock_info)

    with patch("mnemovox.transcriber.WhisperModel", return_value=mock_model):
        result = transcribe_file("/fake/path/timing.wav", "base.en")
        assert result is not None
        full_text, segments, detected_language = result

        # Check timing precision is maintained
        assert segments[0]["start"] == 1.25
        assert segments[0]["end"] == 3.75
        assert segments[1]["start"] == 4.0
        assert segments[1]["end"] == 7.33
        assert segments[2]["start"] == 8.1
        assert segments[2]["end"] == 10.5
        assert detected_language == "en"

        # Check full text concatenation
        assert full_text == "First Second Third"


def test_transcribe_file_handles_missing_confidence():
    """Test transcription when confidence is missing from segments."""
    mock_segments = [
        MagicMock(
            start=0.0, end=2.0, text="No confidence", spec=["start", "end", "text"]
        )
    ]
    # Remove confidence attribute
    del mock_segments[0].confidence

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (mock_segments, mock_info)

    with patch("mnemovox.transcriber.WhisperModel", return_value=mock_model):
        result = transcribe_file("/fake/path/no_conf.wav", "base.en")
        assert result is not None
        full_text, segments, detected_language = result

        assert full_text == "No confidence"
        assert segments[0]["confidence"] is None
        assert detected_language == "en"


# Integration tests with real audio file
@pytest.mark.integration
def test_transcribe_real_audio_file_tiny_model():
    """Integration test: transcribe actual audio file using tiny model for speed."""
    audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"

    # Verify the test file exists
    assert audio_path.exists(), f"Test audio file not found: {audio_path}"

    # Use tiny model for fast testing
    try:
        result = transcribe_file(str(audio_path), "tiny")
    except Exception as e:
        pytest.skip(
            f"Whisper model loading failed, likely due to network or system issues: {e}"
        )

    assert result is not None
    full_text, segments, detected_language = result

    # The audio file contains "This is a test"
    assert "test" in full_text.lower()
    assert len(segments) > 0

    # Check that segments have required fields
    for segment in segments:
        assert "start" in segment
        assert "end" in segment
        assert "text" in segment
        assert segment["start"] <= segment["end"]


@pytest.mark.integration
def test_transcribe_real_audio_file_base_model():
    """Integration test: transcribe actual audio file using base model for accuracy."""
    audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"

    # Verify the test file exists
    assert audio_path.exists(), f"Test audio file not found: {audio_path}"

    # Use base model for better accuracy
    try:
        result = transcribe_file(str(audio_path), "base")
    except Exception as e:
        pytest.skip(
            f"Whisper model loading failed, likely due to network or system issues: {e}"
        )

    assert result is not None
    full_text, segments, detected_language = result

    # The audio file should transcribe to something close to "This is a test"
    # Allow for some variation in transcription
    full_text_lower = full_text.lower()
    assert any(word in full_text_lower for word in ["this", "test"])

    # Should have reasonable timing
    assert len(segments) > 0
    total_duration = max(seg["end"] for seg in segments)
    assert 0.5 <= total_duration <= 10.0  # Reasonable duration for the test phrase


@pytest.mark.integration
def test_transcribe_real_audio_file_invalid_path():
    """Integration test: verify error handling with invalid audio path."""
    result = transcribe_file("/nonexistent/path/fake.wav", "tiny")

    assert result is None


@pytest.mark.integration
def test_transcribe_real_audio_file_segment_timing():
    """Integration test: verify segment timing makes sense for real audio."""
    audio_path = Path(__file__).parent / "assets" / "this_is_a_test.wav"

    # Verify the test file exists
    assert audio_path.exists(), f"Test audio file not found: {audio_path}"

    try:
        result = transcribe_file(str(audio_path), "tiny")
    except Exception as e:
        pytest.skip(
            f"Whisper model loading failed, likely due to network or system issues: {e}"
        )

    assert result is not None
    full_text, segments, detected_language = result

    # Segments should be in chronological order
    for i in range(1, len(segments)):
        assert segments[i]["start"] >= segments[i - 1]["start"]

    # No segment should have negative timing
    for segment in segments:
        assert segment["start"] >= 0
        assert segment["end"] >= 0
        assert segment["end"] >= segment["start"]
