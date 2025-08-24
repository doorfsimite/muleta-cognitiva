"""
OpenAI LLM client for entity and relation extraction.
Supports both OpenAI API and local model fallback.
"""

import json
import logging
import os
import re
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMClient:
    """LLM client supporting OpenAI API and local model fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        fallback_to_local: bool = True,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var
            model: OpenAI model to use
            fallback_to_local: Whether to fallback to local model if API fails
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.fallback_to_local = fallback_to_local
        self._client = None

        # Initialize OpenAI client if API key is available
        if self.api_key:
            try:
                import openai

                self._client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.warning(
                    "OpenAI package not available, will use fallback methods"
                )
                self._client = None
        else:
            logger.info("No OpenAI API key provided, will use fallback methods")

    def extract_entities_relations(
        self, text: str, source_type: str = "text", source_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract entities and relations from text using LLM.

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

        # Try OpenAI API first
        if self._client:
            try:
                return self._extract_with_openai(text, source_type, source_path)
            except Exception as e:
                logger.warning(f"OpenAI API failed: {e}")
                if not self.fallback_to_local:
                    raise LLMError(f"OpenAI API failed: {e}")

        # Fallback to local methods
        try:
            return self._extract_with_fallback(text, source_type, source_path)
        except Exception as e:
            logger.error(f"All LLM methods failed: {e}")
            raise LLMError(f"Entity extraction failed: {e}")

    def _extract_with_openai(
        self, text: str, source_type: str, source_path: Optional[str]
    ) -> Dict[str, Any]:
        """Extract entities using OpenAI API."""
        prompt = self._build_extraction_prompt(text, source_type)

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
                timeout=30,
            )

            content = response.choices[0].message.content.strip()
            return self._parse_llm_response(content)

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _extract_with_fallback(
        self, text: str, source_type: str, source_path: Optional[str]
    ) -> Dict[str, Any]:
        """Extract entities using fallback methods."""
        # Try gh copilot if available
        try:
            return self._extract_with_gh_copilot(text, source_type)
        except Exception as e:
            logger.warning(f"gh copilot failed: {e}")

        # Use rule-based extraction as last resort
        return self._extract_with_rules(text, source_type, source_path)

    def _extract_with_gh_copilot(self, text: str, source_type: str) -> Dict[str, Any]:
        """Extract entities using gh copilot CLI."""
        prompt = self._build_extraction_prompt(text, source_type)

        try:
            result = subprocess.run(
                ["gh", "copilot", "suggest", "-p", prompt, "--chat"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, "gh copilot")

            output = result.stdout.strip()
            return self._parse_llm_response(output)

        except subprocess.TimeoutExpired:
            raise LLMError("gh copilot timed out")
        except subprocess.CalledProcessError as e:
            raise LLMError(f"gh copilot failed: {e}")

    def _extract_with_rules(
        self, text: str, source_type: str, source_path: Optional[str]
    ) -> Dict[str, Any]:
        """Rule-based entity extraction as fallback."""
        logger.info("Using rule-based extraction as fallback")

        entities = []
        relations = []

        # Simple rule-based extraction
        # Look for capitalized words/phrases that might be entities
        words = text.split()
        potential_entities = set()

        for i, word in enumerate(words):
            # Look for capitalized words (potential proper nouns)
            if word[0].isupper() and len(word) > 2:
                potential_entities.add(word.strip(".,!?;:"))

            # Look for quoted terms
            if '"' in text:
                quoted_terms = re.findall(r'"([^"]*)"', text)
                for term in quoted_terms:
                    if len(term.strip()) > 2:
                        potential_entities.add(term.strip())

        # Convert to entities format
        for entity_name in list(potential_entities)[:10]:  # Limit to 10
            entities.append(
                {
                    "name": entity_name,
                    "type": "concept",
                    "description": f"Entity extracted from {source_type} content",
                }
            )

        # Simple relation detection based on common patterns
        relation_patterns = [
            (r"(\w+)\s+is\s+(\w+)", "is_a"),
            (r"(\w+)\s+causes\s+(\w+)", "causes"),
            (r"(\w+)\s+relates\s+to\s+(\w+)", "relates_to"),
            (r"(\w+)\s+and\s+(\w+)", "associated_with"),
        ]

        entity_names = {e["name"] for e in entities}
        for pattern, relation_type in relation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                from_entity, to_entity = match.groups()
                if from_entity in entity_names and to_entity in entity_names:
                    relations.append(
                        {
                            "from": from_entity,
                            "to": to_entity,
                            "type": relation_type,
                            "evidence": match.group(0),
                        }
                    )

        return {"entities": entities, "relations": relations}

    def _build_extraction_prompt(self, text: str, source_type: str) -> str:
        """Build extraction prompt for LLM."""
        return f"""Extraia entidades conceituais e suas relações do texto a seguir.

INSTRUÇÕES:
1. Identifique conceitos importantes, pessoas, lugares, ideias principais
2. Para cada entidade, forneça nome, tipo e descrição breve
3. Identifique relações semânticas entre as entidades
4. Mantenha descrições em português
5. Responda APENAS com JSON válido

FORMATO DE RESPOSTA:
{{
  "entities": [
    {{"name": "Nome da Entidade", "type": "tipo", "description": "descrição breve"}}
  ],
  "relations": [
    {{"from": "Entidade1", "to": "Entidade2", "type": "tipo_relacao", "evidence": "evidência no texto"}}
  ]
}}

TIPOS DE ENTIDADE: person, concept, place, idea, theory, method, tool
TIPOS DE RELAÇÃO: is_a, part_of, causes, enables, contradicts, supports, relates_to

TEXTO ({source_type}):
{text[:2000]}"""  # Limit text length

    def _get_system_prompt(self) -> str:
        """Get system prompt for OpenAI API."""
        return """Você é um especialista em extração de conhecimento e análise de texto. 
Sua tarefa é identificar entidades conceituais importantes e suas relações semânticas 
em textos acadêmicos e educacionais. Seja preciso e conciso."""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract JSON."""
        # Try to parse as direct JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from response using regex
        json_patterns = [
            r"\{.*\}",  # Basic JSON pattern
            r"```json\s*(\{.*?\})\s*```",  # JSON in code blocks
            r"```\s*(\{.*?\})\s*```",  # JSON in generic code blocks
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                json_str = match.group(1) if match.groups() else match.group(0)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

        # If no valid JSON found, return empty structure
        logger.warning(f"Could not parse LLM response as JSON: {response[:200]}...")
        return {"entities": [], "relations": []}

    def health_check(self) -> Dict[str, Any]:
        """Check LLM client health and connectivity."""
        status = {
            "openai_configured": self._client is not None,
            "api_key_available": bool(self.api_key),
            "model": self.model,
            "fallback_enabled": self.fallback_to_local,
        }

        # Test OpenAI connectivity if available
        if self._client:
            try:
                _ = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5,
                    timeout=10,
                )
                status["openai_connectivity"] = "ok"
            except Exception as e:
                status["openai_connectivity"] = f"error: {str(e)}"
        else:
            status["openai_connectivity"] = "not_configured"

        return status
