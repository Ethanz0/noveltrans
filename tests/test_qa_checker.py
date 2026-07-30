"""Unit tests for noveltrans QAChecker (deterministic automated non-LLM checks)."""

import pytest

from noveltrans.core.qa_checker import QAChecker
from noveltrans.glossary.models import Glossary, GlossaryTerm


@pytest.fixture
def qa_checker() -> QAChecker:
    return QAChecker()


# ============================================================================
# Tier 1: Unit Tests (Individual checker rules & regex matching)
# ============================================================================


def test_clean_translation_no_issues(qa_checker: QAChecker) -> None:
    """Tier 1: Verify clean English translation produces zero QA issues."""
    text = "Sung Jinwoo entered the dungeon. He unsheathed his dagger and faced the magic beast."
    source = "성진우는 던전에 들어갔다. 그는 단검을 뽑고 마수를 마주했다."
    issues = qa_checker.check_chapter(text, source_text=source)
    assert issues == []


def test_untranslated_korean_regex_detection(qa_checker: QAChecker) -> None:
    """Tier 1: Test detection of untranslated Korean regex [\uAC00-\uD7A3]+."""
    text = "Sung Jinwoo said, '그는 칼을 들었다' and walked away."
    issues = qa_checker.check_chapter(text, source_language="ko")

    assert len(issues) >= 1
    issue = issues[0]
    assert issue.issue_type == "untranslated_korean"
    assert issue.severity == "warning"
    assert "그는" in issue.description or "칼을" in issue.description


def test_untranslated_japanese_regex_detection(qa_checker: QAChecker) -> None:
    """Tier 1: Test detection of untranslated Japanese text when source_language='ja'."""
    text = "The protagonist said, 'これは日本語のテキストです' and smiled."
    issues = qa_checker.check_chapter(text, source_language="ja")

    assert len(issues) >= 1
    issue = issues[0]
    assert issue.issue_type == "untranslated_japanese"
    assert issue.severity == "warning"
    assert "Found untranslated Japanese text" in issue.description


def test_untranslated_chinese_regex_detection(qa_checker: QAChecker) -> None:
    """Tier 1: Test detection of untranslated Chinese text when source_language='zh'."""
    text = "The cultivator said, '这是中文文本' and closed his eyes."
    issues = qa_checker.check_chapter(text, source_language="zh")

    assert len(issues) >= 1
    issue = issues[0]
    assert issue.issue_type == "untranslated_chinese"
    assert issue.severity == "warning"
    assert "Found untranslated Chinese text" in issue.description


def test_hallucinated_filler_detection(qa_checker: QAChecker) -> None:
    """Tier 1: Test detection of hallucinated LLM filler phrases."""
    text = "As an AI language model, here is the translation of chapter 1:\nSung Jinwoo stood up."
    issues = qa_checker.check_chapter(text)

    assert len(issues) >= 1
    issue = next(i for i in issues if i.issue_type == "hallucinated_filler")
    assert issue.severity == "error"
    assert "as an ai language model" in issue.description.lower()


def test_repetition_loop_detection(qa_checker: QAChecker) -> None:
    """Tier 1: Test detection of repetition loops (consecutive identical lines)."""
    text = (
        "Sung Jinwoo gripped his dagger tightly.\n"
        "Sung Jinwoo gripped his dagger tightly.\n"
        "Sung Jinwoo gripped his dagger tightly.\n"
    )
    issues = qa_checker.check_chapter(text)

    assert len(issues) >= 1
    issue = next(i for i in issues if i.issue_type == "repetition_loop")
    assert issue.severity == "error"


def test_missing_glossary_term_detection(qa_checker: QAChecker, sample_glossary: Glossary) -> None:
    """Tier 1: Test detection of missing expected glossary terms in translation."""
    source = "성진우는 단검을 사용했다."  # term "단검" -> "Dagger"
    translation = "Sung Jinwoo used a sharp blade weapon."  # "Dagger" missing!

    issues = qa_checker.check_chapter(translation, source_text=source, glossary=sample_glossary)

    assert len(issues) >= 1
    issue = next(i for i in issues if i.issue_type == "missing_glossary_term")
    assert issue.severity == "warning"
    assert "Dagger" in issue.description


def test_length_anomaly_detection(qa_checker: QAChecker) -> None:
    """Tier 1: Test detection of output length ratio anomaly (< 20% of source length)."""
    source = "A" * 500
    translation = "Tiny text."

    issues = qa_checker.check_chapter(translation, source_text=source)
    assert len(issues) >= 1
    issue = next(i for i in issues if i.issue_type == "length_anomaly")
    assert issue.severity == "warning"


# ============================================================================
# Tier 2: Component Integration Tests (Multi-anomaly checks & non-blocking)
# ============================================================================


def test_multiple_anomalies_in_single_chapter(
    qa_checker: QAChecker, sample_glossary: Glossary
) -> None:
    """Tier 2: Test simultaneous detection of untranslated text, filler, and missing term."""
    source = "성진우는 단검을 들었다."
    translation = (
        "Here is the translation:\n"
        "Sung Jinwoo held his 칼을.\n"
    )

    issues = qa_checker.check_chapter(translation, source_text=source, glossary=sample_glossary)

    types = [i.issue_type for i in issues]
    assert "untranslated_korean" in types
    assert "hallucinated_filler" in types
    assert "missing_glossary_term" in types


def test_non_blocking_nature_of_qa_checker(qa_checker: QAChecker) -> None:
    """Tier 2: Verify QA check returns issue list without throwing exceptions or blocking."""
    corrupted_text = "As an AI language model, 그는 단검을 들었다. " * 50
    issues = qa_checker.check_chapter(corrupted_text)
    assert isinstance(issues, list)
    assert len(issues) > 0


def test_glossary_term_case_insensitivity(qa_checker: QAChecker) -> None:
    """Tier 2: Verify target terms are checked case-insensitively."""
    term = GlossaryTerm(source="단검", target="Dagger", category="item")
    glossary = Glossary(terms=[term])

    source = "단검을 사용했다."
    translation = "He used a dagger."  # lowercase 'dagger'

    issues = qa_checker.check_chapter(translation, source_text=source, glossary=glossary)
    assert not any(i.issue_type == "missing_glossary_term" for i in issues)


def test_korean_regex_boundary(qa_checker: QAChecker) -> None:
    """Tier 2: Ensure pure English text with punctuation does NOT trigger Korean regex."""
    text = "Chapter 1: The Leveling (Part 2) - 100% Awakened! #Hunter [S-Rank] @123."
    issues = qa_checker.check_chapter(text)
    assert not any(i.issue_type == "untranslated_korean" for i in issues)


def test_severity_levels(qa_checker: QAChecker) -> None:
    """Tier 2: Verify appropriate severity assignment."""
    t1 = qa_checker.check_chapter("Here is untranslated: 성진우")
    assert t1[0].severity == "warning"

    t2 = qa_checker.check_chapter("as an ai language model")
    assert t2[0].severity == "error"


# ============================================================================
# Tier 3: Edge Cases & Boundary Tests
# ============================================================================


def test_empty_source_and_translation(qa_checker: QAChecker) -> None:
    """Tier 3: Test empty source and empty translation strings produce no errors."""
    issues = qa_checker.check_chapter("", source_text="")
    assert isinstance(issues, list)


# ============================================================================
# Tier 4: Real-world Application Scenarios
# ============================================================================


def test_qa_checker_batch_reporting(qa_checker: QAChecker, sample_glossary: Glossary) -> None:
    """Tier 4: Simulate running QA checks on a batch of 3 chapters and compiling issue reports."""
    chapters = [
        (
            "Clean translation of chapter 1. Sung Jinwoo used a Dagger.",
            "성진우는 단검을 썼다. 1장의 깨끗한 번역 테스트 문장입니다.",
        ),
        ("Chapter 2 output with untranslated 부분 text.", "2장 부분 텍스트."),
        (
            "As an AI language model, here is translation.\n"
            "Repeated sentence.\n"
            "Repeated sentence.\n"
            "Repeated sentence.",
            "3장 텍스트.",
        ),
    ]

    report: dict[int, list[str]] = {}
    for idx, (tr, src) in enumerate(chapters, start=1):
        issues = qa_checker.check_chapter(tr, source_text=src, glossary=sample_glossary)
        report[idx] = [i.issue_type for i in issues]

    assert report[1] == []
    assert "untranslated_korean" in report[2]
    assert "hallucinated_filler" in report[3]
    assert "repetition_loop" in report[3]
