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

    async def parse_translation(
        self, prompt: str, system_prompt: str = ""
    ) -> TranslationResult:
        """Execute translation LLM call and parse result."""
        raw = await self.complete(prompt, system_prompt=system_prompt)
        return await self.parser.parse_translation(raw)

    async def parse_analysis(
        self, prompt: str, system_prompt: str = ""
    ) -> AnalysisResult:
        """Execute analysis LLM call and parse result."""
        raw = await self.complete(prompt, system_prompt=system_prompt)
        return await self.parser.parse_analysis(raw)

    async def parse_seed(
        self, prompt: str, system_prompt: str = ""
    ) -> SeedResult:
        """Execute seeding LLM call and parse result."""
        raw = await self.complete(prompt, system_prompt=system_prompt)
        return await self.parser.parse_seed(raw)


OpenAIClient = LLMClient

