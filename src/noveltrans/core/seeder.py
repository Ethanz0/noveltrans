"""Glossary and story summary seeder using LLM seed calls."""

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import structlog

from noveltrans.glossary.manager import GlossaryManager
from noveltrans.llm.client import OpenAIClient
from noveltrans.llm.prompt_renderer import PromptRenderer
from noveltrans.llm.protocols import SeedResult

logger = structlog.get_logger()


class GlossarySeeder:
    """Seeder that generates initial glossary and summaries from initial chapters."""

    def __init__(
        self,
        llm_client: Any = None,
        prompt_renderer: PromptRenderer | None = None,
        project_dir: Path | str | None = None,
        prompts_dir: Path | str | None = None,
    ) -> None:
        """Initialize GlossarySeeder with optional LLM client, prompt renderer, and project dir."""
        self.project_dir = Path(project_dir) if project_dir else None
        self.llm_client = llm_client or OpenAIClient()

        if prompt_renderer is not None:
            self.prompt_renderer = prompt_renderer
        elif self.project_dir and (self.project_dir / "prompts").exists():
            self.prompt_renderer = PromptRenderer(self.project_dir / "prompts")
        elif prompts_dir:
            self.prompt_renderer = PromptRenderer(prompts_dir)
        else:
            self.prompt_renderer = None

    async def seed(
        self,
        chapters_text: list[str] | str,
        save_to_project: bool = True,
    ) -> SeedResult:
        """Run LLM seed call on initial chapters to extract glossary and story/arc summaries."""
        if isinstance(chapters_text, list):
            source_text = "\n\n---\n\n".join(chapters_text)
            ch_count = len(chapters_text)
        else:
            source_text = chapters_text
            ch_count = 1

        if self.prompt_renderer is not None:
            existing_chars = []
            existing_terms = []
            if self.project_dir is not None:
                try:
                    from noveltrans.glossary.manager import GlossaryManager
                    mgr = GlossaryManager(self.project_dir)
                    gloss = mgr.load_glossary()
                    existing_chars = [c.canonical_name for c in gloss.characters]
                    existing_terms = [t.source for t in gloss.terms]
                except Exception:
                    pass

            prompt = self.prompt_renderer.render_seeder(
                source_text=source_text,
                existing_characters=existing_chars,
                existing_terms=existing_terms,
            )
        else:
            prompt = (
                f"# Glossary & Story Seeder\nExtract initial characters and terms.\n\n"
                f"Source Text:\n{source_text}"
            )

        import inspect

        logger.info("seeding_started", chapters_count=ch_count)
        raw_res = self.llm_client.parse_seed(prompt)
        if inspect.isawaitable(raw_res):
            seed_result = await raw_res
        else:
            seed_result = raw_res

        logger.info(
            "seeding_completed",
            characters_extracted=len(seed_result.characters),
            terms_extracted=len(seed_result.terms),
            relationships_extracted=len(seed_result.relationships),
            has_story_summary=bool(seed_result.story_summary),
            has_arc_summary=bool(seed_result.arc_summary),
        )

        if save_to_project and self.project_dir is not None:
            self.save_seed_result(seed_result)

        return seed_result

    def seed_sync(
        self,
        chapters_text: list[str] | str,
        save_to_project: bool = True,
    ) -> SeedResult:
        """Synchronous wrapper for seed()."""
        return asyncio.run(self.seed(chapters_text, save_to_project=save_to_project))

    def seed_from_files(
        self,
        chapter_paths: Sequence[Path | str],
        save_to_project: bool = True,
    ) -> SeedResult:
        """Load chapters from file paths and run seeding."""
        texts: list[str] = []
        for path in chapter_paths:
            p = Path(path)
            if p.exists():
                texts.append(p.read_text(encoding="utf-8"))
        return self.seed_sync(texts, save_to_project=save_to_project)

    def save_seed_result(self, seed_result: SeedResult) -> None:
        """Persist SeedResult data to project's glossary.json and state/ summaries."""
        if self.project_dir is None:
            logger.warning("save_seed_result_skipped_no_project_dir")
            return

        # 1. Update glossary.json via GlossaryManager
        manager = GlossaryManager(project_dir=self.project_dir)
        glossary = manager.load_glossary()

        logger.info(
            "saving_seed_result",
            project_dir=str(self.project_dir),
            glossary_path=str(manager.glossary_path),
        )

        # Merge characters
        existing_char_ids = {c.id for c in glossary.characters}
        existing_char_names = {c.canonical_name.lower(): c.id for c in glossary.characters}
        char_added = 0
        char_updated = 0
        for char in seed_result.characters:
            char.reviewed = False
            for alias in char.aliases:
                alias.reviewed = False
                
            match_id = char.id
            if match_id not in existing_char_ids and char.canonical_name.lower() in existing_char_names:
                match_id = existing_char_names[char.canonical_name.lower()]
                
            if match_id not in existing_char_ids:
                glossary.characters.append(char)
                existing_char_ids.add(char.id)
                char_added += 1
            else:
                for existing_char in glossary.characters:
                    if existing_char.id == match_id:
                        if char.notes:
                            existing_char.notes = char.notes
                        if char.appearance:
                            existing_char.appearance = char.appearance
                        for alias in char.aliases:
                            if not any(ea.source == alias.source for ea in existing_char.aliases):
                                alias.reviewed = False
                                existing_char.aliases.append(alias)
                        char_updated += 1
                        break

        # Merge terms
        existing_term_sources = {t.source for t in glossary.terms}
        terms_added = 0
        terms_updated = 0
        for term in seed_result.terms:
            term.reviewed = False
            if term.source not in existing_term_sources:
                glossary.terms.append(term)
                existing_term_sources.add(term.source)
                terms_added += 1
            else:
                for existing_term in glossary.terms:
                    if existing_term.source == term.source:
                        if term.notes:
                            existing_term.notes = term.notes
                        terms_updated += 1
                        break

        # Merge relationships
        existing_rel_sets = [set(r.characters) for r in glossary.relationships]
        rels_added = 0
        rels_updated = 0
        for rel in seed_result.relationships:
            rel_set = set(rel.characters)
            if rel_set not in existing_rel_sets:
                glossary.relationships.append(rel)
                existing_rel_sets.append(rel_set)
                rels_added += 1
            else:
                for idx, existing_rel in enumerate(glossary.relationships):
                    if set(existing_rel.characters) == rel_set:
                        glossary.relationships[idx] = rel
                        rels_updated += 1
                        break

        manager.save_glossary(glossary)
        logger.info(
            "glossary_saved",
            characters_added=char_added,
            characters_updated=char_updated,
            terms_added=terms_added,
            terms_updated=terms_updated,
            relationships_added=rels_added,
            relationships_updated=rels_updated,
        )

        # 2. Save story summary and arc summary to state/
        state_dir = self.project_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)

        if seed_result.story_summary:
            story_sum_file = state_dir / "story_summary.json"
            story_data = {"story_summary": seed_result.story_summary}
            story_sum_file.write_text(
                json.dumps(story_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("story_summary_saved", path=str(story_sum_file))

        if seed_result.arc_summary:
            arc_sum_file = state_dir / "arc_summary.json"
            arc_data = {"arc_summary": seed_result.arc_summary}
            arc_sum_file.write_text(
                json.dumps(arc_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("arc_summary_saved", path=str(arc_sum_file))
