## 2026-07-30T13:16:44Z
You are the worker agent assigned to complete Milestone 6 (CLI Interface) and R5 (Multi-Language Support) for `noveltrans`.

Working directory: `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_m6_r5`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Inspect existing code under `src/noveltrans/`, prompt templates in `prompts/`, and tests in `tests/`.
2. Implement full CLI interface in `src/noveltrans/cli/`:
   - `app.py`: Main Typer CLI app entrypoint with rich console and subcommands (`init`, `translate`, `glossary`, `epub`, `style`, `summary`, `status`).
   - `init_cmd.py`: `noveltrans init <path> [--language ko|ja|zh]`. Scaffold project directories, create `project.json` with `source_language`, copy prompt templates from package into project `prompts/`, create starter `glossary.json` and `style_guide.md`.
   - `translate_cmd.py`: `noveltrans translate run [--chapters TEXT] [--force] [--dry-run] [--project PATH]`.
   - `glossary_cmd.py`: `noveltrans glossary seed [--chapters TEXT] [--project PATH]`, `noveltrans glossary show [--project PATH]`, `noveltrans glossary approve [--project PATH]`.
   - `epub_cmd.py`: `noveltrans epub build [--chapters TEXT] [--title TEXT] [--author TEXT] [--project PATH]`.
   - `style_cmd.py`: `noveltrans style analyze [--chapters TEXT] [--project PATH]`.
   - `summary_cmd.py`: `noveltrans arc update [--project PATH]`, `noveltrans story update [--project PATH]`.
   - `status_cmd.py`: `noveltrans status [--project PATH]`.
3. Implement R5 Multi-Language Support (Korean `ko`, Japanese `ja`, Chinese `zh`):
   - In `src/noveltrans/config/settings.py`: `source_language: str = "ko"` in `ProjectConfig`.
   - In `src/noveltrans/core/qa_checker.py`: Parameterize untranslated-text regex by `source_language`:
     - Korean (`ko`): `[\uAC00-\uD7A3]+`
     - Japanese (`ja`): `[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+`
     - Chinese (`zh`): `[\u4E00-\u9FFF\u3400-\u4DBF]+`
   - In `prompts/` templates:
     - Use `{{ source_language_name }}` (e.g. "Korean", "Japanese", "Chinese") dynamically instead of hardcoding "Korean".
     - In `translator.jinja2`: Honorifics policy: for Japanese (`ja`), instruct preserving honorifics (e.g. -san, -sama, -kun, -chan, -sensei) as-is; for Korean/Chinese, instruct fully translating honorifics.
     - In `seeder.jinja2` and `analyzer.jinja2`: For Chinese (`zh`), include a note on Simplified vs Traditional Chinese consistency.
4. Update and expand tests in `tests/`:
   - `test_qa_checker.py`: Add test cases for Korean, Japanese, and Chinese untranslated text detection based on project `source_language`.
   - `test_prompt_renderer.py`: Add test cases verifying multi-language prompt rendering (Japanese honorifics preservation vs Korean/Chinese full translation instruction, source language name parameterization).
   - CLI tests: Add tests for `noveltrans init ./test_ja --language ja` and `noveltrans init ./test_zh --language zh` verifying `source_language` in `project.json`.
5. Run Quality Verification Gates using `run_command`:
   - `uv run noveltrans --help`
   - `uv run basedpyright src/`
   - `uv run ruff check src/ tests/`
   - `uv run pytest tests/ -v`
   Ensure ALL 4 pass with ZERO errors / violations.
6. Write a comprehensive `handoff.md` in your working directory `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_m6_r5/handoff.md` detailing all implemented files, R5 changes, test results, and command outputs. Then send a message to parent with your handoff summary.
