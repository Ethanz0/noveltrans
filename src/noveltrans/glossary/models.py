"""Glossary and character data models."""

from pydantic import BaseModel, Field


class CharacterAlias(BaseModel):
    """Alias for a character (e.g. title, disguise, nickname)."""

    source: str
    target: str
    gender: str
    context: str
    alias_type: str = "name"


class Character(BaseModel):
    """Enriched character model with aliases, identity, and speech style."""

    id: str
    canonical_name: str
    aliases: list[CharacterAlias] = Field(default_factory=list)
    gender: str
    speech_style: str
    appearance: str = ""
    knows_identity: list[str] = Field(default_factory=list)
    always_include: bool = False
    notes: str = ""


class Relationship(BaseModel):
    """Relationship model between two or more characters."""

    characters: list[str]
    description: str
    since_chapter: int | None = None


class GlossaryTerm(BaseModel):
    """General glossary term (place, organization, item, etc.)."""

    source: str
    target: str
    category: str
    notes: str = ""
    confidence: float = 1.0


class Glossary(BaseModel):
    """Top-level glossary containing characters, terms, and relationships."""

    characters: list[Character] = Field(default_factory=list)
    terms: list[GlossaryTerm] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
