"""
Additional database-specific tests for the API.
"""

import os
import sqlite3
import tempfile

from fastapi.testclient import TestClient

from api.database import get_connection, init_db
from api.main import app


class TestDatabaseCRUDOperations:
    """Test actual database CRUD operations through the API."""

    def setup_method(self):
        """Setup test database for each test."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.test_db_path = self.test_db.name
        self.test_db.close()

        # Initialize test database
        conn = sqlite3.connect(self.test_db_path)
        conn.row_factory = sqlite3.Row

        # Execute schema creation
        from api.database import SCHEMA_SQL

        conn.executescript(SCHEMA_SQL)

        # Insert test data
        conn.execute("""
            INSERT INTO entities (name, entity_type, description)
            VALUES ('Test Entity', 'concept', 'A test entity for API testing')
        """)

        conn.execute("""
            INSERT INTO observations (entity_id, content, source_type, confidence)
            VALUES (1, 'Test observation content', 'text', 0.9)
        """)

        conn.commit()
        conn.close()

        # Patch the database path in the app
        import api.main

        self.original_get_connection = api.main.get_connection

        def test_get_connection():
            conn = sqlite3.connect(self.test_db_path)
            conn.row_factory = sqlite3.Row
            return conn

        api.main.get_connection = test_get_connection

        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test database."""
        # Restore original connection function
        import api.main

        api.main.get_connection = self.original_get_connection

        # Remove test database file
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_get_entities_with_test_data(self):
        """Test getting entities with actual test data."""
        response = self.client.get("/api/entities")

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert len(data["entities"]) == 1

        entity = data["entities"][0]
        assert entity["name"] == "Test Entity"
        assert entity["entity_type"] == "concept"
        assert entity["description"] == "A test entity for API testing"

    def test_get_specific_entity_with_relations(self):
        """Test getting a specific entity with its observations."""
        response = self.client.get("/api/entities/1")

        assert response.status_code == 200
        data = response.json()

        entity = data["entity"]
        assert entity["name"] == "Test Entity"
        assert len(entity["observations"]) == 1
        assert entity["observations"][0]["content"] == "Test observation content"
        assert len(entity["outgoing_relations"]) == 0
        assert len(entity["incoming_relations"]) == 0

    def test_visualization_with_test_data(self):
        """Test visualization endpoint with test data."""
        response = self.client.get("/api/visualization")

        assert response.status_code == 200
        data = response.json()

        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "Test Entity"
        assert data["nodes"][0]["category"] == "concept"
        assert data["summary"]["total_entities"] == 1
        assert data["summary"]["total_relations"] == 0

    def test_statistics_with_test_data(self):
        """Test statistics endpoint with test data."""
        response = self.client.get("/api/statistics")

        assert response.status_code == 200
        data = response.json()

        stats = data["statistics"]
        assert stats["total_entities"] == 1
        assert stats["total_observations"] == 1
        assert stats["total_relations"] == 0
        assert len(stats["entities_by_type"]) == 1
        assert stats["entities_by_type"][0]["entity_type"] == "concept"
        assert stats["entities_by_type"][0]["count"] == 1


def test_api_documentation():
    """Test that API documentation is accessible."""
    client = TestClient(app)

    # Test OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "Muleta Cognitiva API"
    assert "paths" in schema

    # Check that our main endpoints are documented
    paths = schema["paths"]
    assert "/api/entities" in paths
    assert "/api/visualization" in paths
    assert "/api/statistics" in paths
    assert "/health" in paths
