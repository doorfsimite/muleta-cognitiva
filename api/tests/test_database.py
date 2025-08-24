import os
import sqlite3
from pathlib import Path

from api import database


def test_db_init_and_schema(tmp_path):
    db_path = tmp_path / "test.db"
    database.init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Check main tables exist
    for table in [
        "entities", "observations", "relations", "spaced_repetition_cards",
        "card_reviews", "argument_sequences", "argument_nodes", "argument_connections",
        "assessments", "assessment_questions", "assessment_attempts", "knowledge_gaps"
    ]:
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        assert cur.fetchone(), f"Table {table} missing"
    conn.close()

def test_db_insert_entity(tmp_path):
    db_path = tmp_path / "test2.db"
    database.init_db(db_path)
    conn = database.get_connection(db_path)
    with conn:
        conn.execute("INSERT INTO entities (name, entity_type, description) VALUES (?, ?, ?)",
                     ("Test Entity", "concept", "A test entity"))
        row = conn.execute("SELECT * FROM entities WHERE name=?", ("Test Entity",)).fetchone()
        assert row[1] == "Test Entity"
        assert row[2] == "concept"
        assert row[3] == "A test entity"
    conn.close()
