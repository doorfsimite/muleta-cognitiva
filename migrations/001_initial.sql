-- 001_initial.sql
-- Initial schema for Muleta Cognitiva (extracted from src/api/database.py SCHEMA_SQL)
-- Entidades centrais
CREATE TABLE
    IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        entity_type TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Observações/notas sobre entidades
CREATE TABLE
    IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY,
        entity_id INTEGER REFERENCES entities (id),
        content TEXT NOT NULL,
        source_type TEXT,
        source_path TEXT,
        confidence REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Relações entre entidades
CREATE TABLE
    IF NOT EXISTS relations (
        id INTEGER PRIMARY KEY,
        from_entity_id INTEGER REFERENCES entities (id),
        to_entity_id INTEGER REFERENCES entities (id),
        relation_type TEXT,
        strength REAL DEFAULT 1.0,
        evidence TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Sistema de revisão espaçada com questões socráticas integradas
CREATE TABLE
    IF NOT EXISTS spaced_repetition_cards (
        id INTEGER PRIMARY KEY,
        entity_id INTEGER REFERENCES entities (id),
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        card_type TEXT DEFAULT 'definition',
        socratic_question_type TEXT,
        difficulty INTEGER DEFAULT 3 CHECK (difficulty BETWEEN 1 AND 5),
        next_review DATE,
        review_count INTEGER DEFAULT 0,
        success_rate REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Histórico de revisões para algoritmo espaçado
CREATE TABLE
    IF NOT EXISTS card_reviews (
        id INTEGER PRIMARY KEY,
        card_id INTEGER REFERENCES spaced_repetition_cards (id),
        reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        quality INTEGER CHECK (quality BETWEEN 1 AND 5),
        response_time INTEGER,
        next_interval INTEGER
    );

-- Sequências lógicas argumentativas (fluxogramas)
CREATE TABLE
    IF NOT EXISTS argument_sequences (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        entity_ids TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Nós do fluxograma argumentativo
CREATE TABLE
    IF NOT EXISTS argument_nodes (
        id INTEGER PRIMARY KEY,
        sequence_id INTEGER REFERENCES argument_sequences (id),
        node_type TEXT,
        content TEXT NOT NULL,
        entity_id INTEGER REFERENCES entities (id),
        position_x REAL,
        position_y REAL,
        style_config TEXT
    );

-- Conexões entre nós do fluxograma
CREATE TABLE
    IF NOT EXISTS argument_connections (
        id INTEGER PRIMARY KEY,
        sequence_id INTEGER REFERENCES argument_sequences (id),
        from_node_id INTEGER REFERENCES argument_nodes (id),
        to_node_id INTEGER REFERENCES argument_nodes (id),
        connection_type TEXT,
        strength REAL DEFAULT 1.0
    );

-- Provas/avaliações
CREATE TABLE
    IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        topic_entities TEXT,
        difficulty_level INTEGER DEFAULT 3 CHECK (difficulty_level BETWEEN 1 AND 5),
        estimated_duration INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Questões das avaliações
CREATE TABLE
    IF NOT EXISTS assessment_questions (
        id INTEGER PRIMARY KEY,
        assessment_id INTEGER REFERENCES assessments (id),
        question TEXT NOT NULL,
        question_type TEXT,
        correct_answer TEXT,
        answer_options TEXT,
        points INTEGER DEFAULT 1,
        entity_ids TEXT,
        explanation TEXT
    );

-- Tentativas de avaliação
CREATE TABLE
    IF NOT EXISTS assessment_attempts (
        id INTEGER PRIMARY KEY,
        assessment_id INTEGER REFERENCES assessments (id),
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        score REAL,
        total_points INTEGER,
        feedback TEXT,
        time_spent INTEGER,
        answers TEXT
    );

-- Análise de gaps de conhecimento
CREATE TABLE
    IF NOT EXISTS knowledge_gaps (
        id INTEGER PRIMARY KEY,
        entity_id INTEGER REFERENCES entities (id),
        gap_type TEXT,
        confidence REAL,
        identified_from TEXT,
        suggestion TEXT,
        resolved BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (entity_type);

CREATE INDEX IF NOT EXISTS idx_entities_name ON entities (name);

CREATE INDEX IF NOT EXISTS idx_observations_entity ON observations (entity_id);

CREATE INDEX IF NOT EXISTS idx_relations_from ON relations (from_entity_id);

CREATE INDEX IF NOT EXISTS idx_relations_to ON relations (to_entity_id);

CREATE INDEX IF NOT EXISTS idx_cards_entity ON spaced_repetition_cards (entity_id);

CREATE INDEX IF NOT EXISTS idx_cards_next_review ON spaced_repetition_cards (next_review);

CREATE INDEX IF NOT EXISTS idx_reviews_card ON card_reviews (card_id);

CREATE INDEX IF NOT EXISTS idx_argument_nodes_sequence ON argument_nodes (sequence_id);

CREATE INDEX IF NOT EXISTS idx_argument_connections_sequence ON argument_connections (sequence_id);

CREATE INDEX IF NOT EXISTS idx_assessment_questions_assessment ON assessment_questions (assessment_id);