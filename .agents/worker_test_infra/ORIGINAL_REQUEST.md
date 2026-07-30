## 2026-07-30T05:07:48Z

<USER_REQUEST>
You are worker_test_infra for noveltrans.
Working Directory: /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_test_infra

Mission:
1. Read `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/ORIGINAL_REQUEST.md` to understand all specs, data models (Pydantic v2), CLI commands, configuration, and test requirements.
2. Create `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/TEST_INFRA.md` matching the specifications in ORIGINAL_REQUEST.md. It must include:
   - Test Philosophy (opaque-box, requirement-driven, mock LLM calls)
   - Feature Inventory (all CLI commands, translation pipeline, glossary system, context building, QA system, prompt rendering, EPUB builder, state management)
   - 4-Tier Test Architecture methodology & criteria
   - Real-world Application Scenarios (Tier 4)
   - Coverage Thresholds and Feature Checklist
3. Create `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/tests/__init__.py`.
4. Create `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/tests/conftest.py` containing comprehensive, genuine pytest fixtures:
   - `temp_project_dir`: Scaffolds a full temporary project structure (source/, output/txt, output/epub, state/summaries, state/glossary_snapshots, state/prompts, prompts/, glossary.json, project.json, style_guide.md, .env).
   - `mock_llm_client` / `mock_openai_response`: Mocks OpenAI async client or LLM client calls to return valid JSON/text for translation (TranslationResult), analysis (AnalysisResult), and seeding (SeedResult) without calling real APIs.
   - `sample_glossary`: Returns a fully-populated Pydantic `Glossary` object with `Character` (with `CharacterAlias`, `gender`, `knows_identity`, `always_include`), `GlossaryTerm` (with `confidence`), and `Relationship`.
   - `sample_manifest`: Returns a `TranslationManifest` with `ChapterManifestEntry`, `QAIssue`, and `SignificantEvent`.
   - `sample_checkpoint`: Returns `CheckpointData`.
   - `sample_project_config` & `sample_env_settings`: Return `ProjectConfig` and `EnvSettings`.
   - `sample_jinja_templates`: Sets up temporary Jinja2 templates (translator.jinja2, analyzer.jinja2, etc.).
5. Run syntax check / test runner on `tests/conftest.py` using `run_command` (e.g. `uv run pytest tests/ --collect-only` or `uv run python -m py_compile tests/conftest.py`).
6. Write a completion handoff in `/Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_test_infra/handoff.md`.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
</USER_REQUEST>
