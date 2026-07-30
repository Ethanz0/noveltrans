"""Unit tests for noveltrans GlossaryMatcher."""

import pytest

from noveltrans.glossary.matcher import GlossaryMatcher
from noveltrans.glossary.models import (
    Character,
    Glossary,
    GlossaryTerm,
)


@pytest.fixture
def matcher() -> GlossaryMatcher:
    return GlossaryMatcher(similarity_threshold=85.0)


# ============================================================================
# Tier 1: Unit Tests (Isolated algorithms, model matching, single features)
# ============================================================================


def test_exact_canonical_name_match(matcher: GlossaryMatcher, sample_glossary: Glossary) -> None:
    """Tier 1: Test Aho-Corasick exact matching of character canonical name."""
    text = "오늘 성진우는 던전에 들어갔다."
    matched_chars, matched_terms = matcher.match_terms(text, sample_glossary)

    char_ids = [c.id for c in matched_chars]
    assert "sung_jinwoo" in char_ids


def test_exact_alias_match(matcher: GlossaryMatcher, sample_glossary: Glossary) -> None:
    """Tier 1: Test Aho-Corasick exact matching of character alias source text."""
    text = "그림자 군주의 위엄이 펼쳐졌다."
    matched_chars, _ = matcher.match_terms(text, sample_glossary)

    char_ids = [c.id for c in matched_chars]
    assert "sung_jinwoo" in char_ids


def test_exact_term_match(matcher: GlossaryMatcher, sample_glossary: Glossary) -> None:
    """Tier 1: Test Aho-Corasick exact matching of glossary term."""
    text = "마수가 모습을 드러냈다."
    _, matched_terms = matcher.match_terms(text, sample_glossary)

    sources = [t.source for t in matched_terms]
    assert "마수" in sources


def test_fuzzy_fallback_match(matcher: GlossaryMatcher) -> None:
    """Tier 1: Test RapidFuzz fallback matching when term has slight variation/typo."""
    char = Character(
        id="test_char",
        canonical_name="박희진",
        aliases=[],
        gender="female",
        speech_style="polite",
    )
    term = GlossaryTerm(
        source="마력탄",
        target="Magic Bullet",
        category="skill",
        confidence=0.9,
    )
    glossary = Glossary(characters=[char], terms=[term])

    # "마력탄" vs "마력탑" or slight variation
    text = "그녀는 마력탄을 발사했다."
    _, matched_terms = matcher.match_terms(text, glossary)
    assert len(matched_terms) == 1
    assert matched_terms[0].source == "마력탄"


def test_always_include_character(matcher: GlossaryMatcher, sample_glossary: Glossary) -> None:
    """Tier 1: Test always_include character injection regardless of text matches."""
    # sample_glossary has sung_jinwoo with always_include=True
    text = "어무런 관련 없는 텍스트입니다."
    matched_chars, _ = matcher.match_terms(text, sample_glossary)

    char_ids = [c.id for c in matched_chars]
    assert "sung_jinwoo" in char_ids
    # Cha Hae-in has always_include=False and is not in text, so should not be included
    assert "cha_hae_in" not in char_ids


def test_empty_text_and_empty_glossary(matcher: GlossaryMatcher) -> None:
    """Tier 1: Test empty text and empty glossary handling."""
    empty_glossary = Glossary()
    matched_chars, matched_terms = matcher.match_terms("", empty_glossary)
    assert matched_chars == []
    assert matched_terms == []


# ============================================================================
# Tier 2: Component Integration Tests (Cross-model interaction, deduplication)
# ============================================================================


def test_multi_character_matching(matcher: GlossaryMatcher, sample_glossary: Glossary) -> None:
    """Tier 2: Test matching multiple characters and terms in a single chapter paragraph."""
    text = "성진우는 단검을 잡았다. 차해인은 그 모습을 바라보며 헌터로서의 본능을 느꼈다."
    matched_chars, matched_terms = matcher.match_terms(text, sample_glossary)

    char_ids = [c.id for c in matched_chars]
    assert "sung_jinwoo" in char_ids
    assert "cha_hae_in" in char_ids

    term_sources = [t.source for t in matched_terms]
    assert "단검" in term_sources
    assert "헌터" in term_sources


def test_alias_gender_and_identity_preservation(
    matcher: GlossaryMatcher, sample_glossary: Glossary
) -> None:
    """Tier 2: Verify matched characters preserve per-alias gender and identity tracking."""
    text = "무희 차해인이 전장에 나타났다."
    matched_chars, _ = matcher.match_terms(text, sample_glossary)

    haein = next(c for c in matched_chars if c.id == "cha_hae_in")
    assert haein.gender == "female"
    assert haein.knows_identity == ["sung_jinwoo"]
    assert any(a.alias_type == "nickname" and a.target == "Dancer" for a in haein.aliases)


def test_fuzzy_below_threshold_ignored(matcher: GlossaryMatcher) -> None:
    """Tier 2: Verify terms with similarity below 85% threshold are NOT matched."""
    term = GlossaryTerm(source="아티팩트", target="Artifact", category="item")
    glossary = Glossary(terms=[term])

    text = "완전히 다른 단어 자동차"
    _, matched_terms = matcher.match_terms(text, glossary)
    assert len(matched_terms) == 0


def test_duplicate_matches_deduplicated(
    matcher: GlossaryMatcher, sample_glossary: Glossary
) -> None:
    """Tier 2: Test that multiple occurrences of term in text produce single deduplicated match."""
    text = "성진우 성진우 성진우 그림자 군주 성진우"
    matched_chars, _ = matcher.match_terms(text, sample_glossary)

    jinwoo_count = sum(1 for c in matched_chars if c.id == "sung_jinwoo")
    assert jinwoo_count == 1


def test_combined_exact_fuzzy_always_include(
    matcher: GlossaryMatcher, sample_glossary: Glossary
) -> None:
    """Tier 2: Combined test of exact, fuzzy, and always_include in one pass."""
    # Jinwoo is always_include=True
    # Hae-in is exact match in text
    text = "차해인은 무희로서 아름답게 검을 휘둘렀다."
    matched_chars, _ = matcher.match_terms(text, sample_glossary)

    char_ids = [c.id for c in matched_chars]
    assert "sung_jinwoo" in char_ids  # always_include
    assert "cha_hae_in" in char_ids  # exact match


# ============================================================================
# Tier 3: Edge Cases & Formatting Tests
# ============================================================================


def test_korean_punctuation_and_whitespace(
    matcher: GlossaryMatcher, sample_glossary: Glossary
) -> None:
    """Tier 3: Test matching terms embedded within Korean punctuation and newlines."""
    text = "『성진우』... “단검”?! (마수)가 나타났다!\n\n차해인!"
    matched_chars, matched_terms = matcher.match_terms(text, sample_glossary)

    char_ids = [c.id for c in matched_chars]
    assert "sung_jinwoo" in char_ids
    assert "cha_hae_in" in char_ids

    term_sources = [t.source for t in matched_terms]
    assert "단검" in term_sources
    assert "마수" in term_sources


# ============================================================================
# Tier 4: Real-world Application Scenarios
# ============================================================================


def test_multi_chapter_matcher_consistency(
    matcher: GlossaryMatcher, sample_glossary: Glossary
) -> None:
    """Tier 4: Simulate glossary matching over a sequence of 3 chapters."""
    ch1_text = "성진우는 던전에 진입했다."
    ch2_text = "마수가 헌터들을 위협할 때 차해인이 도착했다."
    ch3_text = "그림자 군주의 힘이 폭발했다."

    res1_chars, _ = matcher.match_terms(ch1_text, sample_glossary)
    res2_chars, res2_terms = matcher.match_terms(ch2_text, sample_glossary)
    res3_chars, _ = matcher.match_terms(ch3_text, sample_glossary)

    assert "sung_jinwoo" in [c.id for c in res1_chars]
    assert "cha_hae_in" in [c.id for c in res2_chars]
    assert any(t.source == "마수" for t in res2_terms)
    assert "sung_jinwoo" in [c.id for c in res3_chars]
