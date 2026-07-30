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
        pending_path: Path | str | None = None,
    ) -> None:
        """Initialize GlossaryManager with project directory or explicit file paths."""
        if project_dir is not None:
            p_dir = Path(project_dir)
            self.glossary_path = Path(glossary_path) if glossary_path else (p_dir / "glossary.json")
            self.pending_path = (
                Path(pending_path) if pending_path else (p_dir / "state" / "pending_terms.json")
            )
        else:
            self.glossary_path = Path(glossary_path or "glossary.json")
            self.pending_path = Path(pending_path or "state/pending_terms.json")

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

    def load_pending_terms(self) -> list[GlossaryTerm]:
        """Load pending low-confidence terms from pending_path."""
        if not self.pending_path.exists():
            return []

        try:
            content = self.pending_path.read_text(encoding="utf-8").strip()
            if not content:
                return []
            raw_data: list[dict[str, Any]] = json.loads(content)
            return [GlossaryTerm.model_validate(item) for item in raw_data]
        except Exception:
            return []

    def save_pending_terms(self, pending_terms: list[GlossaryTerm]) -> None:
        """Save list of pending terms to pending_path."""
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        raw_data = [term.model_dump() for term in pending_terms]
        self.pending_path.write_text(
            json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def add_pending_terms(self, terms: list[GlossaryTerm]) -> None:
        """Append new pending terms to pending_path."""
        existing = self.load_pending_terms()
        existing_sources = {t.source for t in existing}
        for term in terms:
            if term.source not in existing_sources:
                existing.append(term)
                existing_sources.add(term.source)
        self.save_pending_terms(existing)

    def approve_pending_terms(self) -> list[GlossaryTerm]:
        """Approve pending terms by merging into glossary.json and clearing pending_terms.json."""
        pending = self.load_pending_terms()
        if not pending:
            self.save_pending_terms([])
            return []

        glossary = self.load_glossary()

        existing_term_map = {t.source: t for t in glossary.terms}
        approved: list[GlossaryTerm] = []

        for term in pending:
            existing_term_map[term.source] = term
            approved.append(term)

        glossary.terms = list(existing_term_map.values())
        self.save_glossary(glossary)
        self.save_pending_terms([])

        return approved

    def approve(self) -> list[GlossaryTerm]:
        """Alias for approve_pending_terms."""
        return self.approve_pending_terms()

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
