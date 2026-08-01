"""14-step per-chapter translation pipeline implementation."""

import asyncio
import inspect
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from noveltrans.config.settings import ProjectConfig
from noveltrans.core.analyzer import ChapterAnalyzer
from noveltrans.core.context_builder import ContextBuilder
from noveltrans.core.qa_checker import QAChecker
from noveltrans.glossary.manager import GlossaryManager
from noveltrans.llm.client import OpenAIClient
from noveltrans.llm.prompt_renderer import PromptRenderer
from noveltrans.llm.protocols import AnalysisResult, TranslationResult
from noveltrans.state.checkpoint import CheckpointManager
from noveltrans.state.manifest import ManifestManager
from noveltrans.state.models import ChapterManifestEntry, QAIssue
from rich.console import Console

logger = structlog.get_logger()
console = Console()


class TranslationPipeline:
    """Core translation pipeline executing the 14-step per-chapter workflow."""

    def __init__(
        self,
        project_dir: Path | str | None = None,
        config: ProjectConfig | None = None,
        llm_client: Any = None,
        prompt_renderer: PromptRenderer | None = None,
        glossary_manager: GlossaryManager | None = None,
        context_builder: ContextBuilder | None = None,
        qa_checker: QAChecker | None = None,
        analyzer: ChapterAnalyzer | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        manifest_manager: ManifestManager | None = None,
    ) -> None:
        self.project_dir = Path(project_dir) if project_dir else None

        if config is not None:
            self.config = config
        elif self.project_dir and (self.project_dir / "project.json").exists():
            try:
                content = (self.project_dir / "project.json").read_text(encoding="utf-8")
                self.config = ProjectConfig.model_validate_json(content)
            except Exception:
                self.config = ProjectConfig(title="Default")
        else:
            self.config = ProjectConfig(title="Default")

        self.llm_client = llm_client or OpenAIClient()

        if prompt_renderer is not None:
            self.prompt_renderer = prompt_renderer
        elif self.project_dir and (self.project_dir / "prompts").exists():
            self.prompt_renderer = PromptRenderer(self.project_dir / "prompts")
        else:
            self.prompt_renderer = PromptRenderer()

        if glossary_manager is not None:
            self.glossary_manager = glossary_manager
        elif self.project_dir:
            self.glossary_manager = GlossaryManager(project_dir=self.project_dir)
        else:
            self.glossary_manager = GlossaryManager()

        self.context_builder = context_builder or ContextBuilder(config=self.config)
        self.qa_checker = qa_checker or QAChecker()

        if analyzer is not None:
            self.analyzer = analyzer
        else:
            self.analyzer = ChapterAnalyzer(
                llm_client=self.llm_client,
                prompt_renderer=self.prompt_renderer,
                glossary_manager=self.glossary_manager,
                project_dir=self.project_dir,
            )

        if checkpoint_manager is not None:
            self.checkpoint_manager = checkpoint_manager
        elif self.project_dir:
            self.checkpoint_manager = CheckpointManager(
                self.project_dir / self.config.state_dir / "checkpoint.json"
            )
        else:
            self.checkpoint_manager = CheckpointManager("state/checkpoint.json")

        if manifest_manager is not None:
            self.manifest_manager = manifest_manager
        elif self.project_dir:
            self.manifest_manager = ManifestManager(
                self.project_dir / self.config.state_dir / "manifest.json",
                project_title=self.config.title,
            )
        else:
            self.manifest_manager = ManifestManager(
                "state/manifest.json", project_title=self.config.title
            )

        self.last_arc_update_chapter: int = 0

    def _get_model_name(self) -> str:
        if hasattr(self.llm_client, "settings") and hasattr(self.llm_client.settings, "model_name"):
            return str(self.llm_client.settings.model_name)
        return "gemini-2.5-pro"

    def _get_source_text(self, chapter_number: int) -> str:
        if self.project_dir is None:
            raise ValueError("project_dir must be set to load source text")

        source_dir = self.project_dir / self.config.source_dir
        possible_names = [
            f"ch{chapter_number:03d}.txt",
            f"ch{chapter_number:02d}.txt",
            f"ch{chapter_number}.txt",
            f"chapter_{chapter_number:03d}.txt",
            f"chapter_{chapter_number:02d}.txt",
            f"chapter_{chapter_number}.txt",
            f"chapter{chapter_number:03d}.txt",
            f"chapter{chapter_number}.txt",
            f"{chapter_number:03d}.txt",
            f"{chapter_number}.txt",
        ]
        for name in possible_names:
            p = source_dir / name
            if p.exists():
                return p.read_text(encoding="utf-8")

        raise FileNotFoundError(
            f"Source text for chapter {chapter_number} not found in {source_dir}"
        )

    def _load_context_inputs(
        self, current_chapter: int
    ) -> tuple[str, str, str, list[str], list[str]]:
        style_guide = ""
        story_summary = ""
        arc_summary = ""
        chapter_summaries: list[str] = []
        recent_chapters: list[str] = []

        if self.project_dir:
            style_path = self.project_dir / self.config.style_guide_path
            if style_path.exists():
                style_guide = style_path.read_text(encoding="utf-8")

            story_file = self.project_dir / self.config.state_dir / "story_summary.json"
            if story_file.exists():
                try:
                    data = json.loads(story_file.read_text(encoding="utf-8"))
                    story_summary = str(data.get("story_summary", ""))
                except Exception:
                    pass

            arc_file = self.project_dir / self.config.state_dir / "arc_summary.json"
            if arc_file.exists():
                try:
                    data = json.loads(arc_file.read_text(encoding="utf-8"))
                    arc_summary = str(data.get("arc_summary", ""))
                except Exception:
                    pass

            summaries_dir = self.project_dir / self.config.state_dir / "summaries"
            if summaries_dir.exists():
                summary_files = sorted(summaries_dir.glob("ch*.json"))
                for sf in summary_files:
                    try:
                        data = json.loads(sf.read_text(encoding="utf-8"))
                        ch_num = data.get("chapter_number", 0)
                        if ch_num < current_chapter and "summary" in data:
                            chapter_summaries.append(str(data["summary"]))
                    except Exception:
                        pass

            output_txt_dir = self.project_dir / self.config.output_dir / "txt"
            if output_txt_dir.exists():
                txt_files = sorted(output_txt_dir.glob("ch*.txt"))
                for tf in txt_files:
                    try:
                        num_str = "".join(filter(str.isdigit, tf.stem))
                        if num_str:
                            ch_num = int(num_str)
                            if ch_num < current_chapter:
                                recent_chapters.append(tf.read_text(encoding="utf-8"))
                    except Exception:
                        pass

        return style_guide, story_summary, arc_summary, chapter_summaries, recent_chapters

    async def translate_chapter(
        self,
        chapter_number: int,
        source_text: str | None = None,
        force: bool = False,
        dry_run: bool = False,
        skip_glossary: bool = False,
    ) -> ChapterManifestEntry:
        """Execute 14-step per-chapter translation process."""
        start_time = time.time()

        # Step 1: Load chapter source text
        if not source_text:
            source_text = self._get_source_text(chapter_number)

        # Record in_progress status
        if not dry_run:
            in_progress_entry = ChapterManifestEntry(
                chapter_number=chapter_number,
                status="in_progress",
                force_retranslated=force,
            )
            self.manifest_manager.update_chapter(in_progress_entry)

        # Step 2: Build 4-tier context & Step 3: Match glossary terms
        (
            style_guide,
            story_summary,
            arc_summary,
            recent_summaries,
            recent_chapters,
        ) = self._load_context_inputs(chapter_number)

        glossary = self.glossary_manager.load_glossary()

        assembled_context = self.context_builder.build_context(
            chapter_number=chapter_number,
            source_text=source_text,
            glossary=glossary,
            style_guide=style_guide,
            story_summary=story_summary,
            arc_summary=arc_summary,
            chapter_summaries=recent_summaries,
            recent_chapters=recent_chapters,
        )

        # Step 4: Render translator prompt
        translator_prompt = self.prompt_renderer.render_translator(
            assembled_context=assembled_context,
            source_text=source_text,
            chapter_number=chapter_number,
            target_language=self.config.target_language,
            source_language=self.config.source_language,
        )

        # Step 5: DRY RUN check
        if dry_run:
            if self.project_dir:
                prompts_dir = self.project_dir / self.config.state_dir / "prompts"
                prompts_dir.mkdir(parents=True, exist_ok=True)
                (prompts_dir / f"ch{chapter_number:03d}_translator.txt").write_text(
                    translator_prompt, encoding="utf-8"
                )

            entry = ChapterManifestEntry(
                chapter_number=chapter_number,
                status="completed",
                translated_at=datetime.now(UTC),
                model_used=self._get_model_name(),
                translation_duration_seconds=round(time.time() - start_time, 2),
                force_retranslated=force,
            )
            return entry

        # Step 6: Call LLM — TRANSLATION & Step 7: Parse translation response
        analyzer_prompt = ""
        try:
            logger.info("starting_translation_llm", chapter_number=chapter_number)
            console.print(f"  [cyan]>[/] Generating translation for chapter {chapter_number}...")
            raw_tr = self.llm_client.parse_translation(translator_prompt)
            if inspect.isawaitable(raw_tr):
                tr_result: TranslationResult = await raw_tr
            else:
                tr_result = raw_tr
        except Exception as e:
            logger.error("translation_llm_failed", chapter_number=chapter_number, error=str(e))
            failed_entry = ChapterManifestEntry(
                chapter_number=chapter_number,
                status="failed",
                force_retranslated=force,
            )
            self.manifest_manager.update_chapter(failed_entry)
            raise e

        translated_text = tr_result.translated_text

        # Step 8: Save translated chapter to output/txt/
        if self.project_dir:
            output_txt_dir = self.project_dir / self.config.output_dir / "txt"
            output_txt_dir.mkdir(parents=True, exist_ok=True)
            (output_txt_dir / f"ch{chapter_number:03d}.txt").write_text(
                translated_text, encoding="utf-8"
            )

        # Step 9: Run local QA checks (no LLM)
        qa_issues: list[QAIssue] = self.qa_checker.check_chapter(
            translated_text=translated_text,
            source_text=source_text,
            glossary=glossary,
            source_language=self.config.source_language,
        )

        # Step 10: Call LLM — ANALYSIS & Step 11: Process analysis results
        existing_char_names = []
        for c in glossary.characters:
            aliases = [a.source for a in c.aliases if a.source]
            if aliases:
                existing_char_names.append(f"{c.canonical_name} (Aliases: {', '.join(aliases)})")
            else:
                existing_char_names.append(c.canonical_name)

        existing_term_sources = [f"{t.source} -> {t.target}" for t in glossary.terms]

        analyzer_prompt = self.prompt_renderer.render_analyzer(
            chapter_number=chapter_number,
            translated_text=translated_text,
            source_text=source_text,
            existing_characters=existing_char_names,
            existing_terms=existing_term_sources,
            source_language=self.config.source_language,
            skip_glossary_update=skip_glossary,
        )

        try:
            logger.info("starting_analysis_llm", chapter_number=chapter_number)
            console.print(f"  [cyan]>[/] Analyzing chapter {chapter_number} for summary and glossary updates...")
            raw_analysis = self.llm_client.parse_analysis(analyzer_prompt)
            if inspect.isawaitable(raw_analysis):
                analysis_result: AnalysisResult = await raw_analysis
            else:
                analysis_result = raw_analysis
        except Exception as e:
            logger.warning("analysis_llm_failed", chapter_number=chapter_number, error=str(e))
            analysis_result = AnalysisResult(summary=f"Chapter {chapter_number} translation.")

        chapters_since_last_arc = (
            chapter_number - self.last_arc_update_chapter
            if self.last_arc_update_chapter > 0
            else chapter_number
        )

        process_res = self.analyzer.process_analysis_result(
            chapter_number=chapter_number,
            analysis=analysis_result,
            chapters_since_last_arc=chapters_since_last_arc,
            arc_fallback_interval=self.config.arc_summary_fallback_interval,
        )

        if process_res.get("triggers_arc_update"):
            try:
                await self.analyzer.regenerate_arc_summary(chapters_since_last_arc)
                self.last_arc_update_chapter = chapter_number
                await self.analyzer.regenerate_story_summary()
            except Exception as e:
                logger.warning("arc_summary_regeneration_failed", error=str(e))

        # Step 12: Snapshot glossary
        snapshot_rel_path: str | None = None
        if self.project_dir:
            snapshots_dir = self.project_dir / self.config.state_dir / "glossary_snapshots"
            snapshots_dir.mkdir(parents=True, exist_ok=True)
            snapshot_file = snapshots_dir / f"ch{chapter_number:03d}.json"
            updated_glossary = self.glossary_manager.load_glossary()
            snapshot_file.write_text(
                updated_glossary.model_dump_json(indent=2), encoding="utf-8"
            )
            snapshot_rel_path = f"state/glossary_snapshots/ch{chapter_number:03d}.json"

        # Step 13: Save assembled prompts
        if self.project_dir:
            prompts_dir = self.project_dir / self.config.state_dir / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            (prompts_dir / f"ch{chapter_number:03d}_translator.txt").write_text(
                translator_prompt, encoding="utf-8"
            )
            if analyzer_prompt:
                (prompts_dir / f"ch{chapter_number:03d}_analyzer.txt").write_text(
                    analyzer_prompt, encoding="utf-8"
                )

        # Step 14: Update manifest and checkpoint
        duration = round(time.time() - start_time, 2)
        new_terms_count = len(process_res.get("high_confidence_terms", []))

        completed_entry = ChapterManifestEntry(
            chapter_number=chapter_number,
            status="completed",
            translated_at=datetime.now(UTC),
            model_used=self._get_model_name(),
            glossary_snapshot=snapshot_rel_path,
            translation_duration_seconds=duration,
            new_terms_extracted=new_terms_count,
            force_retranslated=force,
            qa_issues=qa_issues,
            significant_events=analysis_result.significant_events,
        )

        self.manifest_manager.update_chapter(completed_entry)
        self.checkpoint_manager.update_completed(chapter_number)

        logger.info(
            "chapter_translation_completed",
            chapter_number=chapter_number,
            duration=duration,
            qa_issues=len(qa_issues),
        )

        return completed_entry

    def translate_chapter_sync(
        self,
        chapter_number: int,
        source_text: str | None = None,
        force: bool = False,
        dry_run: bool = False,
        skip_glossary: bool = False,
    ) -> ChapterManifestEntry:
        """Synchronous wrapper for translate_chapter()."""
        return asyncio.run(
            self.translate_chapter(
                chapter_number,
                source_text=source_text,
                force=force,
                dry_run=dry_run,
                skip_glossary=skip_glossary,
            )
        )

    async def translate_batch(
        self,
        chapter_numbers: list[int] | None = None,
        force: bool = False,
        dry_run: bool = False,
        skip_glossary: bool = False,
    ) -> list[ChapterManifestEntry]:
        """Execute batch translation for multiple chapters."""
        if chapter_numbers is None:
            if self.project_dir is None:
                raise ValueError("project_dir must be specified to auto-discover chapters")
            source_dir = self.project_dir / self.config.source_dir
            files = sorted(source_dir.glob("*.txt"))
            chapter_numbers = []
            for f in files:
                num_str = "".join(filter(str.isdigit, f.stem))
                if num_str:
                    chapter_numbers.append(int(num_str))

        chapter_numbers = sorted(list(set(chapter_numbers)))
        if not dry_run:
            self.checkpoint_manager.set_batch(chapter_numbers)

        entries: list[ChapterManifestEntry] = []
        for ch in chapter_numbers:
            if self.checkpoint_manager.should_skip(ch, force=force):
                existing = self.manifest_manager.get_chapter(ch)
                entries.append(
                    existing
                    or ChapterManifestEntry(chapter_number=ch, status="completed")
                )
                continue

            try:
                console.print(f"\n[bold magenta]Processing Chapter {ch}...[/]")
                entry = await self.translate_chapter(
                    ch, 
                    force=force, 
                    dry_run=dry_run, 
                    skip_glossary=skip_glossary
                )
                entries.append(entry)
            except Exception as e:
                logger.error("batch_translation_failed", chapter_number=ch, error=str(e))
                raise e

        return entries

    def translate_batch_sync(
        self,
        chapter_numbers: list[int] | None = None,
        force: bool = False,
        dry_run: bool = False,
        skip_glossary: bool = False,
    ) -> list[ChapterManifestEntry]:
        """Synchronous wrapper for translate_batch()."""
        return asyncio.run(
            self.translate_batch(
                chapter_numbers=chapter_numbers,
                force=force,
                dry_run=dry_run,
                skip_glossary=skip_glossary,
            )
        )


Translator = TranslationPipeline
