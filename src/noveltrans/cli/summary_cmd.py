"""CLI commands for arc and story summary updates."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from noveltrans.core.analyzer import ChapterAnalyzer
from noveltrans.llm.client import OpenAIClient
from noveltrans.llm.prompt_renderer import PromptRenderer

arc_app = typer.Typer(help="Arc summary commands")
story_app = typer.Typer(help="Story summary commands")
summary_app = typer.Typer(help="Summary management commands")

console = Console()


@arc_app.command("update")
def arc_update(
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Path to project root directory",
        ),
    ] = Path("."),
) -> None:
    """Regenerate narrative arc summary from recent chapter summaries."""
    project_dir = project.resolve()
    if not project_dir.exists():
        console.print(f"[bold red]Project directory does not exist:[/] {project_dir}")
        raise typer.Exit(code=1)

    try:
        analyzer = ChapterAnalyzer(project_dir=project_dir)
        _ = analyzer.regenerate_arc_summary_sync()
        console.print("[bold green]Successfully updated arc summary.[/]")
    except Exception as e:
        console.print(f"[bold red]Failed to update arc summary:[/] {e}")
        raise typer.Exit(code=1) from e


@story_app.command("update")
def story_update(
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Path to project root directory",
        ),
    ] = Path("."),
) -> None:
    """Regenerate overall story summary from arc and chapter summaries."""
    project_dir = project.resolve()
    if not project_dir.exists():
        console.print(f"[bold red]Project directory does not exist:[/] {project_dir}")
        raise typer.Exit(code=1)

    try:
        state_dir = project_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)

        current_story = ""
        story_file = state_dir / "story_summary.json"
        if story_file.exists():
            with open(story_file, encoding="utf-8") as f:
                data = json.load(f)
                current_story = data.get("story_summary", "")

        arc_summary = ""
        arc_file = state_dir / "arc_summary.json"
        if arc_file.exists():
            with open(arc_file, encoding="utf-8") as f:
                data = json.load(f)
                arc_summary = data.get("arc_summary", "")

        prompts_path = project_dir / "prompts"
        renderer = PromptRenderer(prompts_path if prompts_path.exists() else None)
        prompt = renderer.render_story_summary(
            current_story_summary=current_story,
            arc_summary=arc_summary,
        )

        client = OpenAIClient()
        new_story = client.complete(prompt)
        if hasattr(new_story, "__await__"):
            import asyncio
            new_story = asyncio.run(new_story)  # pyright: ignore[reportGeneralTypeIssues]

        new_story_str = str(new_story)
        story_data = {"story_summary": new_story_str}
        story_file.write_text(
            json.dumps(story_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        console.print("[bold green]Successfully updated grand story summary.[/]")
    except Exception as e:
        console.print(f"[bold red]Failed to update story summary:[/] {e}")
        raise typer.Exit(code=1) from e


summary_app.add_typer(arc_app, name="arc")
summary_app.add_typer(story_app, name="story")
