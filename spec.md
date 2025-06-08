📘 Audio Recording Manager  
📦 Developer Specification — Version 1.0

Author: [Client Name]  
Date: [Insert Date]  
Scope: MVP (Minimum Viable Product), Designed for Extension

---

🌟 Overview

The Audio Recording Manager is a self-hosted, single-user system intended to ingest, organize, transcribe, and search through voice recordings. It is tailored for workflows like recording spoken thoughts during walks, with an emphasis on fast access and accurate transcription via local resources.

---

📐 Functional Requirements

✅ 1. File Ingestion

- Audio files can be added by:
  - Dropping new files into a monitored directory (e.g. ~/IncomingRecordings)
  - [Future] Upload via web interface (not part of this spec)
- Valid formats: .wav, .mp3, .m4a (mono is preferred and assumed)
- On detection:
  - Validate audio type and structure
  - Normalize metadata
  - Move file into organized internal storage:
    - /data/audio/YYYY/YYYY-MM-DD/
    - Filename format: <timestamp>\_<short-uuid>.<ext>

✅ 2. Transcription

- Backend: Faster-Whisper (local inference)
- Trigger: Asynchronously post-import
- Output:
  - Full transcript_text (concatenated segments)
  - Segment-level JSON: start, end, text, confidence
  - Language (auto-detected by the model)
- Stored only once, unless manually re-triggered

✅ 3. Metadata Tracking

Stored via a relational database (e.g., SQLite for MVP). Each audio file has:

| Field               | Type        | Notes                                 |
| ------------------- | ----------- | ------------------------------------- |
| id                  | UUID or int | Primary key                           |
| original_filename   | string      | Name when imported                    |
| internal_filename   | string      | Generated on import                   |
| storage_path        | string      | Relative to audio/ directory          |
| import_timestamp    | datetime    | UTC timestamp                         |
| duration_seconds    | float       | Extracted using audio probe           |
| audio_format        | string      | e.g., "mp3"                           |
| sample_rate         | int         | e.g., 16000                           |
| channels            | int         | Usually 1                             |
| file_size_bytes     | int         | On disk                               |
| transcript_status   | enum        | "pending", "complete", "error"        |
| transcript_language | string      | "en", "fr", etc.                      |
| transcript_text     | text        | Full transcript (concatenated string) |
| transcript_segments | JSON        | [{ start, end, text, confidence }]    |
| created_at          | datetime    |                                       |
| updated_at          | datetime    |                                       |

Future fields:

- transcript_text_edited (nullable) for manual corrections
- user_tags (nullable) for filtering/grouping
- summary (nullable) for LLM-generated synopses

✅ 4. Audio Storage

- Final files are moved to /data/audio/YYYY/YYYY-MM-DD/, grouped by date
- Saved as <timestamp>\_<shortuuid>.<ext> to avoid conflicts
- Original filenames are preserved in the metadata DB for reference
- Invalid or failed files go to /data/import_errors/ with log entry

✅ 5. Playback Interface

Phase 1 (MVP):

- Web UI shows:
  - Audio player (HTML5)
  - Plain-text transcript below
- No interactive transcript (highlighting or click-to-seek)

Phase 2 (planned):

- Transcript-follow highlighting as audio plays
- Clickable transcript segments to jump to audio position

✅ 6. Searching (Planned)

Full-text search functionality will be supported later:

- Using SQLite FTS5 or PostgreSQL full-text indexing
- Searchable fields:
  - transcript_text
  - original_filename
  - date/time range
  - length/speaker/language (optional)

---

⚙️ Architecture & Technology Choices

🎯 Components

| Component      | Technology       | Purpose                                 |
| -------------- | ---------------- | --------------------------------------- |
| Web backend    | FastAPI (Python) | Routing, ingestion, templates           |
| Database       | SQLite           | MVP choice; upgrade later to Postgres   |
| File watching  | Watchdog         | React to new files in import dir        |
| Audio metadata | FFmpeg/FFprobe   | Duration, format, channels, etc.        |
| Transcription  | faster-whisper   | On-device Whisper backend (CTranslate2) |
| Frontend       | HTML + Jinja     | Minimal UI                              |
| JSON parsing   | Python stdlib    | Handled during transcription            |

💾 File Structure

└── project-root  
 ├── /data/audio/YYYY/YYYY-MM-DD/  
 ├── /data/import_errors/  
 ├── /incoming/ (watched dir)  
 ├── /scripts/ (optional tools)  
 ├── audio_manager.py (import/transcribe logic)  
 ├── templates/ (UI)  
 └── app.py (web server entry point)

---

🧠 Data Handling Strategy

🗃 Ingestion Pipeline

1. New file appears in watch folder
2. Validate file (correct structure, readable)
3. Move to internal storage folder
4. Extract metadata:
   - Duration, type, channels, etc.
5. Create DB row with metadata
6. Queue job: transcribe
7. Call faster-whisper on stored audio file asynchronously
8. Parse results:
   - Join transcript_text
   - Store all metadata
9. Set transcript_status = complete or error

⚠️ Error Scenarios (and handling)

| Scenario                         | Handling                          |
| -------------------------------- | --------------------------------- |
| Invalid/corrupt audio            | Move to /data/import_errors/, log |
| Transcriber error (timeout, etc) | Log, mark as error in DB          |
| File already exists              | Short UUID ensures uniqueness     |
| Database locked / corrupted      | Log error, retry mechanism        |
| Missing required metadata        | Mark file incomplete in DB        |

---

🔍 Testing Plan

Unit Tests:

- Audio file validator:
  - Accepts MP3, WAV, M4A mono
  - Rejects corrupt/non-audio
- Metadata extraction via FFmpeg probe
- Transcription wrapper (mocked Faster-Whisper)
- Storage path + renaming logic

Integration Tests:

- Full ingestion pipeline:
  - Drop test file → assert DB entry → assert file moved → transcript created
- Failure modes:
  - Drop invalid file → assert error folder
  - Simulate whisper crash

UI Tests:

- Recording playback page loads and renders audio + transcript
- If transcript is missing → display fallback message

Manual Tests:

- Upload a 10-minute voice memo
- Pause/resume playback
- Reload previously imported recordings

---

📄 Configuration Example

config.yml (or .ini/json/yaml file)

```yaml
monitored_directory: /home/user/IncomingRecordings
storage_path: /data/audio
transcription_backend: faster-whisper
whisper_model: base.en
sample_rate: 16000
max_concurrent_transcriptions: 2
```

---

🚦 Future-Ready Design Decisions

✔️ transcript_segments retained in JSON so click-to-seek is easy  
✔️ UI allows fallback display when transcript fails  
✔️ All filenames include UUID to prevent clashes  
✔️ transcript_text_edited field added for later override  
✔️ Modular transcription architecture allows switch to remote APIs later

---

🧩 Phase-Based Roadmap

Phase 1 (MVP - Current Spec):

- Local ingest
- Local faster-whisper
- Plain playback UI
- SQLite DB backend

Phase 2:

- Click-to-seek transcript UI
- Web upload form
- Full-text search
- Re-transcribe option

Phase 3:

- Summarization with LLMs
- Editable transcripts
- Tagging
- Role-based users

Phase 4:

- API access
- Bookmarkable searches
- Smart notifications

---

✅ Final Notes for Developers

- Code base should favor explicit, readable modularity
- Use dependency-injection patterns for transcription backend
- Favor file-path-based discovery over hardcoded filenames
- Keep UI logic and transcription logic completely separate
- Log everything in a developer-facing log file (debug, info, error)

🔗 Dependencies:

- Python 3.9+
- FFmpeg (CLI utilities installed)
- faster-whisper (via pip)
- FastAPI
- SQLite3
- Watchdog (for file import)
