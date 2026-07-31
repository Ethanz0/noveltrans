"""Tests for LLM Client and Response Parsers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from noveltrans.config.settings import EnvSettings
from noveltrans.llm.client import LLMClient
from noveltrans.llm.protocols import (
    AnalysisResult,
    PromptBasedParser,
    SeedResult,
    StructuredOutputParser,
    TranslationResult,
)


@pytest.mark.asyncio
async def test_structured_output_parser() -> None:
    """Test StructuredOutputParser parses JSON output correctly."""
    parser = StructuredOutputParser()

    # Translation
    json_trans = '{"translated_text": "Hello world.", "translator_notes": "None"}'
    trans_res = await parser.parse_translation(f"```json\n{json_trans}\n```")
    assert isinstance(trans_res, TranslationResult)
    assert trans_res.translated_text == "Hello world."
    assert trans_res.translator_notes == "None"

    # Analysis
    json_analysis = (
        '{"summary": "A great battle.", "key_events": ["Battle started"], '
        '"characters_present": ["jinwoo"], "new_characters": [], "new_terms": [], '
        '"character_updates": [], "relationship_updates": [], '
        '"significant_events": [], "qa_flags": []}'
    )
    analysis_res = await parser.parse_analysis(json_analysis)
    assert isinstance(analysis_res, AnalysisResult)
    assert analysis_res.summary == "A great battle."
    assert analysis_res.key_events == ["Battle started"]

    # Seed
    json_seed = (
        '{"characters": [], "terms": [], "relationships": [], '
        '"story_summary": "Story start", "arc_summary": "Arc start"}'
    )
    seed_res = await parser.parse_seed(json_seed)
    assert isinstance(seed_res, SeedResult)
    assert seed_res.story_summary == "Story start"


@pytest.mark.asyncio
async def test_llm_client_exponential_backoff_retry() -> None:
    """Test LLMClient retries up to max_retries on API failures."""
    settings = EnvSettings(max_retries=2, openai_api_key="mock-key")
    client = LLMClient(settings=settings)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Completion result"))]

    mock_create = AsyncMock(
        side_effect=[RuntimeError("API error 1"), RuntimeError("API error 2"), mock_response]
    )
    client.client.chat.completions.create = mock_create

    result = await client.complete("Test prompt")
    assert result == "Completion result"
    assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_llm_client_max_retries_exceeded() -> None:
    """Test LLMClient raises exception when retries are exhausted."""
    settings = EnvSettings(max_retries=1, openai_api_key="mock-key")
    client = LLMClient(settings=settings)

    mock_create = AsyncMock(side_effect=RuntimeError("Persistent API failure"))
    client.client.chat.completions.create = mock_create

    with pytest.raises(RuntimeError, match="Persistent API failure"):
        await client.complete("Test prompt")

    assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_prompt_based_parser() -> None:
    """Test PromptBasedParser parses JSON block output correctly."""
    parser = PromptBasedParser()

    # Translation
    json_trans = '{"translated_text": "Hello JSON.", "translator_notes": "None"}'
    trans_res = await parser.parse_translation(f"```json\\n{json_trans}\\n```")
    assert isinstance(trans_res, TranslationResult)
    assert trans_res.translated_text == "Hello JSON."
    assert trans_res.translator_notes == "None"

    # Seed JSON
    json_seed = (
        '{"characters": [], "terms": ['
        '  {"source": "test1", "target": "target1", "category": "concept", "confidence": "95%"},'
        '  {"source": "test2", "target": "target2", "category": "concept", "confidence": "high"},'
        '  {"source": "test3", "target": "target3", "category": "concept", "confidence": "low"}'
        '], "relationships": [], '
        '"story_summary": "Story start JSON", "arc_summary": "Arc start JSON"}'
    )
    seed_res = await parser.parse_seed(json_seed)
    assert isinstance(seed_res, SeedResult)
    assert seed_res.story_summary == "Story start JSON"
    assert seed_res.arc_summary == "Arc start JSON"
    assert len(seed_res.terms) == 3
    assert seed_res.terms[0].confidence == 0.95
    assert seed_res.terms[1].confidence == 1.0
    assert seed_res.terms[2].confidence == 0.5

    # Analysis JSON
    json_analysis = (
        '{"summary": "Analysis summary JSON", "key_events": ["Event 1"], '
        '"characters_present": ["character1"], "new_characters": [], "new_terms": [], '
        '"character_updates": [], '
        '"relationship_updates": [{'
        '  "character_1": "Daisy Fager", "character_2": "Head Maid", "description": "comrades"'
        '}], "significant_events": [], '
        '"qa_flags": [{'
        '  "issue_type": "Cultural", "description": "Watch your tone."'
        '}]}'
    )
    analysis_res = await parser.parse_analysis(json_analysis)
    assert isinstance(analysis_res, AnalysisResult)
    assert analysis_res.summary == "Analysis summary JSON"
    assert analysis_res.key_events == ["Event 1"]
    assert len(analysis_res.relationship_updates) == 1
    assert "Daisy Fager" in analysis_res.relationship_updates[0].characters
    assert "Head Maid" in analysis_res.relationship_updates[0].characters
    assert len(analysis_res.qa_flags) == 1
    assert analysis_res.qa_flags[0] == "Cultural: Watch your tone."

