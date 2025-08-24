# Database Schema and Migration

## SQLite Schema

The database schema is defined in `api/database.py` and includes tables for entities, observations, relations, spaced repetition cards, argument sequences, assessments, and knowledge gaps. The schema is created automatically if it does not exist.

## Migration Script

The migration script `api/scripts/migrate_memory.py` migrates memory data from a JSONL file to the SQLite database. It expects each line in the JSONL to be a JSON object with keys: `entity`, `observations`, and `relations`.

### Usage

```sh
python api/scripts/migrate_memory.py path/to/memory.jsonl --db path/to/muleta.db
```

## Testing

- Database schema and connection are tested in `api/tests/test_database.py`.
- Migration logic and data integrity are tested in `api/tests/test_migrate_memory.py`.

## Data Integrity

- Entities, observations, and relations are migrated with full data integrity.
- The migration script creates missing entities as needed for relations.

## Example JSONL

```jsonl
{"entity": {"name": "Entity1", "entity_type": "concept", "description": "desc"}, "observations": [{"content": "Obs1", "source_type": "manual", "confidence": 0.9}], "relations": [{"relation_type": "related_to", "to_entity_name": "Entity2", "strength": 0.8, "evidence": "test"}]}
```
