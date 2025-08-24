"""
MCP server implementation for Muleta Cognitiva with complete tool registration.
Implements Model Context Protocol for GitHub Copilot integration.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Tool:
    """Represents an MCP tool with metadata."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters: Optional[Dict] = None,
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters or {}


class ToolRegistry:
    """Registry for MCP tools with discovery and invocation capabilities."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters: Optional[Dict] = None,
    ):
        """Register a tool with the registry."""
        tool = Tool(name, description, handler, parameters)
        self.tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with metadata."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self.tools.values()
        ]


class MCPServer:
    """Main MCP server implementing the Model Context Protocol."""

    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.registry = ToolRegistry()

        # Initialize content processor
        from .content_processor import ContentProcessor

        self.content_processor = ContentProcessor()

        self._register_tools()

    def _register_tools(self):
        """Register all available MCP tools based on API specification."""

        # Content processing tools
        self.registry.register(
            "process_content",
            "Process text content and extract entities and relationships",
            self._process_content,
            {
                "content": {"type": "string", "description": "Text content to process"},
                "source_type": {
                    "type": "string",
                    "description": "Type of source: text, pdf, or video",
                },
                "source_path": {
                    "type": "string",
                    "description": "Path to source file",
                    "optional": True,
                },
            },
        )

        # Entity management tools
        self.registry.register(
            "get_entities",
            "Retrieve all entities from the knowledge graph",
            self._get_entities,
            {},
        )

        self.registry.register(
            "get_entity",
            "Retrieve a specific entity by ID with observations and relations",
            self._get_entity,
            {
                "entity_id": {
                    "type": "integer",
                    "description": "ID of the entity to retrieve",
                }
            },
        )

        # Spaced repetition tools
        self.registry.register(
            "get_due_cards",
            "Get spaced repetition cards that are due for review",
            self._get_due_cards,
            {},
        )

        self.registry.register(
            "generate_cards",
            "Generate spaced repetition cards for specific entities",
            self._generate_cards,
            {
                "entity_ids": {"type": "array", "description": "List of entity IDs"},
                "card_types": {
                    "type": "array",
                    "description": "Types of cards to generate: definition, socratic, relation",
                },
            },
        )

        self.registry.register(
            "review_card",
            "Record a card review and update scheduling",
            self._review_card,
            {
                "card_id": {
                    "type": "integer",
                    "description": "ID of the card reviewed",
                },
                "quality": {
                    "type": "integer",
                    "description": "Review quality score (1-5)",
                },
                "response_time": {
                    "type": "integer",
                    "description": "Response time in seconds",
                },
            },
        )

        # Socratic questioning tools
        self.registry.register(
            "get_socratic_questions",
            "Generate Socratic questions for an entity",
            self._get_socratic_questions,
            {"entity_id": {"type": "integer", "description": "ID of the entity"}},
        )

        self.registry.register(
            "generate_questions",
            "Generate questions for multiple entities with specific types",
            self._generate_questions,
            {
                "entity_ids": {"type": "array", "description": "List of entity IDs"},
                "question_types": {
                    "type": "array",
                    "description": "Types of questions: why_important, evidence, implications",
                },
            },
        )

        # Argument flowchart tools
        self.registry.register(
            "get_arguments", "Get all argument sequences", self._get_arguments, {}
        )

        self.registry.register(
            "create_argument",
            "Create a new argument sequence flowchart",
            self._create_argument,
            {
                "title": {
                    "type": "string",
                    "description": "Title of the argument sequence",
                },
                "entity_ids": {
                    "type": "array",
                    "description": "List of entity IDs to include",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the argument",
                },
            },
        )

        self.registry.register(
            "get_argument",
            "Get a specific argument sequence with nodes and connections",
            self._get_argument,
            {
                "argument_id": {
                    "type": "integer",
                    "description": "ID of the argument sequence",
                }
            },
        )

        # Assessment tools
        self.registry.register(
            "get_assessments",
            "Get all available assessments",
            self._get_assessments,
            {},
        )

        self.registry.register(
            "create_assessment",
            "Create a new assessment with generated questions",
            self._create_assessment,
            {
                "title": {"type": "string", "description": "Title of the assessment"},
                "entity_ids": {
                    "type": "array",
                    "description": "List of entity IDs to test",
                },
                "difficulty": {
                    "type": "integer",
                    "description": "Difficulty level (1-5)",
                },
                "question_types": {
                    "type": "array",
                    "description": "Types of questions to generate",
                },
            },
        )

        self.registry.register(
            "get_assessment",
            "Get a specific assessment with questions",
            self._get_assessment,
            {
                "assessment_id": {
                    "type": "integer",
                    "description": "ID of the assessment",
                }
            },
        )

        # Knowledge analysis tools
        self.registry.register(
            "get_knowledge_gaps",
            "Analyze and identify knowledge gaps",
            self._get_knowledge_gaps,
            {},
        )

        self.registry.register(
            "get_knowledge_stats",
            "Get overall knowledge statistics and performance metrics",
            self._get_knowledge_stats,
            {},
        )

        # Visualization tools
        self.registry.register(
            "get_visualization_data",
            "Get data formatted for knowledge graph visualization",
            self._get_visualization_data,
            {},
        )

        # Export tools
        self.registry.register(
            "export_anki",
            "Export cards to Anki format",
            self._export_anki,
            {
                "entity_ids": {
                    "type": "array",
                    "description": "List of entity IDs",
                    "optional": True,
                },
                "card_types": {
                    "type": "array",
                    "description": "Types of cards to export",
                    "optional": True,
                },
            },
        )

        # Health check
        self.registry.register(
            "health_check",
            "Check server health and database connectivity",
            self._health_check,
            {},
        )

    # Tool handler methods (placeholder implementations)
    async def _process_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process content and extract entities."""
        try:
            content = args.get("content", "")
            source_type = args.get("source_type", "text")
            source_path = args.get("source_path")

            result = self.content_processor.process_text(
                content, source_type, source_path
            )
            return result

        except Exception as e:
            logger.error(f"Content processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "entities_created": 0,
                "relations_created": 0,
            }

    async def _get_entities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get all entities."""
        try:
            from . import database

            conn = database.get_connection(self.content_processor.db_path)
            with conn:
                rows = conn.execute(
                    "SELECT id, name, entity_type, description, created_at FROM entities ORDER BY name"
                ).fetchall()

                entities = [
                    {
                        "id": row[0],
                        "name": row[1],
                        "entity_type": row[2],
                        "description": row[3],
                        "created_at": row[4],
                    }
                    for row in rows
                ]

                return {"entities": entities}
        except Exception as e:
            logger.error(f"Failed to get entities: {e}")
            return {"entities": [], "error": str(e)}

    async def _get_entity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get specific entity."""
        try:
            entity_id = args.get("entity_id")
            if not entity_id:
                return {"error": "entity_id is required"}

            from . import database

            conn = database.get_connection(self.content_processor.db_path)
            with conn:
                # Get entity info
                entity_row = conn.execute(
                    "SELECT id, name, entity_type, description FROM entities WHERE id = ?",
                    (entity_id,),
                ).fetchone()

                if not entity_row:
                    return {"error": f"Entity with id {entity_id} not found"}

                # Get observations
                observations = conn.execute(
                    "SELECT content, source_type, source_path FROM observations WHERE entity_id = ?",
                    (entity_id,),
                ).fetchall()

                # Get relations (both outgoing and incoming)
                relations = conn.execute(
                    """SELECT r.relation_type, e.name, r.evidence, 'outgoing' as direction
                       FROM relations r JOIN entities e ON r.to_entity_id = e.id 
                       WHERE r.from_entity_id = ?
                       UNION
                       SELECT r.relation_type, e.name, r.evidence, 'incoming' as direction
                       FROM relations r JOIN entities e ON r.from_entity_id = e.id 
                       WHERE r.to_entity_id = ?""",
                    (entity_id, entity_id),
                ).fetchall()

                return {
                    "entity": {
                        "id": entity_row[0],
                        "name": entity_row[1],
                        "type": entity_row[2],
                        "description": entity_row[3],
                        "observations": [
                            {
                                "content": obs[0],
                                "source_type": obs[1],
                                "source_path": obs[2],
                            }
                            for obs in observations
                        ],
                        "relations": [
                            {
                                "type": rel[0],
                                "target": rel[1],
                                "evidence": rel[2],
                                "direction": rel[3],
                            }
                            for rel in relations
                        ],
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return {"error": str(e)}

    async def _get_due_cards(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get due cards."""
        # TODO: Implement with spaced repetition system
        return {"cards": []}

    async def _generate_cards(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cards."""
        # TODO: Implement card generation
        return {"cards_created": 0, "cards": []}

    async def _review_card(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Review a card."""
        # TODO: Implement review recording
        return {"next_review_date": "2025-08-25", "interval_days": 1}

    async def _get_socratic_questions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get Socratic questions for entity."""
        # TODO: Implement Socratic questioning
        return {"questions": []}

    async def _generate_questions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate questions."""
        # TODO: Implement question generation
        return {"questions": []}

    async def _get_arguments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get argument sequences."""
        # TODO: Implement argument retrieval
        return {"sequences": []}

    async def _create_argument(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create argument sequence."""
        # TODO: Implement argument creation
        return {"sequence_id": 1, "nodes_created": 0}

    async def _get_argument(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get specific argument."""
        # TODO: Implement argument retrieval
        return {
            "sequence": {
                "id": args.get("argument_id"),
                "title": "Placeholder",
                "nodes": [],
                "connections": [],
            }
        }

    async def _get_assessments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get assessments."""
        # TODO: Implement assessment retrieval
        return {"assessments": []}

    async def _create_assessment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create assessment."""
        # TODO: Implement assessment creation
        return {"assessment_id": 1, "questions_generated": 0}

    async def _get_assessment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get specific assessment."""
        # TODO: Implement assessment retrieval
        return {
            "assessment": {
                "id": args.get("assessment_id"),
                "title": "Placeholder",
                "questions": [],
                "estimated_duration": 30,
            }
        }

    async def _get_knowledge_gaps(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get knowledge gaps."""
        # TODO: Implement gap analysis
        return {"gaps": []}

    async def _get_knowledge_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get knowledge statistics."""
        # TODO: Implement statistics calculation
        return {
            "entities_count": 0,
            "cards_due": 0,
            "avg_success_rate": 0.0,
            "weak_areas": [],
        }

    async def _get_visualization_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get visualization data."""
        # TODO: Implement visualization data formatting
        return {"nodes": [], "links": [], "categories": []}

    async def _export_anki(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Export to Anki."""
        # TODO: Implement Anki export
        return {"export_path": "/tmp/placeholder.apkg", "cards_exported": 0}

    async def _health_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Health check."""
        try:
            content_processor_status = self.content_processor.health_check()
            return {
                "status": "ok",
                "version": "1.0.0",
                "content_processor": content_processor_status,
                "registered_tools": len(self.registry.tools),
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "version": "1.0.0"}

    async def handle_client(self, reader, writer):
        """Handle individual client connections."""
        addr = writer.get_extra_info("peername")
        logger.info(f"Connection from {addr}")

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                try:
                    msg = json.loads(data.decode().strip())
                except json.JSONDecodeError as e:
                    error_response = {"error": "invalid json", "details": str(e)}
                    writer.write((json.dumps(error_response) + "\n").encode())
                    await writer.drain()
                    continue

                response = await self.handle_message(msg)
                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()

        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Connection closed for {addr}")

    async def handle_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP messages."""
        try:
            message_type = msg.get("type")

            if message_type == "tool_discovery":
                return {"type": "tool_list", "tools": self.registry.list_tools()}
            elif message_type == "invoke_tool":
                tool_name = msg.get("tool")
                if not tool_name:
                    return {"error": "missing tool name"}

                tool = self.registry.get(tool_name)
                if not tool:
                    return {"error": f"tool '{tool_name}' not found"}

                try:
                    args = msg.get("args", {})
                    result = await tool.handler(args)
                    return {"type": "tool_result", "result": result}
                except Exception as e:
                    logger.error(f"Error invoking tool {tool_name}: {e}")
                    return {"error": f"tool execution failed: {str(e)}"}
            else:
                return {"error": f"unknown message type: {message_type}"}

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {"error": f"message handling failed: {str(e)}"}

    async def start(self):
        """Start the MCP server."""
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"MCP server running on {self.host}:{self.port}")
        logger.info(f"Registered {len(self.registry.tools)} tools")

        async with server:
            await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(MCPServer().start())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
