import subprocess
import sys
from pathlib import Path

import pytest

from api.llm_client import LLMClient

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    class DummyCompletedProcess:
        def __init__(self, stdout):
            self.stdout = stdout

    def fake_run(cmd, capture_output, text, timeout):
        return DummyCompletedProcess(
            '{"entities": [{"name": "X", "type": "concept", "description": "desc"}], "relations": [{"from": "X", "to": "Y", "type": "related_to", "evidence": "test"}]}'
        )

    monkeypatch.setattr(subprocess, "run", fake_run)


def test_extract_entities_relations(mock_subprocess_run):
    client = LLMClient()
    result = client.extract_entities_relations("Texto de teste.")
    assert "entities" in result
    assert "relations" in result
    assert result["entities"][0]["name"] == "X"
