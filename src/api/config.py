"""Configuration module for LLM client settings."""

import os


class LLMConfig:
    """Configuration for LLM client."""

    def __init__(self):
        self.model = os.environ.get("LLM_MODEL", "deepseek-r1:8b")
        self.url = os.environ.get(
            "LOCAL_LLM_URL", "http://localhost:11434/api/generate"
        )
        self.timeout = int(os.environ.get("LLM_TIMEOUT", "60"))
        self.fallback_enabled = (
            os.environ.get("LLM_FALLBACK_ENABLED", "true").lower() == "true"
        )
