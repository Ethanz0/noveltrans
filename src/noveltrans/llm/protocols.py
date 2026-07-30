"""LLM protocols and data models for structured responses."""

import json
import re
from contextlib import suppress
from typing import Any, Protocol

from pydantic import BaseModel, Field

from noveltrans.glossary.models import Character, GlossaryTerm, Relationship
from noveltrans.state.models import SignificantEvent


class TranslationResult(BaseModel):
    """Result from the translation LLM step."""

    translated_text: str
    translator_notes: str = ""


class AnalysisResult(BaseModel):
    """Result from the merged post-translation analysis LLM step."""

    summary: str
    key_events: list[str] = Field(default_factory=list)
    characters_present: list[str] = Field(default_factory=list)
    new_characters: list[Character] = Field(default_factory=list)
    new_terms: list[GlossaryTerm] = Field(default_factory=list)
    character_updates: list[dict[str, Any]] = Field(default_factory=list)
    relationship_updates: list[Relationship] = Field(default_factory=list)
    significant_events: list[SignificantEvent] = Field(default_factory=list)
    qa_flags: list[str] = Field(default_factory=list)


class SeedResult(BaseModel):
    """Result from the initial glossary and story seeding LLM step."""

    characters: list[Character] = Field(default_factory=list)
    terms: list[GlossaryTerm] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    story_summary: str = ""
    arc_summary: str = ""


class ResponseParser(Protocol):
    """Protocol for parsing LLM response strings into structured models."""

    async def parse_translation(self, raw: str) -> TranslationResult: ...
    async def parse_analysis(self, raw: str) -> AnalysisResult: ...
    async def parse_seed(self, raw: str) -> SeedResult: ...


def _clean_json_str(raw: str) -> str:
    """Strips markdown code blocks and whitespace from JSON string."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening ```json or ```
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _extract_xml_tag(raw: str, tag: str) -> str | None:
    """Extracts text content inside <tag>...</tag>."""
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


class StructuredOutputParser:
    """Parses LLM output using OpenAI response_format / JSON schemas."""

    async def parse_translation(self, raw: str) -> TranslationResult:
        """Parse raw JSON completion into TranslationResult."""
        cleaned = _clean_json_str(raw)
        try:
            return TranslationResult.model_validate_json(cleaned)
        except Exception:
            # Fallback if raw is plain text translation output
            return TranslationResult(translated_text=cleaned)

    async def parse_analysis(self, raw: str) -> AnalysisResult:
        """Parse raw JSON completion into AnalysisResult."""
        cleaned = _clean_json_str(raw)
        try:
            return AnalysisResult.model_validate_json(cleaned)
        except Exception as e:
            err_msg = f"Failed to parse AnalysisResult JSON: {e}\nRaw input: {raw[:200]}"
            raise ValueError(err_msg) from e

    async def parse_seed(self, raw: str) -> SeedResult:
        """Parse raw JSON completion into SeedResult."""
        cleaned = _clean_json_str(raw)
        try:
            return SeedResult.model_validate_json(cleaned)
        except Exception as e:
            err_msg = f"Failed to parse SeedResult JSON: {e}\nRaw input: {raw[:200]}"
            raise ValueError(err_msg) from e


class PromptBasedParser:
    """Parses LLM output from XML tags (e.g. <translation>, <summary>, <terms>)."""

    async def parse_translation(self, raw: str) -> TranslationResult:
        """Parse translation output from XML tags."""
        text_content = _extract_xml_tag(raw, "translation")
        notes_content = (
            _extract_xml_tag(raw, "translator_notes")
            or _extract_xml_tag(raw, "notes")
            or ""
        )

        if text_content is not None:
            return TranslationResult(
                translated_text=text_content,
                translator_notes=notes_content,
            )

        # Fallback if no <translation> tag found
        return TranslationResult(
            translated_text=raw.strip(),
            translator_notes=notes_content,
        )

    async def parse_analysis(self, raw: str) -> AnalysisResult:
        """Parse analysis output from XML tags."""
        summary = _extract_xml_tag(raw, "summary") or ""

        def parse_json_or_lines(tag_name: str) -> list[Any]:
            tag_val = _extract_xml_tag(raw, tag_name)
            if not tag_val:
                return []
            with suppress(Exception):
                parsed = json.loads(_clean_json_str(tag_val))
                if isinstance(parsed, list):
                    return parsed
            # Line fallback
            lines = [line.strip("- *").strip() for line in tag_val.splitlines() if line.strip()]
            return lines

        key_events_raw = parse_json_or_lines("key_events") or parse_json_or_lines("events")
        key_events = [str(x) for x in key_events_raw]
        characters_present = [str(x) for x in parse_json_or_lines("characters_present")]
        qa_flags = [str(x) for x in parse_json_or_lines("qa_flags")]

        new_chars_raw = parse_json_or_lines("new_characters")
        new_characters: list[Character] = []
        for item in new_chars_raw:
            if isinstance(item, dict):
                with suppress(Exception):
                    new_characters.append(Character.model_validate(item))

        new_terms_raw = parse_json_or_lines("new_terms") or parse_json_or_lines("terms")
        new_terms: list[GlossaryTerm] = []
        for item in new_terms_raw:
            if isinstance(item, dict):
                with suppress(Exception):
                    new_terms.append(GlossaryTerm.model_validate(item))

        char_updates_raw = parse_json_or_lines("character_updates")
        character_updates: list[dict[str, Any]] = [
            item for item in char_updates_raw if isinstance(item, dict)
        ]

        rel_updates_raw = parse_json_or_lines("relationship_updates")
        relationship_updates: list[Relationship] = []
        for item in rel_updates_raw:
            if isinstance(item, dict):
                with suppress(Exception):
                    relationship_updates.append(Relationship.model_validate(item))

        sig_events_raw = parse_json_or_lines("significant_events")
        significant_events: list[SignificantEvent] = []
        for item in sig_events_raw:
            if isinstance(item, dict):
                with suppress(Exception):
                    significant_events.append(SignificantEvent.model_validate(item))

        return AnalysisResult(
            summary=summary,
            key_events=key_events,
            characters_present=characters_present,
            new_characters=new_characters,
            new_terms=new_terms,
            character_updates=character_updates,
            relationship_updates=relationship_updates,
            significant_events=significant_events,
            qa_flags=qa_flags,
        )

    async def parse_seed(self, raw: str) -> SeedResult:
        """Parse seed output from XML tags."""
        story_summary = _extract_xml_tag(raw, "story_summary") or ""
        arc_summary = _extract_xml_tag(raw, "arc_summary") or ""

        def parse_json_list(tag_name: str) -> list[dict[str, Any]]:
            tag_val = _extract_xml_tag(raw, tag_name)
            if not tag_val:
                return []
            try:
                parsed = json.loads(_clean_json_str(tag_val))
                if isinstance(parsed, list):
                    return [x for x in parsed if isinstance(x, dict)]
            except Exception:
                pass
            return []

        chars = [Character.model_validate(x) for x in parse_json_list("characters")]
        terms = [GlossaryTerm.model_validate(x) for x in parse_json_list("terms")]
        rels = [Relationship.model_validate(x) for x in parse_json_list("relationships")]

        return SeedResult(
            characters=chars,
            terms=terms,
            relationships=rels,
            story_summary=story_summary,
            arc_summary=arc_summary,
        )

