- 1. [x] The app has a search functionality that can be accessed with the /search endpoint.
         However, there is no button on the main page (`/`, `templates/recordings_list.html`) to access it. Add a button or a
         link to go to the search page. Find a suitable location for the button or link.
- 2. [x] The app has an upload functionality that can be accessed with the
         `/api/recordings/upload`
         endpoint. This endpoint can be accessed from the API. An front-end implementation is supposed to be accessible from the main page (`templates/recordings_list.html`), but it points to an endpoint that has not been created yet (`/recordings/upload`). You should create this endpoint and the corresponding frontend page.
- 3. [x] In the search page (`templates/search.html`), the results are shown as a list
         of recording filename, search score, an excerpt, etc. This is working well. However,
         I would like the search term(s) to be highlighted in bold in the excerpt. I
         suspect you will need to modify the `app.py:_generate_excerpt` function for this.
- 4. [ ] Recordings cannot be deleted at the moment. You should implement this
         functionality in the backend (deletes the entry in all databases, as well as the
         corresponding audio file) and in the frontend (on the `templates/recordings_list.html`
         page and on the `templates/recording_detail.html`). Deletion SHOULD bring up a
         confirmation pop up.
- 5. [ ] Add a Dockerfile and a docker-compose.yml file to serve the application in a
         self-hosted fashion. Update the README.md accordingly.
