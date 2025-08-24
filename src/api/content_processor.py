"""
Content processor: uses LLMClient to extract entities/relations and store in DB.
Handles content processing pipeline with proper error handling and validation.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parents[2] / "api"))

from . import database
from .llm_client import LLMClient, LLMError

logger = logging.getLogger(__name__)


class ContentProcessingError(Exception):
    """Exception raised for content processing errors."""

    pass


class ContentProcessor:
    """
    Processes text content using LLM to extract entities and relations,
    then stores the results in the database.
    """

    def __init__(
        self, db_path: Optional[str] = None, llm_client: Optional[LLMClient] = None
    ):
        """
        Initialize content processor.

        Args:
            db_path: Path to SQLite database file
            llm_client: LLM client instance (if None, creates default)
        """
        self.db_path = db_path or database.DB_PATH
        self.llm = llm_client or LLMClient()

        # Ensure database schema exists
        self._ensure_database_schema()

    def _ensure_database_schema(self):
        """Ensure database schema is created."""
        try:
            conn = database.get_connection(self.db_path)
            with conn:
                conn.executescript(database.SCHEMA_SQL)
            logger.info("Database schema verified")
        except Exception as e:
            logger.error(f"Failed to create database schema: {e}")
            raise ContentProcessingError(f"Database schema error: {e}")

    def process_text(
        self, text: str, source_type: str = "text", source_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process text content and extract entities/relations.

        Args:
            text: Input text to process
            source_type: Type of source (text, pdf, video)
            source_path: Path to source file (optional)

        Returns:
            Dictionary with processing results including entity/relation counts

        Raises:
            ContentProcessingError: If processing fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for processing")
            return {
                "success": True,
                "entities_created": 0,
                "relations_created": 0,
                "observations_created": 0,
                "message": "Empty text, nothing to process",
            }

        try:
            # Extract entities and relations using LLM
            logger.info(f"Processing {len(text)} characters of {source_type} content")
            extraction_result = self.llm.extract_entities_relations(
                text, source_type, source_path
            )

            # Validate extraction result
            entities_data = extraction_result.get("entities", [])
            relations_data = extraction_result.get("relations", [])

            if not isinstance(entities_data, list) or not isinstance(
                relations_data, list
            ):
                raise ContentProcessingError("Invalid extraction result format")

            # Store in database
            entity_counts, relation_counts, observation_counts = self._store_results(
                entities_data, relations_data, text, source_type, source_path
            )

            result = {
                "success": True,
                "entities_created": entity_counts["created"],
                "entities_existing": entity_counts["existing"],
                "relations_created": relation_counts["created"],
                "relations_existing": relation_counts["existing"],
                "observations_created": observation_counts,
                "total_entities": len(entities_data),
                "total_relations": len(relations_data),
                "source_type": source_type,
                "source_path": source_path,
            }

            logger.info(
                f"Processing completed: {entity_counts['created']} entities, "
                f"{relation_counts['created']} relations created"
            )

            return result

        except LLMError as e:
            logger.error(f"LLM extraction failed: {e}")
            raise ContentProcessingError(f"Entity extraction failed: {e}")
        except Exception as e:
            logger.error(f"Content processing failed: {e}")
            raise ContentProcessingError(f"Processing error: {e}")

    def _store_results(
        self,
        entities_data: List[Dict],
        relations_data: List[Dict],
        original_text: str,
        source_type: str,
        source_path: Optional[str],
    ) -> Tuple[Dict[str, int], Dict[str, int], int]:
        """
        Store extraction results in database.

        Returns:
            Tuple of (entity_counts, relation_counts, observation_count)
        """
        conn = database.get_connection(self.db_path)
        entity_counts = {"created": 0, "existing": 0}
        relation_counts = {"created": 0, "existing": 0}
        observation_count = 0

        with conn:
            # Store entities and track IDs
            entity_ids = {}

            for entity_data in entities_data:
                entity_name = entity_data.get("name", "").strip()
                entity_type = entity_data.get("type", "concept").strip()
                description = entity_data.get("description", "").strip()

                if not entity_name:
                    continue

                try:
                    # Try to insert new entity
                    cursor = conn.execute(
                        "INSERT INTO entities (name, entity_type, description) VALUES (?, ?, ?)",
                        (entity_name, entity_type, description),
                    )
                    entity_id = cursor.lastrowid
                    entity_ids[entity_name] = entity_id
                    entity_counts["created"] += 1

                    # Add observation linking entity to source content
                    if description and description != entity_name:
                        conn.execute(
                            "INSERT INTO observations (entity_id, content, source_type, source_path) VALUES (?, ?, ?, ?)",
                            (entity_id, description, source_type, source_path),
                        )
                        observation_count += 1

                except database.sqlite3.IntegrityError:
                    # Entity already exists, get its ID
                    row = conn.execute(
                        "SELECT id FROM entities WHERE name = ?", (entity_name,)
                    ).fetchone()
                    if row:
                        entity_ids[entity_name] = row[0]
                        entity_counts["existing"] += 1

                        # Still add observation for existing entity
                        if description and description != entity_name:
                            conn.execute(
                                "INSERT INTO observations (entity_id, content, source_type, source_path) VALUES (?, ?, ?, ?)",
                                (row[0], description, source_type, source_path),
                            )
                            observation_count += 1

            # Store relations
            for relation_data in relations_data:
                from_entity = relation_data.get("from", "").strip()
                to_entity = relation_data.get("to", "").strip()
                relation_type = relation_data.get("type", "related_to").strip()
                evidence = relation_data.get("evidence", "").strip()

                from_id = entity_ids.get(from_entity)
                to_id = entity_ids.get(to_entity)

                if from_id and to_id and from_id != to_id:
                    try:
                        conn.execute(
                            "INSERT INTO relations (from_entity_id, to_entity_id, relation_type, evidence) VALUES (?, ?, ?, ?)",
                            (from_id, to_id, relation_type, evidence),
                        )
                        relation_counts["created"] += 1
                    except database.sqlite3.IntegrityError:
                        relation_counts["existing"] += 1

        return entity_counts, relation_counts, observation_count

    def get_entity_stats(self) -> Dict[str, Any]:
        """Get statistics about entities in the database."""
        try:
            conn = database.get_connection(self.db_path)
            with conn:
                # Count entities by type
                entity_stats = conn.execute(
                    "SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type"
                ).fetchall()

                # Count total relations
                total_relations = conn.execute(
                    "SELECT COUNT(*) FROM relations"
                ).fetchone()[0]

                # Count total observations
                total_observations = conn.execute(
                    "SELECT COUNT(*) FROM observations"
                ).fetchone()[0]

                return {
                    "total_entities": sum(count for _, count in entity_stats),
                    "entity_types": dict(entity_stats),
                    "total_relations": total_relations,
                    "total_observations": total_observations,
                }
        except Exception as e:
            logger.error(f"Failed to get entity stats: {e}")
            return {}

    def search_entities(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search entities by name or description."""
        try:
            conn = database.get_connection(self.db_path)
            with conn:
                results = conn.execute(
                    """SELECT id, name, entity_type, description 
                       FROM entities 
                       WHERE name LIKE ? OR description LIKE ?
                       ORDER BY name
                       LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()

                return [
                    {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "description": row[3],
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """Check content processor health."""
        status = {
            "database_path": str(self.db_path),
            "database_exists": self.db_path.exists()
            if hasattr(self.db_path, "exists")
            else True,
        }

        # Test database connectivity
        try:
            stats = self.get_entity_stats()
            status["database_connectivity"] = "ok"
            status["entity_count"] = stats.get("total_entities", 0)
        except Exception as e:
            status["database_connectivity"] = f"error: {str(e)}"

        # Check LLM health
        try:
            llm_status = self.llm.health_check()
            status["llm_status"] = llm_status
        except Exception as e:
            status["llm_status"] = f"error: {str(e)}"

        return status
