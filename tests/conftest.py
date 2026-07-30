"""Comprehensive pytest fixtures for noveltrans testing infrastructure."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from noveltrans.config.settings import EnvSettings, ProjectConfig
from noveltrans.glossary.models import (
    Character,
    CharacterAlias,
    Glossary,
    GlossaryTerm,
    Relationship,
)
from noveltrans.llm.protocols import AnalysisResult, SeedResult, TranslationResult
from noveltrans.state.models import (
    ChapterManifestEntry,
    CheckpointData,
    QAIssue,
    SignificantEvent,
    TranslationManifest,
)


@pytest.fixture
def sample_project_config() -> ProjectConfig:
    """Fixture providing a standard ProjectConfig instance."""
    return ProjectConfig(
        title="Test Solo Leveling",
        author="Chugong",
        source_language="ko",
        target_language="en",
        source_dir="source",
        output_dir="output",
        state_dir="state",
        glossary_path="glossary.json",
        style_guide_path="style_guide.md",
        prompts_dir="prompts",
        context_recent_chapters=2,
        context_recent_summaries=5,
        arc_summary_fallback_interval=15,
    )


@pytest.fixture
def sample_env_settings() -> EnvSettings:
    """Fixture providing a standard EnvSettings instance."""
    return EnvSettings(
        openai_api_key="mock-openai-api-key-for-tests",
        openai_base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_name="gemini-2.5-pro",
        temperature=0.3,
        max_retries=3,
        use_structured_output=True,
        log_level="INFO",
    )


@pytest.fixture
def sample_glossary() -> Glossary:
    """Fixture providing a full Glossary instance with characters and terms."""
    jinwoo_alias_name = CharacterAlias(
        source="성진우",
        target="Sung Jinwoo",
        gender="male",
        context="Standard name",
        alias_type="name",
    )
    jinwoo_alias_title = CharacterAlias(
        source="그림자 군주",
        target="Shadow Monarch",
        gender="male",
        context="Title as monarch of shadows",
        alias_type="title",
    )
    jinwoo = Character(
        id="sung_jinwoo",
        canonical_name="Sung Jinwoo",
        aliases=[jinwoo_alias_name, jinwoo_alias_title],
        gender="male",
        speech_style="determined and concise",
        appearance="Black hair, sharp glowing eyes",
        knows_identity=["cha_hae_in", "go_gun_hee"],
        always_include=True,
        notes="Main protagonist, Shadow Monarch hunter",
    )

    haein_alias_name = CharacterAlias(
        source="차해인",
        target="Cha Hae-in",
        gender="female",
        context="Standard name",
        alias_type="name",
    )
    haein_alias_nickname = CharacterAlias(
        source="무희",
        target="Dancer",
        gender="female",
        context="Moniker in battle",
        alias_type="nickname",
    )
    haein = Character(
        id="cha_hae_in",
        canonical_name="Cha Hae-in",
        aliases=[haein_alias_name, haein_alias_nickname],
        gender="female",
        speech_style="polite, focused, and professional",
        appearance="Blonde hair, athletic build",
        knows_identity=["sung_jinwoo"],
        always_include=False,
        notes="S-rank hunter, Vice-Guild Master of Hunters Guild",
    )

    term_dagger = GlossaryTerm(
        source="단검",
        target="Dagger",
        category="item",
        notes="Primary weapon class used by Jinwoo",
        confidence=1.0,
    )
    term_beast = GlossaryTerm(
        source="마수",
        target="Magic Beast",
        category="concept",
        notes="Monsters encountered within gates",
        confidence=0.95,
    )
    term_hunter = GlossaryTerm(
        source="헌터",
        target="Hunter",
        category="title",
        notes="Awakened human fighting magic beasts",
        confidence=1.0,
    )

    relationship = Relationship(
        characters=["sung_jinwoo", "cha_hae_in"],
        description="Comrades-in-arms and mutual romantic interest",
        since_chapter=10,
    )

    return Glossary(
        characters=[jinwoo, haein],
        terms=[term_dagger, term_beast, term_hunter],
        relationships=[relationship],
    )


@pytest.fixture
def sample_manifest() -> TranslationManifest:
    """Fixture providing a TranslationManifest with entries, QA issues, and events."""
    qa_issue = QAIssue(
        issue_type="untranslated_korean",
        description="Untranslated Korean fragment found in paragraph 3",
        severity="warning",
    )
    event = SignificantEvent(
        event_type="power_reveal",
        description="Sung Jinwoo reveals Shadow Extraction ability in D-Rank dungeon",
        affects_characters=["sung_jinwoo"],
        triggers_arc_update=True,
    )

    entry1 = ChapterManifestEntry(
        chapter_number=1,
        status="completed",
        translated_at=datetime.now(UTC),
        model_used="gemini-2.5-pro",
        glossary_snapshot="state/glossary_snapshots/ch001.json",
        translation_duration_seconds=4.2,
        new_terms_extracted=2,
        force_retranslated=False,
        qa_issues=[qa_issue],
        significant_events=[event],
    )
    entry2 = ChapterManifestEntry(
        chapter_number=2,
        status="pending",
    )

    return TranslationManifest(
        project_title="Test Solo Leveling",
        chapters={1: entry1, 2: entry2},
        last_translated_chapter=1,
    )


@pytest.fixture
def sample_checkpoint() -> CheckpointData:
    """Fixture providing sample CheckpointData for translation state resume tests."""
    return CheckpointData(
        last_completed_chapter=1,
        current_batch=[1, 2, 3, 4, 5],
        batch_start_time=datetime.now(UTC),
    )


@pytest.fixture
def sample_jinja_templates(tmp_path: Path) -> dict[str, Path]:
    """Fixture creating temporary Jinja2 templates in a directory."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    repo_prompts = Path(__file__).parent.parent / "prompts"

    templates = {
        "translator.jinja2": (
            "You are an expert translator specializing in "
            "{{ source_language_name | default('Korean') }} web novel translation.\n"
            "# Context\nStyle Guide: {{ style_guide }}\n"
            "Story Summary: {{ story_summary }}\nArc Summary: {{ arc_summary }}\n\n"
            "# Matched Glossary\n{% for char in characters %}\n"
            "- {{ char.canonical_name }} ({{ char.gender }}): {{ char.speech_style }}\n"
            "  Aliases: {% for a in char.aliases %}{{ a.source }} -> {{ a.target }} "
            "({{ a.gender }}); {% endfor %}\n"
            "{% endfor %}\n\n{% for term in terms %}\n"
            "- {{ term.source }} -> {{ term.target }} ({{ term.category }})\n"
            "{% endfor %}\n\n"
            "{% if source_language == 'ja' %}\n"
            "Preserve Japanese honorifics\n"
            "{% else %}\n"
            "Fully translate or adapt Korean/Chinese honorifics\n"
            "{% endif %}\n\n"
            "# Chapter Source Text\n{{ source_text }}\n"
        ),
        "analyzer.jinja2": (
            "# Post-Translation Analysis\n"
            "Analyze chapter {{ chapter_number }} for newly introduced items.\n\n"
            "{% if source_language == 'zh' %}\n"
            "Simplified vs Traditional Chinese\n"
            "{% endif %}\n\n"
            "Translated Text:\n{{ translated_text }}\n"
        ),
        "seeder.jinja2": (
            "# Glossary & Story Seeder\nExtract initial characters and terms.\n\n"
            "{% if source_language == 'zh' %}\n"
            "Simplified vs Traditional Chinese\n"
            "{% endif %}\n\n"
            "Source Text:\n{{ source_text }}\n"
        ),
        "style_analyzer.jinja2": (
            "# Style Guide Generator\nAnalyze style and tone.\n\n"
            "Source Text:\n{{ source_text }}\n"
        ),
        "arc_summary.jinja2": (
            "# Arc Summary Generator\nSummarize current arc.\n\n"
            "Current Arc Summary: {{ current_arc_summary }}\n"
            "Recent Chapter Summaries:\n{% for s in chapter_summaries %}\n"
            "- {{ s }}\n{% endfor %}\n"
        ),
        "story_summary.jinja2": (
            "# Overall Story Summary Generator\nUpdate overall story summary.\n\n"
            "Current Story Summary: {{ current_story_summary }}\n"
            "New Arc Summaries: {{ arc_summary }}\n"
        ),
    }

    result = {}
    for filename, fallback_content in templates.items():
        file_path = prompts_dir / filename
        if repo_prompts.exists() and (repo_prompts / filename).exists():
            file_path.write_text(
                (repo_prompts / filename).read_text(encoding="utf-8"), encoding="utf-8"
            )
        else:
            file_path.write_text(fallback_content, encoding="utf-8")
        result[filename] = file_path

    return result


@pytest.fixture
def temp_project_dir(
    tmp_path: Path,
    sample_project_config: ProjectConfig,
    sample_glossary: Glossary,
    sample_jinja_templates: dict[str, Path],
) -> Path:
    """Scaffolds a full temporary project structure matching noveltrans layout."""
    project_dir = tmp_path / "my_novel"
    project_dir.mkdir(parents=True, exist_ok=True)

    source_dir = project_dir / "source"
    output_txt_dir = project_dir / "output" / "txt"
    output_epub_dir = project_dir / "output" / "epub"
    state_summaries_dir = project_dir / "state" / "summaries"
    state_glossary_snapshots_dir = project_dir / "state" / "glossary_snapshots"
    state_prompts_dir = project_dir / "state" / "prompts"
    prompts_dir = project_dir / "prompts"

    for d in [
        source_dir,
        output_txt_dir,
        output_epub_dir,
        state_summaries_dir,
        state_glossary_snapshots_dir,
        state_prompts_dir,
        prompts_dir,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    (source_dir / "ch001.txt").write_text(
        "성진우는 단검을 쥐었다. 그림자 군주로서의 능력이 각성했다. 차해인은 그를 바라보았다.",
        encoding="utf-8",
    )
    (source_dir / "ch002.txt").write_text(
        "마수가 헌터들을 공격했다. 성진우는 그림자 병사를 소환했다.",
        encoding="utf-8",
    )

    (project_dir / "project.json").write_text(
        sample_project_config.model_dump_json(indent=2), encoding="utf-8"
    )
    (project_dir / "glossary.json").write_text(
        sample_glossary.model_dump_json(indent=2), encoding="utf-8"
    )
    (project_dir / "style_guide.md").write_text(
        "# Style Guide\n"
        "- Keep character names consistent.\n"
        "- Use active voice in action sequences.\n",
        encoding="utf-8",
    )
    (project_dir / ".env").write_text(
        "OPENAI_API_KEY=mock-test-key-12345\nLOG_LEVEL=DEBUG\n", encoding="utf-8"
    )
    (project_dir / "state" / "pending_terms.json").write_text("[]", encoding="utf-8")

    for tpl_name, tpl_path in sample_jinja_templates.items():
        (prompts_dir / tpl_name).write_text(
            tpl_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    return project_dir


@pytest.fixture
def mock_translation_result() -> TranslationResult:
    """Fixture returning a valid TranslationResult object."""
    return TranslationResult(
        translated_text=(
            "Sung Jinwoo gripped his dagger tightly. "
            "His powers as the Shadow Monarch awakened completely. "
            "Cha Hae-in watched him in awe."
        ),
        translator_notes="Translated preserving character tone and active verbs.",
    )


@pytest.fixture
def mock_analysis_result() -> AnalysisResult:
    """Fixture returning a valid AnalysisResult object with extracted data."""
    return AnalysisResult(
        summary="Sung Jinwoo awakens his Shadow Monarch powers in battle.",
        key_events=[
            "Jinwoo grips his dagger",
            "Shadow Monarch power awakens",
            "Cha Hae-in observes Jinwoo",
        ],
        characters_present=["sung_jinwoo", "cha_hae_in"],
        new_characters=[],
        new_terms=[
            GlossaryTerm(
                source="그림자 병사",
                target="Shadow Soldier",
                category="concept",
                notes="Summoned shadow minion",
                confidence=0.9,
            )
        ],
        character_updates=[],
        relationship_updates=[],
        significant_events=[
            SignificantEvent(
                event_type="power_reveal",
                description="Awakening of Shadow Monarch powers observed by S-rank hunter",
                affects_characters=["sung_jinwoo", "cha_hae_in"],
                triggers_arc_update=True,
            )
        ],
        qa_flags=[],
    )


@pytest.fixture
def mock_seed_result(sample_glossary: Glossary) -> SeedResult:
    """Fixture returning a valid SeedResult object."""
    return SeedResult(
        characters=sample_glossary.characters,
        terms=sample_glossary.terms,
        relationships=sample_glossary.relationships,
        story_summary=(
            "Sung Jinwoo, an E-rank hunter, gains levelling powers and becomes the Monarch."
        ),
        arc_summary="D-Rank Double Dungeon Arc",
    )


@pytest.fixture
def mock_openai_response(
    mock_translation_result: TranslationResult,
    mock_analysis_result: AnalysisResult,
    mock_seed_result: SeedResult,
) -> dict[str, Any]:
    """Fixture returning dictionary of serialized JSON responses for OpenAI mocking."""
    return {
        "translation": mock_translation_result.model_dump_json(),
        "analysis": mock_analysis_result.model_dump_json(),
        "seed": mock_seed_result.model_dump_json(),
    }


@pytest.fixture
def mock_llm_client(
    mock_translation_result: TranslationResult,
    mock_analysis_result: AnalysisResult,
    mock_seed_result: SeedResult,
) -> MagicMock:
    """Fixture providing a mock LLM response parser / client.

    Methods parse_translation, parse_analysis, and parse_seed return structured models.
    """
    client = MagicMock()
    client.parse_translation = AsyncMock(return_value=mock_translation_result)
    client.parse_analysis = AsyncMock(return_value=mock_analysis_result)
    client.parse_seed = AsyncMock(return_value=mock_seed_result)
    client.generate = AsyncMock(
        return_value="Mock LLM response generated successfully."
    )
    return client
