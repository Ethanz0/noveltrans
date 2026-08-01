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


def test_process_analysis_term_auto_commit(
    temp_project_dir: Path, mock_llm_client: MagicMock
) -> None:
    analyzer = ChapterAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )

    term1 = GlossaryTerm(
        source="그림자 병사",
        target="Shadow Soldier",
        category="concept",
    )
    term2 = GlossaryTerm(
        source="마력 측정기",
        target="Mana Measuring Device",
        category="item",
    )

    analysis = AnalysisResult(
        summary="Test chapter summary",
        new_terms=[term1, term2],
    )

    processed = analyzer.process_analysis_result(chapter_number=1, analysis=analysis)

    assert term1 in processed["new_terms"]
    assert term2 in processed["new_terms"]

    # Verify both terms committed to glossary.json with reviewed=False
    manager = GlossaryManager(project_dir=temp_project_dir)
    glossary = manager.load_glossary()
    
    saved_terms = {t.source: t for t in glossary.terms}
    assert "그림자 병사" in saved_terms
    assert "마력 측정기" in saved_terms
    assert not saved_terms["그림자 병사"].reviewed
    assert not saved_terms["마력 측정기"].reviewed


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


def test_process_analysis_character_updates(
    temp_project_dir: Path, mock_llm_client: MagicMock
) -> None:
    analyzer = ChapterAnalyzer(
        llm_client=mock_llm_client,
        project_dir=temp_project_dir,
    )

    manager = GlossaryManager(project_dir=temp_project_dir)
    initial_char = Character(
        id="head_maid",
        canonical_name="Head Maid",
        aliases=[],
        gender="female",
        speech_style="Strict",
        appearance="Woman in her 30s",
        knows_identity=[],
    )
    manager.add_character(initial_char)

    analysis = AnalysisResult(
        summary="Head Maid's real name is revealed.",
        character_updates=[
            {
                "id": "head_maid",
                "canonical_name": "Eleanor",
                "aliases": [
                    {
                        "source": "엘리너",
                        "target": "Eleanor",
                        "gender": "female",
                        "context": "Real name",
                        "alias_type": "name"
                    }
                ],
                "knows_identity": ["sung_jinwoo"],
                "speech_style": "Friendly",
            }
        ],
    )

    analyzer.process_analysis_result(chapter_number=1, analysis=analysis)

    glossary = manager.load_glossary()
    updated_char = next(c for c in glossary.characters if c.id == "head_maid")
    assert updated_char.canonical_name == "Eleanor"
    assert updated_char.speech_style == "Friendly"
    assert "sung_jinwoo" in updated_char.knows_identity
    assert len(updated_char.aliases) == 1
    assert updated_char.aliases[0].target == "Eleanor"
