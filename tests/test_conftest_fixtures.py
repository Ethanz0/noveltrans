"""Test file verifying all conftest fixtures execute properly."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from noveltrans.config.settings import EnvSettings, ProjectConfig
from noveltrans.glossary.models import Glossary
from noveltrans.llm.protocols import AnalysisResult, SeedResult, TranslationResult
from noveltrans.state.models import CheckpointData, TranslationManifest


def test_sample_project_config_fixture(sample_project_config: ProjectConfig) -> None:
    assert sample_project_config.title == "Test Solo Leveling"
    assert sample_project_config.author == "Chugong"
    assert sample_project_config.context_recent_chapters == 2
    assert sample_project_config.context_recent_summaries == 5


def test_sample_env_settings_fixture(sample_env_settings: EnvSettings) -> None:
    assert sample_env_settings.model_name == "gemini-2.5-pro"
    assert sample_env_settings.openai_api_key == "mock-openai-api-key-for-tests"


def test_sample_glossary_fixture(sample_glossary: Glossary) -> None:
    assert len(sample_glossary.characters) == 2
    assert sample_glossary.characters[0].canonical_name == "Sung Jinwoo"
    assert sample_glossary.characters[0].always_include is True
    assert len(sample_glossary.terms) == 3
    assert len(sample_glossary.relationships) == 1


def test_sample_manifest_fixture(sample_manifest: TranslationManifest) -> None:
    assert sample_manifest.project_title == "Test Solo Leveling"
    assert 1 in sample_manifest.chapters
    assert sample_manifest.chapters[1].status == "completed"
    assert len(sample_manifest.chapters[1].qa_issues) == 1
    assert len(sample_manifest.chapters[1].significant_events) == 1


def test_sample_checkpoint_fixture(sample_checkpoint: CheckpointData) -> None:
    assert sample_checkpoint.last_completed_chapter == 1
    assert sample_checkpoint.current_batch == [1, 2, 3, 4, 5]


def test_sample_jinja_templates_fixture(sample_jinja_templates: dict[str, Path]) -> None:
    assert "translator.jinja2" in sample_jinja_templates
    assert sample_jinja_templates["translator.jinja2"].exists()


def test_temp_project_dir_fixture(temp_project_dir: Path) -> None:
    assert (temp_project_dir / "project.json").exists()
    assert (temp_project_dir / "glossary.json").exists()
    assert (temp_project_dir / "style_guide.md").exists()
    assert (temp_project_dir / ".env").exists()
    assert (temp_project_dir / "source" / "ch001.txt").exists()
    assert (temp_project_dir / "state" / "pending_terms.json").exists()
    assert (temp_project_dir / "prompts" / "translator.jinja2").exists()


def test_mock_llm_fixtures(
    mock_translation_result: TranslationResult,
    mock_analysis_result: AnalysisResult,
    mock_seed_result: SeedResult,
    mock_llm_client: MagicMock,
) -> None:
    assert "Sung Jinwoo" in mock_translation_result.translated_text
    assert len(mock_analysis_result.key_events) > 0
    assert len(mock_seed_result.characters) == 2
    assert isinstance(mock_llm_client.parse_translation, AsyncMock)
