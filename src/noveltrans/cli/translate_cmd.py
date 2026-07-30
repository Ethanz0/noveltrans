"""CLI command for running novel translation pipeline."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from noveltrans.core.translator import TranslationPipeline

translate_app = typer.Typer(help="Translation execution commands")
console = Console()


def parse_chapters(chapters_str: str | None) -> list[int] | None:
    """Parse chapter selection string into a sorted list of integer chapter numbers."""
    if not chapters_str or chapters_str.strip().lower() == "all":
        return None

    selected: set[int] = set()
    parts = chapters_str.strip().split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        try:
            if ".." in part:
                start_str, end_str = part.split("..", 1)
                selected.update(range(int(start_str.strip()), int(end_str.strip()) + 1))
            elif "-" in part and not part.startswith("-"):
                start_str, end_str = part.split("-", 1)
                selected.update(range(int(start_str.strip()), int(end_str.strip()) + 1))
            elif part.lstrip("-").isdigit():
                val = int(part)
                if val > 0:
                    selected.add(val)
        except Exception:
            continue

    return sorted(list(selected)) if selected else None


@translate_app.command("run")
def translate_run(
    chapters: Annotated[
        str | None,
        typer.Option(
            "--chapters",
            "-c",
            help="Chapters to translate (e.g. '1', '1-5', '1..5', '1,2,5')",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force re-translation of previously completed chapters",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Render and save prompts without calling LLM APIs",
        ),
    ] = False,
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Path to project root directory",
        ),
    ] = Path("."),
) -> None:
    """Run translation pipeline for chapters in source directory."""
    project_dir = project.resolve()
    if not project_dir.exists():
        console.print(f"[bold red]Project directory does not exist:[/] {project_dir}")
        raise typer.Exit(code=1)

    try:
        ch_list = parse_chapters(chapters)
        pipeline = TranslationPipeline(project_dir=project_dir)
        entries = pipeline.translate_batch_sync(
            chapter_numbers=ch_list,
            force=force,
            dry_run=dry_run,
        )
        msg_prefix = (
            "[bold yellow]Dry-run completed[/]"
            if dry_run
            else "[bold green]Translation batch completed[/]"
        )
        console.print(f"{msg_prefix}: Processed {len(entries)} chapter(s).")
    except Exception as e:
        console.print(f"[bold red]Translation failed:[/] {e}")
        raise typer.Exit(code=1) from e
