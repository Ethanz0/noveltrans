import sys
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_project_env() -> None:
    """Dynamically load project-specific .env from command line args if specified."""
    project_path = None
    for idx, arg in enumerate(sys.argv):
        if arg in ("--project", "-p"):
            if idx + 1 < len(sys.argv):
                project_path = Path(sys.argv[idx + 1])
                break
        elif arg.startswith("--project="):
            project_path = Path(arg.split("=", 1)[1])
            break
        elif arg.startswith("-p="):
            project_path = Path(arg.split("=", 1)[1])
            break

    if project_path:
        env_file = (project_path.resolve() / ".env")
        if env_file.exists() and env_file.is_file():
            load_dotenv(env_file, override=True)


# Load project-specific env configuration before pydantic-settings initialization
load_project_env()


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
    analyzer_model_name: str | None = None
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
