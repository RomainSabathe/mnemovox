# Task 6: Add Docker Support for Self-Hosted Deployment

## Problem Analysis

The MnemoVox application currently requires manual installation of Python dependencies, FFmpeg, and configuration setup. To make it easier to deploy in a self-hosted fashion, we need to add Docker support.

## Current Application Structure

- Entry point: `main.py` 
- Dependencies: FastAPI, uvicorn, faster-whisper, watchdog, etc. (defined in pyproject.toml)
- External dependency: FFmpeg (for audio metadata extraction)
- Configuration: `config.yaml` file
- Data persistence: SQLite database and audio files stored in configurable directories
- Default ports: 8000 (web server)

## Implementation Plan

### 1. Create Dockerfile
- Use Python 3.9+ base image 
- Install FFmpeg system dependency
- Install Python dependencies using uv (as recommended in README)
- Copy application code
- Set up proper user permissions
- Configure volumes for data persistence
- Expose port 8000
- Set entrypoint to `python main.py`

### 2. Create docker-compose.yml
- Define the mnemovox service
- Set up volumes for:
  - Configuration file (config.yaml)
  - Data directory (for SQLite DB and audio files)
  - Incoming directory (for file monitoring)
- Map port 8000 to host
- Include environment variable overrides if needed
- Add restart policy

### 3. Update README.md
- Add new "Docker Deployment" section
- Include docker and docker-compose installation instructions
- Provide clear steps for running with Docker
- Document volume mounts and configuration
- Keep existing installation method as alternative

### 4. Consider Configuration
- Ensure paths in config.yaml work within container
- Document how to customize configuration via volume mounts
- Consider if any default paths need adjustment for container environment

## Questions/Considerations

1. Should we create a separate user in the Docker container for security?
2. Do we need any specific file permissions for the monitored directory?
3. Should we support environment variable overrides for configuration?
4. Do we need health checks in the Docker setup?

## Files to Create/Modify

- `Dockerfile` (new)
- `docker-compose.yml` (new) 
- `README.md` (update - add Docker section)
- Potentially `.dockerignore` (new)

## Testing Plan

- Build Docker image successfully
- Run container and verify web interface accessible
- Test file monitoring works with volume mounts
- Verify data persistence across container restarts
- Test with sample audio file upload and transcription