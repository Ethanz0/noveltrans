"""OpenAI client wrapper for noveltrans LLM operations."""

import asyncio
from typing import Any, cast

from openai import AsyncOpenAI

from noveltrans.config.settings import EnvSettings
from noveltrans.llm.protocols import (
    AnalysisResult,
    PromptBasedParser,
    ResponseParser,
    SeedResult,
    StructuredOutputParser,
    TranslationResult,
)


class LLMClient:
    """LLM client wrapper supporting OpenAI / Gemini OpenAI-compatible API endpoints."""

    def __init__(
        self,
        settings: EnvSettings | None = None,
        parser: ResponseParser | None = None,
    ) -> None:
        self.settings = settings or EnvSettings()
        api_key = self.settings.openai_api_key or "mock-key"
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.settings.openai_base_url,
        )
        if parser is not None:
            self.parser = parser
        elif self.settings.use_structured_output:
            self.parser = StructuredOutputParser()
        else:
            self.parser = PromptBasedParser()

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        response_format: Any = None,
    ) -> str:
        """Execute completion call with exponential backoff retry logic."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.settings.model_name,
            "temperature": self.settings.temperature,
            "messages": messages,
            "max_tokens": 8192,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        max_retries = max(0, self.settings.max_retries)
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                return content or ""
            except Exception as e:
                last_exception = e
                if attempt >= max_retries:
                    raise e
                await asyncio.sleep(2**attempt * 0.5)

        if last_exception:
            raise last_exception
        return ""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate raw completion string."""
        system_prompt = cast("str", kwargs.pop("system_prompt", ""))
        response_format = kwargs.pop("response_format", None)
        return await self.complete(
            prompt,
            system_prompt=system_prompt,
            response_format=response_format,
        )

    async def _execute_with_parse_retry(
        self, parse_func: Any, prompt: str, system_prompt: str = ""
    ) -> Any:
        import structlog
        logger = structlog.get_logger()
        last_error = None
        max_attempts = max(1, self.settings.max_retries + 1)
        for attempt in range(max_attempts):
            try:
                raw = await self.complete(prompt, system_prompt=system_prompt)
                return await parse_func(raw)
            except Exception as e:
                last_error = e
                if attempt < max_attempts - 1:
                    logger.warning("llm_parse_retry", attempt=attempt + 1, error=str(e))
                    await asyncio.sleep(1)
        raise last_error or Exception("Failed to parse LLM output")

    async def parse_translation(
        self, prompt: str, system_prompt: str = ""
    ) -> TranslationResult:
        """Execute translation LLM call and parse result."""
        return await self._execute_with_parse_retry(
            self.parser.parse_translation, prompt, system_prompt
        )

    async def parse_analysis(
        self, prompt: str, system_prompt: str = ""
    ) -> AnalysisResult:
        """Execute analysis LLM call and parse result."""
        return await self._execute_with_parse_retry(
            self.parser.parse_analysis, prompt, system_prompt
        )

    async def parse_seed(
        self, prompt: str, system_prompt: str = ""
    ) -> SeedResult:
        """Execute seeding LLM call and parse result."""
        return await self._execute_with_parse_retry(
            self.parser.parse_seed, prompt, system_prompt
        )

    async def parse_term_alternatives(
        self, prompt: str, system_prompt: str = ""
    ) -> "TermAlternativesResult":
        """Execute term alternatives LLM call and parse result."""
        from noveltrans.llm.protocols import TermAlternativesResult
        
        return await self._execute_with_parse_retry(
            self.parser.parse_term_alternatives, prompt, system_prompt
        )


OpenAIClient = LLMClient

