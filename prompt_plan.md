For all these prompts, refer to **@spec.md** to understand the global context of what you
are building.

# Phase 1

```text
PROMPT 1/8: Project Scaffold & Config Loader

Context:
  We are building “Audio Recording Manager” per spec.
  So far, we have only ran `uv init` and only have a miminal pyproject.toml. We need:
    - To extend pyproject.toml with dependencies: FastAPI, watchdog, faster-whisper, pytest, sqlalchemy
    - README.md stub
    - config.yaml sample in project root
    - A `config.py` that loads YAML, provides attributes:
        monitored_directory, storage_path, whisper_model, sample_rate, max_concurrent_transcriptions
    - Defaults if keys are missing.
Approach:
  - Begin with pytest tests in `tests/test_config.py` using tmp_path to write sample YAML and verify loader fields.
  - Then implement `config.py` to satisfy tests.
Request:
  Provide (1) `tests/test_config.py` and (2) `config.py`.
  Use only standard libraries + PyYAML.
  Ensure tests cover missing keys, bad types, and correct override.

End with:
  - All tests passing.
  - `config.py` exposing a `get_config()` function returning a dataclass or namespace.
```

---

```text
PROMPT 2/8: Database Schema & Initialization

Context:
  We have project scaffold and config.get_config().
  Next, implement DB support using SQLAlchemy (or raw sqlite3):
    Table `recordings` matches spec fields.
    Use SQLite; path from config.storage_path + "/metadata.db".
Steps:
  1. Write tests in `tests/test_db.py` to:
     - Initialize DB.
     - Inspect that `recordings` table exists with all columns.
  2. Implement `db.py`:
     - `init_db()` creates DB file and tables.
     - `get_session()` returns SQLAlchemy session (or raw connection).
Request:
  Provide `tests/test_db.py` and `db.py`.
  Wrap in functions for easy imports.
  Tests must pass on empty state.
```

---

```text
PROMPT 3/8: Audio Utilities (probe + filename)

Context:
  We need:
    - `audio_utils.probe_metadata(path: str) -> dict` using ffprobe CLI.
    - `audio_utils.generate_internal_filename(orig_name: str) -> str` producing "<timestamp>_<shortuuid>.<ext>".
Steps:
  1. tests in `tests/test_audio_utils.py`, mocking subprocess output for ffprobe JSON, checking fields.
  2. tests for filename generation pattern and uniqueness.
  3. Implement `audio_utils.py`.
Request:
  Provide tests then implementation.
  Use `subprocess.run` with `capture_output=True`.
  Use `uuid4().hex[:8]` for short uuid.
  Ensure epoch timestamp in seconds.
```

---

```text
PROMPT 4/8: Watcher & Ingestion Pipeline

Context:
  We have config, db, audio_utils.
  Now implement file system watcher:
    - Monitors config.monitored_directory.
    - On new .wav/.mp3/.m4a file:
       a. Copy to temp staging
       b. Call probe_metadata, generate internal_filename
       c. Move to storage_path/YYYY/MM-DD/…
       d. Insert record in DB with transcript_status="pending"
Approach:
  - Write tests in `tests/test_ingest.py` using pytest tmp_path: create a dummy .wav, run one iteration of handler, assert DB row and file moved.
  - Implement `watcher.py` using Watchdog Observer and Handler.
Request:
  Provide `tests/test_ingest.py` and `watcher.py`.
  Use dependency injection for config and db session.
  Ensure idempotency: skip unknown extensions.
```

---

```text
PROMPT 5/8: Transcription Module

Context:
  Now implement `transcriber.py`:
    - Function `transcribe_file(internal_path: str) -> (full_text: str, segments: list)`
    - Use faster-whisper local model from config.whisper_model.
Steps:
  1. tests in `tests/test_transcriber.py` mocking the whisper API call, returning two segments.
  2. implement `transcriber.py` with asynchronous call or sync wrapper.
Request:
  Provide tests + implementation.
  Segments are dicts with start, end, text, confidence.
  full_text = concatenation of texts with spaces.
```

---

```text
PROMPT 6/8: Orchestrate Ingestion → Transcription

Context:
  We have watcher triggering DB inserts, and transcriber.
  Now wire:
    - After insert with status “pending”, schedule transcription (e.g. via asyncio task).
    - On success, update that record’s transcript_status, transcript_text, transcript_segments, transcript_language.
    - On error, set transcript_status="error" and log.
Steps:
  1. Write integration test `tests/test_pipeline.py`: simulate ingestion of a file, then await transcription, assert DB updated.
  2. Implement `pipeline.py` orchestrating.
Request:
  Provide test + implementation.
  Use `asyncio` for concurrency, respect `max_concurrent_transcriptions`.
```

---

```text
PROMPT 7/8: FastAPI Backend & UI

Context:
  Now expose:
    - GET /recordings → list all (from DB), render Jinja `templates/list.html`
    - GET /recordings/{id} → show audio player (`<audio src="…">`) and full transcript.
Steps:
  1. tests in `tests/test_api.py` using FastAPI TestClient: ensure pages 200, expected content.
  2. Create `app.py` with FastAPI, mount static files if needed, configure JinjaTemplates.
  3. Provide `templates/list.html` and `templates/detail.html`.
Request:
  Provide tests, `app.py`, and templates.
  Ensure imports from previous modules for DB and config.
```

---

```text
PROMPT 8/8: CI & Integration Checks

Context:
  All components exist.
  We need a `pytest.ini`, GitHub Actions workflow `.github/workflows/ci.yml` to:
    - Install dependencies
    - Run `pytest --cov`
    - Report pass/fail
Approach:
  - Provide basic CI YAML for python 3.9+
  - Provide `pytest.ini` with markers.
Request:
  Provide both CI config files.
  Ensure on a fresh checkout tests pass.
```

---

Below is Phase 2 broken into:

1. A high-level **Blueprint** (goals, architecture, new components).
2. An **Iterative Chunk Breakdown**: first coarse chunks, then each chunk split into small, safe, test-first steps.
3. A sequence of **Code-Generation Prompts** (to feed an LLM) that build on each other, TDD-driven, wiring everything together.

---

## 1. High-Level Blueprint

### Phase 2 Goals

• Interactive, synchronized transcript UI (highlight & click-to-seek)  
• Web-based audio upload  
• Recordings listing page with pagination  
• Full-text search over transcripts (SQLite FTS5)  
• Manual re-transcription endpoint

### Architecture & Tech Additions

Backend  
• FastAPI + Uvicorn/Gunicorn  
• SQLite w/ FTS5 (or Postgres later)  
• FastAPI BackgroundTasks (or Celery/RQ) for transcription jobs

Frontend  
• Jinja2 + Vanilla JS  
• HTML5 `<audio>`  
• Fetch API for JSON endpoints

New Storage  
• `/data/uploads/` for temporary file uploads  
• Sync FTS index on insert/update

Config Additions  
• upload_temp_path  
• fts_enabled  
• items_per_page

### New API Endpoints

JSON `/api/...`  
• POST `/api/recordings/upload`  
• GET `/api/recordings` (page/per_page)  
• GET `/api/recordings/{id}`  
• GET `/api/recordings/{id}/segments`  
• POST `/api/recordings/{id}/transcribe`  
• GET `/api/search`

HTML pages  
• GET `/recordings` (list + pagination)  
• GET `/recordings/{id}` (player + transcript UI)  
• GET `/search` (search form + results)  
• GET `/recordings/upload` (upload form)

---

Phase 2

```text
PROMPT A/8: Config & FTS Setup ✅ COMPLETED

Context:
  We’ve completed Phase 1. Now Phase 2 needs:
    - config.yaml keys: upload_temp_path, fts_enabled, items_per_page
    - DB init creates FTS5 table `recordings_fts`
    - Helper `sync_fts(recording_id)`

Steps:
  1. Write `tests/test_config_phase2.py` covering loading new keys & defaults.
  2. Update `config.py` for new fields.
  3. Write `tests/test_db_fts.py` verifying:
     - `init_db()` creates `recordings_fts` when fts_enabled
     - `sync_fts()` populates FTS table for a sample recording row
  4. Implement `db.py` changes:
     - In `init_db()`: execute `CREATE VIRTUAL TABLE ...` if enabled
     - Add `sync_fts(session, recording_id)`

Deliver:
  - `tests/test_config_phase2.py`
  - Updated `config.py`
  - `tests/test_db_fts.py`
  - Updated `db.py`
```

---

```text
PROMPT B/8: API Upload Endpoint ✅ COMPLETED

Context:
  Phase 2 requires web upload:
    - POST /api/recordings/upload
    - Use config.upload_temp_path then existing ingestion logic

Steps:
  1. Write `tests/test_api_upload.py` using TestClient:
     - Valid audio → 201 JSON { id, status:"pending" }
     - Invalid ext → 400 JSON { error }
  2. In `app.py`, add `@app.post("/api/recordings/upload")`:
     - Accept `file: UploadFile`
     - Validate extension
     - Save to `upload_temp_path/<uuid>_<orig>`
     - Call existing `ingest_file(path)`
     - Return JSON
  3. Write integration test asserting DB row inserted and file moved.

Deliver:
  - `tests/test_api_upload.py`
  - Updated `app.py` (upload handler)
```

---

```text
PROMPT C/8: Listings & Pagination ✅ COMPLETED

Context:
  We need:
    - GET `/api/recordings?page=&per_page=`
    - GET `/recordings` HTML page (first page server-rendered)

Steps:
  1. Write `tests/test_api_list.py`: default & boundary pagination.
  2. Implement API route in `app.py`.
  3. Create `templates/recordings_list.html` rendering initial page of recordings.
  4. Write `tests/test_page_list.py` asserting HTML response and presence of recordings data.

Deliver:
  - `tests/test_api_list.py`
  - Updated `app.py` (list endpoint)
  - `templates/recordings_list.html`
  - `tests/test_page_list.py`
```

---

```text
PROMPT D/8: Detail Page & Interactive Transcript

Context:
  Phase 2 UI: detail page + JS-driven transcript.

Steps:
  1. Write `tests/test_api_detail.py` for:
     - GET `/api/recordings/{id}`
     - GET `/api/recordings/{id}/segments`
  2. Implement these API handlers in `app.py`.
  3. Create `templates/recording_detail.html` with:
     - `<audio id="player">`
     - `<div id="transcript"></div>`
     - `<script src="/static/js/transcript.js"></script>`
  4. Write `js/transcript.js` (skeleton) and `tests/test_transcript_js.js` for its `buildTranscript()` function.
  5. Write `tests/test_page_detail.py` ensuring page loads and includes player & script tag.

Deliver:
  - `tests/test_api_detail.py`
  - Updated `app.py`
  - `templates/recording_detail.html`
  - `static/js/transcript.js`
  - `tests/test_transcript_js.js`
  - `tests/test_page_detail.py`
```

---

```text
PROMPT E/8: Re-transcription Endpoint

Context:
  We need manual re-transcription trigger:
    - POST `/api/recordings/{id}/transcribe` → sets status pending + enqueues job

Steps:
  1. Write `tests/test_api_retranscribe.py`:
     - POST valid id → 200 {id, status:"pending"} & DB status updated
     - POST invalid id → 404
  2. In `app.py`, add handler using `BackgroundTasks`:
     - Update DB
     - `background_tasks.add_task(run_transcription, id)`
  3. Write integration test verifying job enqueued (mock BackgroundTasks) and DB change.

Deliver:
  - `tests/test_api_retranscribe.py`
  - Updated `app.py`
```

---

```text
PROMPT F/8: Search API & UI

Context:
  Implement full-text search:
    - GET `/api/search?q=&page=&per_page=`
    - GET `/search` page with form + JS

Steps:
  1. Write `tests/test_api_search.py`:
     - q < 3 → 400
     - Valid q → JSON hits with excerpt
  2. Implement API using `session.execute("SELECT ... FROM recordings_fts ...")`.
  3. Create `templates/search.html` with form and `<div id="results">`
  4. Write `static/js/search.js` + `tests/test_search_js.js` testing `renderSearchResults()`.
  5. Write `tests/test_page_search.py` for HTML `/search?q=...`.

Deliver:
  - `tests/test_api_search.py`
  - Updated `app.py`
  - `templates/search.html`
  - `static/js/search.js`
  - `tests/test_search_js.js`
  - `tests/test_page_search.py`
```

---

```text
PROMPT G/8: Background Task Orchestration

Context:
  Tie ingestion & re-transcription into background tasks

Steps:
  1. Write `tests/test_background_task.py` mocking `transcriber.transcribe_file`
     - Ensure `run_transcription(id)` updates DB status/text/segments
  2. In `pipeline.py` or `app.py`, implement `run_transcription(recording_id)`:
     - Load path from DB, call `transcribe_file()`, update DB, sync FTS
     - Exception → status="error"
  3. Wire BackgroundTasks usage in both upload & retranscribe handlers.

Deliver:
  - `tests/test_background_task.py`
  - `pipeline.py` (or update in `app.py`)
```

---

```text
PROMPT H/8: Testing & CI Updates

Context:
  Phase 2 adds new tests & static assets

Steps:
  1. Update `pytest.ini` to include `tests/*_phase2.py` and js tests.
  2. Create `.github/workflows/ci.yml`:
     - Python 3.9+
     - Install deps
     - Run `pytest --cov`
  3. Add/update `README.md` section “Phase 2 Setup & Usage”.

Deliver:
  - Updated `pytest.ini`
  - `.github/workflows/ci.yml`
  - Updated `README.md`
```
