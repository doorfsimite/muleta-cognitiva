"""Tests for the configuration module."""

from api.config import LLMConfig


def test_config_defaults():
    """Test default configuration values."""
    config = LLMConfig()
    assert config.model == "deepseek-r1:8b"
    assert config.url == "http://localhost:11434/api/generate"
    assert config.timeout == 60
    assert config.fallback_enabled is True


def test_config_with_env_vars(monkeypatch):
    """Test configuration with environment variables."""
    monkeypatch.setenv("LLM_MODEL", "custom-model")
    monkeypatch.setenv("LOCAL_LLM_URL", "http://custom.url")
    monkeypatch.setenv("LLM_TIMEOUT", "120")
    monkeypatch.setenv("LLM_FALLBACK_ENABLED", "false")

    config = LLMConfig()
    assert config.model == "custom-model"
    assert config.url == "http://custom.url"
    assert config.timeout == 120
    assert config.fallback_enabled is False


def test_config_fallback_enabled_variations(monkeypatch):
    """Test different ways to disable fallback."""
    # Test with "false"
    monkeypatch.setenv("LLM_FALLBACK_ENABLED", "false")
    config = LLMConfig()
    assert config.fallback_enabled is False

    # Test with "False"
    monkeypatch.setenv("LLM_FALLBACK_ENABLED", "False")
    config = LLMConfig()
    assert config.fallback_enabled is False

    # Test with "true"
    monkeypatch.setenv("LLM_FALLBACK_ENABLED", "true")
    config = LLMConfig()
    assert config.fallback_enabled is True
