# MnemoVox

*Mnemosyne + Vox: Memory through Voice*

Self-hosted audio recording manager with automatic transcription using Faster-Whisper.

## Features

- 📁 **File System Monitoring** - Automatically detects new audio files
- 🎤 **Local Transcription** - Uses Faster-Whisper for privacy and speed
- 🌐 **Web Interface** - Clean UI for browsing recordings and transcripts
- 📊 **Metadata Tracking** - SQLite database with detailed audio information
- 🎵 **Audio Playback** - HTML5 audio player with transcript display
- ⚡ **Async Processing** - Concurrent transcription with configurable limits

## Supported Formats

- WAV (`.wav`)
- MP3 (`.mp3`)
- M4A (`.m4a`)

## Requirements

### Docker (Recommended)
- Docker
- Docker Compose

### Manual Installation
- Python 3.9+
- FFmpeg (for audio metadata extraction)
- uv (recommended) or pip

## Installation

### Option 1: Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd mnemovox
   ```

2. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Open your browser:**
   Navigate to `http://localhost:8000`

That's it! The application will automatically create the necessary directories and start monitoring for audio files.

### Option 2: Manual Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd mnemovox
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   # or with pip: pip install -r requirements.txt
   ```

3. **Install FFmpeg:**
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

## Configuration

Edit `config.yaml` to customize settings:

```yaml
monitored_directory: ./incoming          # Where to watch for new files
storage_path: ./data/audio              # Where to store organized files
whisper_model: base.en                  # Whisper model (tiny, base, small, medium, large-v2)
sample_rate: 16000                      # Audio sample rate
max_concurrent_transcriptions: 2        # Parallel transcription limit
```

## Usage

### Docker Usage

1. **Start the application:**
   ```bash
   docker-compose up -d
   ```

2. **Add audio files:**
   Copy audio files to the `./incoming/` directory

3. **View recordings:**
   - Browse all recordings at `http://localhost:8000/recordings`
   - View individual recordings with transcripts at `/recordings/{id}`
   - Use the JSON API at `/api/recordings`

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

5. **View logs:**
   ```bash
   docker-compose logs -f mnemovox
   ```

### Manual Usage

1. **Start the application:**
   ```bash
   python main.py
   ```

2. **Open your browser:**
   Navigate to `http://127.0.0.1:8000`

3. **Add audio files:**
   Copy audio files to the monitored directory (default: `./incoming/`)

4. **View recordings:**
   - Browse all recordings at `/recordings`
   - View individual recordings with transcripts at `/recordings/{id}`
   - Use the JSON API at `/api/recordings`

## Development

Run tests:
```bash
pytest --cov=mnemovox --cov-report=term-missing
```

## Architecture

- **Config Module** - YAML configuration with sensible defaults
- **Database Module** - SQLAlchemy models for metadata storage
- **Audio Utils** - FFprobe integration for metadata extraction
- **Watcher Module** - File system monitoring with Watchdog
- **Transcriber Module** - Faster-Whisper integration
- **Pipeline Module** - Async orchestration of transcription tasks
- **Web App** - FastAPI with Jinja2 templates