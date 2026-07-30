# Project: noveltrans

## Architecture
`noveltrans` is a production-quality Python CLI tool for AI-powered Korean web novel translation.
It maintains persistent multi-tier context across chapter translations, enriches character/term modeling, logs QA anomalies, and compiles output into styled EPUB3 files.

### Modules:
1. `noveltrans.config`: Pydantic settings loading global `~/.config/noveltrans/.env` and per-project `.env` / `project.json`.
2. `noveltrans.glossary`: Models (`Character`, `CharacterAlias`, `Relationship`, `GlossaryTerm`, `Glossary`), manager, and Aho-Corasick + RapidFuzz matcher.
3. `noveltrans.state`: State models (`ChapterManifestEntry`, `TranslationManifest`, `CheckpointData`, `QAIssue`, `SignificantEvent`), `CheckpointManager`, and `ManifestManager`.
4. `noveltrans.llm`: LLM client wrapper (OpenAI SDK), `ResponseParser` protocols (`StructuredOutputParser`, `PromptBasedParser`), and Jinja2 prompt renderer.
5. `noveltrans.core`: Core translation pipeline (`translator.py`), 4-tier context builder (`context_builder.py`), chapter analyzer (`analyzer.py`), glossary seeder (`seeder.py`), style analyzer (`style_analyzer.py`), and non-LLM QA checker (`qa_checker.py`).
6. `noveltrans.epub`: EPUB3 compiler using `ebooklib` (`builder.py`).
7. `noveltrans.cli`: Typer CLI application (`app.py`) with subcommands (`init`, `translate`, `glossary`, `style`, `arc`, `story`, `epub`, `status`).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Requirement-driven test suite (Tiers 1-4) & `TEST_READY.md` | None | DONE |
| 1 | Foundation & Models | `pyproject.toml`, `settings.py`, `glossary/models.py`, `state/models.py`, prompt templates | None | DONE |
| 2 | Glossary System | `glossary/manager.py`, `glossary/matcher.py`, `core/seeder.py` | M1 | DONE |
| 3 | LLM Layer & Context Builder | `llm/client.py`, `llm/protocols.py`, `llm/prompt_renderer.py`, `core/context_builder.py` | M1 | DONE |
| 4 | Core Pipeline & QA | `core/translator.py`, `core/analyzer.py`, `core/qa_checker.py`, `core/style_analyzer.py`, `state/checkpoint.py`, `state/manifest.py` | M1, M2, M3 | DONE |
| 5 | EPUB Builder | `epub/builder.py` | M1 | DONE |
| 6 | CLI Interface & Multi-Language (R5) | `cli/app.py` and all subcommands (`init_cmd`, `translate_cmd`, `glossary_cmd`, `epub_cmd`, `style_cmd`, `summary_cmd`, `status_cmd`) | M1-M5 | DONE |
| 7 | Integration & Hardening | 100% E2E test pass (169 tests) + R5 multi-language support + Forensic Audit | M6, E2E | DONE |

## Interface Contracts

### Glossary ↔ Context Builder / Translator
- `GlossaryMatcher.match_terms(text: str, glossary: Glossary) -> tuple[list[Character], list[GlossaryTerm]]`
- `ContextBuilder.build_context(chapter_num: int, source_text: str, glossary: Glossary, ...) -> AssembledContext`

### LLM Layer ↔ Core Translator
- `LLMClient.complete(prompt: str, system_prompt: str = "") -> str`
- `ResponseParser.parse_translation(raw: str) -> TranslationResult`
- `ResponseParser.parse_analysis(raw: str) -> AnalysisResult`
- `ResponseParser.parse_seed(raw: str) -> SeedResult`

### State Management ↔ Translator
- `CheckpointManager.load_checkpoint() -> CheckpointData`
- `CheckpointManager.save_checkpoint(data: CheckpointData) -> None`
- `ManifestManager.update_chapter(entry: ChapterManifestEntry) -> None`

## Code Layout
```
noveltrans/
├── pyproject.toml
├── .env.example
├── README.md
├── src/
│   └── noveltrans/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── init_cmd.py
│       │   ├── translate_cmd.py
│       │   ├── glossary_cmd.py
│       │   ├── epub_cmd.py
│       │   ├── style_cmd.py
│       │   ├── summary_cmd.py
│       │   └── status_cmd.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── translator.py
│       │   ├── context_builder.py
│       │   ├── analyzer.py
│       │   ├── seeder.py
│       │   ├── style_analyzer.py
│       │   └── qa_checker.py
│       ├── glossary/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── manager.py
│       │   └── matcher.py
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── protocols.py
│       │   └── prompt_renderer.py
│       ├── epub/
│       │   ├── __init__.py
│       │   └── builder.py
│       ├── state/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── checkpoint.py
│       │   └── manifest.py
│       └── config/
│           ├── __init__.py
│           └── settings.py
├── prompts/
│   ├── translator.jinja2
│   ├── analyzer.jinja2
│   ├── seeder.jinja2
│   ├── style_analyzer.jinja2
│   ├── arc_summary.jinja2
│   └── story_summary.jinja2
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_glossary_matcher.py
    ├── test_context_builder.py
    ├── test_checkpoint.py
    ├── test_manifest.py
    ├── test_qa_checker.py
    ├── test_prompt_renderer.py
    └── test_epub_builder.py
```
