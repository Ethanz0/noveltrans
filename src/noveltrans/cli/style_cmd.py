"""CLI command for style guide analysis."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from noveltrans.cli.translate_cmd import parse_chapters
from noveltrans.core.style_analyzer import StyleAnalyzer

style_app = typer.Typer(help="Style guide management commands")
console = Console()


@style_app.command("analyze")
def style_analyze(
    chapters: Annotated[
        str | None,
        typer.Option(
            "--chapters",
            "-c",
            help="Chapters to sample for style analysis (e.g. '1', '1-3')",
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
    """Analyze source chapters and update style_guide.md."""
    project_dir = project.resolve()
    if not project_dir.exists():
        console.print(f"[bold red]Project directory does not exist:[/] {project_dir}")
        raise typer.Exit(code=1)

    source_dir = project_dir / "source"
    if not source_dir.exists():
        console.print(f"[bold red]Source directory missing:[/] {source_dir}")
        raise typer.Exit(code=1)

    ch_nums = parse_chapters(chapters)
    files = sorted(source_dir.glob("*.txt"))
    target_files: list[Path] = []
    for f in files:
        num_str = "".join(filter(str.isdigit, f.stem))
        if num_str:
            n = int(num_str)
            if ch_nums is None or n in ch_nums:
                target_files.append(f)

    if not target_files:
        sample_text = "Sample text for style guide analysis."
    else:
        sample_text = "\n\n---\n\n".join([f.read_text(encoding="utf-8") for f in target_files])

    try:
        analyzer = StyleAnalyzer(project_dir=project_dir)
        analyzer.analyze_style_sync(sample_text, update_file=True)
        console.print(
            f"[bold green]Successfully updated style guide at:[/] {analyzer.style_guide_path}"
        )
    except Exception as e:
        console.print(f"[bold red]Style analysis failed:[/] {e}")
        raise typer.Exit(code=1) from e
