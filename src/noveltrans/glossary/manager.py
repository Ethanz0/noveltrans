"""Glossary manager for loading, saving, and managing glossary and pending terms."""

import json
from pathlib import Path
from typing import Any

from noveltrans.glossary.models import Character, Glossary, GlossaryTerm, Relationship


class GlossaryManager:
    """Manages reading, writing, updating, and approving terms in project glossary."""

    def __init__(
        self,
        project_dir: Path | str | None = None,
        glossary_path: Path | str | None = None,
    ) -> None:
        """Initialize GlossaryManager with project directory or explicit file paths."""
        if project_dir is not None:
            p_dir = Path(project_dir)
            self.glossary_path = Path(glossary_path) if glossary_path else (p_dir / "glossary.json")
        else:
            self.glossary_path = Path(glossary_path or "glossary.json")

    def load_glossary(self) -> Glossary:
        """Load glossary from glossary_path.

        Returns default empty Glossary if missing or invalid.
        """
        if not self.glossary_path.exists():
            return self.create_default_glossary()

        try:
            content = self.glossary_path.read_text(encoding="utf-8").strip()
            if not content:
                return self.create_default_glossary()
            return Glossary.model_validate_json(content)
        except Exception:
            return Glossary()

    def save_glossary(self, glossary: Glossary) -> None:
        """Save Glossary model to glossary_path."""
        self.glossary_path.parent.mkdir(parents=True, exist_ok=True)
        content = glossary.model_dump_json(indent=2)
        self.glossary_path.write_text(content, encoding="utf-8")

    def create_default_glossary(self) -> Glossary:
        """Create and save a default empty Glossary."""
        glossary = Glossary()
        self.save_glossary(glossary)
        return glossary



    def add_character(self, character: Character) -> None:
        """Add or update a character in the glossary and save."""
        glossary = self.load_glossary()
        char_map = {c.id: c for c in glossary.characters}
        char_map[character.id] = character
        glossary.characters = list(char_map.values())
        self.save_glossary(glossary)

    def add_term(self, term: GlossaryTerm) -> None:
        """Add or update a glossary term in the glossary and save."""
        glossary = self.load_glossary()
        term_map = {t.source: t for t in glossary.terms}
        term_map[term.source] = term
        glossary.terms = list(term_map.values())
        self.save_glossary(glossary)

    def add_relationship(self, relationship: Relationship) -> None:
        """Add or update a relationship in the glossary and save."""
        glossary = self.load_glossary()
        rel_set = set(relationship.characters)
        existing_sets = [set(r.characters) for r in glossary.relationships]

        if rel_set not in existing_sets:
            glossary.relationships.append(relationship)
        else:
            for idx, r in enumerate(glossary.relationships):
                if set(r.characters) == rel_set:
                    glossary.relationships[idx] = relationship
                    break
        self.save_glossary(glossary)
