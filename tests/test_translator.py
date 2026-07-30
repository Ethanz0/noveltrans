"""Unit and integration tests for TranslationPipeline (Translator)."""

from pathlib import Path
from unittest.mock import MagicMock

from noveltrans.core.translator import TranslationPipeline, Translator
from noveltrans.llm.protocols import AnalysisResult, TranslationResult
from noveltrans.state.manifest import ManifestManager


def test_translator_alias() -> None:
    assert Translator is TranslationPipeline


def test_translate_chapter_end_to_end(
    temp_project_dir: Path,
    mock_llm_client: MagicMock,
    mock_translation_result: TranslationResult,
    mock_analysis_result: AnalysisResult,
) -> None:
    pipeline = TranslationPipeline(
        project_dir=temp_project_dir,
        llm_client=mock_llm_client,
    )

    entry = pipeline.translate_chapter_sync(1)

    assert entry.status == "completed"
    assert entry.chapter_number == 1
    assert entry.model_used is not None
    assert entry.translation_duration_seconds >= 0.0

    # 1. Output file saved to output/txt/ch001.txt
    out_txt = temp_project_dir / "output" / "txt" / "ch001.txt"
    assert out_txt.exists()
    assert mock_translation_result.translated_text in out_txt.read_text(encoding="utf-8")

    # 2. Manifest updated
    manifest_mgr = ManifestManager(temp_project_dir / "state" / "manifest.json")
    saved_entry = manifest_mgr.get_chapter(1)
    assert saved_entry is not None
    assert saved_entry.status == "completed"

    # 3. Checkpoint updated
    checkpoint_file = temp_project_dir / "state" / "checkpoint.json"
    assert checkpoint_file.exists()

    # 4. Assembled prompts saved
    prompt_file = temp_project_dir / "state" / "prompts" / "ch001_translator.txt"
    assert prompt_file.exists()

    # 5. Glossary snapshot created
    snapshot_file = temp_project_dir / "state" / "glossary_snapshots" / "ch001.json"
    assert snapshot_file.exists()


def test_dry_run_flag(temp_project_dir: Path, mock_llm_client: MagicMock) -> None:
    pipeline = TranslationPipeline(
        project_dir=temp_project_dir,
        llm_client=mock_llm_client,
    )

    entry = pipeline.translate_chapter_sync(1, dry_run=True)

    assert entry.status == "completed"
    # Mock LLM parse_translation should NOT be called in dry run
    mock_llm_client.parse_translation.assert_not_called()

    # Assembled prompt saved
    prompt_file = temp_project_dir / "state" / "prompts" / "ch001_translator.txt"
    assert prompt_file.exists()


def test_force_retranslate_flag(temp_project_dir: Path, mock_llm_client: MagicMock) -> None:
    pipeline = TranslationPipeline(
        project_dir=temp_project_dir,
        llm_client=mock_llm_client,
    )

    # First run
    pipeline.translate_chapter_sync(1)

    # Second run with force=True
    entry_re = pipeline.translate_chapter_sync(1, force=True)
    assert entry_re.force_retranslated is True


def test_batch_translation_resume_and_skip(
    temp_project_dir: Path, mock_llm_client: MagicMock
) -> None:
    pipeline = TranslationPipeline(
        project_dir=temp_project_dir,
        llm_client=mock_llm_client,
    )

    # Pre-complete chapter 1
    pipeline.checkpoint_manager.update_completed(1)

    entries = pipeline.translate_batch_sync([1, 2], force=False)
    assert len(entries) == 2
    # Chapter 2 should be executed, parse_translation called for ch2
    assert mock_llm_client.parse_translation.call_count >= 1


def test_qa_issues_recorded_in_manifest(
    temp_project_dir: Path, mock_llm_client: MagicMock
) -> None:
    # Set translation output to contain untranslated Korean fragment
    bad_tr = TranslationResult(
        translated_text="Sung Jinwoo spoke: '그는 갔다' before leaving.",
        translator_notes="Note",
    )
    mock_llm_client.parse_translation.return_value = bad_tr

    pipeline = TranslationPipeline(
        project_dir=temp_project_dir,
        llm_client=mock_llm_client,
    )

    entry = pipeline.translate_chapter_sync(1)
    assert len(entry.qa_issues) >= 1
    assert entry.qa_issues[0].issue_type == "untranslated_korean"


def test_fallback_arc_summary_interval(
    temp_project_dir: Path, mock_llm_client: MagicMock
) -> None:
    pipeline = TranslationPipeline(
        project_dir=temp_project_dir,
        llm_client=mock_llm_client,
    )

    # Set last_arc_update_chapter = 0, current chapter = 15
    (temp_project_dir / "source" / "ch015.txt").write_text("Chapter 15 text", encoding="utf-8")

    entry = pipeline.translate_chapter_sync(15)
    assert entry.status == "completed"
    # regenerate_arc_summary called via analyzer
    assert pipeline.last_arc_update_chapter == 15
