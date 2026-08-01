"""Glossary matcher using Aho-Corasick exact search and rapidfuzz fallback."""

import re

import ahocorasick_rs
from rapidfuzz import fuzz

from noveltrans.glossary.models import Character, Glossary, GlossaryTerm, Relationship


class GlossaryMatcher:
    """Matches text against glossary characters, terms, and relationships."""

    def __init__(
        self,
        glossary: Glossary | None = None,
        similarity_threshold: float = 85.0,
    ) -> None:
        """Initialize GlossaryMatcher with optional glossary and fuzzy similarity threshold."""
        self.glossary = glossary
        self.similarity_threshold = similarity_threshold

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

        # Step 3: Fuzzy fallback matching for unmatched terms and characters
        if text:
            raw_words = text.split()
            tokens = list(dict.fromkeys(raw_words))
            cleaned_tokens = list(dict.fromkeys(re.findall(r"[\w\uAC00-\uD7A3]+", text)))

            # Check unmatched characters
            for char in target_glossary.characters:
                if char.id in matched_char_ids:
                    continue

                candidates = [char.canonical_name] + [a.source for a in char.aliases if a.source]
                candidates = [c for c in candidates if c]

                for cand in candidates:
                    matched = False
                    for tok in tokens + cleaned_tokens:
                        if (
                            fuzz.ratio(cand, tok) >= self.similarity_threshold
                            or fuzz.partial_ratio(cand, tok) >= self.similarity_threshold
                        ):
                            matched_char_ids.add(char.id)
                            matched = True
                            break
                    if matched:
                        break

                    if matched:
                        break

            # Check unmatched terms
            for term in target_glossary.terms:
                if term.source in matched_term_sources:
                    continue

                cand = term.source
                if not cand:
                    continue

                matched = False
                for tok in tokens + cleaned_tokens:
                    if (
                        fuzz.ratio(cand, tok) >= self.similarity_threshold
                        or fuzz.partial_ratio(cand, tok) >= self.similarity_threshold
                    ):
                        matched_term_sources.add(term.source)
                        matched = True
                        break
                if matched:
                    continue

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
        """Match characters and terms in text using exact and fuzzy matching.

        Returns a tuple of (matched_characters, matched_terms).
        """
        matched_glossary = self.match(text, glossary)
        return matched_glossary.characters, matched_glossary.terms
