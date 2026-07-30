"""4-tier context assembly builder for novel translation pipeline."""

from pydantic import BaseModel, Field

from noveltrans.config.settings import ProjectConfig
from noveltrans.glossary.matcher import GlossaryMatcher
from noveltrans.glossary.models import Character, Glossary, GlossaryTerm, Relationship


class AssembledContext(BaseModel):
    """4-Tier assembled context data structure."""

    tier1_style_guide: str = ""
    tier1_characters: list[Character] = Field(default_factory=list)
    tier1_terms: list[GlossaryTerm] = Field(default_factory=list)
    tier1_relationships: list[Relationship] = Field(default_factory=list)
    tier2_story_summary: str = ""
    tier3_arc_summary: str = ""
    tier3_recent_summaries: list[str] = Field(default_factory=list)
    tier4_recent_chapters: list[str] = Field(default_factory=list)


class ContextBuilder:
    """Builder that constructs 4-tier context for LLM translation prompt."""

    def __init__(
        self,
        config: ProjectConfig | None = None,
        matcher: GlossaryMatcher | None = None,
    ) -> None:
        self.config = config or ProjectConfig(title="Default")
        self.matcher = matcher or GlossaryMatcher()

    def build_context(
        self,
        chapter_number: int,
        source_text: str,
        glossary: Glossary,
        style_guide: str = "",
        story_summary: str = "",
        arc_summary: str = "",
        chapter_summaries: list[str] | None = None,
        recent_chapters: list[str] | None = None,
    ) -> AssembledContext:
        """Assembles 4-tier context for chapter translation.

        - Tier 1: Style guide + matched glossary terms & characters
          (including always_include) + relationships
        - Tier 2: Story summary
        - Tier 3: Arc summary + recent chapter summaries (sliced to config.context_recent_summaries)
        - Tier 4: Recent full translated chapters (sliced to config.context_recent_chapters)
        """
        # Match glossary terms & characters
        matched_chars, matched_terms = self.matcher.match_terms(source_text, glossary)

        # Match relationships involving any matched character
        matched_char_keys: set[str] = set()
        for char in matched_chars:
            matched_char_keys.add(char.id)
            matched_char_keys.add(char.canonical_name)
            for alias in char.aliases:
                matched_char_keys.add(alias.source)
                matched_char_keys.add(alias.target)

        matched_relationships: list[Relationship] = []
        for rel in glossary.relationships:
            if any(c in matched_char_keys for c in rel.characters):
                matched_relationships.append(rel)

        # Slice recent summaries and chapters according to configuration
        all_summaries = chapter_summaries or []
        n_summaries = self.config.context_recent_summaries
        recent_sums = all_summaries[-n_summaries:] if all_summaries else []

        all_chapters = recent_chapters or []
        n_chapters = self.config.context_recent_chapters
        recent_chaps = all_chapters[-n_chapters:] if all_chapters else []

        return AssembledContext(
            tier1_style_guide=style_guide,
            tier1_characters=matched_chars,
            tier1_terms=matched_terms,
            tier1_relationships=matched_relationships,
            tier2_story_summary=story_summary,
            tier3_arc_summary=arc_summary,
            tier3_recent_summaries=recent_sums,
            tier4_recent_chapters=recent_chaps,
        )
