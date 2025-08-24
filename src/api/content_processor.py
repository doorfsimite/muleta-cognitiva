"""
Content processor: uses LLMClient to extract entities/relations and store in DB.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "api"))
from . import database
from .llm_client import LLMClient


class ContentProcessor:
    def __init__(self, db_path=None, llm_client=None):
        self.db_path = db_path or database.DB_PATH
        self.llm = llm_client or LLMClient()

    def process_text(self, text: str):
        result = self.llm.extract_entities_relations(text)
        conn = database.get_connection(self.db_path)
        with conn:
            entity_ids = {}
            for ent in result.get("entities", []):
                conn.execute(
                    "INSERT OR IGNORE INTO entities (name, entity_type, description) VALUES (?, ?, ?)",
                    (ent.get("name"), ent.get("type"), ent.get("description")),
                )
                row = conn.execute(
                    "SELECT id FROM entities WHERE name=?", (ent["name"],)
                ).fetchone()
                entity_ids[ent["name"]] = row[0]
            for rel in result.get("relations", []):
                from_id = entity_ids.get(rel.get("from"))
                to_id = entity_ids.get(rel.get("to"))
                if from_id and to_id:
                    conn.execute(
                        "INSERT INTO relations (from_entity_id, to_entity_id, relation_type, evidence) VALUES (?, ?, ?, ?)",
                        (from_id, to_id, rel.get("type"), rel.get("evidence")),
                    )
        return result
