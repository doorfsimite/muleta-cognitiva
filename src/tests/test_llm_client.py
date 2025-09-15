"""Tests for local LLM client."""

import json
from unittest.mock import Mock, patch

import pytest

from api.config import LLMConfig
from api.llm_client import LLMClient, LLMError


class TestLLMClientInit:
    """Test LLM client initialization."""

    def test_init_with_config(self):
        """Test initialization with explicit config."""
        config = LLMConfig()
        config.model = "test-model"
        config.url = "http://test.url"
        config.timeout = 30
        config.fallback_enabled = False

        client = LLMClient(config=config)
        assert client.config.model == "test-model"
        assert client.config.url == "http://test.url"
        assert client.config.timeout == 30
        assert client.config.fallback_enabled is False

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        client = LLMClient()
        assert client.config.model == "deepseek-r1:8b"
        assert client.config.url == "http://localhost:11434/api/generate"
        assert client.config.timeout == 60
        assert client.config.fallback_enabled is True

    def test_init_with_env_vars(self, monkeypatch):
        """Test initialization with environment variables."""
        monkeypatch.setenv("LLM_MODEL", "custom-model")
        monkeypatch.setenv("LOCAL_LLM_URL", "http://custom.url")
        monkeypatch.setenv("LLM_TIMEOUT", "120")
        monkeypatch.setenv("LLM_FALLBACK_ENABLED", "false")

        client = LLMClient()
        assert client.config.model == "custom-model"
        assert client.config.url == "http://custom.url"
        assert client.config.timeout == 120
        assert client.config.fallback_enabled is False


class TestLLMClientExtraction:
    """Test entity and relation extraction."""

    def test_extract_empty_text(self):
        """Test extraction with empty text."""
        client = LLMClient()
        result = client.extract_entities_relations("")
        assert result == {"entities": [], "relations": []}

    def test_extract_whitespace_only(self):
        """Test extraction with whitespace-only text."""
        client = LLMClient()
        result = client.extract_entities_relations("   \n\t  ")
        assert result == {"entities": [], "relations": []}

    @patch("api.llm_client.httpx.Client")
    def test_extract_with_llm_success(self, mock_httpx_client):
        """Test successful extraction with local LLM."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": json.dumps(
                {
                    "entities": [
                        {
                            "name": "Test Entity",
                            "type": "conceito",
                            "description": "Test description",
                        }
                    ],
                    "relations": [
                        {
                            "from": "Test Entity",
                            "to": "Another Entity",
                            "type": "relacionado_a",
                            "evidence": "Test evidence",
                        }
                    ],
                }
            )
        }
        mock_response.raise_for_status.return_value = None

        # Mock HTTP client
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        client = LLMClient()
        result = client.extract_entities_relations("Test text")

        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "Test Entity"
        assert len(result["relations"]) == 1
        assert result["relations"][0]["from"] == "Test Entity"

    @patch("api.llm_client.httpx.Client")
    def test_extract_with_llm_failure_fallback_disabled(self, mock_httpx_client):
        """Test extraction with LLM failure and fallback disabled."""
        # Mock HTTP client to raise an exception
        mock_httpx_client.return_value.__enter__.side_effect = Exception(
            "Connection error"
        )

        config = LLMConfig()
        config.fallback_enabled = False
        client = LLMClient(config=config)

        with pytest.raises(LLMError, match="Local LLM failed and fallback disabled"):
            client.extract_entities_relations("Test text")


class TestLLMClientGenerate:
    """Test LLM generate method."""

    @patch("api.llm_client.httpx.Client")
    def test_generate_success(self, mock_httpx_client):
        """Test successful generate call."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"response": '{"result": "success"}'}
        mock_response.raise_for_status.return_value = None

        # Mock HTTP client
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        client = LLMClient()
        result = client.generate("Test prompt")

        assert result == {"result": "success"}

    @patch("api.llm_client.httpx.Client")
    def test_generate_with_custom_model(self, mock_httpx_client):
        """Test generate with custom model."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"response": '{"result": "success"}'}
        mock_response.raise_for_status.return_value = None

        # Mock HTTP client
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        client = LLMClient()
        client.generate("Test prompt", model="custom-model")

        # Check that custom model was used in the request
        call_args = mock_client_instance.post.call_args
        assert call_args[1]["json"]["model"] == "custom-model"

    @patch("api.llm_client.httpx.Client")
    def test_generate_invalid_json_response(self, mock_httpx_client):
        """Test generate with invalid JSON response."""
        # Mock HTTP response with invalid JSON
        mock_response = Mock()
        mock_response.json.return_value = {"response": "invalid json"}
        mock_response.raise_for_status.return_value = None

        # Mock HTTP client
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        client = LLMClient()

        with pytest.raises(LLMError, match="LLM returned invalid JSON"):
            client.generate("Test prompt")

    @patch("api.llm_client.httpx.Client")
    def test_generate_http_error(self, mock_httpx_client):
        """Test generate with HTTP error."""
        import httpx

        # Mock HTTP client to raise an HTTPError
        mock_httpx_client.return_value.__enter__.side_effect = httpx.HTTPError(
            "Connection error"
        )

        client = LLMClient()

        with pytest.raises(LLMError, match="Local LLM HTTP request failed"):
            client.generate("Test prompt")


class TestLLMClientHealthCheck:
    """Test health check functionality."""

    def test_health_check_basic(self):
        """Test basic health check information."""
        client = LLMClient()
        status = client.health_check()

        assert "model" in status
        assert "url" in status
        assert "timeout" in status
        assert "fallback_enabled" in status
        assert "connectivity" in status

    @patch("api.llm_client.httpx.Client")
    def test_health_check_connectivity_success(self, mock_httpx_client):
        """Test health check with successful connectivity."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Hello response"}
        mock_response.raise_for_status.return_value = None

        # Mock HTTP client
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        client = LLMClient()
        status = client.health_check()

        assert status["connectivity"] == "ok"
        assert "test_response_length" in status

    @patch("api.llm_client.httpx.Client")
    def test_health_check_connectivity_failure(self, mock_httpx_client):
        """Test health check with connectivity failure."""
        # Mock HTTP client to raise an exception
        mock_httpx_client.return_value.__enter__.side_effect = Exception(
            "Connection error"
        )

        client = LLMClient()
        status = client.health_check()

        assert "error:" in status["connectivity"]
