"""Configuration models for env settings and project settings."""

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    """Global environment configuration loaded from ~/.config/noveltrans/.env and local .env."""

    model_config = SettingsConfigDict(
        env_file=("~/.config/noveltrans/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    model_name: str = "gemini-2.5-pro"
    temperature: float = 0.3
    max_retries: int = 3
    use_structured_output: bool = True
    log_level: str = "INFO"


class ProjectConfig(BaseModel):
    """Per-project configuration settings."""

    title: str
    author: str = ""
    source_language: str = "ko"
    target_language: str = "en"
    source_dir: str = "source"
    output_dir: str = "output"
    state_dir: str = "state"
    glossary_path: str = "glossary.json"
    style_guide_path: str = "style_guide.md"
    prompts_dir: str = "prompts"
    context_recent_chapters: int = 2
    context_recent_summaries: int = 5
    arc_summary_fallback_interval: int = 15
