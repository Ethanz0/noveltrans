"""Prompt renderer using Jinja2 templates for noveltrans LLM operations."""

from contextlib import suppress
import json
from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader

from noveltrans.core.context_builder import AssembledContext


class PromptRenderer:
    """Renders Jinja2 prompt templates from package or project prompts directory."""

    LANGUAGE_NAMES: dict[str, str] = {
        "ko": "Korean",
        "ja": "Japanese",
        "zh": "Chinese",
    }

    @staticmethod
    def get_source_language_name(lang: str) -> str:
        lang_code = lang.lower()
        return PromptRenderer.LANGUAGE_NAMES.get(lang_code, lang.capitalize())

    def __init__(self, prompts_dir: Path | str | None = None) -> None:
        if prompts_dir is not None:
            loader = FileSystemLoader(str(prompts_dir))
        else:
            loaders = []
            cwd_prompts = Path.cwd() / "prompts"
            if cwd_prompts.is_dir():
                loaders.append(FileSystemLoader(str(cwd_prompts)))

            repo_prompts = Path(__file__).resolve().parents[3] / "prompts"
            if repo_prompts.is_dir():
                loaders.append(FileSystemLoader(str(repo_prompts)))

            with suppress(Exception):
                loaders.append(PackageLoader("noveltrans", "prompts"))

            loader = ChoiceLoader(loaders)

        self.env = Environment(
            loader=loader,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render prompt template by name with context variables."""
        if not template_name.endswith(".jinja2"):
            template_name = f"{template_name}.jinja2"
        template = self.env.get_template(template_name)
        return template.render(**kwargs)

    def render_translator(
        self,
        assembled_context: AssembledContext,
        source_text: str,
        chapter_number: int = 1,
        target_language: str = "English",
        source_language: str = "ko",
        use_structured_output: bool = False,
        **kwargs: Any,
    ) -> str:
        """Render translator prompt template."""
        src_lang = kwargs.pop("source_language", source_language).lower()
        src_lang_name = kwargs.pop(
            "source_language_name", self.get_source_language_name(src_lang)
        )
        context: dict[str, Any] = {
            "style_guide": assembled_context.tier1_style_guide,
            "matched_characters": assembled_context.tier1_characters,
            "characters": assembled_context.tier1_characters,
            "matched_terms": assembled_context.tier1_terms,
            "terms": assembled_context.tier1_terms,
            "relationships": assembled_context.tier1_relationships,
            "story_summary": assembled_context.tier2_story_summary,
            "arc_summary": assembled_context.tier3_arc_summary,
            "recent_summaries": assembled_context.tier3_recent_summaries,
            "chapter_summaries": assembled_context.tier3_recent_summaries,
            "recent_chapters": assembled_context.tier4_recent_chapters,
            "source_text": source_text,
            "chapter_number": chapter_number,
            "target_language": target_language,
            "source_language": src_lang,
            "source_language_name": src_lang_name,
        }
        if not use_structured_output:
            from noveltrans.llm.protocols import TranslationResult
            context["json_schema"] = json.dumps(TranslationResult.model_json_schema(), indent=2)

        context.update(kwargs)
        return self.render("translator.jinja2", **context)

    def render_analyzer(
        self,
        chapter_number: int = 1,
        translated_text: str = "",
        source_text: str = "",
        existing_characters: list[str] | None = None,
        existing_terms: list[str] | None = None,
        source_language: str = "ko",
        use_structured_output: bool = False,
        **kwargs: Any,
    ) -> str:
        """Render post-translation analyzer prompt template."""
        src_lang = kwargs.pop("source_language", source_language).lower()
        src_lang_name = kwargs.pop(
            "source_language_name", self.get_source_language_name(src_lang)
        )
        context: dict[str, Any] = {
            "chapter_number": chapter_number,
            "source_text": source_text,
            "translated_text": translated_text,
            "existing_characters": existing_characters or [],
            "existing_terms": existing_terms or [],
            "source_language": src_lang,
            "source_language_name": src_lang_name,
        }
        if not use_structured_output:
            from noveltrans.llm.protocols import AnalysisResult
            context["json_schema"] = json.dumps(AnalysisResult.model_json_schema(), indent=2)

        context.update(kwargs)
        return self.render("analyzer.jinja2", **context)

    def render_seeder(
        self,
        source_text: str = "",
        sample_chapters: list[Any] | None = None,
        project_title: str = "",
        source_language: str = "ko",
        use_structured_output: bool = False,
        **kwargs: Any,
    ) -> str:
        """Render seeder prompt template."""
        src_lang = kwargs.pop("source_language", source_language).lower()
        src_lang_name = kwargs.pop(
            "source_language_name", self.get_source_language_name(src_lang)
        )
        chaps = sample_chapters or ([source_text] if source_text else [])
        context: dict[str, Any] = {
            "sample_chapters": chaps,
            "project_title": project_title,
            "source_text": source_text,
            "source_language": src_lang,
            "source_language_name": src_lang_name,
        }
        if not use_structured_output:
            from noveltrans.llm.protocols import SeedResult
            context["json_schema"] = json.dumps(SeedResult.model_json_schema(), indent=2)

        context.update(kwargs)
        return self.render("seeder.jinja2", **context)

    def render_style_analyzer(
        self,
        sample_text: str = "",
        source_text: str = "",
        source_language: str = "ko",
        **kwargs: Any,
    ) -> str:
        """Render style analyzer prompt template."""
        src_lang = kwargs.pop("source_language", source_language).lower()
        src_lang_name = kwargs.pop(
            "source_language_name", self.get_source_language_name(src_lang)
        )
        text = sample_text or source_text
        context: dict[str, Any] = {
            "sample_text": text,
            "source_text": text,
            "source_language": src_lang,
            "source_language_name": src_lang_name,
        }
        context.update(kwargs)
        return self.render("style_analyzer.jinja2", **context)

    def render_arc_summary(
        self,
        current_arc_summary: str = "",
        chapter_summaries: list[Any] | None = None,
        previous_arc_summary: str = "",
        recent_chapter_summaries: list[Any] | None = None,
        significant_events: list[Any] | None = None,
        source_language: str = "ko",
        **kwargs: Any,
    ) -> str:
        """Render arc summary generator prompt template."""
        src_lang = kwargs.pop("source_language", source_language).lower()
        src_lang_name = kwargs.pop(
            "source_language_name", self.get_source_language_name(src_lang)
        )
        ch_sums = chapter_summaries or recent_chapter_summaries or []
        arc_sum = current_arc_summary or previous_arc_summary or ""
        context: dict[str, Any] = {
            "current_arc_summary": arc_sum,
            "previous_arc_summary": arc_sum,
            "chapter_summaries": ch_sums,
            "recent_chapter_summaries": ch_sums,
            "significant_events": significant_events or [],
            "source_language": src_lang,
            "source_language_name": src_lang_name,
        }
        context.update(kwargs)
        return self.render("arc_summary.jinja2", **context)

    def render_story_summary(
        self,
        current_story_summary: str = "",
        arc_summary: str = "",
        previous_story_summary: str = "",
        arc_summaries: list[str] | None = None,
        key_events: list[str] | None = None,
        source_language: str = "ko",
        **kwargs: Any,
    ) -> str:
        """Render grand story summary generator prompt template."""
        src_lang = kwargs.pop("source_language", source_language).lower()
        src_lang_name = kwargs.pop(
            "source_language_name", self.get_source_language_name(src_lang)
        )
        st_sum = current_story_summary or previous_story_summary or ""
        arcs = arc_summaries or ([arc_summary] if arc_summary else [])
        context: dict[str, Any] = {
            "current_story_summary": st_sum,
            "previous_story_summary": st_sum,
            "arc_summary": arc_summary,
            "arc_summaries": arcs,
            "key_events": key_events or [],
            "source_language": src_lang,
            "source_language_name": src_lang_name,
        }
        context.update(kwargs)
        return self.render("story_summary.jinja2", **context)

    def render_term_alternatives(
        self,
        source_term: str,
        current_translation: str,
        category: str,
        source_language: str = "ko",
        use_structured_output: bool = False,
        **kwargs: Any,
    ) -> str:
        """Render term alternatives prompt template."""
        src_lang = kwargs.pop("source_language", source_language).lower()
        src_lang_name = kwargs.pop(
            "source_language_name", self.get_source_language_name(src_lang)
        )
        context: dict[str, Any] = {
            "source_term": source_term,
            "current_translation": current_translation,
            "category": category,
            "source_language": src_lang,
            "source_language_name": src_lang_name,
        }
        if not use_structured_output:
            from noveltrans.llm.protocols import TermAlternativesResult
            context["json_schema"] = json.dumps(TermAlternativesResult.model_json_schema(), indent=2)

        context.update(kwargs)
        return self.render("term_alternatives.jinja2", **context)
