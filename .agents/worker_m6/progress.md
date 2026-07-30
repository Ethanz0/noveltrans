## Current Status
Last visited: 2026-07-30T05:19:05Z

- [ ] Implement CLI subcommands and main app in src/noveltrans/cli/:
  - [ ] src/noveltrans/cli/app.py (Typer app entrypoint and subcommands mounting)
  - [ ] src/noveltrans/cli/init_cmd.py (`noveltrans init <path>`)
  - [ ] src/noveltrans/cli/translate_cmd.py (`noveltrans translate run [--chapters TEXT] [--force] [--dry-run] [--project PATH]`)
  - [ ] src/noveltrans/cli/glossary_cmd.py (`noveltrans glossary seed`, `show`, `approve`)
  - [ ] src/noveltrans/cli/epub_cmd.py (`noveltrans epub build`)
  - [ ] src/noveltrans/cli/style_cmd.py (`noveltrans style analyze`)
  - [ ] src/noveltrans/cli/summary_cmd.py (`noveltrans arc update`, `story update`)
  - [ ] src/noveltrans/cli/status_cmd.py (`noveltrans status`)
- [ ] Run basedpyright and ruff check verification
- [ ] Verify `uv run noveltrans --help`
- [ ] Write handoff.md
