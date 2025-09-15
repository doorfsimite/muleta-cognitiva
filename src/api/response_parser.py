"""Response parser for LLM outputs."""

import json
import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


def parse_llm_response(response: str) -> Dict[str, Any]:
    """Parse LLM response to extract JSON.

    Args:
        response: Raw response string from LLM

    Returns:
        Dictionary with entities and relations, or empty structure if parsing fails
    """
    if not response:
        return {"entities": [], "relations": []}

    # Clean the response
    response = response.strip()

    # Try to parse as direct JSON
    try:
        result = json.loads(response)
        if _is_valid_extraction_result(result):
            return result
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from response using regex patterns
    json_patterns = [
        r"```json\s*(\{.*?\})\s*```",  # JSON in code blocks
        r"```\s*(\{.*?\})\s*```",  # JSON in generic code blocks
        r'(\{[^{}]*"entities"[^{}]*"relations"[^{}]*\})',  # Look for entities/relations pattern
        r"(\{.*\})",  # Basic JSON pattern (greedy)
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                result = json.loads(match)
                if _is_valid_extraction_result(result):
                    return result
            except json.JSONDecodeError:
                continue

    # If no valid JSON found, return empty structure
    logger.warning(f"Could not parse LLM response as JSON: {response[:200]}...")
    return {"entities": [], "relations": []}


def _is_valid_extraction_result(result: Any) -> bool:
    """Check if result has expected structure for entity extraction.

    Args:
        result: Parsed JSON result

    Returns:
        True if result has entities and relations keys
    """
    return isinstance(result, dict) and "entities" in result and "relations" in result
