"""Post-translation chapter analyzer for term extraction, summaries, and events."""

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from noveltrans.glossary.manager import GlossaryManager
from noveltrans.llm.client import OpenAIClient
from noveltrans.llm.prompt_renderer import PromptRenderer
from noveltrans.llm.protocols import AnalysisResult

if TYPE_CHECKING:
    from noveltrans.glossary.models import GlossaryTerm

logger = structlog.get_logger()


class ChapterAnalyzer:
    """Executes post-translation analysis and updates project state and glossary."""

    def __init__(
        self,
        llm_client: Any = None,
        prompt_renderer: PromptRenderer | None = None,
        glossary_manager: GlossaryManager | None = None,
        project_dir: Path | str | None = None,
        confidence_threshold: float = 0.8,
    ) -> None:
        self.llm_client = llm_client or OpenAIClient()
        self.project_dir = Path(project_dir) if project_dir else None

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

        self.confidence_threshold = confidence_threshold

    async def analyze(
        self,
        chapter_number: int,
        source_text: str,
        translated_text: str,
        existing_characters: list[str] | None = None,
        existing_terms: list[str] | None = None,
    ) -> AnalysisResult:
        """Run post-translation LLM analysis call."""
        prompt = self.prompt_renderer.render_analyzer(
            chapter_number=chapter_number,
            translated_text=translated_text,
            source_text=source_text,
            existing_characters=existing_characters or [],
            existing_terms=existing_terms or [],
        )

        import inspect

        raw_res = self.llm_client.parse_analysis(prompt)
        if inspect.isawaitable(raw_res):
            analysis_result: AnalysisResult = await raw_res
        else:
            analysis_result = raw_res

        return analysis_result

    def analyze_sync(
        self,
        chapter_number: int,
        source_text: str,
        translated_text: str,
        existing_characters: list[str] | None = None,
        existing_terms: list[str] | None = None,
    ) -> AnalysisResult:
        """Synchronous wrapper for analyze()."""
        return asyncio.run(
            self.analyze(
                chapter_number,
                source_text,
                translated_text,
                existing_characters=existing_characters,
                existing_terms=existing_terms,
            )
        )

    def process_analysis_result(
        self,
        chapter_number: int,
        analysis: AnalysisResult,
        chapters_since_last_arc: int = 0,
        arc_fallback_interval: int = 15,
    ) -> dict[str, Any]:
        """Process and auto-commit analysis outputs to glossary and disk."""
        high_conf_terms: list[GlossaryTerm] = []
        low_conf_terms: list[GlossaryTerm] = []

        for term in analysis.new_terms:
            if term.confidence >= self.confidence_threshold:
                high_conf_terms.append(term)
            else:
                low_conf_terms.append(term)

        # 1. Commit high-confidence terms to glossary
        for term in high_conf_terms:
            self.glossary_manager.add_term(term)

        # 2. Add low-confidence terms to pending_terms.json
        if low_conf_terms:
            self.glossary_manager.add_pending_terms(low_conf_terms)

        # 3. Commit new characters to glossary
        for char in analysis.new_characters:
            self.glossary_manager.add_character(char)

        # 4. Commit relationship updates
        for rel in analysis.relationship_updates:
            self.glossary_manager.add_relationship(rel)

        # 5. Process character updates (if any dict updates)
        if analysis.character_updates:
            glossary = self.glossary_manager.load_glossary()
            char_map = {c.id: c for c in glossary.characters}
            updated = False
            for update in analysis.character_updates:
                char_id = update.get("id") or update.get("character_id")
                if char_id and char_id in char_map:
                    char = char_map[char_id]
                    if "gender" in update:
                        char.gender = str(update["gender"])
                    if "speech_style" in update:
                        char.speech_style = str(update["speech_style"])
                    if "appearance" in update:
                        char.appearance = str(update["appearance"])
                    if "notes" in update:
                        char.notes = str(update["notes"])
                    updated = True
            if updated:
                glossary.characters = list(char_map.values())
                self.glossary_manager.save_glossary(glossary)

        # 6. Save chapter summary to state/summaries/
        if self.project_dir:
            summaries_dir = self.project_dir / "state" / "summaries"
            summaries_dir.mkdir(parents=True, exist_ok=True)
            summary_file = summaries_dir / f"ch{chapter_number:03d}.json"
            summary_data = {
                "chapter_number": chapter_number,
                "summary": analysis.summary,
                "key_events": analysis.key_events,
                "characters_present": analysis.characters_present,
            }
            summary_file.write_text(
                json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        # 7. Check if arc update is triggered
        event_triggered = any(e.triggers_arc_update for e in analysis.significant_events)
        interval_triggered = chapters_since_last_arc >= arc_fallback_interval
        triggers_arc_update = event_triggered or interval_triggered

        logger.info(
            "analysis_processed",
            chapter_number=chapter_number,
            high_conf_terms=len(high_conf_terms),
            low_conf_terms=len(low_conf_terms),
            new_characters=len(analysis.new_characters),
            triggers_arc_update=triggers_arc_update,
        )

        return {
            "high_confidence_terms": high_conf_terms,
            "low_confidence_terms": low_conf_terms,
            "new_characters": analysis.new_characters,
            "triggers_arc_update": triggers_arc_update,
        }

    async def regenerate_arc_summary(
        self,
        chapters_since_last_arc: int = 0,
    ) -> str:
        """Regenerate arc summary using recent chapter summaries."""
        recent_summaries: list[str] = []
        current_arc = ""

        if self.project_dir:
            summaries_dir = self.project_dir / "state" / "summaries"
            if summaries_dir.exists():
                summary_files = sorted(summaries_dir.glob("ch*.json"))
                for f in summary_files[-15:]:
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        if isinstance(data, dict) and "summary" in data:
                            recent_summaries.append(str(data["summary"]))
                    except Exception:
                        pass

            arc_file = self.project_dir / "state" / "arc_summary.json"
            if arc_file.exists():
                try:
                    arc_data = json.loads(arc_file.read_text(encoding="utf-8"))
                    current_arc = str(arc_data.get("arc_summary", ""))
                except Exception:
                    pass

        prompt = self.prompt_renderer.render_arc_summary(
            current_arc_summary=current_arc,
            chapter_summaries=recent_summaries,
        )

        import inspect

        raw_res = self.llm_client.complete(prompt)
        if inspect.isawaitable(raw_res):
            res_val = await raw_res
            new_arc_summary = str(res_val)
        else:
            new_arc_summary = str(raw_res)

        if self.project_dir:
            state_dir = self.project_dir / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            arc_file = state_dir / "arc_summary.json"
            arc_file.write_text(
                json.dumps({"arc_summary": new_arc_summary}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return new_arc_summary

    def regenerate_arc_summary_sync(
        self,
        chapters_since_last_arc: int = 0,
    ) -> str:
        """Synchronous wrapper for regenerate_arc_summary()."""
        return asyncio.run(self.regenerate_arc_summary(chapters_since_last_arc))
