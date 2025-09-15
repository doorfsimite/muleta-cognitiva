"""Fallback extractor for when LLM is unavailable."""

import re
from typing import Any, Dict, List


def extract_entities_relations_fallback(text: str) -> Dict[str, Any]:
    """Very simple heuristic extraction of entities and relations.

    This is used as a fallback when the LLM is unavailable.

    - Quoted phrases become 'conceito' entities.
    - Capitalized words (likely proper nouns) become entities.
    - Creates generic related relations between consecutive entities.

    Args:
        text: Input text to process

    Returns:
        Dictionary with entities and relations
    """
    entities: List[Dict[str, str]] = []
    relations: List[Dict[str, str]] = []

    # Extract quoted phrases
    quoted = re.findall(r'"([^"]+)"', text) + re.findall(r"'([^']+)'", text)
    for q in quoted:
        name = q.strip()
        if name and len(name) > 2:  # Avoid single characters
            entities.append(
                {
                    "name": name,
                    "type": "conceito",
                    "description": f"Conceito mencionado: {name[:20]}{'...' if len(name) > 20 else ''}",
                }
            )

    # Extract capitalized words (basic heuristic, avoid sentence start common words)
    caps = re.findall(r"\b([A-Z][a-zA-ZÀ-ÿ][\w-]*)\b", text)
    common_words = {
        "O",
        "A",
        "Os",
        "As",
        "Um",
        "Uma",
        "Este",
        "Esta",
        "Esse",
        "Essa",
        "Aquele",
        "Aquela",
        "Para",
        "Por",
        "De",
        "Da",
        "Do",
        "Em",
        "Na",
        "No",
    }
    seen = set(e["name"] for e in entities)

    for c in caps:
        if c in seen or c in common_words or len(c) < 3:
            continue
        seen.add(c)
        entities.append(
            {
                "name": c,
                "type": "conceito",
                "description": f"Entidade identificada: {c}",
            }
        )

    # Create simple relations between consecutive entities
    for i in range(len(entities) - 1):
        relations.append(
            {
                "from": entities[i]["name"],
                "to": entities[i + 1]["name"],
                "type": "relacionado_a",
                "evidence": "Proximidade no texto",
            }
        )

    return {"entities": entities, "relations": relations}
