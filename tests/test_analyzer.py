"""Unit and integration tests for ChapterAnalyzer."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from noveltrans.core.analyzer import ChapterAnalyzer
from noveltrans.glossary.manager import GlossaryManager
from noveltrans.glossary.models import Character, GlossaryTerm, Relationship
from noveltrans.llm.protocols import AnalysisResult
from noveltrans.state.models import SignificantEvent


def test_analyze_chapter_basic(temp_project_dir: Path, mock_llm_client: MagicMock) -> None:
    analyzer = ChapterAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )
    result = analyzer.analyze_sync(
        chapter_number=1,
        source_text="성진우는 그림자 병사를 소환했다.",
        translated_text="Sung Jinwoo summoned a Shadow Soldier.",
    )
    assert isinstance(result, AnalysisResult)
    assert result.summary == "Sung Jinwoo awakens his Shadow Monarch powers in battle."


def test_process_analysis_term_filtering(
    temp_project_dir: Path, mock_llm_client: MagicMock
) -> None:
    analyzer = ChapterAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
        confidence_threshold=0.8,
    )

    high_term = GlossaryTerm(
        source="그림자 병사",
        target="Shadow Soldier",
        category="concept",
        confidence=0.9,
    )
    low_term = GlossaryTerm(
        source="마력 측정기",
        target="Mana Measuring Device",
        category="item",
        confidence=0.6,
    )

    analysis = AnalysisResult(
        summary="Test chapter summary",
        new_terms=[high_term, low_term],
    )

    processed = analyzer.process_analysis_result(chapter_number=1, analysis=analysis)

    assert high_term in processed["high_confidence_terms"]
    assert low_term in processed["low_confidence_terms"]

    # Verify high_term committed to glossary.json
    manager = GlossaryManager(project_dir=temp_project_dir)
    glossary = manager.load_glossary()
    term_sources = {t.source for t in glossary.terms}
    assert "그림자 병사" in term_sources
    assert "마력 측정기" not in term_sources

    # Verify low_term added to pending_terms.json
    pending = manager.load_pending_terms()
    pending_sources = {t.source for t in pending}
    assert "마력 측정기" in pending_sources


def test_process_analysis_characters_and_relationships(
    temp_project_dir: Path, mock_llm_client: MagicMock
) -> None:
    analyzer = ChapterAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )

    new_char = Character(
        id="go_gun_hee",
        canonical_name="Go Gun-hee",
        aliases=[],
        gender="male",
        speech_style="authoritative and grandfatherly",
    )
    rel = Relationship(
        characters=["sung_jinwoo", "go_gun_hee"],
        description="Chairman and S-rank hunter mutual respect",
    )

    analysis = AnalysisResult(
        summary="Met Chairman Go Gun-hee.",
        new_characters=[new_char],
        relationship_updates=[rel],
    )

    analyzer.process_analysis_result(chapter_number=1, analysis=analysis)

    manager = GlossaryManager(project_dir=temp_project_dir)
    glossary = manager.load_glossary()
    char_ids = {c.id for c in glossary.characters}
    assert "go_gun_hee" in char_ids
    assert len(glossary.relationships) >= 1


def test_process_analysis_chapter_summary_saved(
    temp_project_dir: Path, mock_llm_client: MagicMock
) -> None:
    analyzer = ChapterAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )

    analysis = AnalysisResult(
        summary="Jinwoo defeats the dungeon boss.",
        key_events=["Enters dungeon", "Defeats boss"],
        characters_present=["sung_jinwoo"],
    )

    analyzer.process_analysis_result(chapter_number=3, analysis=analysis)

    summary_file = temp_project_dir / "state" / "summaries" / "ch003.json"
    assert summary_file.exists()
    data = json.loads(summary_file.read_text(encoding="utf-8"))
    assert data["chapter_number"] == 3
    assert data["summary"] == "Jinwoo defeats the dungeon boss."


def test_process_analysis_arc_trigger(temp_project_dir: Path, mock_llm_client: MagicMock) -> None:
    analyzer = ChapterAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )

    sig_event = SignificantEvent(
        event_type="arc_transition",
        description="Entering the Red Gate arc",
        affects_characters=["sung_jinwoo"],
        triggers_arc_update=True,
    )

    analysis = AnalysisResult(
        summary="Entered Red Gate.",
        significant_events=[sig_event],
    )

    res = analyzer.process_analysis_result(
        chapter_number=1, analysis=analysis, chapters_since_last_arc=1
    )
    assert res["triggers_arc_update"] is True


def test_regenerate_arc_summary(temp_project_dir: Path, mock_llm_client: MagicMock) -> None:
    mock_llm_client.complete.return_value = "New Arc 2 Summary"
    analyzer = ChapterAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )

    # Pre-populate chapter summary
    summaries_dir = temp_project_dir / "state" / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    (summaries_dir / "ch001.json").write_text(
        json.dumps({"chapter_number": 1, "summary": "Ch1 summary"}, ensure_ascii=False),
        encoding="utf-8",
    )

    arc_summary = analyzer.regenerate_arc_summary_sync(chapters_since_last_arc=1)
    assert arc_summary == "New Arc 2 Summary"

    arc_file = temp_project_dir / "state" / "arc_summary.json"
    assert arc_file.exists()
    data = json.loads(arc_file.read_text(encoding="utf-8"))
    assert data["arc_summary"] == "New Arc 2 Summary"
