# ABOUTME: Audio utilities for metadata extraction and filename generation
# ABOUTME: Uses ffprobe for metadata and generates unique internal filenames

import subprocess
import json
import time
from uuid import uuid4
from pathlib import Path
from typing import Optional, Dict, Any


def probe_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Extract audio metadata using ffprobe.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Dictionary with metadata or None if extraction fails
    """
    try:
        # Run ffprobe to get JSON metadata
        result = subprocess.run([
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            file_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return None
            
        # Parse JSON output
        data = json.loads(result.stdout)
        
        # Find the audio stream
        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break
        
        if not audio_stream:
            return None
            
        # Extract relevant metadata
        metadata = {
            'duration': float(audio_stream.get('duration', 0)),
            'sample_rate': int(audio_stream.get('sample_rate', 0)),
            'channels': int(audio_stream.get('channels', 0)),
            'format': audio_stream.get('codec_name', ''),
            'file_size': int(data.get('format', {}).get('size', 0))
        }
        
        return metadata
        
    except (subprocess.SubprocessError, json.JSONDecodeError, ValueError, KeyError):
        return None


def generate_internal_filename(original_filename: str) -> str:
    """
    Generate internal filename with timestamp and short UUID.
    
    Args:
        original_filename: Original filename to extract extension from
        
    Returns:
        Generated filename in format: <timestamp>_<shortuuid>.<ext>
    """
    # Get current timestamp in seconds
    timestamp = int(time.time())
    
    # Generate short UUID (8 characters)
    short_uuid = uuid4().hex[:8]
    
    # Extract extension from original filename
    path = Path(original_filename)
    extension = path.suffix
    
    # Combine parts
    if extension:
        return f"{timestamp}_{short_uuid}{extension}"
    else:
        return f"{timestamp}_{short_uuid}"