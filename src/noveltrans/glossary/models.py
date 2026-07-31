"""Glossary and character data models."""

import re
from typing import Any
from pydantic import BaseModel, Field, model_validator


class CharacterAlias(BaseModel):
    """Alias for a character (e.g. title, disguise, nickname)."""

    source: str
    target: str
    gender: str = "unknown"
    context: str = ""
    alias_type: str = "name"
    reviewed: bool = True


class Character(BaseModel):
    """Enriched character model with aliases, identity, and speech style."""

    id: str = ""
    canonical_name: str
    aliases: list[CharacterAlias] = Field(default_factory=list)
    gender: str = "unknown"
    speech_style: str = "standard"
    appearance: str = ""
    knows_identity: list[str] = Field(default_factory=list)
    always_include: bool = False
    notes: str = ""
    reviewed: bool = True

    @model_validator(mode="before")
    @classmethod
    def generate_fields_if_missing(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("id") and data.get("canonical_name"):
                name = data["canonical_name"].strip().lower()
                data["id"] = re.sub(r"[^a-z0-9_]+", "_", name).strip("_")
            if not data.get("gender"):
                data["gender"] = "unknown"
            if not data.get("speech_style"):
                data["speech_style"] = "standard"
        return data


class Relationship(BaseModel):
    """Relationship model between two or more characters."""

    characters: list[str] = Field(default_factory=list)
    description: str
    since_chapter: int | None = None

    @model_validator(mode="before")
    @classmethod
    def convert_character_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "characters" not in data or not data["characters"]:
                chars = []
                for k in ["character_1", "character_2", "char_1", "char_2", "character1", "character2"]:
                    if k in data and data[k]:
                        chars.append(str(data[k]))
                if chars:
                    data["characters"] = chars
        return data



class GlossaryTerm(BaseModel):
    """General glossary term (place, organization, item, etc.)."""

    source: str
    target: str
    category: str = "general"
    notes: str = ""
    confidence: float = 1.0
    reviewed: bool = True

    @model_validator(mode="before")
    @classmethod
    def clean_confidence(cls, data: Any) -> Any:
        if isinstance(data, dict):
            conf = data.get("confidence")
            if conf is not None:
                if isinstance(conf, str):
                    conf_clean = conf.strip().rstrip("%").strip()
                    try:
                        val = float(conf_clean)
                        if val > 1.0:
                            val = val / 100.0
                        data["confidence"] = val
                    except ValueError:
                        conf_lower = conf_clean.lower()
                        if "high" in conf_lower or "strong" in conf_lower or "sure" in conf_lower:
                            data["confidence"] = 1.0
                        elif "medium" in conf_lower or "med" in conf_lower:
                            data["confidence"] = 0.8
                        elif "low" in conf_lower or "weak" in conf_lower:
                            data["confidence"] = 0.5
                        else:
                            data["confidence"] = 1.0
                elif isinstance(conf, (int, float)):
                    if conf > 1.0:
                        data["confidence"] = float(conf) / 100.0
                else:
                    data["confidence"] = 1.0
        return data



class Glossary(BaseModel):
    """Top-level glossary containing characters, terms, and relationships."""

    characters: list[Character] = Field(default_factory=list)
    terms: list[GlossaryTerm] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
