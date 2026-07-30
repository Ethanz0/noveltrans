"""Manifest manager for tracking chapter translation status, issues, and statistics."""

from pathlib import Path
from typing import Any

from noveltrans.state.models import (
    ChapterManifestEntry,
    QAIssue,
    SignificantEvent,
    TranslationManifest,
)


class ManifestManager:
    """Manages translation manifest state persistence and statistics."""

    def __init__(self, manifest_path: Path | str, project_title: str = "Untitled") -> None:
        self.manifest_path = Path(manifest_path)
        self.project_title = project_title

    def load_manifest(self) -> TranslationManifest:
        """Load manifest from disk or return a new empty manifest."""
        if not self.manifest_path.exists():
            return TranslationManifest(project_title=self.project_title)
        try:
            content = self.manifest_path.read_text(encoding="utf-8")
            return TranslationManifest.model_validate_json(content)
        except Exception:
            return TranslationManifest(project_title=self.project_title)

    def save_manifest(self, manifest: TranslationManifest) -> None:
        """Save translation manifest atomically to disk."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        content = manifest.model_dump_json(indent=2)
        self.manifest_path.write_text(content, encoding="utf-8")

    def update_chapter(self, entry: ChapterManifestEntry) -> None:
        """Update or add a chapter entry in the manifest."""
        manifest = self.load_manifest()
        manifest.chapters[entry.chapter_number] = entry
        if entry.status == "completed" and entry.chapter_number > manifest.last_translated_chapter:
            manifest.last_translated_chapter = entry.chapter_number
        self.save_manifest(manifest)

    def get_chapter(self, chapter_number: int) -> ChapterManifestEntry | None:
        """Get manifest entry for a specific chapter."""
        manifest = self.load_manifest()
        return manifest.chapters.get(chapter_number)

    def record_qa_issue(self, chapter_number: int, issue: QAIssue) -> None:
        """Record a QA anomaly issue for a chapter entry."""
        manifest = self.load_manifest()
        entry = manifest.chapters.get(chapter_number) or ChapterManifestEntry(
            chapter_number=chapter_number
        )
        entry.qa_issues.append(issue)
        manifest.chapters[chapter_number] = entry
        self.save_manifest(manifest)

    def record_event(self, chapter_number: int, event: SignificantEvent) -> None:
        """Record a significant story event for a chapter entry."""
        manifest = self.load_manifest()
        entry = manifest.chapters.get(chapter_number) or ChapterManifestEntry(
            chapter_number=chapter_number
        )
        entry.significant_events.append(event)
        manifest.chapters[chapter_number] = entry
        self.save_manifest(manifest)

    def get_stats(self) -> dict[str, Any]:
        """Compute summary statistics across all recorded chapters."""
        manifest = self.load_manifest()
        total = len(manifest.chapters)
        completed = sum(1 for c in manifest.chapters.values() if c.status == "completed")
        pending = sum(1 for c in manifest.chapters.values() if c.status == "pending")
        failed = sum(1 for c in manifest.chapters.values() if c.status == "failed")
        total_qa_issues = sum(len(c.qa_issues) for c in manifest.chapters.values())

        return {
            "project_title": manifest.project_title,
            "total_chapters": total,
            "completed": completed,
            "pending": pending,
            "failed": failed,
            "last_translated_chapter": manifest.last_translated_chapter,
            "total_qa_issues": total_qa_issues,
        }
