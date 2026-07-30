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


def test_approve_pending_terms_workflow(tmp_path: Path) -> None:
    """Test approval workflow: merge pending terms into glossary and clear pending file."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    manager = GlossaryManager(project_dir=project_dir)
    # Ensure default empty glossary exists
    manager.create_default_glossary()

    pending1 = GlossaryTerm(source="마석", target="Mana Stone", category="item", confidence=0.7)
    pending2 = GlossaryTerm(source="게이트", target="Gate", category="concept", confidence=0.6)

    manager.add_pending_terms([pending1, pending2])

    loaded_pending = manager.load_pending_terms()
    assert len(loaded_pending) == 2
    assert {t.source for t in loaded_pending} == {"마석", "게이트"}

    # Approve pending terms
    approved = manager.approve()
    assert len(approved) == 2

    # Check glossary now contains approved terms
    updated_glossary = manager.load_glossary()
    term_sources = {t.source for t in updated_glossary.terms}
    assert "마석" in term_sources
    assert "게이트" in term_sources

    # Check pending terms file is now cleared
    cleared_pending = manager.load_pending_terms()
    assert len(cleared_pending) == 0
