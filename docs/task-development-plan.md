Task approach: Backend-first incremental API + mocked LLM (recommended)
	- Pros: Builds a stable API contract (/api/content/process) first; easier deterministic tests by mocking LLM; aligns with requirement to use FastAPI and local LLM in runtime.
	- Cons: Frontend UX is minimal initially.
	- Risks: Need to ensure DB migration/reset is safe; invoking video processing script must be orchestrated reliably.
	- Impact on tests/migrations: Tests will mock LLM and heavy processing; DB migrations may reset data (allowed).
	- Rationale: Matches repository, CI/testing needs, and user preference. Selected.

Scope definition

- In scope:
	- Implement `POST /api/content/process` (FastAPI) with text and file uploads.
	- `content_processor` with text/image/video processing (video invokes `video_to_text.sh`).
	- DB helper with `ensure_schema` and `reset_db` utilities.
	- Tests (pytest) mocking LLM and heavy processing.
	- Minimal frontend panel in `index.html` that calls the endpoint and supports AbortController.

- Out of scope:
	- Optimizing the video processing pipeline (script is present and used).
	- Advanced LLM prompt engineering beyond a basic extraction prompt.
	- Full UI visualizations (ECharts) — only minimal panel is required now.

---

A) Development plan summary

- Concise summary:
	- Implement a FastAPI `POST /api/content/process` endpoint backed by a modular `content_processor` and a SQLite DB helper.
	- The `content_processor` accepts text or files; videos are processed by invoking `video_to_text.sh` to obtain OCR text; runtime LLM calls use the local llama HTTP endpoint (`http://localhost:11434/api/generate`); tests mock LLM calls.

- Current state and target state:
	- Current: docs + video script + skeleton server present.
	- Target: working API, processor, DB migration/reset, tests, and minimal UI panel.

- Related subjects to give context:
	- Use `requests`/`httpx` for LLM calls at runtime; in tests, monkeypatch `LLMClient.generate`.
	- Use `subprocess` to run `video_to_text.sh` reliably and read its output file.
	- Use `sqlite3` for a simple DB helper with idempotent schema creation.


B) Development plan (granular, incremental)

Steps (6) — each independently runnable and verifiable:
1. Add DB helper and migration/reset utilities.
2. Implement `content_processor` with LLM client and video invocation.
3. Add FastAPI route `POST /api/content/process` and wire into the app.
4. Add unit & integration tests (db, processor, route). LLM calls are mocked in tests.
5. Add minimal frontend panel to `index.html` with AbortController and `refreshData()` call.
6. Add test runner entry to `pyproject.toml` and ensure `scripts/serve_web.py` calls `ensure_schema` on startup.


C) Step Instructions

Step Prompt template (each step follows this structure)

- Title: Add DB helper and migration/reset utilities
- Goal: Create a lightweight SQLite DB helper that ensures schema exists and allows reset for development.
- General context:
	- Repository paths to inspect/change: `src/api/db.py`, `scripts/serve_web.py`, `pyproject.toml`
	- Relevant modules/classes/functions: `db.ensure_schema(db_path)`, `db.get_connection(db_path)`, `db.insert_entities(...)`
	- Dependencies/libraries involved: `sqlite3`, `pathlib`
- Design and implementation details (concrete and code-ready):
	- Implement `src/api/db.py` with functions:
		- `get_connection(db_path: str) -> sqlite3.Connection` (PRAGMA setup, check_same_thread=False)
		- `ensure_schema(db_path: str)` — creates tables if missing: `entities`, `relations`, `observations`.
		- `reset_db(db_path: str)` — drops and recreates schema (development only).
		- `insert_entities(conn, entities: List[dict]) -> List[int]` (batch insert inside transaction)
	- Table minimal schemas:
		- `entities(id INTEGER PRIMARY KEY, name TEXT, text TEXT, source TEXT, created_at TEXT)`
		- `relations(id INTEGER PRIMARY KEY, subject_id INTEGER, object_id INTEGER, type TEXT, metadata TEXT, created_at TEXT)`
		- `observations(id INTEGER PRIMARY KEY, entity_id INTEGER, text TEXT, source TEXT, created_at TEXT)`
	- Call `ensure_schema` during app startup in `scripts/serve_web.py`.
- Algorithm/flow:
	1. `get_connection` opens sqlite3 connection and applies PRAGMA settings.
	2. `ensure_schema` runs `CREATE TABLE IF NOT EXISTS` statements.
	3. Insert functions use transactions and `executemany`.
- Tests to implement now (tests-first):
	- New test file: `src/tests/test_db.py`
	- Test cases:
		- Happy path: `ensure_schema` creates tables; `insert_entities` returns ids and rows present.
		- Reset path: `reset_db` clears tables.
		- Edge: inserting empty list returns empty list.
- Acceptance criteria:
	- `ensure_schema` creates three tables without error.
	- Insert functions return predictable ids and persistence is verifiable.


- Title: Implement content_processor with LLM client and video invocation
- Goal: Add `src/api/content_processor.py` implementing `process_text`, `process_files`, `process_video` and an `LLMClient` that calls `http://localhost:11434/api/generate` at runtime; in tests the LLM calls are mocked.
- General context:
	- Repository paths: `src/api/content_processor.py`, `src/api/db.py`, `video_to_text.sh`.
	- Relevant functions: `content_processor.process_text`, `process_files`, `process_video`; `LLMClient.generate`.
	- Dependencies: `httpx` or `requests`, `subprocess`, `tempfile`, `pathlib`.
- Design and implementation details:
	- Implement `LLMClient.generate(prompt: str, model: str = "deepseek-r1:8b") -> dict` that POSTs JSON to `http://localhost:11434/api/generate` and returns parsed JSON.
	- `process_text(text, source, db_path)`:
		- Validate length (10..50000)
		- Build prompt and call `LLMClient.generate`.
		- Parse LLM response for entities/relations/observations (assume JSON or use simple heuristics).
		- Persist using `db.insert_*` and return summary dict.
	- `process_files(files, source, db_path)`:
		- For images call `tesseract` via subprocess if available; fallback to placeholder.
		- For PDFs use `pdftotext` if available; fallback to skip.
		- Aggregate extracted text and call `process_text`.
	- `process_video(video_path, source, db_path)`:
		- Run `video_to_text.sh -i <video> -o <tempdir>` via subprocess.
		- Read generated text file and call `process_text`.
- Algorithm/flow:
	1. Validate input.
	2. Extract text (direct, file OCR, or video script).
	3. Call LLM client to extract structured info.
	4. Persist via DB helper.
	5. Return summary with counts and ids.
- Tests to implement now:
	- New test file: `src/tests/test_content_processor.py`
	- Cases:
		- Happy path: `process_text` with mocked LLM returns counts and persists.
		- `process_video`: mock `subprocess.run` to create output text file and assert processing.
		- Edge: short text raises validation error.
- Acceptance criteria:
	- `process_text` returns integer counts and persists rows.
	- `process_video` invokes the script (or mocked call) and processes the resulting text.


- Title: Add FastAPI route POST /api/content/process
- Goal: Implement HTTP endpoint that validates requests, accepts text and multipart files, delegates to the content_processor, and returns summary JSON.
- General context:
	- Repository paths: `src/api/process_route.py`, `scripts/serve_web.py`, `index.html`.
	- Relevant modules: FastAPI `APIRouter`, `UploadFile`, `content_processor`.
	- Dependencies: `fastapi`, `pydantic`, `starlette`.
- Design and implementation details:
	- Implement POST `/api/content/process` accepting either JSON or multipart/form-data.
	- Validation: `text` min 10 / max 50000, or at least one file.
	- Save uploaded files to a secure tempdir and call `content_processor.process_*` based on file types.
	- Return `{entities_created, relations_created, observations_created, details}`.
	- Include structured logging and timing.
	- Wire router into the main app in `scripts/serve_web.py`.
- Algorithm/flow:
	1. Parse request.
	2. Save files to tempdir.
	3. Choose processing function: `process_video` for video files, else `process_files` or `process_text`.
	4. Return JSON or HTTP error status as needed.
- Tests to implement now:
	- New test file: `src/tests/test_process_route.py`
	- Cases:
		- Happy path: valid JSON text returns 200 (mock `content_processor.process_text`).
		- Multipart image/video: route accepts and delegates (mock processor).
		- Edge: short text returns 400.
		- Failure: processor raises -> 500.
- Acceptance criteria:
	- Endpoint reachable and returns expected JSON for valid inputs.
	- Validation errors return 400; processor exceptions map to 500.


- Title: Add unit & integration tests and CI test entry
- Goal: Add pytest tests for DB, processor and route; ensure LLM calls are mocked in tests, and add a test runner entry in `pyproject.toml`.
- General context:
	- Paths: `src/tests/*`, `pyproject.toml`.
	- Dependencies: `pytest`, `httpx`, `pytest-mock`, `pytest-asyncio` if needed.
- Design and implementation details:
	- Write tests as described above, use `tmp_path` for temp DB and tempdirs.
	- Use monkeypatch to stub `LLMClient.generate` and `subprocess.run`.
	- Add a `[tool.pytest.ini_options]` or `scripts` entry in `pyproject.toml` for `pytest`.
- Tests to implement now:
	- `src/tests/test_db.py`, `src/tests/test_content_processor.py`, `src/tests/test_process_route.py`.
- Acceptance criteria:
	- `pytest` runs and all new tests pass locally without calling the real LLM.


- Title: Add minimal frontend panel and wire to API
- Goal: Add a "Process Text" sidebar panel to `index.html` that posts to `/api/content/process` (supports AbortController), displays summary and calls `refreshData()`.
- General context:
	- Paths: `index.html`.
	- Relevant functions: `processText()` JS implementation.
- Design and implementation details:
	- Add a textarea (minlength=10), source input (default `browser:manual`), file input for files, a Process button and a Cancel button using `AbortController`.
	- Send JSON body for text-only submissions; use `FormData` for files.
	- On success, display summary and call `window.refreshData()` if available.
	- Show user-friendly errors for validation/network/timeout.
- Tests to implement now:
	- Manual UI validation steps only (no automated UI tests now).
- Acceptance criteria:
	- With the API running, the panel submits successfully and displays the summary.


How to run & validate during development
- Start API: use `sh start_api.sh` or run `scripts/serve_web.py` directly after ensuring dependencies are installed.
- Run tests: `pytest`
- Manual UI check: open `index.html` and use the Process Text panel with the API running.

References and files to inspect when implementing
- `docs/overview.md`, `docs/UI-documentation.md`
- `video_to_text.sh`
- `scripts/serve_web.py`, `start_api.sh`
- `index.html`
- `pyproject.toml`, `muleta.db`, `knowledge.db`
- `src/api` and `src/tests`


Requirements coverage checklist (for this task)
- Implement `POST /api/content/process` -> Planned
- Use `video_to_text.sh` for video processing -> Planned
- Use local LLM runtime at `http://localhost:11434/api/generate` (mocked in tests) -> Planned
- FastAPI only for server framework -> Planned
- DB reset support -> Planned
- Minimal UI panel with AbortController -> Planned

---

If you'd like, I can now create the initial skeleton files for step 1 (the DB helper) and step 3 (the route) and the matching tests and run the test suite. I marked the main todo as in-progress in the task list and left the rest not-started.

