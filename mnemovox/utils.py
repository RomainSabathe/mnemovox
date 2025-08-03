# ABOUTME: Utility functions shared across modules
# ABOUTME: Contains helper functions for common database operations

import logging
from typing import Optional

from .db import Recording

logger = logging.getLogger(__name__)


def get_recording(session, recording_id: int) -> Optional[Recording]:
    """
    Get a recording by ID with error logging.

    Args:
        session: Database session
        recording_id: ID of the recording to retrieve

    Returns:
        The recording object or None if not found (logs error when not found)
    """
    recording: Optional[Recording] = (
        session.query(Recording).filter_by(id=recording_id).first()
    )
    if not recording:
        logger.error(f"Recording {recording_id} not found")
    return recording
