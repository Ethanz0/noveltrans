"""CLI command for building EPUB3 files from translated markdown chapters."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from noveltrans.epub.builder import EPUBBuilder

epub_app = typer.Typer(help="EPUB generation commands")
console = Console()


@epub_app.command("build")
def epub_build(
    chapters: Annotated[
        str | None,
        typer.Option(
            "--chapters",
            "-c",
            help="Chapters to include (e.g. '1..10', '1,2,5')",
        ),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option(
            "--title",
            "-t",
            help="EPUB book title (overrides project.json title)",
        ),
    ] = None,
    author: Annotated[
        str | None,
        typer.Option(
            "--author",
            "-a",
            help="EPUB book author (overrides project.json author)",
        ),
    ] = None,
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Path to project root directory",
        ),
    ] = Path("."),
) -> None:
    """Build an EPUB3 file from translated markdown output chapters."""
    try:
        builder = EPUBBuilder(
            project_dir=project,
            title=title or "Untitled",
            author=author or "",
        )
        epub_path = builder.build(chapters=chapters)
        console.print(f"[bold green]Successfully built EPUB:[/] {epub_path}")
    except Exception as e:
        console.print(f"[bold red]Failed to build EPUB:[/] {e}")
        raise typer.Exit(code=1) from e
