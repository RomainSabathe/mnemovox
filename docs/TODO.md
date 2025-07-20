# Simple-ish changes, frontend

- [x] Add a search button on the main page (right now we have to use /search)
- [x] The "Upload files directly" button on the main page is broken
- [ ] Show transcription's metadata (model used, time spent,...)
- [x] In the search, highlight in bold the detected terms/words

# Simple-ish changes, backend

- [ ] Add a Docker image and docker build/serving instructions.

# Simple-ish changes, frontend + backend

- [ ] Ability to delete a recording
- [ ] Settings page (default transcription config, LLM config)

# Medium effort

- [ ] Add support for piping to OpenRouter, to open the door to LLM post-processing
- [ ] Upgrade to postgres
- [ ] Add the date of recording in the metadata: either inferred from speech or from
      file metadata
- [ ] Ability to export the DB (for backup). Or export recordings to e.g. Google Drive,
      etc.
- [ ] Support for the new model from HuggingFace
- [ ] When transcribing, actually show a spinning wheel (with percentage), if possible.

# Big works

- [ ] Have the text been retranscribed/reworked through an LLM?
- [ ] Ability to manually edit recordings... (ML use etc.) Big feature. For later. Need
      to implement versioning.
  - [ ] Use the previous corrections to feed the error-correction LLM (0-shot, directly in
        the prompt)
- [ ] Support for API-based transcriptions (e.g. Groq,...). For later, since have to deal with merging
      the chucnks together....
- [ ] Change UI to have: recordings on the left side, transcription on the right. We can
      quickly change from one recording to the next. The search bar is directly integrated
      and dynamically updates the list of recordings on the left.
- [ ] Add fuzzy matching to the search (e.g. via fzf)
