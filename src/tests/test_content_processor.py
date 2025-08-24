import sqlite3
import sys
from pathlib import Path

import pytest

from api import database
from api.content_processor import ContentProcessingError, ContentProcessor

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))


class DummyLLM:
    """Mock LLM client for testing."""

    def extract_entities_relations(self, text, source_type="text", source_path=None):
        return {
            "entities": [
                {
                    "name": "Philosophy",
                    "type": "concept",
                    "description": "Study of fundamental questions",
                },
                {
                    "name": "Socrates",
                    "type": "person",
                    "description": "Ancient Greek philosopher",
                },
            ],
            "relations": [
                {
                    "from": "Socrates",
                    "to": "Philosophy",
                    "type": "practices",
                    "evidence": "Socrates practiced philosophy",
                }
            ],
        }

    def health_check(self):
        return {"status": "ok"}


@pytest.fixture
def temp_processor(tmp_path):
    """Create a content processor with temporary database."""
    db_path = tmp_path / "test_content.db"

    # Create database with schema
    conn = sqlite3.connect(db_path)
    with conn:
        conn.executescript(database.SCHEMA_SQL)
    conn.close()

    return ContentProcessor(str(db_path), DummyLLM())


def test_content_processor_initialization(tmp_path):
    """Test content processor initialization."""
    db_path = tmp_path / "test.db"
    processor = ContentProcessor(str(db_path))
    assert str(processor.db_path) == str(db_path)
    assert processor.llm is not None


def test_process_text_empty_input(temp_processor):
    """Test processing empty text."""
    result = temp_processor.process_text("")
    assert result["success"] is True
    assert result["entities_created"] == 0
    assert result["relations_created"] == 0


def test_process_text_inserts_entities_and_relations(temp_processor):
    """Test that processing text creates entities and relations in database."""
    result = temp_processor.process_text(
        "Socrates was a great philosopher in ancient Greece."
    )

    # Check results
    assert result["success"] is True
    assert result["entities_created"] == 2  # Philosophy and Socrates
    assert result["relations_created"] == 1  # Socrates practices Philosophy
    assert result["observations_created"] > 0

    # Verify data was actually stored
    conn = sqlite3.connect(temp_processor.db_path)
    with conn:
        # Check entities
        entities = conn.execute("SELECT name, entity_type FROM entities").fetchall()
        entity_names = [e[0] for e in entities]
        assert "Philosophy" in entity_names
        assert "Socrates" in entity_names

        # Check relations
        relations = conn.execute("SELECT relation_type FROM relations").fetchall()
        assert len(relations) == 1
        assert relations[0][0] == "practices"

        # Check observations
        observations = conn.execute("SELECT content FROM observations").fetchall()
        assert len(observations) > 0


def test_process_text_duplicate_entities(temp_processor):
    """Test processing text with duplicate entities."""
    # Process text twice
    result1 = temp_processor.process_text("Socrates was a philosopher.")
    result2 = temp_processor.process_text("Socrates taught philosophy.")

    assert result1["entities_created"] == 2
    assert result2["entities_created"] == 0  # No new entities
    assert result2["entities_existing"] == 2  # Both entities already exist


def test_process_text_with_source_info(temp_processor):
    """Test processing with source type and path."""
    result = temp_processor.process_text(
        "Ancient philosophy", source_type="pdf", source_path="/path/to/book.pdf"
    )

    assert result["success"] is True
    assert result["source_type"] == "pdf"
    assert result["source_path"] == "/path/to/book.pdf"


def test_get_entity_stats(temp_processor):
    """Test getting entity statistics."""
    # Add some data first
    temp_processor.process_text("Socrates was a philosopher.")

    stats = temp_processor.get_entity_stats()
    assert stats["total_entities"] == 2
    assert "entity_types" in stats
    assert stats["total_relations"] == 1
    assert stats["total_observations"] > 0


def test_search_entities(temp_processor):
    """Test entity search functionality."""
    # Add some data first
    temp_processor.process_text("Socrates was a philosopher.")

    # Search for entities
    results = temp_processor.search_entities("Socrates")
    assert len(results) == 1
    assert results[0]["name"] == "Socrates"
    assert results[0]["type"] == "person"

    # Search with partial match
    results = temp_processor.search_entities("phil")
    assert len(results) > 0


def test_health_check(temp_processor):
    """Test content processor health check."""
    status = temp_processor.health_check()

    assert "database_path" in status
    assert "database_connectivity" in status
    assert "llm_status" in status
    assert status["database_connectivity"] == "ok"


def test_processing_error_handling(tmp_path):
    """Test error handling in content processing."""

    class FailingLLM:
        def extract_entities_relations(
            self, text, source_type="text", source_path=None
        ):
            raise Exception("LLM extraction failed")

        def health_check(self):
            return {"status": "error"}

    db_path = tmp_path / "test.db"
    processor = ContentProcessor(str(db_path), FailingLLM())

    with pytest.raises(ContentProcessingError):
        processor.process_text("Test content")


def test_invalid_extraction_result(tmp_path):
    """Test handling of invalid extraction results."""

    class InvalidLLM:
        def extract_entities_relations(
            self, text, source_type="text", source_path=None
        ):
            return {"invalid": "format"}  # Missing entities and relations

        def health_check(self):
            return {"status": "ok"}

    db_path = tmp_path / "test.db"

    # Create database with schema
    conn = sqlite3.connect(db_path)
    with conn:
        conn.executescript(database.SCHEMA_SQL)
    conn.close()

    processor = ContentProcessor(str(db_path), InvalidLLM())

    # Should handle gracefully and process empty entities/relations
    result = processor.process_text("Test content")
    assert result["success"] is True
    assert result["entities_created"] == 0
    assert result["relations_created"] == 0
