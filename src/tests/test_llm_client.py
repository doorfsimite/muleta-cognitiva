"""Tests for LLM client with Anthropic integration."""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from api.llm_client import LLMClient, LLMError


class TestLLMClientInit:
    """Test LLM client initialization."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        client = LLMClient(api_key="test-key", model="test-model")
        assert client.api_key == "test-key"
        assert client.model == "test-model"
        assert client.fallback_to_local is True
        assert client.request_timeout == 60

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization with environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        client = LLMClient()
        assert client.api_key == "env-key"
        assert client.model == "claude-3-5-sonnet-20241022"

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient()
        assert client.api_key is None
        assert client._client is None

    @patch("api.llm_client.anthropic")
    def test_init_with_anthropic_client(self, mock_anthropic):
        """Test initialization with Anthropic client."""
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        client = LLMClient(api_key="test-key")

        mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")
        assert client._client == mock_client

    @patch("api.llm_client.anthropic")
    def test_init_anthropic_client_failure(self, mock_anthropic):
        """Test initialization when Anthropic client creation fails."""
        mock_anthropic.Anthropic.side_effect = Exception("API error")

        client = LLMClient(api_key="test-key")

        assert client._client is None


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

    @patch("api.llm_client.anthropic")
    def test_extract_with_anthropic_success(self, mock_anthropic):
        """Test successful extraction with Anthropic API."""
        # Mock Anthropic client and response
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        # Mock message response
        mock_content_block = Mock()
        mock_content_block.type = "text"
        mock_content_block.text = json.dumps(
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

        mock_message = Mock()
        mock_message.content = [mock_content_block]

        mock_client.messages.create.return_value = mock_message

        client = LLMClient(api_key="test-key")
        result = client.extract_entities_relations("Test text about concepts")

        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "Test Entity"
        assert len(result["relations"]) == 1
        assert result["relations"][0]["from"] == "Test Entity"

    @patch("api.llm_client.anthropic")
    def test_extract_with_anthropic_failure_fallback(self, mock_anthropic):
        """Test extraction with Anthropic failure and fallback."""
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        client = LLMClient(api_key="test-key", fallback_to_local=True)
        result = client.extract_entities_relations(
            'Test text with "quoted concept" and Capitalized words'
        )

        # Should fall back to rule-based extraction
        assert "entities" in result
        assert "relations" in result

    @patch("api.llm_client.anthropic")
    def test_extract_with_anthropic_failure_no_fallback(self, mock_anthropic):
        """Test extraction with Anthropic failure and no fallback."""
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        client = LLMClient(api_key="test-key", fallback_to_local=False)

        with pytest.raises(LLMError):
            client.extract_entities_relations("Test text")

    def test_extract_rule_based_fallback(self):
        """Test rule-based extraction fallback."""
        client = LLMClient(api_key=None, fallback_to_local=True)

        text = 'This is about "Machine Learning" and Artificial Intelligence concepts.'
        result = client.extract_entities_relations(text)

        assert "entities" in result
        assert "relations" in result

        # Should find quoted phrases and capitalized words
        entity_names = [e["name"] for e in result["entities"]]
        assert "Machine Learning" in entity_names
        assert "Artificial" in entity_names or "Intelligence" in entity_names

    def test_extract_no_method_available(self):
        """Test extraction when no method is available."""
        client = LLMClient(api_key=None, fallback_to_local=False)

        with pytest.raises(LLMError):
            client.extract_entities_relations("Test text")


class TestLLMClientResponseParsing:
    """Test response parsing methods."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        client = LLMClient()

        response = json.dumps(
            {
                "entities": [
                    {"name": "Test", "type": "conceito", "description": "Test entity"}
                ],
                "relations": [],
            }
        )

        result = client._parse_llm_response(response)
        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "Test"

    def test_parse_json_in_code_block(self):
        """Test parsing JSON wrapped in code blocks."""
        client = LLMClient()

        response = """Here is the result:
```json
{
    "entities": [{"name": "Test", "type": "conceito", "description": "Test entity"}],
    "relations": []
}
```
"""

        result = client._parse_llm_response(response)
        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "Test"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON response."""
        client = LLLClient()

        response = "This is not JSON at all"
        result = client._parse_llm_response(response)

        assert result == {"entities": [], "relations": []}

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        client = LLMClient()

        result = client._parse_llm_response("")
        assert result == {"entities": [], "relations": []}

    def test_extract_text_from_anthropic_message(self):
        """Test extracting text from Anthropic message format."""
        client = LLMClient()

        # Mock message with content blocks
        mock_block = Mock()
        mock_block.type = "text"
        mock_block.text = "Test response"

        mock_message = Mock()
        mock_message.content = [mock_block]

        result = client._extract_text_from_anthropic_message(mock_message)
        assert result == "Test response"

    def test_extract_text_from_anthropic_message_string(self):
        """Test extracting text when content is a string."""
        client = LLMClient()

        mock_message = Mock()
        mock_message.content = "Direct string content"

        result = client._extract_text_from_anthropic_message(mock_message)
        assert result == "Direct string content"

    def test_extract_text_from_anthropic_message_error(self):
        """Test extracting text when there's an error."""
        client = LLMClient()

        mock_message = Mock()
        mock_message.content = None

        result = client._extract_text_from_anthropic_message(mock_message)
        assert result == ""


class TestLLMClientRuleBasedExtraction:
    """Test rule-based extraction fallback."""

    def test_rule_based_quoted_phrases(self):
        """Test rule-based extraction of quoted phrases."""
        client = LLMClient()

        text = "This discusses \"machine learning\" and 'data science' concepts."
        result = client._rule_based_extraction(text)

        entity_names = [e["name"] for e in result["entities"]]
        assert "machine learning" in entity_names
        assert "data science" in entity_names

    def test_rule_based_capitalized_words(self):
        """Test rule-based extraction of capitalized words."""
        client = LLMClient()

        text = "Python and TensorFlow are used in Machine Learning projects."
        result = client._rule_based_extraction(text)

        entity_names = [e["name"] for e in result["entities"]]
        assert "Python" in entity_names
        assert "TensorFlow" in entity_names
        assert "Machine" in entity_names

    def test_rule_based_filters_common_words(self):
        """Test that rule-based extraction filters common words."""
        client = LLMClient()

        text = "O sistema usa Python. A ferramenta é útil."
        result = client._rule_based_extraction(text)

        entity_names = [e["name"] for e in result["entities"]]
        # Should not include common Portuguese words
        assert "O" not in entity_names
        assert "A" not in entity_names
        # Should include actual entities
        assert "Python" in entity_names

    def test_rule_based_creates_relations(self):
        """Test that rule-based extraction creates relations between entities."""
        client = LLMClient()

        text = "Python and TensorFlow work together in projects."
        result = client._rule_based_extraction(text)

        assert len(result["relations"]) > 0
        # Should create relations between consecutive entities
        for relation in result["relations"]:
            assert relation["type"] == "relacionado_a"
            assert relation["evidence"] == "Proximidade no texto"


class TestLLMClientHealthCheck:
    """Test health check functionality."""

    def test_health_check_no_anthropic(self):
        """Test health check without Anthropic configuration."""
        client = LLMClient(api_key=None)
        status = client.health_check()

        assert status["anthropic_configured"] is False
        assert status["api_key_available"] is False
        assert status["anthropic_connectivity"] == "not_configured"

    @patch("api.llm_client.anthropic")
    def test_health_check_anthropic_success(self, mock_anthropic):
        """Test health check with successful Anthropic connection."""
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_message = Mock()
        mock_message.content = "Hello response"
        mock_client.messages.create.return_value = mock_message

        client = LLMClient(api_key="test-key")
        status = client.health_check()

        assert status["anthropic_configured"] is True
        assert status["api_key_available"] is True
        assert status["anthropic_connectivity"] == "ok"
        assert "test_response_length" in status

    @patch("api.llm_client.anthropic")
    def test_health_check_anthropic_failure(self, mock_anthropic):
        """Test health check with failed Anthropic connection."""
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Connection failed")

        client = LLMClient(api_key="test-key")
        status = client.health_check()

        assert status["anthropic_configured"] is True
        assert status["api_key_available"] is True
        assert "error: Connection failed" in status["anthropic_connectivity"]


class TestLLMClientPromptBuilding:
    """Test prompt building functionality."""

    def test_build_extraction_prompt(self):
        """Test that extraction prompt is built correctly."""
        client = LLMClient()

        prompt = client._build_extraction_prompt("Test text", "pdf")

        assert "Test text" in prompt
        assert "pdf" in prompt
        assert "entities" in prompt
        assert "relations" in prompt
        assert "JSON" in prompt

    def test_build_extraction_prompt_different_source_types(self):
        """Test prompt building with different source types."""
        client = LLMClient()

        for source_type in ["text", "pdf", "video"]:
            prompt = client._build_extraction_prompt("Test content", source_type)
            assert f"TEXTO ({source_type}):" in prompt
