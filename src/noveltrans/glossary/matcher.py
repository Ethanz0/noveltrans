"""Glossary matcher using Aho-Corasick exact search."""

import ahocorasick_rs

from noveltrans.glossary.models import Character, Glossary, GlossaryTerm, Relationship


class GlossaryMatcher:
    """Matches text against glossary characters, terms, and relationships."""

    def __init__(
        self,
        glossary: Glossary | None = None,
    ) -> None:
        """Initialize GlossaryMatcher with optional glossary."""
        self.glossary = glossary

    def match(self, text: str, glossary: Glossary | None = None) -> Glossary:
        """Match characters, terms, and relationships in text.

        Returns a filtered Glossary subset.
        """
        target_glossary = glossary if glossary is not None else self.glossary
        if target_glossary is None:
            return Glossary()

        matched_char_ids: set[str] = set()
        matched_term_sources: set[str] = set()

        # Step 1: Collect patterns for Aho-Corasick exact search & always_include
        pattern_to_chars: dict[str, list[Character]] = {}
        pattern_to_terms: dict[str, list[GlossaryTerm]] = {}
        patterns: list[str] = []

        for char in target_glossary.characters:
            if char.always_include:
                matched_char_ids.add(char.id)

            if char.canonical_name:
                patterns.append(char.canonical_name)
                pattern_to_chars.setdefault(char.canonical_name, []).append(char)

            for alias in char.aliases:
                if alias.source:
                    patterns.append(alias.source)
                    pattern_to_chars.setdefault(alias.source, []).append(char)

        for term in target_glossary.terms:
            if term.source:
                patterns.append(term.source)
                pattern_to_terms.setdefault(term.source, []).append(term)

        # Step 2: Exact matching via Aho-Corasick
        if patterns and text:
            unique_patterns = [p for p in dict.fromkeys(patterns) if p]
            if unique_patterns:
                ac = ahocorasick_rs.AhoCorasick(unique_patterns)
                found_strings = set(ac.find_matches_as_strings(text))

                for found_str in found_strings:
                    if found_str in pattern_to_chars:
                        for char in pattern_to_chars[found_str]:
                            matched_char_ids.add(char.id)
                    if found_str in pattern_to_terms:
                        for term in pattern_to_terms[found_str]:
                            matched_term_sources.add(term.source)



        # Construct matched subset
        matched_characters = [c for c in target_glossary.characters if c.id in matched_char_ids]
        matched_terms = [t for t in target_glossary.terms if t.source in matched_term_sources]

        # Filter relevant relationships
        matched_relationships: list[Relationship] = []
        for rel in target_glossary.relationships:
            rel_chars = set(rel.characters)
            if any(
                c.id in rel_chars or c.canonical_name in rel_chars
                for c in matched_characters
            ):
                matched_relationships.append(rel)

        return Glossary(
            characters=matched_characters,
            terms=matched_terms,
            relationships=matched_relationships,
        )

    def match_terms(
        self, text: str, glossary: Glossary | None = None
    ) -> tuple[list[Character], list[GlossaryTerm]]:
        """Match characters and terms in text using exact matching.

        Returns a tuple of (matched_characters, matched_terms).
        """
        matched_glossary = self.match(text, glossary)
        return matched_glossary.characters, matched_glossary.terms
