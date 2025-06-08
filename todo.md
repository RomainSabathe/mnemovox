# 📝 Audio Recording Manager — TODO Checklist

Use this `todo.md` as your master checklist. Mark each item ✔️ as you complete it.

---

## 📦 1. Project Setup & Scaffolding

- [ ] Create repository and initialize Git
- [ ] Add `pyproject.toml` or `requirements.txt` with:
  - FastAPI
  - watchdog
  - faster-whisper
  - pytest, pytest-asyncio
  - SQLAlchemy (or sqlite3)
  - PyYAML
- [ ] Create top-level directories:
  - `/incoming/` (watched dir)
  - `/data/audio/`
  - `/data/import_errors/`
  - `/scripts/`
  - `/templates/`
  - `/tests/`
- [ ] Add initial `README.md`
- [ ] Add `.gitignore` (Python, virtualenv, **pycache**)

---

## ⚙️ 2. Configuration Loader

- [ ] Create sample `config.yaml` with:
  - `monitored_directory`
  - `storage_path`
  - `transcription_backend`
  - `whisper_model`
  - `sample_rate`
  - `max_concurrent_transcriptions`
- [ ] Write `tests/test_config.py`:
  - [ ] Load valid YAML → correct values
  - [ ] Missing keys → defaults
  - [ ] Invalid types → raise errors
- [ ] Implement `config.py`:
  - [ ] `get_config(): Config`
  - [ ] Validation & defaults

---

## 🗄 3. Database Schema & Initialization

- [ ] Define schema for `recordings` table
- [ ] Write `tests/test_db.py`:
  - [ ] After `init_db()`, table exists
  - [ ] Columns match spec
- [ ] Implement `db.py`:
  - [ ] `init_db(path)`
  - [ ] `get_session()`

---

## 🎧 4. Audio Utilities

- [ ] Write `tests/test_audio_utils.py`:
  - [ ] `probe_metadata()` parses ffprobe JSON
  - [ ] Returns duration, format, sample_rate, channels, file_size_bytes
  - [ ] `generate_internal_filename()` produces `<timestamp>_<uuid8>.<ext>`
- [ ] Implement `audio_utils.py`:
  - [ ] `probe_metadata(path)`
  - [ ] `generate_internal_filename(orig_name)`

---

## 🚀 5. File Watcher & Ingestion

- [ ] Write `tests/test_ingest.py`:
  - [ ] Drop `.wav/.mp3/.m4a` in tmp incoming dir
  - [ ] Handler moves file to `/data/audio/YYYY/MM-DD/`
  - [ ] DB row inserted with `transcript_status="pending"`
  - [ ] Invalid ext → ignored
- [ ] Implement `watcher.py`:
  - [ ] Watchdog observer on `config.monitored_directory`
  - [ ] Ingestion handler
  - [ ] Staging copy, metadata probe, move, DB insert

---

## 📝 6. Transcription Module

- [ ] Write `tests/test_transcriber.py`:
  - [ ] Mock faster-whisper output
  - [ ] Validate `segments` list and `full_text` join
- [ ] Implement `transcriber.py`:
  - [ ] `transcribe_file(path) → (full_text, segments, language)`
  - [ ] Use local faster-whisper API

---

## 🔗 7. Ingestion → Transcription Orchestration

- [ ] Write `tests/test_pipeline.py`:
  - [ ] Simulate ingestion event
  - [ ] Await transcription completion
  - [ ] DB fields updated (`status`, `text`, `segments`, `language`)
- [ ] Implement `pipeline.py`:
  - [ ] Async job scheduling (respect `max_concurrent_transcriptions`)
  - [ ] Error handling & retries
  - [ ] Logging

---

## 🌐 8. FastAPI Backend & Web UI

- [ ] Write `tests/test_api.py`:
  - [ ] GET `/recordings` returns list page (200)
  - [ ] GET `/recordings/{id}` returns detail page with `<audio>` and transcript text
- [ ] Implement `app.py`:
  - [ ] FastAPI app & routes
  - [ ] JinjaTemplates configuration
  - [ ] Static file mounting (if needed)
- [ ] Create templates:
  - [ ] `templates/list.html`
  - [ ] `templates/detail.html`
- [ ] Add basic CSS (optional)

---

## 🧪 9. Testing & CI

- [ ] Add `pytest.ini` (markers, test paths)
- [ ] Add `tox.ini` or GitHub Actions workflow:
  - [ ] Install dependencies
  - [ ] Run `pytest --cov`
  - [ ] Fail on coverage < threshold
- [ ] Add pre-commit hooks:
  - [ ] Black
  - [ ] isort
  - [ ] Flake8

---

## 📖 10. Documentation & Final Touches

- [ ] Update `README.md` with:
  - [ ] Setup instructions
  - [ ] Config format
  - [ ] How to run watcher & app
  - [ ] Testing instructions
- [ ] Add sample `config.yaml.example`
- [ ] Add LICENSE file (if needed)
- [ ] Verify end-to-end manually:
  - [ ] Drop sample audio → DB + transcription → Web UI playback

---

## ✅ 11. Future Extensions (not for MVP)

- [ ] Web upload endpoint
- [ ] Full-text search (SQLite FTS5)
- [ ] Click-to-seek transcript UI
- [ ] Manual transcript editing & re-transcription
- [ ] LLM summarization & tagging
