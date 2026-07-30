## 2026-07-30T05:08:01Z

You are worker_test_core for noveltrans.
Working Directory: /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_test_core

Mission:
1. Read `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/ORIGINAL_REQUEST.md` for exact data models, functions, requirements, and test specs.
2. Implement unit test files in `tests/`:
   - `tests/test_glossary_matcher.py` (covering Aho-Corasick exact matching, fuzzy fallback matching at 85% threshold, `always_include` character injection, 4-tier test methodology with >=5 tests for Tier 1 & Tier 2)
   - `tests/test_context_builder.py` (covering 4-tier context assembly, recent chapters/summaries count configuration, `always_include` character injection, 4-tier test methodology)
   - `tests/test_checkpoint.py` (covering checkpoint save/load round-trip, resume from chapter, batch state handling, 4-tier test methodology)
   - `tests/test_manifest.py` (covering chapter metadata tracking, QA issue storage, force-retranslate behavior, manifest stats updates, 4-tier test methodology)
   - `tests/test_qa_checker.py` (covering untranslated Korean regex [\uAC00-\uD7A3]+ detection, repetition loop detection, hallucinated filler, missing glossary terms, non-blocking warning/error logging)
   - `tests/test_prompt_renderer.py` (covering Jinja2 template rendering with per-alias gender, knows_identity, style guide, summaries, matched terms)
   - `tests/test_epub_builder.py` (covering EPUB3 creation from markdown, generic chapter titles, partial chapter builds, table of contents, CSS styling)

3. Structure tests cleanly using `pytest` conventions, importing fixtures from `conftest.py`.
4. Run syntax verification via `uv run pytest tests/ --collect-only` or `uv run python -m py_compile tests/test_*.py`.
5. Write a completion handoff report in `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_test_core/handoff.md`.
