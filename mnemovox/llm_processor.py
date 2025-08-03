# ABOUTME: LLM processing functions for recording analysis
# ABOUTME: Handles async processing of recordings with OpenRouter API

import logging
from typing import Optional

from .config import get_config
from .db import get_session
from .openrouter import OpenRouterError, create_openrouter_client
from .prompts import format_prompt, parse_llm_response
from .utils import get_recording

logger = logging.getLogger(__name__)


async def summarize_recording(recording_id: int, db_path: str) -> None:
    """
    Background task to summarize a recording using OpenRouter API.

    Args:
        recording_id: ID of the recording to summarize
        db_path: Path to the database file
    """
    session = get_session(db_path)

    try:
        # Get recording for additional metadata logging
        recording = get_recording(session, recording_id)
        if not recording:
            return

        # Use the generic LLM processing function
        summary = await process_recording_with_llm(
            recording_id, "summarization", db_path
        )

        if summary:
            # Log the summarization result with additional metadata
            logger.info(
                f"Recording summarization completed: {summary}",
                extra={
                    "recording_id": recording_id,
                    "original_filename": recording.original_filename,
                    "transcript_length": len(recording.transcript_text or ""),
                    "summary_length": len(summary),
                    "summary": summary,
                },
            )
        else:
            logger.warning(f"Summarization failed for recording {recording_id}")

    finally:
        session.close()


async def process_recording_with_llm(
    recording_id: int, task: str, db_path: str
) -> Optional[str]:
    """
    Generic function to process a recording with any LLM task.

    Args:
        recording_id: ID of the recording to process
        task: The LLM task to perform (e.g., "summarization")
        db_path: Path to the database file

    Returns:
        The processed result or None if failed
    """
    config = get_config()
    session = get_session(db_path)

    try:
        # Get the recording from database
        recording = get_recording(session, recording_id)
        if not recording:
            return None

        # Check if transcript is available
        if not recording.transcript_text or recording.transcript_status != "complete":
            logger.warning(
                f"Recording {recording_id} has no transcript available for {task}"
            )
            return None

        # Create OpenRouter client
        try:
            client = await create_openrouter_client(config)
        except OpenRouterError as e:
            logger.error(f"Failed to create OpenRouter client: {e}")
            return None

        # Format the prompt with the transcript text
        prompt = format_prompt(task, transcript_text=recording.transcript_text)

        # Send request to OpenRouter API
        try:
            logger.info(f"Starting {task} for recording {recording_id}")
            response = await client.send_prompt(prompt)

            # Parse the response
            result = parse_llm_response(task, response)

            logger.info(
                f"LLM processing completed for recording {recording_id}, task: {task}"
            )
            return result

        except OpenRouterError as e:
            logger.error(
                f"OpenRouter API error for recording {recording_id}, task {task}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error during {task} for recording {recording_id}: {e}"
            )
            return None

    finally:
        session.close()


async def assess_recording_title(recording_id: int, db_path: str) -> None:
    """
    Background task to assess titles for a recording using OpenRouter API.

    Args:
        recording_id: ID of the recording to assess titles for
        db_path: Path to the database file
    """
    session = get_session(db_path)

    try:
        # Get recording for additional metadata logging
        recording = get_recording(session, recording_id)
        if not recording:
            return

        # Use the generic LLM processing function
        titles = await process_recording_with_llm(
            recording_id, "title_assessment", db_path
        )

        if titles:
            # Log all title suggestions with additional metadata
            titles_text = (
                " | ".join(titles) if isinstance(titles, list) else str(titles)
            )
            logger.info(
                f"Recording title assessment completed: {titles_text}",
                extra={
                    "recording_id": recording_id,
                    "original_filename": recording.original_filename,
                    "transcript_length": len(recording.transcript_text or ""),
                    "title_suggestions": titles,
                    "num_suggestions": len(titles) if isinstance(titles, list) else 1,
                },
            )
        else:
            logger.warning(f"Title assessment failed for recording {recording_id}")

    finally:
        session.close()


async def format_recording(recording_id: int, db_path: str) -> None:
    """
    Background task to format a recording using OpenRouter API.

    Args:
        recording_id: ID of the recording to format
        db_path: Path to the database file
    """
    session = get_session(db_path)

    try:
        # Get recording for additional metadata logging
        recording = get_recording(session, recording_id)
        if not recording:
            return

        # Use the generic LLM processing function
        formatted_text = await process_recording_with_llm(
            recording_id, "formatting", db_path
        )

        if formatted_text:
            # Log the formatting result with additional metadata
            logger.info(
                f"Recording formatting completed: {formatted_text}",
                extra={
                    "recording_id": recording_id,
                    "original_filename": recording.original_filename,
                    "original_length": len(recording.transcript_text or ""),
                    "formatted_length": len(formatted_text),
                    "formatted_text": formatted_text,
                },
            )
        else:
            logger.warning(f"Formatting failed for recording {recording_id}")

    finally:
        session.close()
