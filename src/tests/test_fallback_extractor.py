"""Tests for the fallback extractor module."""

from api.fallback_extractor import extract_entities_relations_fallback


def test_extract_quoted_phrases():
    """Test extraction of quoted phrases."""
    text = (
        'This text contains "Machine Learning" and "Artificial Intelligence" concepts.'
    )
    result = extract_entities_relations_fallback(text)

    entity_names = [e["name"] for e in result["entities"]]
    assert "Machine Learning" in entity_names
    assert "Artificial Intelligence" in entity_names


def test_extract_capitalized_words():
    """Test extraction of capitalized words."""
    text = "Python and JavaScript are programming languages."
    result = extract_entities_relations_fallback(text)

    entity_names = [e["name"] for e in result["entities"]]
    assert "Python" in entity_names
    assert "JavaScript" in entity_names


def test_extract_creates_relations():
    """Test that relations are created between entities."""
    text = 'test with "entity one" and "entity two"'  # Use lowercase to avoid extra capitalized entities
    result = extract_entities_relations_fallback(text)

    assert len(result["entities"]) == 2
    assert len(result["relations"]) == 1
    assert result["relations"][0]["from"] == "entity one"
    assert result["relations"][0]["to"] == "entity two"


def test_extract_empty_text():
    """Test extraction with empty text."""
    result = extract_entities_relations_fallback("")
    assert result["entities"] == []
    assert result["relations"] == []
