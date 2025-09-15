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
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        """Initialize content processor with database and LLM client."""
        # store paths and clients on the instance
        self.db_path = Path(database_path)
        # Allow injecting a custom LLM client for testing
        self.llm_client = llm_client or LLMClient()
        # Backwards-compatible attribute used in some tests
        self.llm = self.llm_client

        logger.info(f"ContentProcessor initialized with database path: {self.db_path}")
        # Keep a lightweight print to aid debugging in some CI environments
        print(f"ContentProcessor initialized with database path: {self.db_path}")

        # Ensure DB schema exists when initializing
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
            # Use the LLM client's `generate`/`extract_entities_relations` if available
            if hasattr(self.llm_client, "extract_entities_relations"):
                extraction_result = self.llm_client.extract_entities_relations(
                    text, source_type, source_path
                )
            elif hasattr(self.llm_client, "generate"):
                # Build a simple extraction prompt and call generate
                prompt = (
                    f"Extract entities and relations from the following text:\n\n{text}"
                )
                resp = self.llm_client.generate(prompt)
                if isinstance(resp, dict):
                    extraction_result = resp
                else:
                    extraction_result = {"entities": [], "relations": []}
            else:
                raise ContentProcessingError("No LLM client methods available")

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

        The implementation is defensive: it will try to reuse existing entities
        when possible (so repeated processing doesn't inflate counts), and will
        create missing entities referenced by relations.
        """

        # Add explicit print statements for debugging (kept lightweight)
        print("=== _store_results method called ===")
        print(f"llm_result keys: {list(llm_result.keys()) if llm_result else 'None'}")
        print(f"source_type: {source_type}")
        print(f"source_path: {source_path}")

        logger.info("Starting to store results in the database")
        logger.info(f"Database path: {self.db_path}")

        entities_created = 0
        entities_existing = 0
        relations_created = 0
        observations_created = 0

        try:
            conn = database.get_connection(str(self.db_path))

            # Process entities
            entity_map = {}
            entities_data = llm_result.get("entities", [])

            for entity_data in entities_data:
                entity_name = (entity_data.get("name") or "").strip()
                if not entity_name:
                    continue

                entity_type = entity_data.get("type", "conceito")

                # Check if entity already exists in DB
                existing = conn.execute(
                    "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
                    (entity_name, entity_type),
                ).fetchone()

                if existing:
                    entity_id = existing[0]
                    entities_existing += 1
                else:
                    entity_id = database.add_entity(
                        conn,
                        name=entity_name,
                        entity_type=entity_type,
                        description=entity_data.get("description", ""),
                    )
                    entities_created += 1

                # store in map for relation resolution
                entity_map[entity_name] = entity_id
                entity_map[entity_name.lower().strip()] = entity_id

                # Add observation when description present
                description = (entity_data.get("description") or "").strip()
                if description:
                    database.add_observation(
                        conn,
                        entity_id=entity_id,
                        content=description,
                        source_type=source_type,
                        source_path=source_path,
                    )
                    observations_created += 1

            # Helper to find an entity id in the current map
            def find_entity_id(name: str) -> Optional[int]:
                if not name:
                    return None
                if name in entity_map:
                    return entity_map[name]
                norm = name.lower().strip()
                return entity_map.get(norm)

            # Helper to create missing entities referenced in relations
            def create_missing_entity(name: str) -> int:
                # Try to find in DB first
                existing_row = conn.execute(
                    "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
                    (name, "conceito"),
                ).fetchone()
                if existing_row:
                    eid = existing_row[0]
                else:
                    eid = database.add_entity(
                        conn,
                        name=name,
                        entity_type="conceito",
                        description="Entidade criada automaticamente a partir de relação",
                    )
                    # increment created
                    nonlocal entities_created
                    entities_created += 1

                entity_map[name] = eid
                entity_map[name.lower().strip()] = eid
                return eid

            # Process relations
            relations_data = llm_result.get("relations", [])
            for relation in relations_data:
                frm = (relation.get("from") or "").strip()
                to = (relation.get("to") or "").strip()
                if not frm or not to:
                    continue

                from_id = find_entity_id(frm)
                if from_id is None:
                    from_id = create_missing_entity(frm)

                to_id = find_entity_id(to)
                if to_id is None:
                    to_id = create_missing_entity(to)

                database.add_relation(
                    conn,
                    from_entity_id=from_id,
                    to_entity_id=to_id,
                    relation_type=relation.get("type", "relacionado_a"),
                    evidence=relation.get("evidence", ""),
                    strength=float(relation.get("strength", 1.0)),
                )
                relations_created += 1

            conn.commit()
            conn.close()

        except Exception as e:
            logger.exception(f"Error storing results: {e}")
            raise

        result = {
            "entities_created": entities_created,
            "entities_existing": entities_existing,
            "relations_created": relations_created,
            "observations_created": observations_created,
        }

        print("=== _store_results completed ===")
        print(f"Result: {result}")

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

    def process_files(self, files: List[Path], source: str = "files") -> Dict[str, Any]:
        """Process uploaded files: images (OCR), PDFs (pdftotext), or others.

        Args:
            files: List of Path objects pointing to saved uploaded files
            source: source label to store in DB

        Returns:
            result dict from process_text
        """
        import subprocess

        aggregated_text = []

        for f in files:
            suffix = f.suffix.lower()
            try:
                if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
                    # Try tesseract
                    try:
                        out_txt = f.with_suffix("")
                        subprocess.run(["tesseract", str(f), str(out_txt)], check=True)
                        txt_path = out_txt.with_suffix(".txt")
                        if txt_path.exists():
                            aggregated_text.append(txt_path.read_text(encoding="utf-8"))
                    except Exception:
                        # fallback placeholder
                        aggregated_text.append(f"[image:{f.name}]")

                elif suffix == ".pdf":
                    # pdftotext
                    try:
                        out_txt = f.with_suffix(".txt")
                        subprocess.run(["pdftotext", str(f), str(out_txt)], check=True)
                        if out_txt.exists():
                            aggregated_text.append(out_txt.read_text(encoding="utf-8"))
                    except Exception:
                        # skip if not available
                        logger.warning("pdftotext not available or failed for %s", f)
                        continue
                else:
                    # Unknown file types: try to read as text
                    try:
                        aggregated_text.append(f.read_text(encoding="utf-8"))
                    except Exception:
                        aggregated_text.append(f"[file:{f.name}]")

            except Exception as e:
                logger.warning(f"Failed processing file {f}: {e}")

        full_text = "\n\n".join(aggregated_text)
        return self.process_text(
            full_text, source_type=source, source_path=",".join([str(p) for p in files])
        )

    def process_video(self, video_path: Path, source: str = "video") -> Dict[str, Any]:
        """Process a video by invoking `video_to_text.sh` and processing the resulting text.

        Args:
            video_path: Path to video file
            source: source label

        Returns:
            result dict from process_text
        """
        import subprocess
        import tempfile

        if not video_path.exists():
            raise ContentProcessingError(f"Video not found: {video_path}")

        with tempfile.TemporaryDirectory() as tmpd:
            # Call the script to produce text output
            try:
                subprocess.run(
                    ["/bin/sh", "video_to_text.sh", "-i", str(video_path), "-o", tmpd],
                    check=True,
                )
            except Exception as e:
                logger.error(f"Video processing failed: {e}")
                raise ContentProcessingError(f"Video processing failed: {e}")

            # Find produced txt file
            out_txts = list(Path(tmpd).glob("**/*.txt"))
            if not out_txts:
                raise ContentProcessingError(
                    "No text output found from video processing"
                )

            # Concatenate and process
            texts = [p.read_text(encoding="utf-8") for p in out_txts]
            full_text = "\n\n".join(texts)
            return self.process_text(
                full_text, source_type=source, source_path=str(video_path)
            )
