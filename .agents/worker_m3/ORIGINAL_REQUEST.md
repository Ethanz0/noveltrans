## 2026-07-30T05:09:36Z
You are the LLM Layer & Context Builder Worker for noveltrans (Milestone 3).
Working Directory: /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_m3
Parent Conversation ID: 16dd66f1-bb4c-4ce2-a9f2-262bf935b0a2

Mission: Implement Milestone 3 according to the technical spec in /Users/ethanzhang/Documents/Personal/repositories/noveltrans/ORIGINAL_REQUEST.md.

Scope of work:
1. `src/noveltrans/llm/client.py`:
   - `LLMClient`: Wrapper around OpenAI SDK (`openai.AsyncOpenAI` or `OpenAI`). Reads `EnvSettings` (base URL, API key, model, temperature, max_retries). Implements exponential backoff with retry up to `max_retries` (default 3 retries).
2. `src/noveltrans/llm/protocols.py`:
   - Data models: `TranslationResult` (translated_text, translator_notes), `AnalysisResult` (summary, key_events, characters_present, new_characters, new_terms, character_updates, relationship_updates, significant_events, qa_flags), `SeedResult` (characters, terms, relationships, story_summary, arc_summary).
   - `ResponseParser` Protocol.
   - `StructuredOutputParser`: Parses LLM output using OpenAI response_format / JSON schemas.
   - `PromptBasedParser`: Parses LLM output from XML tags (e.g. `<translation>`, `<summary>`, `<terms>`, `<events>`, `<qa_flags>`).
3. `src/noveltrans/llm/prompt_renderer.py`:
   - `PromptRenderer`: Loads Jinja2 templates from package `prompts/` or project `prompts/` directory. Renders prompt templates (`translator.jinja2`, `analyzer.jinja2`, `seeder.jinja2`, `style_analyzer.jinja2`, `arc_summary.jinja2`, `story_summary.jinja2`) with all context variables.
4. `src/noveltrans/core/context_builder.py`:
   - `ContextBuilder`: Assembles 4-tier context for translation:
     - Tier 1 (Global): Global style guide (`style_guide.md`) + matched glossary entries (characters with per-alias gender, terms, relationships) + `always_include` characters.
     - Tier 2 (Story): Story-level summary (`story_summary.json`).
     - Tier 3 (Arc): Arc-level summary (`arc_summary.json`) + recent chapter summaries (up to `context_recent_summaries` chapters, default 5).
     - Tier 4 (Immediate): Last full translated chapters (up to `context_recent_chapters` chapters, default 2).

Verification steps:
1. Run `uv run basedpyright src/` (must pass 0 errors)
2. Run `uv run ruff check src/` (must pass 0 violations)

Write handoff.md in /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_m3/handoff.md with execution and verification outputs, and send a message back to parent (16dd66f1-bb4c-4ce2-a9f2-262bf935b0a2).

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
