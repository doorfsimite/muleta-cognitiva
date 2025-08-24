"""
Script to migrate memory data from JSONL to SQLite using the schema in database.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import argparse

from database import DB_PATH, get_connection, init_db


def migrate(jsonl_path, db_path=DB_PATH):
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                obj = json.loads(line)
                # Example: expects {"entity": {...}, "observations": [...], "relations": [...]} per line
                entity = obj.get("entity")
                if entity:
                    conn.execute(
                        "INSERT OR IGNORE INTO entities (name, entity_type, description) VALUES (?, ?, ?)",
                        (entity.get("name"), entity.get("entity_type"), entity.get("description"))
                    )
                    entity_id = conn.execute("SELECT id FROM entities WHERE name=?", (entity["name"],)).fetchone()[0]
                else:
                    entity_id = None
                for obs in obj.get("observations", []):
                    conn.execute(
                        "INSERT INTO observations (entity_id, content, source_type, source_path, confidence) VALUES (?, ?, ?, ?, ?)",
                        (entity_id, obs.get("content"), obs.get("source_type"), obs.get("source_path"), obs.get("confidence", 1.0))
                    )
                for rel in obj.get("relations", []):
                    from_id = entity_id
                    to_name = rel.get("to_entity_name")
                    if to_name:
                        to_row = conn.execute("SELECT id FROM entities WHERE name=?", (to_name,)).fetchone()
                        if not to_row:
                            conn.execute("INSERT OR IGNORE INTO entities (name) VALUES (?)", (to_name,))
                            to_row = conn.execute("SELECT id FROM entities WHERE name=?", (to_name,)).fetchone()
                        to_id = to_row[0]
                    else:
                        to_id = None
                    conn.execute(
                        "INSERT INTO relations (from_entity_id, to_entity_id, relation_type, strength, evidence) VALUES (?, ?, ?, ?, ?)",
                        (from_id, to_id, rel.get("relation_type"), rel.get("strength", 1.0), rel.get("evidence"))
                    )
    print(f"Migration complete. Data loaded into {db_path}")

def main():
    parser = argparse.ArgumentParser(description="Migrate memory JSONL to SQLite DB.")
    parser.add_argument("jsonl_path", help="Path to memory.jsonl file")
    parser.add_argument("--db", default=DB_PATH, help="Path to SQLite DB (default: api/muleta.db)")
    args = parser.parse_args()
    migrate(args.jsonl_path, args.db)

if __name__ == "__main__":
    main()
