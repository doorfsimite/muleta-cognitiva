import os
import sqlite3
import sys
from pathlib import Path

from api import database
from api.content_processor import ContentProcessor

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))


class DummyLLM:
    def extract_entities_relations(self, text):
        return {
            "entities": [
                {"name": "A", "type": "concept", "description": "descA"},
                {"name": "B", "type": "concept", "description": "descB"},
            ],
            "relations": [
                {"from": "A", "to": "B", "type": "related_to", "evidence": "test"}
            ],
        }


def test_process_text_inserts_entities_and_relations(tmp_path):
    # Use a temp DB
    db_path = tmp_path / "test_content.db"
    # Create schema

    sys.path.insert(0, os.path.abspath("api"))

    database.init_db(db_path)
    processor = ContentProcessor(db_path=db_path, llm_client=DummyLLM())
    processor.process_text("Texto de teste.")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name, entity_type, description FROM entities ORDER BY name")
    entities = cur.fetchall()
    assert ("A", "concept", "descA") in entities
    assert ("B", "concept", "descB") in entities
    cur.execute("SELECT relation_type, evidence FROM relations")
    rel = cur.fetchone()
    assert rel[0] == "related_to"
    assert rel[1] == "test"
    conn.close()
    conn.close()
