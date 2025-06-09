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

---

Audio Recording Manager – Phase 2 Developer Specification
Version 2.0
Date: [Insert Date]
Prerequisite: Phase 1 MVP (local ingestion + transcription + plain-transcript UI) is fully implemented and stable.

    Phase 2 Goals
    • Add an interactive, synchronized transcript UI (highlight & click-to-seek)
    • Introduce Web-based audio upload
    • Provide a recordings listing page
    • Implement full-text search over transcripts
    • Allow manual re-transcription of recordings

    High-Level Architecture

Backend
– FastAPI (Python 3.9+) with Uvicorn/Gunicorn for async request handling
– SQLite with FTS5 extension for on-disk full-text indexing (or switch to PostgreSQL if preferred)
– A background worker for transcription tasks (e.g. Celery + Redis, RQ, or FastAPI’s built-in BackgroundTasks)

Frontend
– Server-rendered templates via Jinja2 + Vanilla JavaScript (no heavy SPA)
– HTML5 <audio> element for playback
– Fetch API for JSON calls (listings, search, segment data, upload)

Storage
– Audio files in /data/audio/YYYY/YYYY-MM-DD/… (Phase 1)
– Incoming uploads go to a temporary folder (/data/uploads/) before processing
– Transcript segments remain stored as JSON in DB

Configuration
– config.yml (or .env) with keys:
• monitored_directory
• storage_path
• upload_temp_path
• transcription_backend
• fts_enabled: true
• items_per_page: 20

    Data Model & Indexing

3.1 recordings table (extends Phase 1)
• id (UUID PK)
• original_filename, internal_filename, storage_path, import_timestamp,… (unchanged)
• transcript_text (text)
• transcript_segments (JSON)
• transcript_status (pending/complete/error)
• transcript_language
• created_at, updated_at

3.2 Full-Text Search Index
If SQLite:
CREATE VIRTUAL TABLE recordings_fts USING fts5(
transcript_text, original_filename, content='recordings', content_rowid='rowid'
);
On INSERT/UPDATE of recordings:
– Populate / sync recordings_fts with transcript_text + original_filename

    API Endpoints

All endpoints prefixed with /api for JSON, and non-/api for HTML pages.

4.1 Recording Upload
POST /api/recordings/upload
– multipart/form-data: file (audio)
– Response 201 { id, status:"pending", message } or 400 on validation error

4.2 Listings
GET /api/recordings?page=&per_page=
– Params: page (default 1), per_page (configurable)
– Returns JSON list of { id, original_filename, date, duration_seconds, transcript_status }

HTML page: GET /recordings → server-rendered Jinja template that loads the first page via API and paginates

4.3 Recording Details
GET /api/recordings/{id}
– Returns { id, original_filename, audio_url, transcript_text, transcript_language, transcript_status }

GET /api/recordings/{id}/segments
– Returns transcript_segments JSON array:
[ { start, end, text, confidence }, … ]

HTML page: GET /recordings/{id}
– Renders player + transcript container
– JS fetches /segments and wires up highlight/seek

4.4 Re-transcription
POST /api/recordings/{id}/transcribe
– Enqueue transcription job, set transcript_status=pending
– Returns { id, status:"pending" }

4.5 Search
GET /api/search?q=&page=&per_page=
– Validates q length ≥3
– Queries recordings_fts for transcript_text and original_filename
– Returns paginated list of matches with an excerpt and recording metadata

HTML page: GET /search?q=…
– Server-rendered search form + container; initial results loaded via API

    Frontend Interaction

5.1 Synchronized Transcript UI
– On page load (recordings/{id}):

    Render <audio id="player"> with src=audio_url
    Empty <div id="transcript"> placeholder
    JS fetches /segments → builds HTML:
    <span class="segment" data-start="…" data-end="…">…</span>
    Attach event listener “timeupdate” on audio:
    – currentTime = player.currentTime
    – Find active segment (binary search or linear scan)
    – Add CSS class .highlight to the matching span; remove from previous
    On click of a .segment element: player.currentTime = span.dataset.start

5.2 Web Upload Form
– Page GET /recordings/upload: simple form with <input type="file">
– On submit: JS intercepts, performs fetch POST /api/recordings/upload, shows success/error

5.3 Listings & Pagination
– /recordings page: fetch first page, render table/list of recordings
– Prev/Next controls fetch via API

5.4 Search UI
– /search?q=… page: form + results container
– JS on form submit prevents full reload, fetches /api/search, updates container

    Error Handling

6.1 Upload Errors
– Invalid file type → 400 { error:"Unsupported format" }
– Large file limit → 413 Response
– On the frontend, display inline error message

6.2 Transcription Errors
– If transcription backend throws → catch in worker, update DB transcript_status="error" with log
– On detail page, if status=error, show “Transcription failed; retry?” button

6.3 API Errors
– 404 for missing recording → JSON { error:"Not found" }, HTML 404 page
– 422 for invalid query params → JSON validation errors (FastAPI auto)

    Background Tasks & Queue

– Use FastAPI’s BackgroundTasks or Celery:
• Task: run_transcription(recording_id)
– Load file, call faster-whisper, parse result
– Update DB transcript_text + transcript_segments + transcript_status="complete"
– On exception: transcript_status="error", write error log

– Ensure max concurrency = config.max_concurrent_transcriptions

    Testing Plan

8.1 Unit Tests
– API input validation (upload, search query length)
– DB helpers: FTS index sync on insert/update
– Background task: mock faster-whisper, ensure DB updated correctly
– Segment parsing & HTML generation logic

8.2 Integration Tests
– Use FastAPI’s TestClient:
• POST /api/recordings/upload with valid/invalid files
• GET /api/recordings, /api/recordings/{id}, /api/recordings/{id}/segments
• POST /api/recordings/{id}/transcribe → status transitions
• GET /api/search?q=… → correct hits & pagination

8.3 Frontend (E2E) Tests
– Headless browser (Playwright or Selenium):
• Upload a small audio → wait for transcription → load detail page → segments fetched
• Play audio, verify highlight moves as timeupdate fires (mock currentTime)
• Click on a transcript segment → assert audio.currentTime set correctly
• Search for known phrase → results displayed

8.4 Performance Tests
– Seed DB with 1,000 transcripts of ~5 min each → benchmark search latency (<200 ms)
– Upload concurrency test: 5 simultaneous uploads

    Deployment & Configuration

– Dockerfile / docker-compose can orchestrate: FastAPI + Uvicorn + Redis (if Celery) + SQLite volume
– ENV vars override config.yml for:
• STORAGE_PATH, UPLOAD_PATH, REDIS_URL, MAX_TRANSCRIBE_JOBS
– Service startup:

    Run DB migrations (create tables + FTS)

    Start FastAPI server

    Launch worker processes
