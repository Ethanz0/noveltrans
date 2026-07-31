"""Unit tests for noveltrans GlossaryManager."""

from pathlib import Path

from noveltrans.glossary.manager import GlossaryManager
from noveltrans.glossary.models import (
    Character,
    CharacterAlias,
    GlossaryTerm,
    Relationship,
)


def test_load_save_glossary_roundtrip(tmp_path: Path) -> None:
    """Test creating, saving, and loading a Glossary model roundtrip."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    manager = GlossaryManager(project_dir=project_dir)
    glossary = manager.load_glossary()
    assert len(glossary.characters) == 0
    assert len(glossary.terms) == 0

    char = Character(
        id="hero",
        canonical_name="Lee Jin",
        aliases=[CharacterAlias(source="이진", target="Lee Jin", gender="male", context="name")],
        gender="male",
        speech_style="heroic",
    )
    term = GlossaryTerm(source="마검", target="Demon Sword", category="item")
    rel = Relationship(characters=["hero"], description="Solo wanderer")

    manager.add_character(char)
    manager.add_term(term)
    manager.add_relationship(rel)

    loaded = manager.load_glossary()
    assert len(loaded.characters) == 1
    assert loaded.characters[0].id == "hero"
    assert len(loaded.terms) == 1
    assert loaded.terms[0].source == "마검"
    assert len(loaded.relationships) == 1

