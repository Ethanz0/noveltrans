"""Unit tests for noveltrans ManifestManager (metadata, QA issues, force-retranslate, and stats)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from noveltrans.state.manifest import ManifestManager
from noveltrans.state.models import (
    ChapterManifestEntry,
    QAIssue,
    SignificantEvent,
    TranslationManifest,
)


@pytest.fixture
def manifest_path(tmp_path: Path) -> Path:
    return tmp_path / "state" / "manifest.json"


@pytest.fixture
def manager(manifest_path: Path) -> ManifestManager:
    return ManifestManager(manifest_path, project_title="Test Solo Leveling")


# ============================================================================
# Tier 1: Unit Tests (Basic CRUD operations on manifest entries)
# ============================================================================


def test_manifest_load_non_existent(manager: ManifestManager) -> None:
    """Tier 1: Test loading non-existent manifest returns empty TranslationManifest."""
    manifest = manager.load_manifest()
    assert manifest.project_title == "Test Solo Leveling"
    assert manifest.chapters == {}
    assert manifest.last_translated_chapter == 0


def test_manifest_save_and_load_roundtrip(
    manager: ManifestManager, sample_manifest: TranslationManifest
) -> None:
    """Tier 1: Test save and load round-trip preserves all manifest fields."""
    manager.save_manifest(sample_manifest)

    loaded = manager.load_manifest()
    assert loaded.project_title == sample_manifest.project_title
    assert len(loaded.chapters) == 2
    assert loaded.chapters[1].status == "completed"
    assert loaded.chapters[1].qa_issues[0].issue_type == "untranslated_korean"


def test_update_chapter_entry(manager: ManifestManager) -> None:
    """Tier 1: Test updating chapter manifest entry."""
    entry = ChapterManifestEntry(
        chapter_number=1,
        status="completed",
        model_used="gemini-2.5-pro",
        translation_duration_seconds=3.5,
    )
    manager.update_chapter(entry)

    loaded = manager.get_chapter(1)
    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.model_used == "gemini-2.5-pro"
    assert loaded.translation_duration_seconds == 3.5


def test_record_qa_issue(manager: ManifestManager) -> None:
    """Tier 1: Test recording a QA issue for a chapter."""
    issue = QAIssue(
        issue_type="untranslated_korean",
        description="Untranslated text found",
        severity="warning",
    )
    manager.record_qa_issue(1, issue)

    loaded = manager.get_chapter(1)
    assert loaded is not None
    assert len(loaded.qa_issues) == 1
    assert loaded.qa_issues[0].issue_type == "untranslated_korean"


def test_record_significant_event(manager: ManifestManager) -> None:
    """Tier 1: Test recording a significant story event."""
    event = SignificantEvent(
        event_type="identity_reveal",
        description="Shadow Monarch identity revealed",
        affects_characters=["sung_jinwoo"],
        triggers_arc_update=True,
    )
    manager.record_event(1, event)

    loaded = manager.get_chapter(1)
    assert loaded is not None
    assert len(loaded.significant_events) == 1
    assert loaded.significant_events[0].triggers_arc_update is True


def test_get_chapter_entry(manager: ManifestManager) -> None:
    """Tier 1: Test getting existing and non-existing chapter entries."""
    entry = ChapterManifestEntry(chapter_number=5, status="pending")
    manager.update_chapter(entry)

    assert manager.get_chapter(5) is not None
    assert manager.get_chapter(99) is None


# ============================================================================
# Tier 2: Component Integration Tests (Stats calculation & force-retranslate)
# ============================================================================


def test_manifest_stats_updates(manager: ManifestManager) -> None:
    """Tier 2: Test get_stats returns correct counts for manifest entries and QA issues."""
    manager.update_chapter(ChapterManifestEntry(chapter_number=1, status="completed"))
    manager.update_chapter(ChapterManifestEntry(chapter_number=2, status="completed"))
    manager.update_chapter(ChapterManifestEntry(chapter_number=3, status="pending"))
    manager.update_chapter(ChapterManifestEntry(chapter_number=4, status="failed"))

    issue = QAIssue(issue_type="repetition_loop", description="Loop", severity="error")
    manager.record_qa_issue(1, issue)
    manager.record_qa_issue(1, issue)

    stats = manager.get_stats()
    assert stats["total_chapters"] == 4
    assert stats["completed"] == 2
    assert stats["pending"] == 1
    assert stats["failed"] == 1
    assert stats["last_translated_chapter"] == 2
    assert stats["total_qa_issues"] == 2


def test_force_retranslate_manifest_behavior(manager: ManifestManager) -> None:
    """Tier 2: Test retranslating chapter with force=True updates force_retranslated flag."""
    # First translation
    entry = ChapterManifestEntry(
        chapter_number=1,
        status="completed",
        model_used="gemini-2.5-pro",
        force_retranslated=False,
    )
    manager.update_chapter(entry)

    # Force retranslate
    entry_re = ChapterManifestEntry(
        chapter_number=1,
        status="completed",
        model_used="gemini-2.5-pro",
        force_retranslated=True,
    )
    manager.update_chapter(entry_re)

    loaded = manager.get_chapter(1)
    assert loaded is not None
    assert loaded.force_retranslated is True


def test_manifest_persistence_across_instances(manifest_path: Path) -> None:
    """Tier 2: Test manifest persistence across distinct manager instances."""
    mgr1 = ManifestManager(manifest_path, project_title="Title A")
    mgr1.update_chapter(ChapterManifestEntry(chapter_number=1, status="completed"))

    mgr2 = ManifestManager(manifest_path, project_title="Title A")
    assert mgr2.get_chapter(1) is not None
    assert mgr2.get_chapter(1).status == "completed"


def test_last_translated_chapter_auto_update(manager: ManifestManager) -> None:
    """Tier 2: Completing chapter updates last_translated_chapter monotonically."""
    manager.update_chapter(ChapterManifestEntry(chapter_number=10, status="completed"))
    assert manager.load_manifest().last_translated_chapter == 10

    # Pending status does not update last_translated_chapter
    manager.update_chapter(ChapterManifestEntry(chapter_number=11, status="pending"))
    assert manager.load_manifest().last_translated_chapter == 10


def test_multiple_qa_issues_aggregation(manager: ManifestManager) -> None:
    """Tier 2: Test appending multiple QA issues to the same chapter."""
    q1 = QAIssue(
        issue_type="untranslated_korean", description="Korean fragment", severity="warning"
    )
    q2 = QAIssue(
        issue_type="hallucinated_filler", description="LLM meta phrase", severity="error"
    )

    manager.record_qa_issue(1, q1)
    manager.record_qa_issue(1, q2)

    entry = manager.get_chapter(1)
    assert entry is not None
    assert len(entry.qa_issues) == 2
    types = [q.issue_type for q in entry.qa_issues]
    assert "untranslated_korean" in types
    assert "hallucinated_filler" in types


# ============================================================================
# Tier 3: Edge Cases & Boundary Tests
# ============================================================================


def test_corrupt_manifest_file_fallback(manifest_path: Path) -> None:
    """Tier 3: Test corrupt JSON manifest file falls back to default empty manifest."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("NOT JSON CONTENT", encoding="utf-8")

    mgr = ManifestManager(manifest_path, project_title="Fallback Title")
    loaded = mgr.load_manifest()
    assert loaded.project_title == "Fallback Title"
    assert loaded.chapters == {}


# ============================================================================
# Tier 4: Real-world Application Scenarios
# ============================================================================


def test_full_chapter_manifest_lifecycle(manager: ManifestManager) -> None:
    """Tier 4: Simulate complete chapter lifecycle tracking."""
    # 1. Init chapter as pending
    manager.update_chapter(ChapterManifestEntry(chapter_number=1, status="pending"))
    assert manager.get_chapter(1).status == "pending"

    # 2. Start translation
    manager.update_chapter(ChapterManifestEntry(chapter_number=1, status="in_progress"))
    assert manager.get_chapter(1).status == "in_progress"

    # 3. Finish translation with duration, QA issues, and events
    final_entry = ChapterManifestEntry(
        chapter_number=1,
        status="completed",
        translated_at=datetime.now(UTC),
        model_used="gemini-2.5-pro",
        glossary_snapshot="state/glossary_snapshots/ch001.json",
        translation_duration_seconds=5.4,
        new_terms_extracted=3,
        qa_issues=[
            QAIssue(
                issue_type="untranslated_korean", description="Minor fragment", severity="warning"
            )
        ],
        significant_events=[
            SignificantEvent(
                event_type="power_reveal",
                description="Powers revealed",
                affects_characters=["sung_jinwoo"],
                triggers_arc_update=True,
            )
        ],
    )
    manager.update_chapter(final_entry)

    res = manager.get_chapter(1)
    assert res is not None
    assert res.status == "completed"
    assert res.translation_duration_seconds == 5.4
    assert res.new_terms_extracted == 3
    assert len(res.qa_issues) == 1
    assert len(res.significant_events) == 1
