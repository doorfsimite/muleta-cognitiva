"""
Anthropic LLM client for entity and relation extraction.
Uses Anthropic Messages API when ANTHROPIC_API_KEY is available,
with a simple local heuristic fallback.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

try:
    import anthropic  # type: ignore
except Exception:  # pragma: no cover - optional dependency in tests
    anthropic = None  # Fallback if package not installed

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMClient:
    """LLM client supporting Anthropic API and local fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_to_local: bool = True,
        request_timeout: int = 60,
    ) -> None:
        """Initialize the LLM client.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY.
            model: Anthropic model to use. Defaults to "claude-3-5-sonnet-20241022".
            fallback_to_local: Whether to use heuristic extraction on failure.
            request_timeout: Timeout in seconds for API requests.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model or "claude-3-5-sonnet-20241022"
        self.fallback_to_local = bool(fallback_to_local)
        self.request_timeout = int(request_timeout)

        # Create Anthropic client if possible
        if self.api_key and anthropic is not None:
            try:
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to init Anthropic client: {e}")
                self._client = None
        else:
            self._client = None

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

        prompt = self._build_extraction_prompt(text, source_type)

        # Try Anthropic first (if configured)
        if self._client is not None:
            try:
                message = self._client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}],
                )
                output_text = self._extract_text_from_anthropic_message(message)
                result = self._parse_llm_response(output_text)
                logger.info(
                    f"Anthropic extraction successful: {len(result.get('entities', []))} entities, {len(result.get('relations', []))} relations"
                )
                return result
            except Exception as e:
                logger.exception(f"Anthropic API call failed: {e}")
                if not self.fallback_to_local:
                    raise LLMError(f"Anthropic API failed and fallback disabled: {e}")

        # No extraction method available
        raise LLMError("No extraction method available")

    def _extract_text_from_anthropic_message(self, message: Any) -> str:
        """Extract concatenated text from Anthropic message response."""
        try:
            # Handle the new Anthropic SDK response format
            if hasattr(message, "content") and isinstance(message.content, list):
                text_parts = []
                for block in message.content:
                    if hasattr(block, "type") and block.type == "text":
                        text_parts.append(block.text)
                return "\n".join(text_parts).strip()

            # Fallback for different response formats
            if hasattr(message, "content"):
                if isinstance(message.content, str):
                    return message.content.strip()
                elif isinstance(message.content, list):
                    text_parts = []
                    for item in message.content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            text_parts.append(item)
                    return "\n".join(text_parts).strip()

            # Last resort - convert to string
            return str(message.content or "").strip()

        except Exception as e:
            logger.warning(f"Error extracting text from Anthropic message: {e}")
            return str(getattr(message, "content", "")).strip()

    def _build_extraction_prompt(self, text: str, source_type: str) -> str:
        """Build extraction prompt for LLM."""
        return f"""Tarefa:
Você receberá um texto-fonte. Sua missão é ajudar a aprender o conteúdo identificando entidades e relações entre elas, para construir um grafo de conhecimento (como uma wiki) e servir de base para um infográfico.

Regras gerais:
- Use apenas informações presentes no texto fornecido (sem conhecimento externo).
- Escreva todas as descrições em português do Brasil.
- Seja objetivo: descrições com no máximo 25 palavras.
- Normalize nomes de entidades (forma canônica, singular quando apropriado).
- Se houver entidades duplicadas, consolide em um único nome canônico.
- Se não tiver certeza do tipo de relação, use "relacionado_a".
- Se não encontrar nada relevante, retorne "entities": [] e "relations": [].
- Responda APENAS com JSON válido, sem comentários, sem texto fora do JSON.
- Desconsidere texto mal formatado. O input pode ter sido dinamicamente gerado a partir de audio ou imagem e pode ter ruido.

Entrada:
- Um único bloco de texto.

Passos de análise (internos):
1) Leia e segmente o texto em parágrafos/tópicos.
2) Liste candidatos a entidades: conceitos, pessoas, lugares, organizações, obras, eventos, tecnologias, métodos, problemas, soluções, premissas, conclusões, temas/assuntos.
3) Selecione as entidades essenciais ao entendimento do texto (evite termos triviais).
4) Para cada entidade selecionada, gere:
   - name: nome canônico curto e claro.
   - type: um dos tipos permitidos (ver abaixo).
   - description: resumo objetivo do papel/definição no contexto do texto.
5) Identifique relações explícitas ou fortemente implícitas entre as entidades.
6) Para cada relação, registre:
   - from, to: nomes canônicos das entidades.
   - type: um dos tipos permitidos (ver abaixo).
   - evidence: citação curta do texto OU explicação breve baseada no texto.
7) Valide o JSON: chaves corretas, aspas duplas, sem vírgulas sobrando.

Tipos permitidos:
- Entidades (campo "type"): "pessoa", "lugar", "organizacao", "conceito", "ideia", "teoria", "evento", "obra", "tecnologia", "metodo", "metrica", "problema", "solucao", "premissa", "conclusao", "tema", "assunto", "outro".
- Relações (campo "type"): "tipo_de", "parte_de", "exemplo_de", "causa_de", "efeito_de", "apoia", "contradiz", "requer", "usa", "depende_de", "autor_de", "publicado_em", "ocorre_em", "compara_com", "resolve", "conduz_a", "precede", "sucede", "relacionado_a".

Formato de saída (JSON):
{{
  "entities": [
    {{
      "name": "Nome da Entidade", 
      "type": "tipo", 
      "description": "descrição em PT-BR com até 25 palavras"
    }}
  ],
  "relations": [
    {{
      "from": "Entidade1", 
      "to": "Entidade2", 
      "type": "tipo_relacao", 
      "evidence": "Citação curta do texto ou explicação objetiva baseada no texto"
    }}
  ]
}}

Exemplo (apenas demonstrativo):
{{
  "entities": [
    {{
      "name": "Aprendizado Baseado em Grafos", 
      "type": "conceito", 
      "description": "Estratégia que organiza conhecimento como nós e arestas para facilitar entendimento e revisão."
    }},
    {{
      "name": "Entidade", 
      "type": "conceito", 
      "description": "Elemento fundamental do grafo representando um conceito, pessoa, lugar, evento ou objeto."
    }},
    {{
      "name": "Relação", 
      "type": "conceito", 
      "description": "Ligação semântica entre entidades que expressa dependência, causalidade, composição ou associação."
    }}
  ],
  "relations": [
    {{
      "from": "Aprendizado Baseado em Grafos", 
      "to": "Entidade", 
      "type": "parte_de", 
      "evidence": "O método define entidades e relações como componentes do grafo."
    }},
    {{
      "from": "Aprendizado Baseado em Grafos", 
      "to": "Relação", 
      "type": "parte_de", 
      "evidence": "A abordagem usa relações para conectar conceitos no grafo."
    }},
    {{
      "from": "Entidade", 
      "to": "Relação", 
      "type": "relacionado_a", 
      "evidence": "As entidades são conectadas por relações."
    }}
  ]
}}

TEXTO ({source_type}):
{text}"""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract JSON."""
        if not response:
            return {"entities": [], "relations": []}

        # Clean the response
        response = response.strip()

        # Try to parse as direct JSON
        try:
            result = json.loads(response)
            # Validate structure
            if (
                isinstance(result, dict)
                and "entities" in result
                and "relations" in result
            ):
                return result
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from response using regex
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
                    if (
                        isinstance(result, dict)
                        and "entities" in result
                        and "relations" in result
                    ):
                        return result
                except json.JSONDecodeError:
                    continue

        # If no valid JSON found, return empty structure
        logger.warning(f"Could not parse LLM response as JSON: {response[:200]}...")
        return {"entities": [], "relations": []}

    def health_check(self) -> Dict[str, Any]:
        """Check LLM client health and connectivity."""
        status = {
            "anthropic_configured": self._client is not None,
            "api_key_available": bool(self.api_key),
            "model": self.model,
            "fallback_enabled": self.fallback_to_local,
        }

        # Test Anthropic connectivity if available
        if self._client is not None:
            try:
                test_message = self._client.messages.create(
                    model=self.model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}],
                )
                status["anthropic_connectivity"] = "ok"
                status["test_response_length"] = len(str(test_message.content))
            except Exception as e:
                status["anthropic_connectivity"] = f"error: {str(e)}"
        else:
            status["anthropic_connectivity"] = "not_configured"

        return status
