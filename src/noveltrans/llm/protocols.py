"""LLM protocols and data models for structured responses."""

import json
import re
from contextlib import suppress
from typing import Any, Protocol

from pydantic import BaseModel, Field, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def clean_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in ["key_events", "characters_present", "qa_flags"]:
                val = data.get(field)
                if isinstance(val, list):
                    cleaned = []
                    for item in val:
                        if isinstance(item, dict):
                            parts = []
                            for k in ["event", "name", "issue_type", "description", "text"]:
                                if k in item and item[k]:
                                    parts.append(str(item[k]))
                            if not parts:
                                parts.append(json.dumps(item, ensure_ascii=False))
                            cleaned.append(": ".join(parts))
                        elif item is not None:
                            cleaned.append(str(item))
                    data[field] = cleaned
        return data


class SeedResult(BaseModel):
    """Result from the initial glossary and story seeding LLM step."""

    characters: list[Character] = Field(default_factory=list)
    terms: list[GlossaryTerm] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    story_summary: str = ""
    arc_summary: str = ""


class TermAlternativesResult(BaseModel):
    """Result from the term alternatives generation LLM step."""

    alternatives: list[str] = Field(default_factory=list)


class ResponseParser(Protocol):
    """Protocol for parsing LLM response strings into structured models."""

    async def parse_translation(self, raw: str) -> TranslationResult: ...
    async def parse_analysis(self, raw: str) -> AnalysisResult: ...
    async def parse_seed(self, raw: str) -> SeedResult: ...
    async def parse_term_alternatives(self, raw: str) -> TermAlternativesResult: ...


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


def _extract_json_block(raw: str) -> str:
    """Finds and extracts the first JSON object block from a string."""
    # Look for ```json ... ``` or ``` ... ```
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
    if json_match:
        return json_match.group(1).strip()

    # Fallback: look for the first '{' and last '}'
    start_idx = raw.find("{")
    end_idx = raw.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return raw[start_idx:end_idx + 1].strip()

    return raw.strip()


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

    async def parse_term_alternatives(self, raw: str) -> TermAlternativesResult:
        """Parse raw JSON completion into TermAlternativesResult."""
        cleaned = _clean_json_str(raw)
        try:
            return TermAlternativesResult.model_validate_json(cleaned)
        except Exception as e:
            err_msg = f"Failed to parse TermAlternativesResult JSON: {e}\nRaw input: {raw[:200]}"
            raise ValueError(err_msg) from e


class PromptBasedParser:
    """Parses LLM output from a JSON block in the text response."""

    async def parse_translation(self, raw: str) -> TranslationResult:
        """Parse translation output from JSON block."""
        cleaned = _extract_json_block(raw)
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                return TranslationResult.model_validate_json(cleaned)
            except Exception as e:
                err_msg = f"Failed to parse TranslationResult JSON: {e}\nRaw input: {raw[:200]}"
                raise ValueError(err_msg) from e
        # Fallback if raw is plain text translation output
        return TranslationResult(translated_text=raw.strip())

    async def parse_analysis(self, raw: str) -> AnalysisResult:
        """Parse analysis output from JSON block."""
        cleaned = _extract_json_block(raw)
        try:
            return AnalysisResult.model_validate_json(cleaned)
        except Exception as e:
            err_msg = f"Failed to parse AnalysisResult JSON: {e}\nRaw input: {raw[:200]}"
            raise ValueError(err_msg) from e

    async def parse_seed(self, raw: str) -> SeedResult:
        """Parse seed output from JSON block."""
        cleaned = _extract_json_block(raw)
        try:
            return SeedResult.model_validate_json(cleaned)
        except Exception as e:
            err_msg = f"Failed to parse SeedResult JSON: {e}\nRaw input: {raw[:200]}"
            raise ValueError(err_msg) from e

    async def parse_term_alternatives(self, raw: str) -> TermAlternativesResult:
        """Parse term alternatives output from JSON block."""
        cleaned = _extract_json_block(raw)
        try:
            return TermAlternativesResult.model_validate_json(cleaned)
        except Exception as e:
            err_msg = f"Failed to parse TermAlternativesResult JSON: {e}\nRaw input: {raw[:200]}"
            raise ValueError(err_msg) from e
