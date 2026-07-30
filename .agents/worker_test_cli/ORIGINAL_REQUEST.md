## 2026-07-30T05:08:06Z
<USER_REQUEST>
You are worker_test_cli for noveltrans.
Working Directory: /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_test_cli

Mission:
1. Read `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/ORIGINAL_REQUEST.md` for CLI command specifications and requirements.
2. Implement integration test file `tests/test_cli.py`:
   - Use `typer.testing.CliRunner` to test the Typer CLI app (`noveltrans.cli.app:app`).
   - Comprehensive test cases for all subcommands:
     * `noveltrans init <path>` (creates scaffold, copies prompt templates, generates project.json, empty glossary.json, starter style_guide.md)
     * `noveltrans status [--project PATH]` (displays chapter status, QA warnings)
     * `noveltrans translate run [--chapters TEXT] [--force] [--dry-run] [--project PATH]` (dry-run saves prompts to state/prompts/, force retranslates)
     * `noveltrans glossary seed [--chapters TEXT] [--project PATH]`
     * `noveltrans glossary show [--project PATH]`
     * `noveltrans glossary approve [--project PATH]` (merges pending_terms.json into glossary.json and clears pending file)
     * `noveltrans style analyze [--chapters TEXT] [--project PATH]`
     * `noveltrans arc update [--project PATH]`
     * `noveltrans story update [--project PATH]`
     * `noveltrans epub build [--chapters TEXT] [--title TEXT] [--author TEXT] [--project PATH]`
   - Follow 4-tier testing methodology:
     * Tier 1: Feature coverage (>=5 tests per command / group)
     * Tier 2: Boundary & Corner cases (invalid paths, non-existent projects, bad chapter ranges, missing flags, corrupt json)
     * Tier 3: Cross-command interactions (init -> seed -> approve -> translate --dry-run -> status -> epub build)
     * Tier 4: Real-world workflow integration scenarios
3. Ensure all tests use mock LLM responses where applicable and fixtures from `conftest.py`.
4. Verify syntax via `uv run pytest tests/test_cli.py --collect-only` or `uv run python -m py_compile tests/test_cli.py`.
5. Write handoff report in `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_test_cli/handoff.md`.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
</USER_REQUEST>
