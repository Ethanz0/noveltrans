"""Tests for 4-tier context builder."""

from noveltrans.config.settings import ProjectConfig
from noveltrans.core.context_builder import ContextBuilder
from noveltrans.glossary.models import (
    Character,
    CharacterAlias,
    Glossary,
    GlossaryTerm,
    Relationship,
)


def test_context_builder_4_tier_assembly() -> None:
    """Test 4-tier context assembly with slicing and term matching."""
    config = ProjectConfig(
        title="Test Novel",
        context_recent_summaries=3,
        context_recent_chapters=2,
        arc_summary_fallback_interval=3,
    )
    builder = ContextBuilder(config=config)

    jinwoo = Character(
        id="sung_jinwoo",
        canonical_name="Sung Jinwoo",
        aliases=[
            CharacterAlias(
                source="성진우",
                target="Sung Jinwoo",
                gender="male",
                context="Full name",
                alias_type="name",
            )
        ],
        gender="male",
        speech_style="confident",
        always_include=True,
    )
    haein = Character(
        id="cha_hae_in",
        canonical_name="Cha Hae-in",
        aliases=[
            CharacterAlias(
                source="차해인",
                target="Cha Hae-in",
                gender="female",
                context="Full name",
                alias_type="name",
            )
        ],
        gender="female",
        speech_style="polite",
        always_include=False,
    )
    term_dagger = GlossaryTerm(
        source="단검",
        target="Dagger",
        category="item",
    )
    rel = Relationship(
        characters=["sung_jinwoo", "cha_hae_in"],
        description="Teammates",
    )
    glossary = Glossary(
        characters=[jinwoo, haein],
        terms=[term_dagger],
        relationships=[rel],
    )

    summaries = [f"Summary of Ch {i}" for i in range(1, 10)]
    chapters = [f"Translated Ch {i} text" for i in range(1, 6)]

    context = builder.build_context(
        chapter_number=10,
        source_text="성진우는 단검을 쥐었다.",
        glossary=glossary,
        style_guide="# Style Guide\nUse active voice.",
        story_summary="Overall story about hunter Jinwoo.",
        arc_summary="Double Dungeon Arc",
        chapter_summaries=summaries,
        recent_chapters=chapters,
    )

    assert context.tier1_style_guide == "# Style Guide\nUse active voice."
    assert len(context.tier1_characters) == 1
    assert context.tier1_characters[0].canonical_name == "Sung Jinwoo"
    assert len(context.tier1_terms) == 1
    assert context.tier1_terms[0].target == "Dagger"
    assert len(context.tier1_relationships) == 1
    assert context.tier1_relationships[0].description == "Teammates"

    assert context.tier2_story_summary == "Overall story about hunter Jinwoo."
    assert context.tier3_arc_summary == "Double Dungeon Arc"

    # Verify slicing limits: 3 summaries, 2 chapters
    expected_sums = ["Summary of Ch 7", "Summary of Ch 8", "Summary of Ch 9"]
    assert context.tier3_recent_summaries == expected_sums

    assert len(context.tier4_recent_chapters) == 2
    assert context.tier4_recent_chapters == ["Translated Ch 4 text", "Translated Ch 5 text"]


def test_context_builder_always_include_characters() -> None:
    """Test always_include characters are present even without text match."""
    builder = ContextBuilder()

    jinwoo = Character(
        id="sung_jinwoo",
        canonical_name="Sung Jinwoo",
        aliases=[
            CharacterAlias(
                source="성진우",
                target="Sung Jinwoo",
                gender="male",
                context="Full name",
                alias_type="name",
            )
        ],
        gender="male",
        speech_style="sharp",
        always_include=True,
    )
    haein = Character(
        id="cha_hae_in",
        canonical_name="Cha Hae-in",
        aliases=[
            CharacterAlias(
                source="차해인",
                target="Cha Hae-in",
                gender="female",
                context="Full name",
                alias_type="name",
            )
        ],
        gender="female",
        speech_style="quiet",
        always_include=False,
    )
    glossary = Glossary(characters=[jinwoo, haein])

    # Text contains no character names
    context = builder.build_context(
        chapter_number=1,
        source_text="바람이 불었다.",
        glossary=glossary,
    )

    char_ids = [c.id for c in context.tier1_characters]
    assert "sung_jinwoo" in char_ids
    assert "cha_hae_in" not in char_ids


def test_context_builder_empty_inputs() -> None:
    """Test context builder handles None or empty inputs gracefully."""
    builder = ContextBuilder()
    glossary = Glossary()

    context = builder.build_context(
        chapter_number=1,
        source_text="Hello world",
        glossary=glossary,
        chapter_summaries=None,
        recent_chapters=None,
    )

    assert context.tier1_characters == []
    assert context.tier1_terms == []
    assert context.tier1_relationships == []
    assert context.tier3_recent_summaries == []
    assert context.tier4_recent_chapters == []
