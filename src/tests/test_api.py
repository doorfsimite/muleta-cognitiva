"""
Tests for the FastAPI server endpoints.
"""

import os
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add the parent directory to sys.path to import from api module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_success(self, client):
        """Test successful health check."""
        with patch("api.main.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
            mock_cursor.execute.assert_called_with("SELECT 1")

    def test_health_check_failure(self, client):
        """Test health check when database is unavailable."""
        with patch("api.main.get_connection") as mock_get_conn:
            mock_get_conn.side_effect = sqlite3.Error("Database unavailable")

            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "Database unavailable" in data["error"]


class TestEntityEndpoints:
    """Test entity-related endpoints."""

    @patch("api.main.get_connection")
    def test_get_entities_success(self, mock_get_conn, client):
        """Test successful retrieval of entities."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Mock cursor description for column names
        mock_cursor.description = [
            ("id",), ("name",), ("type",), ("description",), ("created_at",), ("updated_at",)
        ]

        # Set up row_factory to convert tuples to dictionaries
        def mock_dict_factory(cursor, row):
            return dict(zip([col[0] for col in cursor.description], row))

        mock_conn.row_factory = mock_dict_factory
        
        # Mock fetchall to return raw tuples (as SQLite would)
        mock_cursor.fetchall.return_value = [
            (
                1,
                "Filosofia",
                "conceito",
                "Estudo da natureza",
                "2024-01-01",
                "2024-01-01",
            ),
            (2, "Platão", "filósofo", "Filósofo grego", "2024-01-01", "2024-01-01"),
        ]
        mock_cursor.fetchone.return_value = (2,)  # count query

        response = client.get("/api/entities")

        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "total_count" in data
        assert len(data["entities"]) == 2
        assert data["total_count"] == 2
        assert data["entities"][0]["name"] == "Filosofia"
        assert data["entities"][1]["name"] == "Platão"

    @patch("api.main.get_connection")
    def test_get_entity_not_found(self, mock_get_conn, client):
        """Test getting non-existent entity."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.return_value = None

        response = client.get("/api/entities/999")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Entity not found"


class TestContentProcessingEndpoint:
    """Test content processing endpoint."""

    def test_validation_empty_content(self, client):
        response = client.post("/api/content/process", json={"content": "   "})
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["code"] == "VALIDATION_ERROR"

    def test_validation_min_length(self, client):
        response = client.post("/api/content/process", json={"content": "short"})
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"

    def test_validation_max_length(self, client):
        too_long = "a" * 60000
        response = client.post("/api/content/process", json={"content": too_long})
        assert response.status_code in (400, 413)
        data = response.json()
        assert data["success"] is False

    def test_success_response_structure(self, client, monkeypatch):
        # Patch ContentProcessor.process_text to deterministic result
        from api import main as api_main

        class DummyProcessor:
            def process_text(self, text, source_type="text", source_path=None):
                return {
                    "success": True,
                    "entities_created": 2,
                    "relations_created": 1,
                    "observations_created": 3,
                    "entities_existing": 0,
                    "relations_existing": 0,
                }

        monkeypatch.setattr(api_main, "ContentProcessor", lambda: DummyProcessor())

        payload = {"content": "Texto de teste válido."}
        response = client.post("/api/content/process", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["entities_created"] == 2
        assert data["relations_created"] == 1
        assert data["observations_created"] == 3

    def test_processing_timeout(self, client, monkeypatch):
        from api import main as api_main

        class SlowProcessor:
            def process_text(self, *args, **kwargs):
                import time
                time.sleep(2)
                return {"success": True, "entities_created": 0, "relations_created": 0}

        monkeypatch.setattr(api_main, "ContentProcessor", lambda: SlowProcessor())
        monkeypatch.setattr(api_main, "PROCESSING_TIMEOUT_SECONDS", 0.5)

        response = client.post("/api/content/process", json={"content": "conteúdo válido e suficiente"})
        assert response.status_code in (504, 500)


class TestDatabaseIntegration:
    """Integration tests with actual database operations."""

    def test_database_connection_real(self, client):
        """Test real database connection and basic operations."""
        # This test uses the actual database connection
        response = client.get("/health")

        # Should succeed if database is properly configured
        assert response.status_code in [200, 503]  # Either healthy or can't connect

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"

    def test_entities_endpoint_real_db(self, client):
        """Test entities endpoint with real database."""
        response = client.get("/api/entities")

        # Should return valid response structure even if empty
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["entities"], list)
        assert isinstance(data["total_count"], int)

    def test_visualization_endpoint_real_db(self, client):
        """Test visualization endpoint with real database."""
        response = client.get("/api/visualization")

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "links" in data
        assert "categories" in data
        assert "summary" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["links"], list)
        assert isinstance(data["categories"], list)

    def test_statistics_endpoint_real_db(self, client):
        """Test statistics endpoint with real database."""
        response = client.get("/api/statistics")

        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data
        stats = data["statistics"]
        assert "total_entities" in stats
        assert "total_observations" in stats
        assert "total_relations" in stats
        assert isinstance(stats["total_entities"], int)
        assert isinstance(stats["total_observations"], int)
        assert isinstance(stats["total_relations"], int)

    def test_relations_endpoint_real_db(self, client):
        """Test relations endpoint with real database."""
        response = client.get("/api/relations")

        assert response.status_code == 200
        data = response.json()
        assert "relations" in data
        assert "total_count" in data
        assert isinstance(data["relations"], list)
        assert isinstance(data["total_count"], int)


class TestAPIResponseValidation:
    """Test API response structures and validation."""

    def test_entities_response_structure(self, client):
        """Test that entities endpoint returns correct structure."""
        response = client.get("/api/entities")
        assert response.status_code == 200

        data = response.json()
        required_keys = ["entities", "total_count", "limit", "offset"]
        for key in required_keys:
            assert key in data

    def test_visualization_response_structure(self, client):
        """Test that visualization endpoint returns correct structure."""
        response = client.get("/api/visualization")
        assert response.status_code == 200

        data = response.json()
        required_keys = ["nodes", "links", "categories", "summary"]
        for key in required_keys:
            assert key in data

        # Check summary structure
        summary = data["summary"]
        summary_keys = ["total_entities", "total_relations", "entity_types"]
        for key in summary_keys:
            assert key in summary

    def test_statistics_response_structure(self, client):
        """Test that statistics endpoint returns correct structure."""
        response = client.get("/api/statistics")
        assert response.status_code == 200

        data = response.json()
        assert "statistics" in data

        stats = data["statistics"]
        required_keys = [
            "total_entities",
            "total_observations",
            "total_relations",
            "total_cards",
            "cards_due",
        ]
        for key in required_keys:
            assert key in stats
