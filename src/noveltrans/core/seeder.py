"""Glossary and story summary seeder using LLM seed calls."""

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from noveltrans.glossary.manager import GlossaryManager
from noveltrans.llm.client import OpenAIClient
from noveltrans.llm.prompt_renderer import PromptRenderer
from noveltrans.llm.protocols import SeedResult


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
        self.llm_client = llm_client or OpenAIClient()
        self.project_dir = Path(project_dir) if project_dir else None

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
        else:
            source_text = chapters_text

        if self.prompt_renderer is not None:
            prompt = self.prompt_renderer.render_seeder(source_text)
        else:
            prompt = (
                f"# Glossary & Story Seeder\nExtract initial characters and terms.\n\n"
                f"Source Text:\n{source_text}"
            )

        import inspect

        raw_res = self.llm_client.parse_seed(prompt)
        if inspect.isawaitable(raw_res):
            seed_result = await raw_res
        else:
            seed_result = raw_res

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
            return

        # 1. Update glossary.json via GlossaryManager
        manager = GlossaryManager(project_dir=self.project_dir)
        glossary = manager.load_glossary()

        # Merge characters
        existing_char_ids = {c.id for c in glossary.characters}
        for char in seed_result.characters:
            if char.id not in existing_char_ids:
                glossary.characters.append(char)
                existing_char_ids.add(char.id)
            else:
                for idx, existing_char in enumerate(glossary.characters):
                    if existing_char.id == char.id:
                        glossary.characters[idx] = char
                        break

        # Merge terms
        existing_term_sources = {t.source for t in glossary.terms}
        for term in seed_result.terms:
            if term.source not in existing_term_sources:
                glossary.terms.append(term)
                existing_term_sources.add(term.source)
            else:
                for idx, existing_term in enumerate(glossary.terms):
                    if existing_term.source == term.source:
                        glossary.terms[idx] = term
                        break

        # Merge relationships
        existing_rel_sets = [set(r.characters) for r in glossary.relationships]
        for rel in seed_result.relationships:
            rel_set = set(rel.characters)
            if rel_set not in existing_rel_sets:
                glossary.relationships.append(rel)
                existing_rel_sets.append(rel_set)
            else:
                for idx, existing_rel in enumerate(glossary.relationships):
                    if set(existing_rel.characters) == rel_set:
                        glossary.relationships[idx] = rel
                        break

        manager.save_glossary(glossary)

        # 2. Save story summary and arc summary to state/
        state_dir = self.project_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)

        if seed_result.story_summary:
            story_sum_file = state_dir / "story_summary.json"
            story_data = {"story_summary": seed_result.story_summary}
            story_sum_file.write_text(
                json.dumps(story_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        if seed_result.arc_summary:
            arc_sum_file = state_dir / "arc_summary.json"
            arc_data = {"arc_summary": seed_result.arc_summary}
            arc_sum_file.write_text(
                json.dumps(arc_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
