"""Style analyzer for generating and updating translation style guides."""

import asyncio
from pathlib import Path
from typing import Any

from noveltrans.llm.client import OpenAIClient
from noveltrans.llm.prompt_renderer import PromptRenderer


class StyleAnalyzer:
    """Analyzes source text samples to generate and update style guide rules."""

    def __init__(
        self,
        llm_client: Any = None,
        prompt_renderer: PromptRenderer | None = None,
        project_dir: Path | str | None = None,
        style_guide_path: Path | str | None = None,
    ) -> None:
        self.llm_client = llm_client or OpenAIClient()
        self.project_dir = Path(project_dir) if project_dir else None

        if style_guide_path:
            self.style_guide_path = Path(style_guide_path)
        elif self.project_dir:
            self.style_guide_path = self.project_dir / "style_guide.md"
        else:
            self.style_guide_path = Path("style_guide.md")

        if prompt_renderer is not None:
            self.prompt_renderer = prompt_renderer
        elif self.project_dir and (self.project_dir / "prompts").exists():
            self.prompt_renderer = PromptRenderer(self.project_dir / "prompts")
        else:
            self.prompt_renderer = PromptRenderer()

    async def analyze_style(
        self,
        sample_text: str,
        update_file: bool = True,
    ) -> str:
        """Run LLM style analyzer call on sample text."""
        prompt = self.prompt_renderer.render_style_analyzer(sample_text=sample_text)

        import inspect

        raw_res = self.llm_client.complete(prompt)
        if inspect.isawaitable(raw_res):
            res_val = await raw_res
            style_guide = str(res_val)
        else:
            style_guide = str(raw_res)

        if update_file:
            self.save_style_guide(style_guide)

        return style_guide

    def analyze_style_sync(
        self,
        sample_text: str,
        update_file: bool = True,
    ) -> str:
        """Synchronous wrapper for analyze_style()."""
        return asyncio.run(self.analyze_style(sample_text, update_file=update_file))

    def save_style_guide(self, style_guide_content: str) -> None:
        """Save style guide content to style_guide_path."""
        self.style_guide_path.parent.mkdir(parents=True, exist_ok=True)
        self.style_guide_path.write_text(style_guide_content, encoding="utf-8")
