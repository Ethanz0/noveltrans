"""Non-LLM automated QA checker for translated chapter text."""

import re
from typing import Literal

import structlog

from noveltrans.glossary.models import Glossary
from noveltrans.state.models import QAIssue

logger = structlog.get_logger()


class QAChecker:
    """Evaluates translated text for anomalies and logs non-blocking QA issues."""

    UNTRANSLATED_REGEXES: dict[str, re.Pattern[str]] = {
        "ko": re.compile(r"[\uAC00-\uD7A3]+"),
        "ja": re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+"),
        "zh": re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF]+"),
    }
    LANG_NAMES: dict[str, str] = {
        "ko": "Korean",
        "ja": "Japanese",
        "zh": "Chinese",
    }
    KOREAN_REGEX = UNTRANSLATED_REGEXES["ko"]

    FILLER_PHRASES = [
        "as an ai language model",
        "here is the translation",
        "here is a translation",
        "translating chapter",
        "sure, here is",
        "certainly! here is",
        "i have translated",
    ]

    def __init__(self, source_language: str = "ko") -> None:
        self.source_language = source_language

    def check_chapter(
        self,
        translated_text: str,
        source_text: str = "",
        glossary: Glossary | None = None,
        source_language: str | None = None,
    ) -> list[QAIssue]:
        """Perform automated quality checks on translated chapter text."""
        issues: list[QAIssue] = []

        lang = (source_language or self.source_language).lower()
        lang_name = self.LANG_NAMES.get(lang, lang.capitalize())
        regex = self.UNTRANSLATED_REGEXES.get(lang, self.UNTRANSLATED_REGEXES["ko"])

        # 1. Untranslated text detection
        untranslated_matches = regex.findall(translated_text)
        if untranslated_matches:
            match_str = ", ".join(set(untranslated_matches[:5]))
            issue_type_map: dict[
                str,
                Literal["untranslated_korean", "untranslated_japanese", "untranslated_chinese"],
            ] = {
                "ko": "untranslated_korean",
                "ja": "untranslated_japanese",
                "zh": "untranslated_chinese",
            }
            issue_type = issue_type_map.get(lang, "untranslated_korean")
            issue = QAIssue(
                issue_type=issue_type,
                description=f"Found untranslated {lang_name} text in output: {match_str}",
                severity="warning",
            )
            issues.append(issue)
            logger.warning("qa_check_failed", issue_type=issue_type, details=match_str)

        # 2. Hallucinated filler phrase detection
        lower_text = translated_text.lower()
        for phrase in self.FILLER_PHRASES:
            if phrase in lower_text:
                issue = QAIssue(
                    issue_type="hallucinated_filler",
                    description=f"Found LLM meta-filler phrase: '{phrase}'",
                    severity="error",
                )
                issues.append(issue)
                logger.error("qa_check_failed", issue_type="hallucinated_filler", phrase=phrase)
                break

        # 3. Repetition loop detection
        lines = [line.strip() for line in translated_text.splitlines() if line.strip()]
        if len(lines) >= 3:
            # Check for 3 consecutive identical or near-identical lines
            for i in range(len(lines) - 2):
                if lines[i] == lines[i + 1] == lines[i + 2]:
                    issue = QAIssue(
                        issue_type="repetition_loop",
                        description=(
                            f"Detected repetitive line loop starting with: '{lines[i][:40]}'"
                        ),
                        severity="error",
                    )
                    issues.append(issue)
                    logger.error(
                        "qa_check_failed",
                        issue_type="repetition_loop",
                        snippet=lines[i][:40],
                    )
                    break

        # 4. Missing glossary terms check
        if glossary and source_text:
            for term in glossary.terms:
                if term.source in source_text and term.target.lower() not in lower_text:
                    issue = QAIssue(
                        issue_type="missing_glossary_term",
                        description=(
                            f"Expected glossary target '{term.target}' for source '{term.source}' "
                            "was missing in translation."
                        ),
                        severity="warning",
                    )
                    issues.append(issue)
                    logger.warning(
                        "qa_check_failed",
                        issue_type="missing_glossary_term",
                        source=term.source,
                        target=term.target,
                    )

        # 5. Length anomaly check
        if source_text:
            src_len = len(source_text.strip())
            tr_len = len(translated_text.strip())
            if src_len > 0:
                ratio = tr_len / src_len
                if ratio < 0.2 or ratio > 3.5:
                    issue = QAIssue(
                        issue_type="length_anomaly",
                        description=(
                            f"Translation length ratio anomaly (translated: {tr_len}, "
                            f"source: {src_len}, ratio: {ratio:.2f})"
                        ),
                        severity="warning",
                    )
                    issues.append(issue)
                    logger.warning("qa_check_failed", issue_type="length_anomaly", ratio=ratio)

        return issues
