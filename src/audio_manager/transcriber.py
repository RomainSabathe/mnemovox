# ABOUTME: Transcription module using faster-whisper
# ABOUTME: Handles audio file transcription with segment-level details

import logging
from typing import Optional, Tuple, List, Dict, Any
from faster_whisper import WhisperModel

# Configure logging
logger = logging.getLogger(__name__)


def transcribe_file(
    file_path: str, model_name: str = "base.en"
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    """
    Transcribe an audio file using faster-whisper.

    Args:
        file_path: Path to the audio file to transcribe
        model_name: Whisper model to use (e.g., "base.en", "small", "large-v2")

    Returns:
        Tuple of (full_text, segments) or None if transcription fails
        - full_text: Concatenated text from all segments
        - segments: List of segment dictionaries with start, end, text, confidence
    """
    try:
        logger.info(f"Starting transcription of {file_path} with model {model_name}")

        # Load the Whisper model (force CPU to avoid GPU issues in testing)
        model = WhisperModel(model_name, device="cpu")

        # Transcribe the audio file
        segments_generator, info = model.transcribe(file_path)

        # Process segments
        segments = []
        text_parts = []

        for segment in segments_generator:
            # Extract segment information
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": getattr(segment, "confidence", None),
            }

            segments.append(segment_dict)
            text_parts.append(segment.text)

        # Concatenate all text with spaces
        full_text = " ".join(text_parts)

        logger.info(
            f"Transcription completed: {len(segments)} segments, {len(full_text)} characters"
        )

        return full_text, segments

    except Exception as e:
        logger.error(f"Transcription failed for {file_path}: {e}")
        return None
