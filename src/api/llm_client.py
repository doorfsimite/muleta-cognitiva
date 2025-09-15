"""
Local LLM client for entity and relation extraction.
Uses local LLM HTTP endpoint with fallback to rule-based extraction.
"""

import json
import logging
from typing import Any, Dict, Optional

import httpx

from .config import LLMConfig
from .fallback_extractor import extract_entities_relations_fallback
from .prompts import build_extraction_prompt
from .response_parser import parse_llm_response

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMClient:
    """Local LLM client for entity and relation extraction."""

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        """Initialize the LLM client.

        Args:
            config: Configuration object. If None, creates default config.
        """
        self.config = config or LLMConfig()

    def extract_entities_relations(
        self, text: str, source_type: str = "text", source_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract entities and relations from text using local LLM.

        Args:
            text: Input text to process
            source_type: Type of source (text, pdf, video)
            source_path: Path to source file (optional)

        Returns:
            Dictionary with entities and relations

        Raises:
            LLMError: If all extraction methods fail
        """
        if not text or not text.strip():
            return {"entities": [], "relations": []}

        prompt = build_extraction_prompt(text, source_type)

        # Try local LLM first
        try:
            response = self._call_local_llm(prompt)
            result = parse_llm_response(response)
            logger.info(
                f"LLM extraction successful: {len(result.get('entities', []))} entities, "
                f"{len(result.get('relations', []))} relations"
            )
            return result
        except Exception as e:
            logger.exception(f"Local LLM call failed: {e}")

            # Use fallback if enabled
            if self.config.fallback_enabled:
                logger.info("Using rule-based fallback extraction")
                return extract_entities_relations_fallback(text)

            raise LLMError(f"Local LLM failed and fallback disabled: {e}")

    def generate(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Call local LLM HTTP endpoint and return parsed JSON.

        Args:
            prompt: Text prompt to send to LLM
            model: Model name to use (overrides config default)

        Returns:
            Parsed JSON response from LLM

        Raises:
            LLMError: If LLM request fails
        """
        model_name = model or self.config.model
        response = self._call_local_llm(prompt, model_name)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM returned invalid JSON: {e}")

    def _call_local_llm(self, prompt: str, model: Optional[str] = None) -> str:
        """Make HTTP request to local LLM endpoint.

        Args:
            prompt: Text prompt to send
            model: Model name to use

        Returns:
            Raw response text from LLM

        Raises:
            LLMError: If HTTP request fails
        """
        model_name = model or self.config.model
        payload = {"prompt": prompt, "model": model_name}

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                resp = client.post(self.config.url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # Extract response text from various possible formats
            if isinstance(data, dict):
                if "response" in data:
                    return data["response"]
                elif "text" in data:
                    return data["text"]
                elif "content" in data:
                    return data["content"]
                else:
                    return str(data)
            elif isinstance(data, str):
                return data
            else:
                return str(data)

        except httpx.HTTPError as e:
            logger.exception("Local LLM HTTP request failed")
            raise LLMError(f"Local LLM HTTP request failed: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Check LLM client health and connectivity.

        Returns:
            Dictionary with health status information
        """
        status = {
            "model": self.config.model,
            "url": self.config.url,
            "timeout": self.config.timeout,
            "fallback_enabled": self.config.fallback_enabled,
        }

        # Test local LLM connectivity
        try:
            response = self._call_local_llm("Hello", self.config.model)
            status["connectivity"] = "ok"
            status["test_response_length"] = len(response)
        except Exception as e:
            status["connectivity"] = f"error: {str(e)}"

        return status
