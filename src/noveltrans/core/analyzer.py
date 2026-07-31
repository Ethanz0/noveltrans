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
        # 1. Commit all terms to glossary
        for term in analysis.new_terms:
            term.reviewed = False
            self.glossary_manager.add_term(term)

        # 2. Commit new characters to glossary
        for char in analysis.new_characters:
            char.reviewed = False
            for alias in char.aliases:
                alias.reviewed = False
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
                        
                    if "canonical_name" in update:
                        char.canonical_name = str(update["canonical_name"])
                        
                    if "knows_identity" in update and isinstance(update["knows_identity"], list):
                        for kid in update["knows_identity"]:
                            kid_str = str(kid)
                            if kid_str not in char.knows_identity:
                                char.knows_identity.append(kid_str)
                                
                    if "aliases" in update and isinstance(update["aliases"], list):
                        from noveltrans.glossary.models import CharacterAlias
                        for a_data in update["aliases"]:
                            if isinstance(a_data, dict):
                                try:
                                    alias = CharacterAlias(**a_data)
                                    if not any(ea.source == alias.source for ea in char.aliases):
                                        alias.reviewed = False
                                        char.aliases.append(alias)
                                except Exception:
                                    pass
                    updated = True
            if updated:
                glossary.characters = list(char_map.values())
                self.glossary_manager.save_glossary(glossary)

        # 5.5 Process term updates
        if analysis.term_updates:
            glossary = self.glossary_manager.load_glossary()
            term_map = {t.source: t for t in glossary.terms}
            updated = False
            for update in analysis.term_updates:
                source = update.get("source")
                if source and source in term_map:
                    term = term_map[source]
                    if "category" in update:
                        term.category = str(update["category"])
                    if "notes" in update:
                        term.notes = str(update["notes"])
                    updated = True
            if updated:
                glossary.terms = list(term_map.values())
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
            new_terms=len(analysis.new_terms),
            new_characters=len(analysis.new_characters),
            triggers_arc_update=triggers_arc_update,
        )

        return {
            "new_terms": analysis.new_terms,
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

    async def regenerate_story_summary(self) -> str:
        """Regenerate overall story summary from arc and chapter summaries."""
        current_story = ""
        arc_summary = ""

        if self.project_dir:
            state_dir = self.project_dir / "state"
            state_dir.mkdir(parents=True, exist_ok=True)

            story_file = state_dir / "story_summary.json"
            if story_file.exists():
                try:
                    data = json.loads(story_file.read_text(encoding="utf-8"))
                    current_story = str(data.get("story_summary", ""))
                except Exception:
                    pass

            arc_file = state_dir / "arc_summary.json"
            if arc_file.exists():
                try:
                    data = json.loads(arc_file.read_text(encoding="utf-8"))
                    arc_summary = str(data.get("arc_summary", ""))
                except Exception:
                    pass

        prompt = self.prompt_renderer.render_story_summary(
            current_story_summary=current_story,
            arc_summary=arc_summary,
        )

        import inspect

        raw_res = self.llm_client.complete(prompt)
        if inspect.isawaitable(raw_res):
            res_val = await raw_res
            new_story_summary = str(res_val)
        else:
            new_story_summary = str(raw_res)

        if self.project_dir:
            state_dir = self.project_dir / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            story_file = state_dir / "story_summary.json"
            story_file.write_text(
                json.dumps({"story_summary": new_story_summary}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return new_story_summary

    def regenerate_story_summary_sync(self) -> str:
        """Synchronous wrapper for regenerate_story_summary()."""
        return asyncio.run(self.regenerate_story_summary())
