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
async def test_prompt_based_parser() -> None:
    """Test PromptBasedParser parses XML tagged output correctly."""
    parser = PromptBasedParser()

    # Translation
    xml_trans = (
        "<translation>Sung Jinwoo fought the beast.</translation>"
        "<notes>Translated smoothly.</notes>"
    )
    trans_res = await parser.parse_translation(xml_trans)
    assert trans_res.translated_text == "Sung Jinwoo fought the beast."
    assert trans_res.translator_notes == "Translated smoothly."

    # Analysis
    xml_analysis = """
    <summary>Jinwoo defeated the dungeon boss.</summary>
    <key_events>
    - Defeated boss
    - Acquired dagger
    </key_events>
    <characters_present>sung_jinwoo</characters_present>
    <qa_flags>None</qa_flags>
    """
    analysis_res = await parser.parse_analysis(xml_analysis)
    assert analysis_res.summary == "Jinwoo defeated the dungeon boss."
    assert "Defeated boss" in analysis_res.key_events
    assert "sung_jinwoo" in analysis_res.characters_present

    # Seed
    xml_seed = """
    <story_summary>Overarching story</story_summary>
    <arc_summary>Opening arc</arc_summary>
    """
    seed_res = await parser.parse_seed(xml_seed)
    assert seed_res.story_summary == "Overarching story"
    assert seed_res.arc_summary == "Opening arc"


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
