"""State data models for chapter manifest, QA issues, events, and checkpoint data."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class QAIssue(BaseModel):
    """QA anomaly issue logged during chapter translation."""

    issue_type: Literal[
        "untranslated_korean",
        "untranslated_japanese",
        "untranslated_chinese",
        "missing_glossary_term",
        "repetition_loop",
        "hallucinated_filler",
        "length_anomaly",
    ]
    description: str
    severity: Literal["warning", "error"]


class SignificantEvent(BaseModel):
    """Significant plot event extracted during post-translation analysis."""

    event_type: Literal[
        "identity_reveal",
        "power_reveal",
        "relationship_change",
        "new_location",
        "major_conflict",
        "arc_transition",
    ]
    description: str
    affects_characters: list[str] = Field(default_factory=list)
    triggers_arc_update: bool = False


class ChapterManifestEntry(BaseModel):
    """Manifest entry tracking state, timing, and issues for a single chapter."""

    chapter_number: int
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    translated_at: datetime | None = None
    model_used: str | None = None
    glossary_snapshot: str | None = None
    translation_duration_seconds: float = 0.0
    new_terms_extracted: int = 0
    force_retranslated: bool = False
    qa_issues: list[QAIssue] = Field(default_factory=list)
    significant_events: list[SignificantEvent] = Field(default_factory=list)


class TranslationManifest(BaseModel):
    """Manifest tracking translation status across all project chapters."""

    project_title: str
    chapters: dict[int, ChapterManifestEntry] = Field(default_factory=dict)
    last_translated_chapter: int = 0


class CheckpointData(BaseModel):
    """Checkpoint state for resuming translation runs."""

    last_completed_chapter: int = 0
    current_batch: list[int] = Field(default_factory=list)
    batch_start_time: datetime | None = None
