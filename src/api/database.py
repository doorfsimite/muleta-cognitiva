"""
Database schema and connection for Muleta Cognitiva MCP server.
"""

import os
import sqlite3
from pathlib import Path

# Allow overriding DB path via environment for tests/deployments
DB_PATH = Path(os.environ.get("MULETA_DB_PATH", Path(__file__).parent / "muleta.db"))

SCHEMA_SQL = """
-- Entidades centrais
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    entity_type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Observações/notas sobre entidades
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id),
    content TEXT NOT NULL,
    source_type TEXT,
    source_path TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relações entre entidades
CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY,
    from_entity_id INTEGER REFERENCES entities(id),
    to_entity_id INTEGER REFERENCES entities(id),
    relation_type TEXT,
    strength REAL DEFAULT 1.0,
    evidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sistema de revisão espaçada com questões socráticas integradas
CREATE TABLE IF NOT EXISTS spaced_repetition_cards (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    card_type TEXT DEFAULT 'definition',
    socratic_question_type TEXT,
    difficulty INTEGER DEFAULT 3 CHECK(difficulty BETWEEN 1 AND 5),
    next_review DATE,
    review_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de revisões para algoritmo espaçado
CREATE TABLE IF NOT EXISTS card_reviews (
    id INTEGER PRIMARY KEY,
    card_id INTEGER REFERENCES spaced_repetition_cards(id),
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality INTEGER CHECK(quality BETWEEN 1 AND 5),
    response_time INTEGER,
    next_interval INTEGER
);

-- Sequências lógicas argumentativas (fluxogramas)
CREATE TABLE IF NOT EXISTS argument_sequences (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    entity_ids TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Nós do fluxograma argumentativo
CREATE TABLE IF NOT EXISTS argument_nodes (
    id INTEGER PRIMARY KEY,
    sequence_id INTEGER REFERENCES argument_sequences(id),
    node_type TEXT,
    content TEXT NOT NULL,
    entity_id INTEGER REFERENCES entities(id),
    position_x REAL,
    position_y REAL,
    style_config TEXT
);

-- Conexões entre nós do fluxograma
CREATE TABLE IF NOT EXISTS argument_connections (
    id INTEGER PRIMARY KEY,
    sequence_id INTEGER REFERENCES argument_sequences(id),
    from_node_id INTEGER REFERENCES argument_nodes(id),
    to_node_id INTEGER REFERENCES argument_nodes(id),
    connection_type TEXT,
    strength REAL DEFAULT 1.0
);

-- Provas/avaliações
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    topic_entities TEXT,
    difficulty_level INTEGER DEFAULT 3 CHECK(difficulty_level BETWEEN 1 AND 5),
    estimated_duration INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Questões das avaliações
CREATE TABLE IF NOT EXISTS assessment_questions (
    id INTEGER PRIMARY KEY,
    assessment_id INTEGER REFERENCES assessments(id),
    question TEXT NOT NULL,
    question_type TEXT,
    correct_answer TEXT,
    answer_options TEXT,
    points INTEGER DEFAULT 1,
    entity_ids TEXT,
    explanation TEXT
);

-- Tentativas de avaliação
CREATE TABLE IF NOT EXISTS assessment_attempts (
    id INTEGER PRIMARY KEY,
    assessment_id INTEGER REFERENCES assessments(id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    score REAL,
    total_points INTEGER,
    feedback TEXT,
    time_spent INTEGER,
    answers TEXT
);

-- Análise de gaps de conhecimento
CREATE TABLE IF NOT EXISTS knowledge_gaps (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id),
    gap_type TEXT,
    confidence REAL,
    identified_from TEXT,
    suggestion TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_observations_entity ON observations(entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_cards_entity ON spaced_repetition_cards(entity_id);
CREATE INDEX IF NOT EXISTS idx_cards_next_review ON spaced_repetition_cards(next_review);
CREATE INDEX IF NOT EXISTS idx_reviews_card ON card_reviews(card_id);
CREATE INDEX IF NOT EXISTS idx_argument_nodes_sequence ON argument_nodes(sequence_id);
CREATE INDEX IF NOT EXISTS idx_argument_connections_sequence ON argument_connections(sequence_id);
CREATE INDEX IF NOT EXISTS idx_assessment_questions_assessment ON assessment_questions(assessment_id);
"""


def get_connection(db_path=DB_PATH):
    # Create connection with sensible defaults for migrations and integrity
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    # PRAGMAs: enforce foreign keys and use WAL for better concurrency
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    except Exception:
        # Some SQLite builds or paths may not support these; ignore failures
        pass
    return conn


def init_db(db_path=DB_PATH):
    """Initialize the database using the migration runner.

    This will apply any unapplied SQL files from the top-level `migrations/`
    folder and is safer for incremental schema evolution than blindly
    executing the full schema script.
    """
    # import locally to avoid circular imports at module import time
    try:
        from . import migrations as migration_runner
    except Exception:
        # fall back to executing SCHEMA_SQL if migration runner is unavailable
        conn = get_connection(db_path)
        with conn:
            conn.executescript(SCHEMA_SQL)
        conn.close()
        return

    # Ensure migrations are applied to the chosen DB path
    migration_runner.apply_migrations(db_path=Path(db_path))


def add_entity(conn, name: str, entity_type: str, description: str = "") -> int:
    """Add an entity to the database and return its ID.

    Args:
        conn: Database connection
        name: Entity name
        entity_type: Type of entity
        description: Optional description

    Returns:
        Entity ID (int)
    """
    cursor = conn.cursor()

    # Check if entity already exists
    cursor.execute(
        "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
        (name, entity_type),
    )
    existing = cursor.fetchone()

    if existing:
        # Update description if provided and current is empty
        if description and description.strip():
            cursor.execute(
                "UPDATE entities SET description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND (description IS NULL OR description = '')",
                (description, existing[0]),
            )
        return existing[0]

    # Insert new entity
    cursor.execute(
        """INSERT INTO entities (name, entity_type, description, created_at, updated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
        (name, entity_type, description),
    )

    return cursor.lastrowid


def add_observation(
    conn,
    entity_id: int,
    content: str,
    source_type: str = "text",
    source_path: str = "unknown",
    confidence: float = 1.0,
) -> int:
    """Add an observation to the database and return its ID.

    Args:
        conn: Database connection
        entity_id: ID of the entity this observation relates to
        content: Observation content
        source_type: Type of source (text, pdf, video, etc.)
        source_path: Path or identifier of source
        confidence: Confidence score (0.0 to 1.0)

    Returns:
        Observation ID (int)
    """
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO observations (entity_id, content, source_type, source_path, confidence, created_at)
           VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (entity_id, content, source_type, source_path, confidence),
    )

    return cursor.lastrowid


def add_relation(
    conn,
    from_entity_id: int,
    to_entity_id: int,
    relation_type: str,
    evidence: str = "",
    strength: float = 1.0,
) -> int:
    """Add a relation to the database and return its ID.

    Args:
        conn: Database connection
        from_entity_id: ID of the source entity
        to_entity_id: ID of the target entity
        relation_type: Type of relation
        evidence: Evidence or description of the relation
        strength: Strength of the relation (0.0 to 1.0)

    Returns:
        Relation ID (int)
    """
    cursor = conn.cursor()

    # Check if relation already exists
    cursor.execute(
        """SELECT id FROM relations 
           WHERE from_entity_id = ? AND to_entity_id = ? AND relation_type = ?""",
        (from_entity_id, to_entity_id, relation_type),
    )
    existing = cursor.fetchone()

    if existing:
        # Update evidence and strength if provided
        if evidence and evidence.strip():
            cursor.execute(
                """UPDATE relations 
                   SET evidence = ?, strength = ? 
                   WHERE id = ?""",
                (evidence, strength, existing[0]),
            )
        return existing[0]

    # Insert new relation
    cursor.execute(
        """INSERT INTO relations (from_entity_id, to_entity_id, relation_type, evidence, strength, created_at)
           VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (from_entity_id, to_entity_id, relation_type, evidence, strength),
    )

    return cursor.lastrowid


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
