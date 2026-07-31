"""CLI command for displaying noveltrans project status."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from noveltrans.config.settings import ProjectConfig
from noveltrans.glossary.manager import GlossaryManager
from noveltrans.state.checkpoint import CheckpointManager
from noveltrans.state.manifest import ManifestManager

status_app = typer.Typer(help="Project status commands")
console = Console()


@status_app.command("status")
def status_cmd(
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Path to project root directory",
        ),
    ] = Path("."),
) -> None:
    """Display translation progress, manifest entries, glossary stats, and QA warnings."""
    project_dir = project.resolve()
    if not project_dir.exists():
        console.print(f"[bold red]Project directory does not exist:[/] {project_dir}")
        raise typer.Exit(code=1)

    # 1. Load project config
    config_path = project_dir / "project.json"
    if config_path.exists():
        try:
            config = ProjectConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
        except Exception:
            config = ProjectConfig(title=project_dir.name)
    else:
        config = ProjectConfig(title=project_dir.name)

    # 2. Count source files & output files
    source_dir = project_dir / config.source_dir
    source_files = sorted(source_dir.glob("*.txt")) if source_dir.exists() else []

    output_dir = project_dir / config.output_dir / "txt"
    output_files = sorted(output_dir.glob("*.txt")) if output_dir.exists() else []

    # 3. Load manifest and checkpoint
    manifest_mgr = ManifestManager(
        project_dir / config.state_dir / "manifest.json",
        project_title=config.title,
    )
    manifest = manifest_mgr.load_manifest()

    chk_mgr = CheckpointManager(project_dir / config.state_dir / "checkpoint.json")
    checkpoint = chk_mgr.load_checkpoint()

    # 4. Load glossary & pending terms
    gloss_mgr = GlossaryManager(project_dir=project_dir)
    try:
        glossary = gloss_mgr.load_glossary()
        char_count = len(glossary.characters)
        term_count = len(glossary.terms)
    except Exception:
        char_count = 0
        term_count = 0

    unreviewed_count = 0
    try:
        unreviewed_count += sum(1 for c in glossary.characters if not c.reviewed)
        unreviewed_count += sum(1 for t in glossary.terms if not t.reviewed)
    except Exception:
        pass

    # Render header panel
    lang_text = f"{config.source_language.upper()} -> {config.target_language.upper()}"
    gloss_text = f"{char_count} character(s), {term_count} term(s), {unreviewed_count} unreviewed"
    header_text = (
        f"[bold cyan]Project:[/] {config.title}\n"
        f"[bold cyan]Language:[/] {lang_text}\n"
        f"[bold cyan]Source Chapters:[/] {len(source_files)}\n"
        f"[bold cyan]Translated Files:[/] {len(output_files)}\n"
        f"[bold cyan]Last Checkpoint Chapter:[/] {checkpoint.last_completed_chapter or 'None'}\n"
        f"[bold cyan]Glossary:[/] {gloss_text}"
    )
    console.print(Panel(header_text, title="noveltrans Project Status", expand=False))

    # Render Manifest Chapter Table
    if manifest.chapters:
        table = Table(title="Chapter Manifest", show_header=True, header_style="bold blue")
        table.add_column("Chapter", justify="right", style="bold green")
        table.add_column("Status", style="magenta")
        table.add_column("Model Used")
        table.add_column("Duration (s)", justify="right")
        table.add_column("QA Issues", style="yellow")

        for ch_num in sorted(manifest.chapters.keys()):
            entry = manifest.chapters[ch_num]
            qa_summary = "-"
            if entry.qa_issues:
                qa_summary = ", ".join([f"{i.issue_type}({i.severity})" for i in entry.qa_issues])
            dur_str = (
                f"{entry.translation_duration_seconds:.1f}"
                if entry.translation_duration_seconds
                else "-"
            )
            table.add_row(
                str(entry.chapter_number),
                entry.status,
                entry.model_used or "-",
                dur_str,
                qa_summary,
            )
        console.print(table)
    else:
        console.print("[dim]No manifest entries recorded yet.[/]")
