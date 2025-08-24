"""
OpenAI LLM client for entity and relation extraction.
"""
import json
import re
import subprocess


class LLMClient:
    def __init__(self):
        pass

    def extract_entities_relations(self, text: str):
        prompt = (
            "Extraia entidades, tipos, descrições e relações do texto a seguir. "
            "Responda em JSON com campos: entities (lista de {name, type, description}), "
            "relations (lista de {from, to, type, evidence}).\nTexto:\n" + text
        )
        try:
            result = subprocess.run(
                ["gh", "copilot", "suggest", "-p", prompt, "--chat"],
                capture_output=True, text=True, timeout=60
            )
            output = result.stdout.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to call gh copilot: {e}")
        # Try to parse JSON from Copilot output
        try:
            return json.loads(output)
        except Exception:
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError("Copilot output not valid JSON: " + output)
