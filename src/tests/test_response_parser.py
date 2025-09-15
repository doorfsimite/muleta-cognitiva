"""Tests for the new response parser module."""

import json

from api.response_parser import parse_llm_response


def test_parse_valid_json():
    """Test parsing valid JSON response."""
    response = json.dumps(
        {
            "entities": [
                {"name": "Test", "type": "conceito", "description": "Test entity"}
            ],
            "relations": [],
        }
    )

    result = parse_llm_response(response)
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Test"


def test_parse_json_in_code_block():
    """Test parsing JSON wrapped in code blocks."""
    response = """Here is the result:
```json
{
    "entities": [{"name": "Test", "type": "conceito", "description": "Test entity"}],
    "relations": []
}
```
"""

    result = parse_llm_response(response)
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Test"


def test_parse_invalid_json():
    """Test parsing invalid JSON response."""
    response = "This is not JSON at all"
    result = parse_llm_response(response)
    assert result == {"entities": [], "relations": []}


def test_parse_empty_response():
    """Test parsing empty response."""
    result = parse_llm_response("")
    assert result == {"entities": [], "relations": []}
