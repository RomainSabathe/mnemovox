# Audio Recording Manager

Self-hosted audio recording manager with automatic transcription using Faster-Whisper.

## Features

- File system monitoring for automatic audio ingestion
- Local transcription using Faster-Whisper
- Web interface for playback and transcript viewing
- Organized storage with metadata tracking

## Setup

1. Install dependencies: `uv sync`
2. Configure settings in `config.yaml`
3. Run the application: `python app.py`

## Configuration

Copy and modify `config.yaml` to customize:
- Monitored directory for incoming audio files
- Storage path for organized files
- Whisper model selection
- Transcription settings