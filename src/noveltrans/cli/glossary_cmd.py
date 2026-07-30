"""CLI commands for managing glossary (seed, show, approve)."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from noveltrans.cli.translate_cmd import parse_chapters
from noveltrans.core.seeder import GlossarySeeder
from noveltrans.glossary.manager import GlossaryManager
from noveltrans.glossary.models import GlossaryTerm

glossary_app = typer.Typer(help="Glossary management commands")
console = Console()


@glossary_app.command("seed")
def glossary_seed(
    chapters: Annotated[
        str | None,
        typer.Option(
            "--chapters",
            "-c",
            help="Chapters to sample for seeding (e.g. '1', '1-3')",
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
    """Extract initial glossary terms and story summaries from source chapters."""
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
        console.print("[bold yellow]No source chapters found for seeding.[/]")
        return

    try:
        seeder = GlossarySeeder(project_dir=project_dir)
        seeder.seed_from_files(target_files, save_to_project=True)
        console.print(
            f"[bold green]Successfully seeded glossary from {len(target_files)} chapter(s).[/]"
        )
    except Exception as e:
        console.print(f"[bold red]Glossary seeding failed:[/] {e}")
        raise typer.Exit(code=1) from e


@glossary_app.command("show")
def glossary_show(
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Path to project root directory",
        ),
    ] = Path("."),
) -> None:
    """Display current characters and terms from project glossary.json."""
    project_dir = project.resolve()
    if not project_dir.exists():
        console.print(f"[bold red]Project directory does not exist:[/] {project_dir}")
        raise typer.Exit(code=1)

    manager = GlossaryManager(project_dir=project_dir)
    try:
        glossary = manager.load_glossary()
    except Exception as e:
        console.print(f"[bold red]Failed to load glossary.json:[/] {e}")
        raise typer.Exit(code=1) from e

    console.print(f"[bold cyan]Glossary for project:[/] {project_dir.name}\n")

    # Characters Table
    char_table = Table(title="Characters", show_header=True, header_style="bold magenta")
    char_table.add_column("Canonical Name", style="bold green")
    char_table.add_column("Gender", style="yellow")
    char_table.add_column("Speech Style")
    char_table.add_column("Aliases")

    for char in glossary.characters:
        aliases_str = ", ".join([f"{a.source} -> {a.target}" for a in char.aliases])
        char_table.add_row(
            char.canonical_name,
            char.gender,
            char.speech_style,
            aliases_str or "-",
        )

    console.print(char_table)
    console.print()

    # Terms Table
    term_table = Table(title="Glossary Terms", show_header=True, header_style="bold cyan")
    term_table.add_column("Source", style="bold green")
    term_table.add_column("Target", style="bold blue")
    term_table.add_column("Category", style="yellow")
    term_table.add_column("Notes")

    for term in glossary.terms:
        term_table.add_row(term.source, term.target, term.category, term.notes or "-")

    console.print(term_table)


@glossary_app.command("approve")
def glossary_approve(
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Path to project root directory",
        ),
    ] = Path("."),
) -> None:
    """Approve and merge pending terms from state/pending_terms.json into glossary.json."""
    project_dir = project.resolve()
    if not project_dir.exists():
        console.print(f"[bold red]Project directory does not exist:[/] {project_dir}")
        raise typer.Exit(code=1)

    pending_file = project_dir / "state" / "pending_terms.json"
    if not pending_file.exists():
        console.print("[bold yellow]No pending terms file found.[/]")
        return

    try:
        content = pending_file.read_text(encoding="utf-8")
        pending_data = json.loads(content)
    except Exception as e:
        console.print(f"[bold red]Failed to parse pending_terms.json:[/] {e}")
        raise typer.Exit(code=1) from e

    if not pending_data or not isinstance(pending_data, list):
        console.print("[bold yellow]No pending terms to approve.[/]")
        pending_file.write_text("[]", encoding="utf-8")
        return

    manager = GlossaryManager(project_dir=project_dir)
    glossary = manager.load_glossary()

    existing_sources = {t.source for t in glossary.terms}
    approved_count = 0

    for item in pending_data:
        if isinstance(item, dict) and "source" in item and "target" in item:
            term = GlossaryTerm(
                source=str(item["source"]),
                target=str(item["target"]),
                category=str(item.get("category", "general")),
                notes=str(item.get("notes", "")),
                confidence=float(item.get("confidence", 1.0)),
            )
            if term.source not in existing_sources:
                glossary.terms.append(term)
                existing_sources.add(term.source)
            else:
                for idx, existing in enumerate(glossary.terms):
                    if existing.source == term.source:
                        glossary.terms[idx] = term
                        break
            approved_count += 1

    manager.save_glossary(glossary)
    pending_file.write_text("[]", encoding="utf-8")

    console.print(
        f"[bold green]Successfully approved and merged {approved_count} "
        "pending term(s) into glossary.json.[/]"
    )
