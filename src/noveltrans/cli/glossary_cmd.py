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
from noveltrans.llm.client import OpenAIClient
from noveltrans.llm.prompt_renderer import PromptRenderer
from rich.prompt import Prompt

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
    update_summaries: Annotated[
        bool,
        typer.Option(
            "--update-summaries",
            help="Overwrite story and arc summaries even if they already exist",
        ),
    ] = False,
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
        seeder.seed_from_files(target_files, save_to_project=True, update_summaries=update_summaries)
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


@glossary_app.command("review")
def glossary_review(
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Path to project root directory",
        ),
    ] = Path("."),
    skip_llm: Annotated[
        bool,
        typer.Option(
            "--skip-llm",
            help="Skip LLM alternative generation for faster manual review",
        ),
    ] = False,
) -> None:
    """Review and lock in new glossary terms and characters interactively."""
    import asyncio
    project_dir = project.resolve()
    if not project_dir.exists():
        console.print(f"[bold red]Project directory does not exist:[/] {project_dir}")
        raise typer.Exit(code=1)

    manager = GlossaryManager(project_dir=project_dir)
    try:
        glossary = manager.load_glossary()
    except Exception as e:
        console.print(f"[bold red]Failed to load glossary.json:[/] {e}")
        raise typer.Exit(code=1)

    unreviewed_terms = [t for t in glossary.terms if not t.reviewed]
    unreviewed_chars = [c for c in glossary.characters if not c.reviewed or any(not a.reviewed for a in c.aliases)]

    if not unreviewed_terms and not unreviewed_chars:
        console.print("[bold green]All glossary terms and characters are already reviewed![/]")
        return

    console.print(f"[bold cyan]Found {len(unreviewed_terms)} unreviewed term(s) and {len(unreviewed_chars)} unreviewed character(s).[/]\n")

    llm_client = OpenAIClient() if not skip_llm else None
    prompt_renderer = PromptRenderer() if not skip_llm else None

    items_to_review = []
    for term in unreviewed_terms:
        items_to_review.append({
            "source_term": term.source,
            "current_translation": term.target,
            "category": term.category,
            "type": "term",
            "obj": term,
        })
    for char in unreviewed_chars:
        if not char.reviewed:
            items_to_review.append({
                "source_term": char.id,
                "current_translation": char.canonical_name,
                "category": "Character Name",
                "type": "char",
                "obj": char,
            })
        for alias in char.aliases:
            if not alias.reviewed:
                items_to_review.append({
                    "source_term": alias.source,
                    "current_translation": alias.target,
                    "category": f"Character Alias ({char.canonical_name})",
                    "type": "alias",
                    "obj": alias,
                    "char": char,
                })

    alternatives_map = {}
    if llm_client and prompt_renderer and items_to_review:
        with console.status(f"Generating alternatives for {len(items_to_review)} items..."):
            chunk_size = 20
            for i in range(0, len(items_to_review), chunk_size):
                chunk = items_to_review[i:i + chunk_size]
                prompt = prompt_renderer.render_term_alternatives(items=chunk)
                try:
                    res = asyncio.run(llm_client.parse_term_alternatives(prompt))
                    if res and res.results:
                        alternatives_map.update(res.results)
                except Exception as e:
                    console.print(f"[red]Failed to generate alternatives for chunk: {e}[/]")

    rejected_chars = set()

    for item in items_to_review:
        is_char = item["type"] == "char"
        is_alias = item["type"] == "alias"
        
        if is_alias and item["char"].id in rejected_chars:
            continue
            
        if is_char:
            char = item["obj"]
            console.print(f"\n[bold magenta]Character:[/] {char.canonical_name} (ID: {char.id})")
            console.print(f"[italic]Gender:[/] {char.gender} | [italic]Speech:[/] {char.speech_style}")
        elif is_alias:
            alias = item["obj"]
            char = item["char"]
            console.print(f"\n[bold magenta]Character Alias for {char.canonical_name}:[/] {alias.source} -> {alias.target}")
            console.print(f"[italic]Context:[/] {alias.context}")
        else:
            term = item["obj"]
            console.print(f"\n[bold yellow]Term:[/] {term.source} -> {term.target}")
            console.print(f"[italic]Category:[/] {term.category}")
        
        source_key = item["source_term"]
        alts = alternatives_map.get(source_key, [])

        for i, alt in enumerate(alts, 1):
            console.print(f"  [[cyan]{i}[/]] {alt}")
            
        choice = Prompt.ask(
            "Select alternative [Enter to keep current, 1/2/3, type 'x' to reject, or type custom]",
            default="",
            show_default=False
        )
        
        if choice.lower() == 'x':
            if is_char:
                if item["obj"] in glossary.characters:
                    glossary.characters.remove(item["obj"])
                rejected_chars.add(item["obj"].id)
                console.print("[red]Rejected character and its aliases.[/]")
            elif is_alias:
                if item["obj"] in item["char"].aliases:
                    item["char"].aliases.remove(item["obj"])
                console.print("[red]Rejected alias.[/]")
            else:
                if item["obj"] in glossary.terms:
                    glossary.terms.remove(item["obj"])
                console.print("[red]Rejected term.[/]")
            continue
        
        if choice:
            if choice.isdigit() and 1 <= int(choice) <= len(alts):
                new_val = alts[int(choice) - 1]
            else:
                new_val = choice
                
            if is_char:
                item["obj"].canonical_name = new_val
            else:
                item["obj"].target = new_val
        
        item["obj"].reviewed = True
        console.print(f"[green]Saved as:[/] {item['obj'].canonical_name if is_char else item['obj'].target}")

    manager.save_glossary(glossary)
    console.print("\n[bold green]Review complete! Saved to glossary.json.[/]")
