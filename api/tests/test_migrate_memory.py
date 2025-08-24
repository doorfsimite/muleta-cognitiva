import json
import os
import sqlite3
import tempfile

from api import database
from api.scripts import migrate_memory


def test_migrate_memory(tmp_path):
    # Create a sample JSONL file
    jsonl_path = tmp_path / "memory.jsonl"
    db_path = tmp_path / "test_migrate.db"
    sample = {
        "entity": {"name": "Entity1", "entity_type": "concept", "description": "desc"},
        "observations": [
            {"content": "Obs1", "source_type": "manual", "source_path": "", "confidence": 0.9}
        ],
        "relations": [
            {"relation_type": "related_to", "to_entity_name": "Entity2", "strength": 0.8, "evidence": "test"}
        ]
    }
    with open(jsonl_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(sample) + "\n")
    # Run migration
    migrate_memory.migrate(str(jsonl_path), str(db_path))
    # Check DB contents
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name, entity_type, description FROM entities ORDER BY name")
    entities = cur.fetchall()
    assert ("Entity1", "concept", "desc") in entities
    assert ("Entity2", None, None) in entities
    cur.execute("SELECT content, source_type, confidence FROM observations")
    obs = cur.fetchone()
    assert obs[0] == "Obs1"
    assert obs[1] == "manual"
    assert abs(obs[2] - 0.9) < 1e-6
    cur.execute("SELECT relation_type, strength, evidence FROM relations")
    rel = cur.fetchone()
    assert rel[0] == "related_to"
    assert abs(rel[1] - 0.8) < 1e-6
    assert rel[2] == "test"
    conn.close()
