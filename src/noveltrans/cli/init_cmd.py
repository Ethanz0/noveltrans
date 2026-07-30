"""CLI command for initializing noveltrans project workspace."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from noveltrans.config.settings import ProjectConfig

init_app = typer.Typer(help="Initialize translation project workspace")
console = Console()


def copy_prompt_templates(target_dir: Path) -> None:
    """Copy default prompt Jinja2 templates into target directory."""
    target_dir.mkdir(parents=True, exist_ok=True)

    possible_sources = [
        Path(__file__).resolve().parents[3] / "prompts",
        Path(__file__).resolve().parents[2] / "prompts",
        Path.cwd() / "prompts",
    ]
    source_prompts_dir: Path | None = None
    for src in possible_sources:
        if src.is_dir() and any(src.glob("*.jinja2")):
            source_prompts_dir = src
            break

    if source_prompts_dir:
        for tpl in source_prompts_dir.glob("*.jinja2"):
            dest = target_dir / tpl.name
            dest.write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        default_templates = {
            "translator.jinja2": (
                "You are an expert translator specializing in "
                "{{ source_language_name | default('Korean') }} web novel translation."
            ),
            "analyzer.jinja2": "Analyze chapter...",
            "seeder.jinja2": "Extract characters...",
            "style_analyzer.jinja2": "Generate style guide...",
            "arc_summary.jinja2": "Summarize arc...",
            "story_summary.jinja2": "Summarize story...",
        }
        for name, content in default_templates.items():
            dest = target_dir / name
            dest.write_text(content, encoding="utf-8")


@init_app.command("init")
def init_cmd(
    path: Annotated[
        Path,
        typer.Argument(
            ...,
            help="Path to directory for initializing noveltrans project",
        ),
    ],
    language: Annotated[
        str,
        typer.Option(
            "--language",
            "-l",
            help="Source language of web novel (ko, ja, zh)",
        ),
    ] = "ko",
) -> None:
    """Initialize project directory structure and config files."""
    lang = language.lower().strip()
    if lang not in ("ko", "ja", "zh"):
        console.print(
            f"[bold red]Unsupported source language:[/] {language}. Supported: ko, ja, zh."
        )
        raise typer.Exit(code=1)

    project_dir = path.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    subdirs = [
        project_dir / "source",
        project_dir / "output" / "txt",
        project_dir / "output" / "epub",
        project_dir / "state" / "summaries",
        project_dir / "state" / "glossary_snapshots",
        project_dir / "state" / "prompts",
        project_dir / "prompts",
    ]
    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)

    copy_prompt_templates(project_dir / "prompts")

    project_title = project_dir.name or "Untitled Web Novel"
    config = ProjectConfig(
        title=project_title,
        author="",
        source_language=lang,
        target_language="en",
    )
    (project_dir / "project.json").write_text(
        config.model_dump_json(indent=2), encoding="utf-8"
    )

    glossary_data = {
        "characters": [],
        "terms": [],
        "relationships": [],
    }
    (project_dir / "glossary.json").write_text(
        json.dumps(glossary_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    style_guide_content = (
        f"# {project_title} - Translation Style Guide\n\n"
        "## Tone & Register\n"
        "Maintain natural, fluent narrative prose appropriate for modern web novels.\n\n"
        "## Naming & Title Conventions\n"
        "Preserve character name consistency and follow glossary specifications.\n\n"
        "## Formatting Rules\n"
        "- Use italics for internal monologue.\n"
        "- Use bracket notation for system status notifications.\n"
    )
    (project_dir / "style_guide.md").write_text(style_guide_content, encoding="utf-8")

    env_content = (
        "# noveltrans project environment configuration\n"
        "OPENAI_API_KEY=\n"
        "OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/\n"
        "MODEL_NAME=gemini-2.5-pro\n"
    )
    (project_dir / ".env").write_text(env_content, encoding="utf-8")

    (project_dir / "state" / "pending_terms.json").write_text("[]", encoding="utf-8")

    console.print(
        f"[bold green]Successfully initialized noveltrans project:[/] {project_dir}"
    )
