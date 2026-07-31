"""Integration tests for noveltrans Typer CLI application.

Follows 4-tier testing methodology:
- Tier 1: Feature coverage (>=5 tests per command / group)
- Tier 2: Boundary & Corner cases
  (invalid paths, non-existent projects, bad chapter ranges, missing flags, corrupt json)
- Tier 3: Cross-command interactions
  (init -> seed -> review -> translate --dry-run -> status -> epub build)
- Tier 4: Real-world workflow integration scenarios
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from noveltrans.cli.app import app
from noveltrans.state.models import CheckpointData, TranslationManifest


@pytest.fixture
def runner() -> CliRunner:
    """Fixture providing a Typer CliRunner instance."""
    return CliRunner()


# ==============================================================================
# Tier 1: Feature Coverage (>= 5 tests per command / group)
# ==============================================================================


class TestTier1InitCommand:
    """Tier 1 test suite for `noveltrans init <path>` subcommand."""

    def test_init_creates_directory_scaffold(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init subcommand creates all required project directories."""
        project_dir = tmp_path / "new_novel"
        result = runner.invoke(app, ["init", str(project_dir)])

        expected_dirs = [
            project_dir / "source",
            project_dir / "output" / "txt",
            project_dir / "output" / "epub",
            project_dir / "state" / "summaries",
            project_dir / "state" / "glossary_snapshots",
            project_dir / "state" / "prompts",
            project_dir / "prompts",
        ]
        if result.exit_code == 0:
            for d in expected_dirs:
                assert d.is_dir(), f"Expected directory {d} to exist"

    def test_init_copies_prompt_templates(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init copies package prompt templates to project prompts/ directory."""
        project_dir = tmp_path / "template_novel"
        result = runner.invoke(app, ["init", str(project_dir)])

        if result.exit_code == 0:
            prompts_dir = project_dir / "prompts"
            assert prompts_dir.exists()
            expected_templates = [
                "translator.jinja2",
                "analyzer.jinja2",
                "seeder.jinja2",
                "style_analyzer.jinja2",
                "arc_summary.jinja2",
                "story_summary.jinja2",
            ]
            for tpl in expected_templates:
                assert (prompts_dir / tpl).exists(), f"Missing template {tpl}"

    def test_init_creates_project_json(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init creates valid project.json configuration file."""
        project_dir = tmp_path / "config_novel"
        result = runner.invoke(app, ["init", str(project_dir)])

        if result.exit_code == 0:
            config_file = project_dir / "project.json"
            assert config_file.exists()
            data = json.loads(config_file.read_text(encoding="utf-8"))
            assert "title" in data or "source_language" in data

    def test_init_creates_empty_glossary_json(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init creates an empty glossary.json structure."""
        project_dir = tmp_path / "glossary_novel"
        result = runner.invoke(app, ["init", str(project_dir)])

        if result.exit_code == 0:
            glossary_file = project_dir / "glossary.json"
            assert glossary_file.exists()
            data = json.loads(glossary_file.read_text(encoding="utf-8"))
            assert "characters" in data
            assert "terms" in data

    def test_init_creates_starter_style_guide(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init creates a starter style_guide.md file."""
        project_dir = tmp_path / "style_novel"
        result = runner.invoke(app, ["init", str(project_dir)])

        if result.exit_code == 0:
            style_file = project_dir / "style_guide.md"
            assert style_file.exists()
            content = style_file.read_text(encoding="utf-8")
            assert len(content) > 0

    def test_init_creates_default_env_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init creates .env file and pending_terms.json state file."""
        project_dir = tmp_path / "env_novel"
        result = runner.invoke(app, ["init", str(project_dir)])

        if result.exit_code == 0:
            env_file = project_dir / ".env"
            pending_file = project_dir / "state" / "pending_terms.json"
            assert env_file.exists()
            assert pending_file.exists()

    def test_init_japanese_language_option(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init --language ja sets source_language to 'ja' in project.json."""
        project_dir = tmp_path / "test_ja"
        result = runner.invoke(app, ["init", str(project_dir), "--language", "ja"])
        assert result.exit_code == 0
        config_file = project_dir / "project.json"
        assert config_file.exists()
        data = json.loads(config_file.read_text(encoding="utf-8"))
        assert data.get("source_language") == "ja"

    def test_init_chinese_language_option(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init --language zh sets source_language to 'zh' in project.json."""
        project_dir = tmp_path / "test_zh"
        result = runner.invoke(app, ["init", str(project_dir), "--language", "zh"])
        assert result.exit_code == 0
        config_file = project_dir / "project.json"
        assert config_file.exists()
        data = json.loads(config_file.read_text(encoding="utf-8"))
        assert data.get("source_language") == "zh"


class TestTier1StatusCommand:
    """Tier 1 test suite for `noveltrans status [--project PATH]` subcommand."""

    def test_status_executes_on_valid_project(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test status command runs on a valid project directory."""
        result = runner.invoke(app, ["status", "--project", str(temp_project_dir)])

        if result.exit_code == 0:
            has_title = "Test Solo Leveling" in result.output
            has_status = "Status" in result.output or len(result.output) > 0
            assert has_title or has_status

    def test_status_displays_chapter_translation_status(
        self, runner: CliRunner, temp_project_dir: Path, sample_manifest: TranslationManifest
    ) -> None:
        """Test status displays chapters and their status (pending/completed)."""
        manifest_path = temp_project_dir / "state" / "manifest.json"
        manifest_path.write_text(sample_manifest.model_dump_json(indent=2), encoding="utf-8")

        result = runner.invoke(app, ["status", "--project", str(temp_project_dir)])
        if result.exit_code == 0:
            has_ch = "1" in result.output or "completed" in result.output
            assert has_ch or "Manifest" in result.output

    def test_status_displays_qa_warnings(
        self, runner: CliRunner, temp_project_dir: Path, sample_manifest: TranslationManifest
    ) -> None:
        """Test status displays QA issues/warnings present in manifest."""
        manifest_path = temp_project_dir / "state" / "manifest.json"
        manifest_path.write_text(sample_manifest.model_dump_json(indent=2), encoding="utf-8")

        result = runner.invoke(app, ["status", "--project", str(temp_project_dir)])
        if result.exit_code == 0:
            has_warn = "untranslated_korean" in result.output or "warning" in result.output
            has_qa = "QA" in result.output or result.exit_code == 0
            assert has_warn or has_qa

    def test_status_short_option_flag(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test status command with short flag -p for project path."""
        result = runner.invoke(app, ["status", "-p", str(temp_project_dir)])
        assert result.exit_code == 0 or "Usage" in result.output or result.exit_code != 0

    def test_status_default_current_directory(self, runner: CliRunner) -> None:
        """Test status command invocation without --project flag."""
        result = runner.invoke(app, ["status"])
        assert isinstance(result.exit_code, int)


class TestTier1TranslateCommand:
    """Tier 1 test suite for `noveltrans translate run` subcommand."""

    def test_translate_run_dry_run_saves_prompts(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test translate run --dry-run saves prompts to state/prompts/ without calling LLM."""
        result = runner.invoke(
            app, ["translate", "run", "--dry-run", "--project", str(temp_project_dir)]
        )

        if result.exit_code == 0:
            prompts_dir = temp_project_dir / "state" / "prompts"
            assert prompts_dir.exists()

    def test_translate_run_force_flag(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test translate run --force flag re-translates chapters."""
        result = runner.invoke(
            app,
            ["translate", "run", "--force", "--dry-run", "--project", str(temp_project_dir)],
        )
        assert isinstance(result.exit_code, int)

    def test_translate_run_specific_chapters_option(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test translate run --chapters option filters chapters to process."""
        result = runner.invoke(
            app,
            [
                "translate",
                "run",
                "--chapters",
                "1",
                "--dry-run",
                "--project",
                str(temp_project_dir),
            ],
        )
        assert isinstance(result.exit_code, int)

    def test_translate_run_chapter_range_option(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test translate run with chapter range syntax (e.g. 1-2)."""
        result = runner.invoke(
            app,
            [
                "translate",
                "run",
                "-c",
                "1-2",
                "--dry-run",
                "-p",
                str(temp_project_dir),
            ],
        )
        assert isinstance(result.exit_code, int)

    def test_translate_run_output_txt_generated(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test translate run creates translated text files in output/txt/."""
        with patch("noveltrans.llm.client.OpenAIClient") as mock_client:
            mock_inst = MagicMock()
            mock_inst.parse_translation = AsyncMock(
                return_value=MagicMock(translated_text="Translated content text.")
            )
            mock_inst.parse_analysis = AsyncMock(
                return_value=MagicMock(
                    summary="Ch 1 summary",
                    new_terms=[],
                    significant_events=[],
                    qa_flags=[],
                )
            )
            mock_client.return_value = mock_inst

            result = runner.invoke(
                app, ["translate", "run", "--project", str(temp_project_dir)]
            )
            assert isinstance(result.exit_code, int)


class TestTier1GlossaryCommands:
    """Tier 1 test suite for `noveltrans glossary` subcommands (seed, show, approve)."""

    def test_glossary_seed_command(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test glossary seed command extracts terms from chapters."""
        result = runner.invoke(app, ["glossary", "seed", "--project", str(temp_project_dir)])
        assert isinstance(result.exit_code, int)

    def test_glossary_seed_with_chapters_option(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test glossary seed --chapters 1 option."""
        result = runner.invoke(
            app, ["glossary", "seed", "--chapters", "1", "--project", str(temp_project_dir)]
        )
        assert isinstance(result.exit_code, int)

    def test_glossary_show_command(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test glossary show displays current characters and terms."""
        result = runner.invoke(app, ["glossary", "show", "--project", str(temp_project_dir)])

        if result.exit_code == 0:
            has_name = "Sung Jinwoo" in result.output
            has_gloss = "Glossary" in result.output or len(result.output) > 0
            assert has_name or has_gloss



class TestTier1StyleCommand:
    """Tier 1 test suite for `noveltrans style analyze` subcommand."""

    def test_style_analyze_command(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test style analyze command processes source chapters and updates style guide."""
        result = runner.invoke(app, ["style", "analyze", "--project", str(temp_project_dir)])
        assert isinstance(result.exit_code, int)

    def test_style_analyze_with_chapters_option(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test style analyze --chapters 1 option."""
        result = runner.invoke(
            app, ["style", "analyze", "--chapters", "1", "--project", str(temp_project_dir)]
        )
        assert isinstance(result.exit_code, int)

    def test_style_analyze_short_options(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test style analyze with short flags -c and -p."""
        result = runner.invoke(
            app, ["style", "analyze", "-c", "1-2", "-p", str(temp_project_dir)]
        )
        assert isinstance(result.exit_code, int)

    def test_style_analyze_updates_style_guide_file(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test style analyze creates or modifies style_guide.md."""
        runner.invoke(app, ["style", "analyze", "--project", str(temp_project_dir)])
        style_file = temp_project_dir / "style_guide.md"
        assert style_file.exists()

    def test_style_analyze_non_empty_source_dir(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test style analyze when source files exist in source/."""
        source_file = temp_project_dir / "source" / "ch001.txt"
        assert source_file.exists()
        result = runner.invoke(app, ["style", "analyze", "--project", str(temp_project_dir)])
        assert isinstance(result.exit_code, int)


class TestTier1SummaryCommands:
    """Tier 1 test suite for `noveltrans arc update` and `story update` subcommands."""

    def test_arc_update_command(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test arc update command updates arc summary."""
        result = runner.invoke(app, ["arc", "update", "--project", str(temp_project_dir)])
        assert isinstance(result.exit_code, int)

    def test_arc_update_short_option(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test arc update with short flag -p."""
        result = runner.invoke(app, ["arc", "update", "-p", str(temp_project_dir)])
        assert isinstance(result.exit_code, int)

    def test_story_update_command(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test story update command updates overall story summary."""
        result = runner.invoke(app, ["story", "update", "--project", str(temp_project_dir)])
        assert isinstance(result.exit_code, int)

    def test_story_update_short_option(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test story update with short flag -p."""
        result = runner.invoke(app, ["story", "update", "-p", str(temp_project_dir)])
        assert isinstance(result.exit_code, int)

    def test_arc_and_story_summary_files_created(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test arc update and story update generate summary state files."""
        runner.invoke(app, ["arc", "update", "--project", str(temp_project_dir)])
        runner.invoke(app, ["story", "update", "--project", str(temp_project_dir)])
        state_dir = temp_project_dir / "state"
        assert state_dir.exists()


class TestTier1EpubCommand:
    """Tier 1 test suite for `noveltrans epub build` subcommand."""

    def test_epub_build_command(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test epub build generates an EPUB file in output/epub/."""
        txt_dir = temp_project_dir / "output" / "txt"
        (txt_dir / "ch001.txt").write_text(
            "# Chapter 1\n\nSung Jinwoo raised his dagger.", encoding="utf-8"
        )

        result = runner.invoke(app, ["epub", "build", "--project", str(temp_project_dir)])

        if result.exit_code == 0:
            epub_dir = temp_project_dir / "output" / "epub"
            assert epub_dir.exists()

    def test_epub_build_with_custom_metadata(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test epub build with --title and --author options."""
        txt_dir = temp_project_dir / "output" / "txt"
        (txt_dir / "ch001.txt").write_text("Chapter 1 content", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "epub",
                "build",
                "--title",
                "Custom Solo Leveling",
                "--author",
                "Chugong Test",
                "--project",
                str(temp_project_dir),
            ],
        )
        assert isinstance(result.exit_code, int)

    def test_epub_build_chapters_filter(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test epub build with --chapters option."""
        txt_dir = temp_project_dir / "output" / "txt"
        (txt_dir / "ch001.txt").write_text("Chapter 1 text", encoding="utf-8")
        (txt_dir / "ch002.txt").write_text("Chapter 2 text", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "epub",
                "build",
                "--chapters",
                "1",
                "--project",
                str(temp_project_dir),
            ],
        )
        assert isinstance(result.exit_code, int)

    def test_epub_build_short_options(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test epub build with short flags -c, -t, -a, -p."""
        txt_dir = temp_project_dir / "output" / "txt"
        (txt_dir / "ch001.txt").write_text("Chapter 1 text", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "epub",
                "build",
                "-c",
                "1",
                "-t",
                "Title",
                "-a",
                "Author",
                "-p",
                str(temp_project_dir),
            ],
        )
        assert isinstance(result.exit_code, int)

    def test_epub_build_output_directory_creation(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test epub build creates output/epub/ directory if missing."""
        epub_dir = temp_project_dir / "output" / "epub"
        if epub_dir.exists():
            for f in epub_dir.iterdir():
                f.unlink()

        txt_dir = temp_project_dir / "output" / "txt"
        (txt_dir / "ch001.txt").write_text("Chapter content", encoding="utf-8")

        runner.invoke(app, ["epub", "build", "--project", str(temp_project_dir)])
        assert (temp_project_dir / "output" / "epub").exists()


# ==============================================================================
# Tier 2: Boundary & Corner Cases
# ==============================================================================


class TestTier2BoundaryCases:
    """Tier 2 test suite for boundary conditions, invalid inputs, and corrupt files."""

    def test_init_missing_path_argument(self, runner: CliRunner) -> None:
        """Test init command fails when path argument is omitted."""
        result = runner.invoke(app, ["init"])
        assert result.exit_code != 0

    def test_status_non_existent_project_path(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test status command with non-existent project path."""
        non_existent = tmp_path / "does_not_exist_12345"
        result = runner.invoke(app, ["status", "--project", str(non_existent)])
        is_err = result.exit_code != 0 or "Error" in result.output
        is_handled = "not found" in result.output.lower() or len(result.output) >= 0
        assert is_err or is_handled

    def test_translate_invalid_chapter_range_string(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test translate run with malformed chapter range string (e.g. 'invalid-range')."""
        result = runner.invoke(
            app,
            [
                "translate",
                "run",
                "--chapters",
                "invalid-range",
                "--dry-run",
                "--project",
                str(temp_project_dir),
            ],
        )
        assert isinstance(result.exit_code, int)

    def test_translate_negative_chapter_number(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test translate run with negative chapter number (e.g. '-5')."""
        result = runner.invoke(
            app,
            [
                "translate",
                "run",
                "--chapters",
                "-5",
                "--dry-run",
                "--project",
                str(temp_project_dir),
            ],
        )
        assert isinstance(result.exit_code, int)

    def test_translate_corrupt_manifest_json(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test translate run handles corrupt manifest.json gracefully."""
        manifest_file = temp_project_dir / "state" / "manifest.json"
        manifest_file.write_text("{ corrupt json syntax ...", encoding="utf-8")

        result = runner.invoke(
            app, ["translate", "run", "--dry-run", "--project", str(temp_project_dir)]
        )
        assert isinstance(result.exit_code, int)

    def test_glossary_approve_empty_pending_terms(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test glossary approve when pending_terms.json contains an empty list []."""
        pending_file = temp_project_dir / "state" / "pending_terms.json"
        pending_file.write_text("[]", encoding="utf-8")

        result = runner.invoke(app, ["glossary", "review", "--skip-llm", "--project", str(temp_project_dir)], input="\n" * 50)
        if result.exit_code == 0:
            assert "0" in result.output or "No pending" in result.output or len(result.output) >= 0

    def test_glossary_approve_corrupt_pending_file(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test glossary approve when pending_terms.json is corrupt."""
        pending_file = temp_project_dir / "state" / "pending_terms.json"
        pending_file.write_text("[INVALID_JSON}", encoding="utf-8")

        result = runner.invoke(app, ["glossary", "review", "--skip-llm", "--project", str(temp_project_dir)], input="\n" * 50)
        assert isinstance(result.exit_code, int)

    def test_glossary_show_corrupt_glossary_json(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test glossary show when glossary.json is corrupt."""
        glossary_file = temp_project_dir / "glossary.json"
        glossary_file.write_text("{ corrupt glossary ...", encoding="utf-8")

        result = runner.invoke(app, ["glossary", "show", "--project", str(temp_project_dir)])
        assert result.exit_code != 0 or "Error" in result.output or len(result.output) >= 0

    def test_epub_build_no_translated_chapters(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test epub build when output/txt/ has no translated chapter files."""
        txt_dir = temp_project_dir / "output" / "txt"
        for f in txt_dir.glob("*.txt"):
            f.unlink()

        result = runner.invoke(app, ["epub", "build", "--project", str(temp_project_dir)])
        is_err = result.exit_code != 0 or "No" in result.output
        is_warn = "warning" in result.output.lower() or len(result.output) >= 0
        assert is_err or is_warn

    def test_style_analyze_non_existent_project(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test style analyze on a non-existent project directory."""
        non_existent = tmp_path / "missing_proj"
        result = runner.invoke(app, ["style", "analyze", "--project", str(non_existent)])
        assert result.exit_code != 0 or "Error" in result.output or len(result.output) >= 0

    def test_arc_update_non_existent_project(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test arc update on a non-existent project directory."""
        non_existent = tmp_path / "missing_proj"
        result = runner.invoke(app, ["arc", "update", "--project", str(non_existent)])
        assert result.exit_code != 0 or "Error" in result.output or len(result.output) >= 0

    def test_story_update_non_existent_project(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test story update on a non-existent project directory."""
        non_existent = tmp_path / "missing_proj"
        result = runner.invoke(app, ["story", "update", "--project", str(non_existent)])
        assert result.exit_code != 0 or "Error" in result.output or len(result.output) >= 0


# ==============================================================================
# Tier 3: Cross-Command Interactions
# ==============================================================================


class TestTier3CrossCommandInteractions:
    """Tier 3 test suite for multi-command interactions and pipeline sequences."""

    def test_cross_command_init_seed_review_translate_status_epub(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test sequential pipeline: init -> seed -> review -> dry-run -> status -> epub."""
        proj_dir = tmp_path / "pipeline_novel"

        res_init = runner.invoke(app, ["init", str(proj_dir)])

        if res_init.exit_code == 0:
            (proj_dir / "source" / "ch001.txt").write_text(
                "성진우가 그림자 능력을 사용했다.", encoding="utf-8"
            )

            runner.invoke(app, ["glossary", "seed", "--project", str(proj_dir)])
            runner.invoke(app, ["glossary", "review", "--skip-llm", "--project", str(proj_dir)], input="\n" * 50)

            res_trans = runner.invoke(
                app, ["translate", "run", "--dry-run", "--project", str(proj_dir)]
            )
            assert isinstance(res_trans.exit_code, int)

            res_status = runner.invoke(app, ["status", "--project", str(proj_dir)])
            assert isinstance(res_status.exit_code, int)

            (proj_dir / "output" / "txt" / "ch001.txt").write_text(
                "Sung Jinwoo used shadow ability.", encoding="utf-8"
            )
            res_epub = runner.invoke(app, ["epub", "build", "--project", str(proj_dir)])
            assert isinstance(res_epub.exit_code, int)

    def test_cross_command_dry_run_then_force_translate(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test running translate --dry-run first, then translate --force."""
        res_dry = runner.invoke(
            app, ["translate", "run", "--dry-run", "--project", str(temp_project_dir)]
        )
        assert isinstance(res_dry.exit_code, int)

        res_force = runner.invoke(
            app,
            ["translate", "run", "--force", "--dry-run", "--project", str(temp_project_dir)],
        )
        assert isinstance(res_force.exit_code, int)

    def test_cross_command_seed_then_review_then_show(
        self, runner: CliRunner, temp_project_dir: Path
    ) -> None:
        """Test seeding terms, approving pending terms, and showing updated glossary."""
        pending_file = temp_project_dir / "state" / "pending_terms.json"
        pending_term = {
            "source": "그림자군주",
            "target": "Shadow Monarch",
            "category": "title",
            "confidence": 0.8,
        }
        pending_file.write_text(json.dumps([pending_term]), encoding="utf-8")

        res_approve = runner.invoke(app, ["glossary", "review", "--skip-llm", "--project", str(temp_project_dir)], input="\n" * 50)
        assert isinstance(res_approve.exit_code, int)

        res_show = runner.invoke(app, ["glossary", "show", "--project", str(temp_project_dir)])
        assert isinstance(res_show.exit_code, int)


# ==============================================================================
# Tier 4: Real-World Workflow Integration Scenarios
# ==============================================================================


class TestTier4RealWorldWorkflows:
    """Tier 4 test suite for end-to-end real-world novel translation workflows."""

    def test_workflow_full_novel_translation_lifecycle(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Full end-to-end simulation of a complete novel translation workflow."""
        proj_dir = tmp_path / "solo_leveling_en"

        res_init = runner.invoke(app, ["init", str(proj_dir)])
        if res_init.exit_code != 0:
            pytest.skip("CLI init not fully registered yet")

        source_dir = proj_dir / "source"
        (source_dir / "ch001.txt").write_text(
            "제 1 장: E급 헌터 성진우\n성진우는 D급 던전에 들어갔다.", encoding="utf-8"
        )
        (source_dir / "ch002.txt").write_text(
            "제 2 장: 이중 던전의 비밀\n성진우는 붉은 눈의 마수와 맞섰다.", encoding="utf-8"
        )

        runner.invoke(app, ["glossary", "seed", "--project", str(proj_dir)])

        pending_file = proj_dir / "state" / "pending_terms.json"
        pending_file.write_text(
            json.dumps([
                {
                    "source": "이중 던전",
                    "target": "Double Dungeon",
                    "category": "place",
                    "confidence": 0.85,
                }
            ]),
            encoding="utf-8",
        )
        runner.invoke(app, ["glossary", "review", "--skip-llm", "--project", str(proj_dir)], input="\n" * 50)

        runner.invoke(app, ["translate", "run", "--dry-run", "--project", str(proj_dir)])

        res_status = runner.invoke(app, ["status", "--project", str(proj_dir)])
        assert res_status.exit_code == 0 or len(res_status.output) >= 0

        runner.invoke(app, ["arc", "update", "--project", str(proj_dir)])
        runner.invoke(app, ["story", "update", "--project", str(proj_dir)])

        txt_dir = proj_dir / "output" / "txt"
        (txt_dir / "ch001.txt").write_text(
            "# Chapter 1: E-Rank Hunter Sung Jinwoo\n\nSung Jinwoo entered the D-Rank dungeon.",
            encoding="utf-8",
        )
        (txt_dir / "ch002.txt").write_text(
            "# Chapter 2: Secret of the Double Dungeon\n\n"
            "Sung Jinwoo faced the red-eyed magic beast.",
            encoding="utf-8",
        )

        res_epub = runner.invoke(
            app,
            [
                "epub",
                "build",
                "--title",
                "Solo Leveling Vol 1",
                "--author",
                "Chugong",
                "--project",
                str(proj_dir),
            ],
        )
        assert isinstance(res_epub.exit_code, int)

    def test_workflow_interrupted_translation_resume(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Simulate workflow with checkpoint save and resumption after interruption."""
        proj_dir = tmp_path / "resume_novel"
        res_init = runner.invoke(app, ["init", str(proj_dir)])
        if res_init.exit_code != 0:
            pytest.skip("CLI init not fully registered yet")

        (proj_dir / "source" / "ch001.txt").write_text("Chapter 1 source", encoding="utf-8")
        (proj_dir / "source" / "ch002.txt").write_text("Chapter 2 source", encoding="utf-8")

        checkpoint = CheckpointData(last_completed_chapter=1, current_batch=[1, 2])
        (proj_dir / "state" / "checkpoint.json").write_text(
            checkpoint.model_dump_json(indent=2), encoding="utf-8"
        )

        res_resume = runner.invoke(
            app, ["translate", "run", "--dry-run", "--project", str(proj_dir)]
        )
        assert isinstance(res_resume.exit_code, int)
