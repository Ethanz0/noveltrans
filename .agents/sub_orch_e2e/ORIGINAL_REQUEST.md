# Original User Request

## 2026-07-30T05:07:28Z

<USER_REQUEST>
You are the E2E Testing Track Orchestrator for noveltrans.
Working Directory: /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/sub_orch_e2e
Parent Conversation ID: 16dd66f1-bb4c-4ce2-a9f2-262bf935b0a2

Mission: Build a complete, opaque-box, requirement-driven unit and integration test suite in tests/ matching all user acceptance criteria and technical specifications in /Users/ethanzhang/Documents/Personal/repositories/noveltrans/ORIGINAL_REQUEST.md.

Methodology:
- 4-Tier test structure (Tier 1: Feature coverage >=5 per feature; Tier 2: Boundary/corner cases >=5 per feature; Tier 3: Pairwise cross-feature interactions; Tier 4: Real-world application scenarios).
- Opaque-box: Exercise features via public API / functions / CLI entry points without relying on internal implementation details. Mock all LLM calls using pytest fixtures.

Required test files in tests/:
- tests/__init__.py
- tests/conftest.py (fixtures for temp directories, mock LLM responses, sample glossary data, sample manifests)
- tests/test_glossary_matcher.py (Aho-Corasick exact matching, fuzzy fallback matching at 85% threshold, always_include character injection)
- tests/test_context_builder.py (4-tier context assembly, recent chapters/summaries, always_include injection)
- tests/test_checkpoint.py (checkpoint save/load round-trip, resume from chapter)
- tests/test_manifest.py (chapter metadata tracking, QA issue storage, force-retranslate behavior)
- tests/test_qa_checker.py (untranslated Korean detection with regex [\uAC00-\uD7A3]+, repetition loop detection, hallucinated filler, missing glossary terms)
- tests/test_prompt_renderer.py (Jinja2 template rendering with context variables)
- tests/test_epub_builder.py (EPUB3 creation from markdown, generic chapter titles, partial chapter builds)
- tests/test_cli.py (CLI commands integration tests: init, status, translate dry-run, glossary approve, etc.)

Deliverables:
1. Create /Users/ethanzhang/Documents/Personal/repositories/noveltrans/TEST_INFRA.md detailing feature inventory, test philosophy, test architecture, and coverage thresholds.
2. Implement all test files in tests/ using uv run pytest conventions.
3. Publish /Users/ethanzhang/Documents/Personal/repositories/noveltrans/TEST_READY.md with coverage summary once all test cases are written.
4. Verify by running `uv run pytest tests/ -v` (Note: tests requiring full implementation may fail initially until implementation milestones complete; ensure tests themselves are syntactically valid, properly structured, and correctly assert against expected models/interfaces).
5. Write handoff.md in /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/sub_orch_e2e/handoff.md and notify parent (16dd66f1-bb4c-4ce2-a9f2-262bf935b0a2).

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All test implementations and fixtures must be genuine.
</USER_REQUEST>
