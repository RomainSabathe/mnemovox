This codebase has become complex and not necessarily well organized. I want you to go
through each of these items one by one. For each, you will:

- execute them (complete them)
- run the tests
- if they fail, you will iterate in fixing the code (or fixing the tests) and running
  the tests again
- if they succeed, you will commit the changes using `git`, add a descriptive commit
  message and the list of changes you have made.
- Finally, you will cross-out the item in the TODO list you have just accomplished. For
  instance, at this present moment, the item [] Reading instructions has become [X] Reading instructions.

# TODO

- [] Organize the tests in semantically-meaningful directories
- [] Use "transcription_config" instead of "overrides" in the
  `api_retranscribe_recording` function of the `app.py` file.
- [] Have a centralized list for models and languages, rather than having it hard-coded multiple times in the code. For instance, the list of languages is present in `api_retranscribe_recording` and in `recording_detail.html`. They should all fetch this information from a single source of truth.
- [] Have a TranscriptionConfig class to express the transcription params, rather than having to handle the two indepedant params (language/model). This could translate into another table in the DB.
