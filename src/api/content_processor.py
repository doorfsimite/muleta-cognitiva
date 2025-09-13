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

# Configure logging to ensure it's visible
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ContentProcessingError(Exception):
    """Exception raised for content processing errors."""

    pass


class ContentProcessor:
    """Processes content and extracts entities/relations using LLM."""

    def __init__(
        self,
        database_path: str = "/Users/davisimite/Documents/muleta-cognitiva/src/api/muleta.db",
    ) -> None:
        """Initialize content processor with database and LLM client."""
        self.db_path = Path(database_path)
        self.llm_client = LLMClient()
        logger.info(f"ContentProcessor initialized with database path: {self.db_path}")
        print(f"ContentProcessor initialized with database path: {self.db_path}")
        self._ensure_database_schema()

    def _ensure_database_schema(self):
        """Ensure database schema is created."""
        try:
            conn = database.get_connection(str(self.db_path))
            with conn:
                conn.executescript(database.SCHEMA_SQL)
            logger.info("Database schema verified")
            print("Database schema verified")
        except Exception as e:
            logger.error(f"Failed to create database schema: {e}")
            print(f"Failed to create database schema: {e}")
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
            extraction_result = self.llm_client.extract_entities_relations(
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
            result = self._store_results(
                extraction_result, source_type, source_path or "unknown"
            )

            result.update(
                {
                    "success": True,
                    "total_entities": len(entities_data),
                    "total_relations": len(relations_data),
                    "source_type": source_type,
                    "source_path": source_path,
                }
            )

            logger.info(
                f"Processing completed: {result.get('entities_created', 0)} entities, "
                f"{result.get('relations_created', 0)} relations created"
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
        llm_result: Dict[str, Any],
        source_type: str = "text",
        source_path: str = "unknown",
    ) -> Dict[str, Any]:
        """Store LLM extraction results in database.

        This method is exposed to allow direct insertion of JSON data
        without going through the LLM extraction process.

        Args:
            llm_result: Dictionary with 'entities' and 'relations' keys
            source_type: Type of source content
            source_path: Path or identifier of source

        Returns:
            Dictionary with creation counts
        """
        # Add explicit print statements for debugging
        print("=== _store_results method called ===")
        print(f"llm_result keys: {list(llm_result.keys()) if llm_result else 'None'}")
        print(f"source_type: {source_type}")
        print(f"source_path: {source_path}")

        logger.info("Starting to store results in the database")
        logger.info(f"Database path: {self.db_path}")

        entities_created = 0
        relations_created = 0
        observations_created = 0

        try:
            print(f"Attempting to connect to database: {self.db_path}")
            conn = database.get_connection(str(self.db_path))
            logger.info("Database connection established")
            print("Database connection established successfully")

            # Process entities
            entity_map = {}  # Map entity names to IDs
            entities_data = llm_result.get("entities", [])
            print(f"Processing {len(entities_data)} entities")

            for i, entity_data in enumerate(entities_data):
                try:
                    entity_name = entity_data.get("name", "").strip()
                    if not entity_name:
                        logger.warning("Skipping entity with empty name")
                        print(f"Skipping entity {i} with empty name")
                        continue

                    print(f"Processing entity {i}: {entity_name}")
                    logger.info(f"Processing entity: {entity_name}")

                    entity_id = database.add_entity(
                        conn,
                        name=entity_name,
                        entity_type=entity_data.get("type", "conceito"),
                        description=entity_data.get("description", ""),
                    )

                    print(f"Entity {entity_name} created/found with ID: {entity_id}")

                    # Store both exact name and normalized name for matching
                    entity_map[entity_name] = entity_id
                    entity_map[entity_name.lower().strip()] = entity_id
                    entities_created += 1

                    # Add observation for the entity
                    description = entity_data.get("description", "").strip()
                    if description:
                        obs_id = database.add_observation(
                            conn,
                            entity_id=entity_id,
                            content=description,
                            source_type=source_type,
                            source_path=source_path,
                        )
                        observations_created += 1
                        print(f"Added observation {obs_id} for entity: {entity_name}")
                        logger.info(f"Added observation for entity: {entity_name}")

                except Exception as e:
                    error_msg = f"Failed to create entity {entity_data.get('name', 'unknown')}: {e}"
                    logger.warning(error_msg)
                    print(f"ERROR: {error_msg}")

            print(
                f"Entity processing complete. Entity map has {len(entity_map)} entries"
            )

            # Helper function to find entity ID by name (with fuzzy matching)
            def find_entity_id(entity_name: str) -> Optional[int]:
                if not entity_name:
                    return None

                # Try exact match first
                if entity_name in entity_map:
                    return entity_map[entity_name]

                # Try case-insensitive match
                normalized_name = entity_name.lower().strip()
                if normalized_name in entity_map:
                    return entity_map[normalized_name]

                # Try to find by similarity (simple approach)
                for existing_name, entity_id in entity_map.items():
                    if existing_name.lower().strip() == normalized_name:
                        return entity_id

                return None

            # Helper function to create missing entity
            def create_missing_entity(entity_name: str) -> int:
                """Create a missing entity referenced in relations."""
                try:
                    print(f"Creating missing entity: {entity_name}")
                    logger.info(f"Creating missing entity: {entity_name}")

                    entity_id = database.add_entity(
                        conn,
                        name=entity_name,
                        entity_type="conceito",
                        description="Entidade criada automaticamente a partir de relação",
                    )

                    # Add to entity_map for future references
                    entity_map[entity_name] = entity_id
                    entity_map[entity_name.lower().strip()] = entity_id

                    print(f"Created missing entity: {entity_name} with ID: {entity_id}")
                    logger.info(f"Created missing entity: {entity_name}")
                    return entity_id
                except Exception as e:
                    error_msg = f"Failed to create missing entity {entity_name}: {e}"
                    logger.error(error_msg)
                    print(f"ERROR: {error_msg}")
                    raise

            # Process relations
            relations_data = llm_result.get("relations", [])
            print(f"Processing {len(relations_data)} relations")

            for i, relation_data in enumerate(relations_data):
                try:
                    from_entity = relation_data.get("from", "").strip()
                    to_entity = relation_data.get("to", "").strip()

                    if not from_entity or not to_entity:
                        logger.warning("Skipping relation with empty entity names")
                        print(f"Skipping relation {i} with empty entity names")
                        continue

                    print(f"Processing relation {i}: {from_entity} -> {to_entity}")
                    logger.info(f"Processing relation: {from_entity} -> {to_entity}")

                    # Find or create from_entity
                    from_entity_id = find_entity_id(from_entity)
                    if from_entity_id is None:
                        print(f"Entity '{from_entity}' not found, creating it")
                        logger.info(
                            f"Creating missing entity referenced in relation: {from_entity}"
                        )
                        from_entity_id = create_missing_entity(from_entity)
                        entities_created += 1

                    # Find or create to_entity
                    to_entity_id = find_entity_id(to_entity)
                    if to_entity_id is None:
                        print(f"Entity '{to_entity}' not found, creating it")
                        logger.info(
                            f"Creating missing entity referenced in relation: {to_entity}"
                        )
                        to_entity_id = create_missing_entity(to_entity)
                        entities_created += 1

                    # Create the relation
                    relation_id = database.add_relation(
                        conn,
                        from_entity_id=from_entity_id,
                        to_entity_id=to_entity_id,
                        relation_type=relation_data.get("type", "relacionado_a"),
                        evidence=relation_data.get("evidence", ""),
                        strength=float(relation_data.get("strength", 1.0)),
                    )
                    relations_created += 1
                    print(
                        f"Created relation {relation_id}: {from_entity} -> {to_entity}"
                    )
                    logger.info(
                        f"Created relation: {from_entity} -> {to_entity} of type {relation_data.get('type', 'relacionado_a')}"
                    )

                except Exception as e:
                    error_msg = (
                        f"Failed to create relation {from_entity} -> {to_entity}: {e}"
                    )
                    logger.warning(error_msg)
                    print(f"ERROR: {error_msg}")

            print("Committing database changes...")
            conn.commit()
            conn.close()
            logger.info("Database changes committed successfully")
            print("Database changes committed successfully")

        except Exception as e:
            error_msg = f"Error storing results: {e}"
            logger.exception(error_msg)
            print(f"FATAL ERROR: {error_msg}")
            raise

        result = {
            "entities_created": entities_created,
            "relations_created": relations_created,
            "observations_created": observations_created,
        }

        print(f"=== _store_results completed ===")
        print(f"Result: {result}")

        logger.info(
            f"Storing results completed: {entities_created} entities, "
            f"{relations_created} relations, {observations_created} observations created"
        )

        return result

    def get_entity_stats(self) -> Dict[str, Any]:
        """Get statistics about entities in the database."""
        try:
            conn = database.get_connection(str(self.db_path))
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
            conn = database.get_connection(str(self.db_path))
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
            "database_exists": self.db_path.exists(),
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
            llm_status = self.llm_client.health_check()
            status["llm_status"] = llm_status
        except Exception as e:
            status["llm_status"] = f"error: {str(e)}"

        return status
