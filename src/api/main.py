"""
FastAPI server for Muleta Cognitiva MCP server.
Provides REST API endpoints for web visualization and data access.
"""

import sqlite3
from typing import Any, Dict, Optional
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import get_connection, init_db
from .content_processor import ContentProcessor, ContentProcessingError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler."""
    # Startup logic
    init_db()  # Initialize database schema on startup
    yield
    # Shutdown logic
    # Clean up resources, close connections, etc.


app = FastAPI(
    title="Muleta Cognitiva API",
    description="REST API for personal knowledge graph and learning system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handlers
@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(request: Request, exc: sqlite3.Error):
    return JSONResponse(
        status_code=500, content={"detail": f"Database error: {str(exc)}"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"detail": f"Internal server error: {str(exc)}"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "error": str(e)}
        )


# Entity endpoints
@app.get("/api/entities")
async def get_entities(
    entity_type: Optional[str] = None, limit: int = 100, offset: int = 0
):
    """Get all entities with optional filtering by type."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        base_query = """
            SELECT id, name, entity_type, description, created_at, updated_at
            FROM entities
        """

        params = []
        if entity_type:
            base_query += " WHERE entity_type = ?"
            params.append(entity_type)

        base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries, handling both Row objects and tuples
        entities = []
        if rows:
            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description]
            for row in rows:
                if hasattr(row, 'keys'):  # sqlite3.Row object
                    entities.append(dict(row))
                else:  # tuple
                    entities.append(dict(zip(columns, row)))

        # Get total count
        count_query = "SELECT COUNT(*) FROM entities"
        count_params = []
        if entity_type:
            count_query += " WHERE entity_type = ?"
            count_params.append(entity_type)

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]

        conn.close()

        return {
            "entities": entities,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entities/{entity_id}")
async def get_entity(entity_id: int):
    """Get a specific entity with its observations and relations."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get entity
        cursor.execute(
            """
            SELECT id, name, entity_type, description, created_at, updated_at
            FROM entities WHERE id = ?
        """,
            (entity_id,),
        )

        entity_row = cursor.fetchone()
        if not entity_row:
            raise HTTPException(status_code=404, detail="Entity not found")

        entity = dict(entity_row)

        # Get observations
        cursor.execute(
            """
            SELECT id, content, source_type, source_path, confidence, created_at
            FROM observations WHERE entity_id = ?
            ORDER BY created_at DESC
        """,
            (entity_id,),
        )
        entity["observations"] = [dict(row) for row in cursor.fetchall()]

        # Get outgoing relations
        cursor.execute(
            """
            SELECT r.id, r.relation_type, r.strength, r.evidence, r.created_at,
                   e.id as to_entity_id, e.name as to_entity_name, e.entity_type as to_entity_type
            FROM relations r
            JOIN entities e ON r.to_entity_id = e.id
            WHERE r.from_entity_id = ?
            ORDER BY r.created_at DESC
        """,
            (entity_id,),
        )
        entity["outgoing_relations"] = [dict(row) for row in cursor.fetchall()]

        # Get incoming relations
        cursor.execute(
            """
            SELECT r.id, r.relation_type, r.strength, r.evidence, r.created_at,
                   e.id as from_entity_id, e.name as from_entity_name, e.entity_type as from_entity_type
            FROM relations r
            JOIN entities e ON r.from_entity_id = e.id
            WHERE r.to_entity_id = ?
            ORDER BY r.created_at DESC
        """,
            (entity_id,),
        )
        entity["incoming_relations"] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return {"entity": entity}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Relations endpoints
@app.get("/api/relations")
async def get_relations(limit: int = 100, offset: int = 0):
    """Get all relations with entity details."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT r.id, r.relation_type, r.strength, r.evidence, r.created_at,
                   e1.id as from_entity_id, e1.name as from_entity_name, e1.entity_type as from_entity_type,
                   e2.id as to_entity_id, e2.name as to_entity_name, e2.entity_type as to_entity_type
            FROM relations r
            JOIN entities e1 ON r.from_entity_id = e1.id
            JOIN entities e2 ON r.to_entity_id = e2.id
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        relations = [dict(row) for row in cursor.fetchall()]

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM relations")
        total_count = cursor.fetchone()[0]

        conn.close()

        return {
            "relations": relations,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Visualization endpoint
@app.get("/api/visualization")
async def get_visualization_data():
    """Get data formatted for web visualization (nodes and links)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get entities as nodes
        cursor.execute("""
            SELECT id, name, entity_type, description,
                   (SELECT COUNT(*) FROM observations WHERE entity_id = entities.id) as observation_count,
                   (SELECT COUNT(*) FROM relations WHERE from_entity_id = entities.id OR to_entity_id = entities.id) as relation_count
            FROM entities
            ORDER BY created_at DESC
        """)

        nodes = []
        for row in cursor.fetchall():
            entity = dict(row)
            nodes.append(
                {
                    "id": str(entity["id"]),
                    "name": entity["name"],
                    "category": entity["entity_type"] or "unknown",
                    "symbolSize": min(10 + entity["observation_count"] * 2, 50),
                    "value": entity["observation_count"],
                    "label": {"show": True},
                    "tooltip": {
                        "formatter": f"{entity['name']}<br/>Type: {entity['entity_type'] or 'Unknown'}<br/>Observations: {entity['observation_count']}<br/>Relations: {entity['relation_count']}"
                    },
                }
            )

        # Get relations as links
        cursor.execute("""
            SELECT from_entity_id, to_entity_id, relation_type, strength
            FROM relations
        """)

        links = []
        for row in cursor.fetchall():
            relation = dict(row)
            links.append(
                {
                    "source": str(relation["from_entity_id"]),
                    "target": str(relation["to_entity_id"]),
                    "name": relation["relation_type"] or "related_to",
                    "value": relation["strength"] or 1.0,
                    "lineStyle": {"width": max(1, (relation["strength"] or 1.0) * 3)},
                }
            )

        # Get categories for legend
        cursor.execute("""
            SELECT DISTINCT entity_type, COUNT(*) as count
            FROM entities
            WHERE entity_type IS NOT NULL
            GROUP BY entity_type
            ORDER BY count DESC
        """)

        categories = []
        for row in cursor.fetchall():
            category = dict(row)
            categories.append(
                {"name": category["entity_type"], "count": category["count"]}
            )

        conn.close()

        return {
            "nodes": nodes,
            "links": links,
            "categories": categories,
            "summary": {
                "total_entities": len(nodes),
                "total_relations": len(links),
                "entity_types": len(categories),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Statistics endpoint
@app.get("/api/statistics")
async def get_statistics():
    """Get overall system statistics."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        stats = {}

        # Entity statistics
        cursor.execute("SELECT COUNT(*) FROM entities")
        stats["total_entities"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM entities
            WHERE entity_type IS NOT NULL
            GROUP BY entity_type
            ORDER BY count DESC
        """)
        stats["entities_by_type"] = [dict(row) for row in cursor.fetchall()]

        # Observation statistics
        cursor.execute("SELECT COUNT(*) FROM observations")
        stats["total_observations"] = cursor.fetchone()[0]

        # Relation statistics
        cursor.execute("SELECT COUNT(*) FROM relations")
        stats["total_relations"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT relation_type, COUNT(*) as count
            FROM relations
            WHERE relation_type IS NOT NULL
            GROUP BY relation_type
            ORDER BY count DESC
        """)
        stats["relations_by_type"] = [dict(row) for row in cursor.fetchall()]

        # Card statistics (if any exist)
        cursor.execute("SELECT COUNT(*) FROM spaced_repetition_cards")
        stats["total_cards"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM spaced_repetition_cards
            WHERE next_review <= date('now')
        """)
        stats["cards_due"] = cursor.fetchone()[0]

        conn.close()

        return {"statistics": stats}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Content processing endpoint (placeholder for future implementation)
PROCESSING_TIMEOUT_SECONDS = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "60"))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "50000"))
MIN_CONTENT_LENGTH = int(os.getenv("MIN_CONTENT_LENGTH", "10"))


@app.post("/api/content/process")
async def process_content(request: Dict[str, Any]):
    """Process content and extract entities/relations using ContentProcessor."""
    try:
        # Extract and validate payload
        content = (request or {}).get("content", "")
        source_type = (request or {}).get("source_type", "text") or "text"
        source_path = (request or {}).get("source_path", "browser:manual")

        if not content or not isinstance(content, str) or not content.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "O texto é obrigatório",
                    "code": "VALIDATION_ERROR",
                },
            )

        # if len(content) > MAX_CONTENT_LENGTH:
        #     return JSONResponse(
        #         status_code=413,
        #         content={
        #             "success": False,
        #             "error": "O texto excede o limite máximo",
        #             "code": "PAYLOAD_TOO_LARGE",
        #         },
        #     )

        if len(content) < MIN_CONTENT_LENGTH:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "O texto é obrigatório",
                    "code": "VALIDATION_ERROR",
                },
            )

        processor = ContentProcessor()

        # Run processing with timeout in a worker thread to avoid blocking event loop
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    processor.process_text,
                    content,
                    source_type,
                    source_path,
                ),
                timeout=PROCESSING_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "success": False,
                    "error": "Tempo de processamento excedido",
                    "code": "TIMEOUT",
                },
            )

        # Ensure minimal response contract
        response_payload = {
            "success": bool(result.get("success", True)),
            "entities_created": int(result.get("entities_created", 0)),
            "relations_created": int(result.get("relations_created", 0)),
            "observations_created": int(result.get("observations_created", 0)),
        }

        # Include optional diagnostics for QA
        for key in (
            "entities_existing",
            "relations_existing",
            "total_entities",
            "total_relations",
            "source_type",
            "source_path",
        ):
            if key in result:
                response_payload[key] = result[key]

        return JSONResponse(status_code=200, content=response_payload)

    except ContentProcessingError as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "code": "PROCESSING_ERROR",
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Erro interno: {str(e)}",
                "code": "INTERNAL_ERROR",
            },
        )


def main():
    """Start the FastAPI server."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
