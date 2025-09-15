
## 2025-09-13 — Migration scaffolding added

Added initial migration scaffolding to support safe, incremental schema changes:

- `migrations/001_initial.sql` — extracted initial schema from `src/api/database.py`.
- `src/api/migrations.py` — small Python migration runner that:
	- applies `*.sql` files from `migrations/` in filename order,
	- records applied migrations in an `applied_migrations` table,
	- creates a simple timestamped backup of the DB file before running,
	- sets recommended PRAGMAs (foreign_keys, WAL, synchronous=NORMAL).

Notes:
- Next steps: move SCHEMA_SQL out of `src/api/database.py` (or call the runner from init scripts), add CI job to run migrations against a fresh DB, and add tests for migrations.
