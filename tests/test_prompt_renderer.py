"""Unit tests for noveltrans PromptRenderer (Jinja2 template rendering)."""

from pathlib import Path

import pytest
from jinja2 import TemplateNotFound

from noveltrans.core.context_builder import AssembledContext
from noveltrans.glossary.models import Glossary
from noveltrans.llm.prompt_renderer import PromptRenderer


@pytest.fixture
def prompts_dir(temp_project_dir: Path) -> Path:
    return temp_project_dir / "prompts"


@pytest.fixture
def renderer(prompts_dir: Path) -> PromptRenderer:
    return PromptRenderer(prompts_dir)


# ============================================================================
# Tier 1: Unit Tests (Individual template rendering)
# ============================================================================


def test_render_translator_prompt(
    renderer: PromptRenderer, sample_glossary: Glossary
) -> None:
    """Tier 1: Verify render_translator embeds 4-tier context variables correctly."""
    context = AssembledContext(
        tier1_style_guide="# Style Guide\n- High quality.",
        tier1_characters=sample_glossary.characters,
        tier1_terms=sample_glossary.terms,
        tier2_story_summary="Story of Jinwoo",
        tier3_arc_summary="Double Dungeon Arc",
        tier3_recent_summaries=["Summary 1", "Summary 2"],
        tier4_recent_chapters=["Chapter 1 text"],
    )

    rendered = renderer.render_translator(context, source_text="성진우가 단검을 쥐었다.")
    assert "High quality" in rendered
    assert "Sung Jinwoo" in rendered
    assert "Shadow Monarch" in rendered
    assert "Dagger" in rendered
    assert "Double Dungeon Arc" in rendered
    assert "성진우가 단검을 쥐었다." in rendered


def test_render_analyzer_prompt(renderer: PromptRenderer) -> None:
    """Tier 1: Verify render_analyzer embeds chapter number and translated text."""
    rendered = renderer.render_analyzer(
        chapter_number=5, translated_text="Translated text of chapter 5."
    )
    assert "chapter 5" in rendered.lower()
    assert "Translated text of chapter 5." in rendered


def test_render_seeder_prompt(renderer: PromptRenderer) -> None:
    """Tier 1: Verify render_seeder embeds source text."""
    rendered = renderer.render_seeder("Initial raw Korean chapter 1 text.")
    assert "Initial raw Korean chapter 1 text." in rendered


def test_render_style_analyzer_prompt(renderer: PromptRenderer) -> None:
    """Tier 1: Verify render_style_analyzer embeds source text."""
    rendered = renderer.render_style_analyzer("Korean novel style sample text.")
    assert "Korean novel style sample text." in rendered


def test_render_arc_summary_prompt(renderer: PromptRenderer) -> None:
    """Tier 1: Verify render_arc_summary embeds current summary and chapter summaries."""
    rendered = renderer.render_arc_summary(
        current_arc_summary="Arc 1 Summary",
        chapter_summaries=["Ch 1 summary", "Ch 2 summary"],
    )
    assert "Arc 1 Summary" in rendered
    assert "Ch 1 summary" in rendered
    assert "Ch 2 summary" in rendered


def test_render_story_summary_prompt(renderer: PromptRenderer) -> None:
    """Tier 1: Verify render_story_summary embeds story and arc summaries."""
    rendered = renderer.render_story_summary(
        current_story_summary="Overall story",
        arc_summary="New arc summary",
    )
    assert "Overall story" in rendered
    assert "New arc summary" in rendered


def test_japanese_honorifics_prompt_rendering(renderer: PromptRenderer) -> None:
    """Verify Japanese prompt instructs preserving honorifics as-is and uses Japanese name."""
    context = AssembledContext(tier1_style_guide="Style", tier1_characters=[], tier1_terms=[])
    rendered = renderer.render_translator(
        context, source_text="Sample Japanese text", source_language="ja"
    )

    assert "Japanese web novel translation" in rendered
    assert "Preserve Japanese honorifics" in rendered
    assert "-san" in rendered or "-sama" in rendered


def test_korean_chinese_honorifics_prompt_rendering(renderer: PromptRenderer) -> None:
    """Verify Korean and Chinese prompts instruct fully translating honorifics."""
    context = AssembledContext(tier1_style_guide="Style", tier1_characters=[], tier1_terms=[])

    rendered_ko = renderer.render_translator(
        context, source_text="Sample Korean", source_language="ko"
    )
    assert "Korean web novel translation" in rendered_ko
    assert "Fully translate or adapt Korean/Chinese honorifics" in rendered_ko

    rendered_zh = renderer.render_translator(
        context, source_text="Sample Chinese", source_language="zh"
    )
    assert "Chinese web novel translation" in rendered_zh
    assert "Fully translate or adapt Korean/Chinese honorifics" in rendered_zh


def test_chinese_simplified_traditional_note_prompt_rendering(
    renderer: PromptRenderer,
) -> None:
    """Verify Chinese seeder and analyzer prompts include Simplified vs Traditional note."""
    analyzer_rendered = renderer.render_analyzer(
        chapter_number=1,
        source_text="Chinese text",
        translated_text="English text",
        source_language="zh",
    )
    assert "Simplified vs Traditional Chinese" in analyzer_rendered

    seeder_rendered = renderer.render_seeder(
        source_text="Chinese text sample",
        source_language="zh",
    )
    assert "Simplified vs Traditional Chinese" in seeder_rendered


# ============================================================================
# Tier 2: Component Integration Tests (Complex formatting & character fields)
# ============================================================================


def test_alias_gender_and_knows_identity_in_rendered_prompt(
    renderer: PromptRenderer, sample_glossary: Glossary
) -> None:
    """Tier 2: Test that character alias gender and alias targets are present in rendered prompt."""
    context = AssembledContext(
        tier1_style_guide="Style Guide",
        tier1_characters=sample_glossary.characters,
        tier1_terms=[],
    )

    rendered = renderer.render_translator(context, source_text="Source")

    # Sung Jinwoo alias: "성진우" -> "Sung Jinwoo" (Gender: male...)
    assert '"성진우" -> "Sung Jinwoo" (Gender: male' in rendered
    # Cha Hae-in alias: "무희" -> "Dancer" (Gender: female...)
    assert '"무희" -> "Dancer" (Gender: female' in rendered


def test_empty_glossary_rendering(renderer: PromptRenderer) -> None:
    """Tier 2: Verify template renders cleanly when characters and terms lists are empty."""
    context = AssembledContext(
        tier1_style_guide="Minimal guide",
        tier1_characters=[],
        tier1_terms=[],
    )
    rendered = renderer.render_translator(context, source_text="Pure source text")
    assert "Minimal guide" in rendered
    assert "Pure source text" in rendered


def test_rendering_with_special_characters(renderer: PromptRenderer) -> None:
    """Tier 2: Verify special symbols, quotes, and HTML-like tags render without error."""
    context = AssembledContext(
        tier1_style_guide="Use <angle_brackets> & 'quotes'",
        tier1_characters=[],
        tier1_terms=[],
    )
    rendered = renderer.render_translator(context, source_text="Source with <tag> and 'quote'.")
    assert "<angle_brackets>" in rendered
    assert "<tag>" in rendered


def test_chapter_summaries_formatting(renderer: PromptRenderer) -> None:
    """Tier 2: Test formatting of multiple chapter summaries in arc prompt."""
    summaries = ["Ch1: Jinwoo awakens", "Ch2: Jinwoo fights d-rank boss", "Ch3: Jinwoo escapes"]
    rendered = renderer.render_arc_summary(current_arc_summary="Arc 1", chapter_summaries=summaries)

    for sum_text in summaries:
        assert sum_text in rendered


# ============================================================================
# Tier 3: Edge Cases & Exception Handling
# ============================================================================


def test_missing_template_file_raises_error(tmp_path: Path) -> None:
    """Tier 3: Test that instantiating renderer with empty dir raises TemplateNotFound on render."""
    empty_dir = tmp_path / "empty_prompts"
    empty_dir.mkdir(parents=True, exist_ok=True)

    bad_renderer = PromptRenderer(empty_dir)
    with pytest.raises(TemplateNotFound):
        bad_renderer.render_seeder("Text")


# ============================================================================
# Tier 4: Real-world Application Scenarios (Prompt Archiving)
# ============================================================================


def test_prompt_archiving_simulation(
    renderer: PromptRenderer, sample_glossary: Glossary, tmp_path: Path
) -> None:
    """Tier 4: Simulate rendering translator prompt and archiving prompt snapshot."""
    context = AssembledContext(
        tier1_style_guide="Style",
        tier1_characters=sample_glossary.characters,
        tier1_terms=sample_glossary.terms,
        tier2_story_summary="Story",
        tier3_arc_summary="Arc",
    )

    prompt_text = renderer.render_translator(context, source_text="Chapter 1 Korean")

    archive_path = tmp_path / "state" / "prompts" / "ch001_translator.txt"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(prompt_text, encoding="utf-8")

    assert archive_path.exists()
    saved_content = archive_path.read_text(encoding="utf-8")
    assert "Sung Jinwoo" in saved_content
    assert "Chapter 1 Korean" in saved_content
