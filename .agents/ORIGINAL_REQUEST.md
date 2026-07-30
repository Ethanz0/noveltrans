# Original User Request

## Initial Request — 2026-07-30T05:05:35Z

<USER_REQUEST>
Build `noveltrans`, a production-quality Python CLI tool for high-quality AI-powered Korean web novel translation with persistent context, enriched character modeling, glossary management, and EPUB output.

Working directory: /Users/ethanzhang/Documents/Personal/repositories/noveltrans
Integrity mode: development

## Requirements

### R1. Fully functional CLI tool

A Python CLI tool installable via `uv` that provides the following commands: `init`, `translate run`, `glossary seed`, `glossary show`, `glossary approve`, `style analyze`, `arc update`, `story update`, `epub build`, and `status`. Each command must work end-to-end as a standalone operation. The tool must use `typer` for the CLI framework and `rich` for console output.

### R2. Translation pipeline with persistent context

The translation pipeline must maintain persistent context across chapters using a 4-tier system: (1) global style guide + glossary entries, (2) story-level summary, (3) arc-level summary + recent chapter summaries, (4) last 2 full translated chapters. Each chapter translation must produce exactly 2 LLM calls: one for translation, one for merged post-translation analysis (term extraction + summary + events + QA flags). All state (glossary snapshots, chapter summaries, manifests, assembled prompts) must be persisted to disk after each chapter.

### R3. Enriched glossary with character modeling

The glossary must support: characters with multiple aliases (each alias having its own gender field for pronoun-aware translation), `knows_identity` tracking, `always_include` flag for major characters, relationship modeling (bidirectional, top-level), and non-character terms with confidence scores. Auto-extracted terms below a confidence threshold must go to a pending queue for manual review. Glossary matching must use Aho-Corasick for O(N) exact matching with fuzzy fallback for Korean text variants.

### R4. EPUB output

The tool must compile translated markdown chapters into valid EPUB3 files with metadata, table of contents, and CSS styling. Generic chapter titles ("Chapter 1", "Chapter 2", etc.). Must support partial builds (specific chapter ranges).

### R5. Robust state management and error handling

Translation runs must support resume from interruption (checkpoint system), force-retranslate individual chapters, and dry-run mode (show assembled prompts without LLM calls). QA issues must be logged to the manifest and displayed as console warnings but must never block translation. LLM calls must use exponential backoff with 3 retries, then stop the batch on persistent failure.

## Implementation Reference

The user has provided a comprehensive implementation specification that the team MUST follow. This includes:

- **Exact project structure** with specific file paths and module organization
- **Exact data models** (Pydantic v2) for glossary, state, manifest, and LLM response types
- **Exact CLI commands** with all options and flags
- **Exact pipeline flow** (14-step per-chapter process)
- **Exact dependencies** specified in pyproject.toml
- **Exact configuration** system (global + per-project .env layering via pydantic-settings)
- **Prompt templates** using Jinja2, shipped with the package and copied to projects on init
- **Output parsing** via strategy pattern (StructuredOutputParser / PromptBasedParser toggle)
- **Logging** via structlog with Rich console + JSON file output

The full implementation specification is provided below in the "Detailed Implementation Spec" section. The team should follow it as a blueprint, not just as guidance.

## Acceptance Criteria

### Project Setup
- [ ] `uv run noveltrans --help` displays all subcommands without errors
- [ ] `uv run basedpyright src/` passes with zero errors
- [ ] `uv run ruff check src/ tests/` passes with zero violations

### Init Command
- [ ] `noveltrans init ./test_project` creates the complete directory scaffold matching the spec (source/, output/txt/, output/epub/, state/summaries/, state/glossary_snapshots/, state/prompts/, prompts/)
- [ ] Default prompt templates are copied from the package's `prompts/` directory into the project's `prompts/` directory
- [ ] `project.json`, empty `glossary.json`, and starter `style_guide.md` are created

### Glossary System
- [ ] `uv run pytest tests/test_glossary_matcher.py -v` — all tests pass, covering: Aho-Corasick exact matching, fuzzy fallback matching, `always_include` characters always returned regardless of text match
- [ ] Glossary models match the spec: Character with aliases (per-alias gender), `knows_identity`, `always_include`; top-level Relationship; GlossaryTerm with confidence
- [ ] `glossary approve` merges pending_terms.json into glossary.json and clears the pending file

### Context Building
- [ ] `uv run pytest tests/test_context_builder.py -v` — all tests pass, covering: 4-tier assembly, correct number of recent chapters/summaries included, `always_include` characters injected

### Translation Pipeline
- [ ] `uv run pytest tests/test_checkpoint.py -v` — all tests pass, covering: save/load round-trip, resume from correct chapter
- [ ] `uv run pytest tests/test_manifest.py -v` — all tests pass, covering: per-chapter metadata tracking, QA issue storage, force-retranslate updates
- [ ] `--dry-run` flag saves assembled prompts to state/prompts/ without making LLM calls
- [ ] `--force` flag retranslates already-completed chapters with fresh glossary snapshot

### QA System
- [ ] `uv run pytest tests/test_qa_checker.py -v` — all tests pass, covering: untranslated Korean detection (regex [\uAC00-\uD7A3]+), repetition loop detection, hallucinated filler detection, missing glossary term detection
- [ ] QA issues are logged to manifest and displayed via `noveltrans status`, never block translation

### Prompt Rendering
- [ ] `uv run pytest tests/test_prompt_renderer.py -v` — all tests pass, covering: Jinja2 templates render with all context variables (per-alias gender, knows_identity, style guide, summaries, matched terms)

### EPUB
- [ ] `uv run pytest tests/test_epub_builder.py -v` — all tests pass, covering: valid EPUB3 output from markdown files, partial chapter builds, generic chapter titles
- [ ] `noveltrans epub build` produces a readable .epub file

### State Management
- [ ] Glossary snapshots saved per chapter in state/glossary_snapshots/
- [ ] Assembled prompts archived in state/prompts/
- [ ] Chapter summaries saved in state/summaries/
- [ ] Manifest tracks per-chapter metadata including QA issues and significant events

### Full Test Suite
- [ ] `uv run pytest tests/ -v` — ALL tests pass
- [ ] Tests use mocked LLM responses (no real API calls)

---

## Detailed Implementation Spec

> IMPORTANT: The following is the user's complete implementation blueprint. The team MUST follow this structure, these data models, and this pipeline design. Deviations are only acceptable if a technical constraint makes the spec impossible to implement as written.

### Dependencies (`pyproject.toml`)

```toml
[project]
name = "noveltrans"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15",
    "rich>=14",
    "pydantic>=2.10",
    "pydantic-settings>=2.8",
    "openai>=1.80",
    "jinja2>=3.1",
    "structlog>=25",
    "ebooklib>=0.18",
    "ahocorasick-rs>=0.22",
    "rapidfuzz>=3.12",
    "python-dotenv>=1.1",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=1",
    "ruff>=0.12",
    "basedpyright>=1.29",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH"]

[tool.basedpyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"

[project.scripts]
noveltrans = "noveltrans.cli.app:app"
```

### Project Structure

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

### Translation Project Directory (created by `noveltrans init`)

```
my_novel/
├── source/
├── output/
│   ├── txt/
│   └── epub/
├── state/
│   ├── checkpoint.json
│   ├── manifest.json
│   ├── summaries/
│   ├── story_summary.json
│   ├── arc_summary.json
│   ├── glossary_snapshots/
│   ├── prompts/
│   └── pending_terms.json
├── prompts/
│   ├── translator.jinja2
│   ├── analyzer.jinja2
│   ├── seeder.jinja2
│   ├── style_analyzer.jinja2
│   ├── arc_summary.jinja2
│   └── story_summary.jinja2
├── glossary.json
├── style_guide.md
├── project.json
└── .env
```

### Config Layer — `settings.py`

```python
class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("~/.config/noveltrans/.env", ".env"),
        env_file_encoding="utf-8",
    )
    openai_api_key: str
    openai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    model_name: str = "gemini-2.5-pro"
    temperature: float = 0.3
    max_retries: int = 3
    use_structured_output: bool = True
    log_level: str = "INFO"

class ProjectConfig(BaseModel):
    title: str
    author: str = ""
    source_language: str = "ko"
    target_language: str = "en"
    source_dir: str = "source"
    output_dir: str = "output"
    state_dir: str = "state"
    glossary_path: str = "glossary.json"
    style_guide_path: str = "style_guide.md"
    prompts_dir: str = "prompts"
    context_recent_chapters: int = 2
    context_recent_summaries: int = 5
    arc_summary_fallback_interval: int = 15
```

### Glossary Models — `glossary/models.py`

```python
class CharacterAlias(BaseModel):
    source: str          # Korean text
    target: str          # English translation
    gender: str          # Gender for THIS alias
    context: str         # When this alias is used
    alias_type: str = "name"  # name | title | nickname | disguise

class Character(BaseModel):
    id: str
    canonical_name: str
    aliases: list[CharacterAlias]
    gender: str
    speech_style: str
    appearance: str = ""
    knows_identity: list[str] = []
    always_include: bool = False
    notes: str = ""

class Relationship(BaseModel):
    characters: list[str]
    description: str
    since_chapter: int | None = None

class GlossaryTerm(BaseModel):
    source: str
    target: str
    category: str   # place | organization | title | concept | item | skill
    notes: str = ""
    confidence: float = 1.0

class Glossary(BaseModel):
    characters: list[Character] = []
    terms: list[GlossaryTerm] = []
    relationships: list[Relationship] = []
```

### State Models — `state/models.py`

```python
class QAIssue(BaseModel):
    issue_type: Literal["untranslated_korean", "missing_glossary_term", "repetition_loop",
                        "hallucinated_filler", "length_anomaly"]
    description: str
    severity: Literal["warning", "error"]

class SignificantEvent(BaseModel):
    event_type: Literal["identity_reveal", "power_reveal", "relationship_change",
                        "new_location", "major_conflict", "arc_transition"]
    description: str
    affects_characters: list[str]
    triggers_arc_update: bool

class ChapterManifestEntry(BaseModel):
    chapter_number: int
    status: Literal["pending", "in_progress", "completed", "failed"]
    translated_at: datetime | None = None
    model_used: str | None = None
    glossary_snapshot: str | None = None
    translation_duration_seconds: float = 0
    new_terms_extracted: int = 0
    force_retranslated: bool = False
    qa_issues: list[QAIssue] = []
    significant_events: list[SignificantEvent] = []

class TranslationManifest(BaseModel):
    project_title: str
    chapters: dict[int, ChapterManifestEntry] = {}
    last_translated_chapter: int = 0

class CheckpointData(BaseModel):
    last_completed_chapter: int
    current_batch: list[int] = []
    batch_start_time: datetime | None = None
```

### LLM Layer — `llm/protocols.py`

```python
class TranslationResult(BaseModel):
    translated_text: str
    translator_notes: str = ""

class AnalysisResult(BaseModel):
    summary: str
    key_events: list[str] = []
    characters_present: list[str] = []
    new_characters: list[Character] = []
    new_terms: list[GlossaryTerm] = []
    character_updates: list[dict] = []
    relationship_updates: list[Relationship] = []
    significant_events: list[SignificantEvent] = []
    qa_flags: list[str] = []

class SeedResult(BaseModel):
    characters: list[Character] = []
    terms: list[GlossaryTerm] = []
    relationships: list[Relationship] = []
    story_summary: str = ""
    arc_summary: str = ""

class ResponseParser(Protocol):
    async def parse_translation(self, raw: str) -> TranslationResult: ...
    async def parse_analysis(self, raw: str) -> AnalysisResult: ...
    async def parse_seed(self, raw: str) -> SeedResult: ...
```

Two implementations: `StructuredOutputParser` (OpenAI SDK `response_format`) and `PromptBasedParser` (XML-tagged plain text).

### Translation Pipeline — `core/translator.py`

Per-chapter flow (2 LLM calls per chapter):

1. Load chapter source text
2. Build 4-tier context (context_builder.py)
3. Match glossary terms in chapter (glossary/matcher.py)
4. Render translator prompt (llm/prompt_renderer.py)
5. [DRY RUN: save prompt and stop]
6. Call LLM — TRANSLATION
7. Parse translation response
8. Save translated chapter to output/txt/
9. Run local QA checks — no LLM (core/qa_checker.py)
10. Call LLM — ANALYSIS: extract terms + summary + events + QA flags
11. Process analysis results:
    a. High-confidence terms → auto-commit to glossary
    b. Low-confidence terms → append to pending_terms.json
    c. Character/relationship updates → auto-commit
    d. Save chapter summary
    e. If significant event triggers arc update → regenerate arc summary (extra LLM call)
    f. If chapters since last arc update >= 15 → fallback arc regeneration
12. Snapshot glossary
13. Save assembled prompts
14. Update manifest and checkpoint

### Context Builder — `core/context_builder.py`

4-tier context assembly:
- **Tier 1 (Global):** Style guide + matched glossary entries + `always_include` characters
- **Tier 2 (Story):** Overall story progression summary
- **Tier 3 (Arc):** Current arc summary + last 5 chapter summaries
- **Tier 4 (Immediate):** Last 2 full translated chapters

### Glossary Matcher — `glossary/matcher.py`

Two-stage matching:
1. Aho-Corasick (`ahocorasick-rs`): O(N) exact matching
2. Fuzzy fallback (`rapidfuzz`): 85% similarity threshold for Korean text variants

Output: filtered glossary subset for current chapter + `always_include` characters.

### QA Checker — `core/qa_checker.py`

No-LLM automated checks:
- Untranslated Korean detection (regex: [\uAC00-\uD7A3]+)
- Glossary term consistency check
- Output length range check
- Repetition loop detection (TF-IDF similarity)
- Hallucinated LLM filler phrase detection

### EPUB Builder — `epub/builder.py`

Uses `ebooklib`: EPUB3 with metadata, markdown→HTML conversion, CSS styling, generic chapter titles, partial builds.

### CLI Commands

- `noveltrans init <path>` — scaffold project
- `noveltrans translate run [--chapters TEXT] [--force] [--dry-run] [--project PATH]`
- `noveltrans glossary seed [--chapters TEXT] [--project PATH]`
- `noveltrans glossary show [--project PATH]`
- `noveltrans glossary approve [--project PATH]`
- `noveltrans style analyze [--chapters TEXT] [--project PATH]`
- `noveltrans arc update [--project PATH]`
- `noveltrans story update [--project PATH]`
- `noveltrans epub build [--chapters TEXT] [--title TEXT] [--author TEXT] [--project PATH]`
- `noveltrans status [--project PATH]`

### Prompt Templates

6 Jinja2 templates in `prompts/`: `translator.jinja2`, `analyzer.jinja2`, `seeder.jinja2`, `style_analyzer.jinja2`, `arc_summary.jinja2`, `story_summary.jinja2`. Copied to each project on init.

### Configuration

- Global: `~/.config/noveltrans/.env` (API key, base URL, model, temperature, retries, structured output toggle, log level)
- Per-project: `.env` overrides + `project.json` (title, author, languages, directory paths, context settings)

## Follow-up — 2026-07-30T23:01:41Z

<USER_REQUEST>
Build `noveltrans`, a production-quality Python CLI tool for high-quality AI-powered CJK (Korean, Japanese, Chinese) web novel translation with persistent context, enriched character modeling, glossary management, and EPUB output. The primary use case is Korean, but the tool must support Japanese and Chinese source texts as first-class languages.

Working directory: /Users/ethanzhang/Documents/Personal/repositories/noveltrans
Integrity mode: development

> IMPORTANT: A previous run already made significant progress on this project. Before writing any new files, INSPECT what already exists in the working directory and BUILD ON IT rather than starting from scratch. Previous progress included: Milestone 1 (foundation + models) was completed and audited. Core modules (glossary/matcher.py, glossary/manager.py, llm/client.py, llm/prompt_renderer.py, epub/builder.py, state/checkpoint.py, state/manifest.py) were built. Test suites for 7 modules were created. Continue from where the previous run left off.

## Requirements

### R1. Fully functional CLI tool

A Python CLI tool installable via `uv` that provides the following commands: `init`, `translate run`, `glossary seed`, `glossary show`, `glossary approve`, `style analyze`, `arc update`, `story update`, `epub build`, and `status`. Each command must work end-to-end as a standalone operation. The tool must use `typer` for the CLI framework and `rich` for console output. The `init` command must accept a `--language` option accepting `ko` (default), `ja`, or `zh` which sets `source_language` in `project.json`.

### R2. Translation pipeline with persistent context

The translation pipeline must maintain persistent context across chapters using a 4-tier system: (1) global style guide + glossary entries, (2) story-level summary, (3) arc-level summary + recent chapter summaries, (4) last 2 full translated chapters. Each chapter translation must produce exactly 2 LLM calls: one for translation, one for merged post-translation analysis (term extraction + summary + events + QA flags). All state (glossary snapshots, chapter summaries, manifests, assembled prompts) must be persisted to disk after each chapter.

### R3. Enriched glossary with character modeling

The glossary must support: characters with multiple aliases (each alias having its own gender field for pronoun-aware translation), `knows_identity` tracking, `always_include` flag for major characters, relationship modeling (bidirectional, top-level), and non-character terms with confidence scores. Auto-extracted terms below a confidence threshold must go to a pending queue for manual review. Glossary matching must use Aho-Corasick for O(N) exact matching with fuzzy fallback for Korean text variants.

### R4. EPUB output

The tool must compile translated markdown chapters into valid EPUB3 files with metadata, table of contents, and CSS styling. Generic chapter titles ("Chapter 1", "Chapter 2", etc.). Must support partial builds (specific chapter ranges).

### R5. Multi-language support (Korean, Japanese, Chinese)

All source-language-specific logic must be parameterized by `source_language` from `project.json`. Concretely: (1) The QA checker's untranslated-text detection must use language-appropriate Unicode ranges — Korean: `[\uAC00-\uD7A3]`, Japanese: `[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]`, Chinese: `[\u4E00-\u9FFF\u3400-\u4DBF]`. (2) All prompt templates must reference the source language dynamically (e.g., `{{ source_language_name }}`) rather than hardcoding "Korean". (3) Honorifics policy: for Japanese (`ja`), honorifics (e.g., -san, -sama, -kun, -chan, -sensei) must be preserved as-is; for Korean and Chinese, fully translate honorifics. This policy must be communicated to the LLM via the translator prompt template. (4) For Chinese (`zh`), the seeder and analyzer prompts should note the Simplified vs Traditional distinction and instruct the LLM to be consistent with the source text's variant.

### R6. Robust state management and error handling

Translation runs must support resume from interruption (checkpoint system), force-retranslate individual chapters, and dry-run mode (show assembled prompts without LLM calls). QA issues must be logged to the manifest and displayed as console warnings but must never block translation. LLM calls must use exponential backoff with 3 retries, then stop the batch on persistent failure.

## Implementation Reference

The user has provided a comprehensive implementation specification that the team MUST follow. This includes:

- **Exact project structure** with specific file paths and module organization
- **Exact data models** (Pydantic v2) for glossary, state, manifest, and LLM response types
- **Exact CLI commands** with all options and flags
- **Exact pipeline flow** (14-step per-chapter process)
- **Exact dependencies** specified in pyproject.toml
- **Exact configuration** system (global + per-project .env layering via pydantic-settings)
- **Prompt templates** using Jinja2, shipped with the package and copied to projects on init
- **Output parsing** via strategy pattern (StructuredOutputParser / PromptBasedParser toggle)
- **Logging** via structlog with Rich console + JSON file output

The full implementation specification is provided below in the "Detailed Implementation Spec" section. The team should follow it as a blueprint, not just as guidance.

## Acceptance Criteria

### Project Setup
- [ ] `uv run noveltrans --help` displays all subcommands without errors
- [ ] `uv run basedpyright src/` passes with zero errors
- [ ] `uv run ruff check src/ tests/` passes with zero violations

### Init Command
- [ ] `noveltrans init ./test_project` creates the complete directory scaffold matching the spec (source/, output/txt/, output/epub/, state/summaries/, state/glossary_snapshots/, state/prompts/, prompts/)
- [ ] Default prompt templates are copied from the package's `prompts/` directory into the project's `prompts/` directory
- [ ] `project.json`, empty `glossary.json`, and starter `style_guide.md` are created

### Glossary System
- [ ] `uv run pytest tests/test_glossary_matcher.py -v` — all tests pass, covering: Aho-Corasick exact matching, fuzzy fallback matching, `always_include` characters always returned regardless of text match
- [ ] Glossary models match the spec: Character with aliases (per-alias gender), `knows_identity`, `always_include`; top-level Relationship; GlossaryTerm with confidence
- [ ] `glossary approve` merges pending_terms.json into glossary.json and clears the pending file

### Context Building
- [ ] `uv run pytest tests/test_context_builder.py -v` — all tests pass, covering: 4-tier assembly, correct number of recent chapters/summaries included, `always_include` characters injected

### Translation Pipeline
- [ ] `uv run pytest tests/test_checkpoint.py -v` — all tests pass, covering: save/load round-trip, resume from correct chapter
- [ ] `uv run pytest tests/test_manifest.py -v` — all tests pass, covering: per-chapter metadata tracking, QA issue storage, force-retranslate updates
- [ ] `--dry-run` flag saves assembled prompts to state/prompts/ without making LLM calls
- [ ] `--force` flag retranslates already-completed chapters with fresh glossary snapshot

### Multi-language Support
- [ ] `noveltrans init ./test_ja --language ja` creates a project with `source_language: "ja"` in `project.json`
- [ ] `noveltrans init ./test_zh --language zh` creates a project with `source_language: "zh"` in `project.json`
- [ ] Translator prompt rendered for a `ja` project contains honorifics preservation instruction, not a "fully translate" instruction
- [ ] Translator prompt rendered for a `ko` project contains fully-translate-honorifics instruction

### QA System
- [ ] `uv run pytest tests/test_qa_checker.py -v` — all tests pass, covering: language-aware untranslated text detection (Korean regex for `ko` projects, Japanese regex for `ja` projects, Chinese regex for `zh` projects), repetition loop detection, hallucinated filler detection, missing glossary term detection
- [ ] QA issues are logged to manifest and displayed via `noveltrans status`, never block translation

### Prompt Rendering
- [ ] `uv run pytest tests/test_prompt_renderer.py -v` — all tests pass, covering: Jinja2 templates render with all context variables (per-alias gender, knows_identity, style guide, summaries, matched terms)

### EPUB
- [ ] `uv run pytest tests/test_epub_builder.py -v` — all tests pass, covering: valid EPUB3 output from markdown files, partial chapter builds, generic chapter titles
- [ ] `noveltrans epub build` produces a readable .epub file

### State Management
- [ ] Glossary snapshots saved per chapter in state/glossary_snapshots/
- [ ] Assembled prompts archived in state/prompts/
- [ ] Chapter summaries saved in state/summaries/
- [ ] Manifest tracks per-chapter metadata including QA issues and significant events

### Full Test Suite
- [ ] `uv run pytest tests/ -v` — ALL tests pass
- [ ] Tests use mocked LLM responses (no real API calls)

---

## Detailed Implementation Spec

> IMPORTANT: The following is the user's complete implementation blueprint. The team MUST follow this structure, these data models, and this pipeline design. Deviations are only acceptable if a technical constraint makes the spec impossible to implement as written.

### Dependencies (`pyproject.toml`)

```toml
[project]
name = "noveltrans"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15",
    "rich>=14",
    "pydantic>=2.10",
    "pydantic-settings>=2.8",
    "openai>=1.80",
    "jinja2>=3.1",
    "structlog>=25",
    "ebooklib>=0.18",
    "ahocorasick-rs>=0.22",
    "rapidfuzz>=3.12",
    "python-dotenv>=1.1",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=1",
    "ruff>=0.12",
    "basedpyright>=1.29",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH"]

[tool.basedpyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"

[project.scripts]
noveltrans = "noveltrans.cli.app:app"
```

### Project Structure

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

### Translation Project Directory (created by `noveltrans init`)

```
my_novel/
├── source/
├── output/
│   ├── txt/
│   └── epub/
├── state/
│   ├── checkpoint.json
│   ├── manifest.json
│   ├── summaries/
│   ├── story_summary.json
│   ├── arc_summary.json
│   ├── glossary_snapshots/
│   ├── prompts/
│   └── pending_terms.json
├── prompts/
│   ├── translator.jinja2
│   ├── analyzer.jinja2
│   ├── seeder.jinja2
│   ├── style_analyzer.jinja2
│   ├── arc_summary.jinja2
│   └── story_summary.jinja2
├── glossary.json
├── style_guide.md
├── project.json
└── .env
```

### Config Layer — `settings.py`

```python
class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("~/.config/noveltrans/.env", ".env"),
        env_file_encoding="utf-8",
    )
    openai_api_key: str
    openai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    model_name: str = "gemini-2.5-pro"
    temperature: float = 0.3
    max_retries: int = 3
    use_structured_output: bool = True
    log_level: str = "INFO"

class ProjectConfig(BaseModel):
    title: str
    author: str = ""
    source_language: str = "ko"  # ko | ja | zh
    target_language: str = "en"
    source_dir: str = "source"
    output_dir: str = "output"
    state_dir: str = "state"
    glossary_path: str = "glossary.json"
    style_guide_path: str = "style_guide.md"
    prompts_dir: str = "prompts"
    context_recent_chapters: int = 2
    context_recent_summaries: int = 5
    arc_summary_fallback_interval: int = 15
```

### Glossary Models — `glossary/models.py`

```python
class CharacterAlias(BaseModel):
    source: str          # Korean text
    target: str          # English translation
    gender: str          # Gender for THIS alias
    context: str         # When this alias is used
    alias_type: str = "name"  # name | title | nickname | disguise

class Character(BaseModel):
    id: str
    canonical_name: str
    aliases: list[CharacterAlias]
    gender: str
    speech_style: str
    appearance: str = ""
    knows_identity: list[str] = []
    always_include: bool = False
    notes: str = ""

class Relationship(BaseModel):
    characters: list[str]
    description: str
    since_chapter: int | None = None

class GlossaryTerm(BaseModel):
    source: str
    target: str
    category: str   # place | organization | title | concept | item | skill
    notes: str = ""
    confidence: float = 1.0

class Glossary(BaseModel):
    characters: list[Character] = []
    terms: list[GlossaryTerm] = []
    relationships: list[Relationship] = []
```

### State Models — `state/models.py`

```python
class QAIssue(BaseModel):
    issue_type: Literal["untranslated_korean", "missing_glossary_term", "repetition_loop",
                        "hallucinated_filler", "length_anomaly"]
    description: str
    severity: Literal["warning", "error"]

class SignificantEvent(BaseModel):
    event_type: Literal["identity_reveal", "power_reveal", "relationship_change",
                        "new_location", "major_conflict", "arc_transition"]
    description: str
    affects_characters: list[str]
    triggers_arc_update: bool

class ChapterManifestEntry(BaseModel):
    chapter_number: int
    status: Literal["pending", "in_progress", "completed", "failed"]
    translated_at: datetime | None = None
    model_used: str | None = None
    glossary_snapshot: str | None = None
    translation_duration_seconds: float = 0
    new_terms_extracted: int = 0
    force_retranslated: bool = False
    qa_issues: list[QAIssue] = []
    significant_events: list[SignificantEvent] = []

class TranslationManifest(BaseModel):
    project_title: str
    chapters: dict[int, ChapterManifestEntry] = {}
    last_translated_chapter: int = 0

class CheckpointData(BaseModel):
    last_completed_chapter: int
    current_batch: list[int] = []
    batch_start_time: datetime | None = None
```

### LLM Layer — `llm/protocols.py`

```python
class TranslationResult(BaseModel):
    translated_text: str
    translator_notes: str = ""

class AnalysisResult(BaseModel):
    summary: str
    key_events: list[str] = []
    characters_present: list[str] = []
    new_characters: list[Character] = []
    new_terms: list[GlossaryTerm] = []
    character_updates: list[dict] = []
    relationship_updates: list[Relationship] = []
    significant_events: list[SignificantEvent] = []
    qa_flags: list[str] = []

class SeedResult(BaseModel):
    characters: list[Character] = []
    terms: list[GlossaryTerm] = []
    relationships: list[Relationship] = []
    story_summary: str = ""
    arc_summary: str = ""

class ResponseParser(Protocol):
    async def parse_translation(self, raw: str) -> TranslationResult: ...
    async def parse_analysis(self, raw: str) -> AnalysisResult: ...
    async def parse_seed(self, raw: str) -> SeedResult: ...
```

Two implementations: `StructuredOutputParser` (OpenAI SDK `response_format`) and `PromptBasedParser` (XML-tagged plain text).

### Translation Pipeline — `core/translator.py`

Per-chapter flow (2 LLM calls per chapter):

1. Load chapter source text
2. Build 4-tier context (context_builder.py)
3. Match glossary terms in chapter (glossary/matcher.py)
4. Render translator prompt (llm/prompt_renderer.py)
5. [DRY RUN: save prompt and stop]
6. Call LLM — TRANSLATION
7. Parse translation response
8. Save translated chapter to output/txt/
9. Run local QA checks — no LLM (core/qa_checker.py)
10. Call LLM — ANALYSIS: extract terms + summary + events + QA flags
11. Process analysis results:
    a. High-confidence terms → auto-commit to glossary
    b. Low-confidence terms → append to pending_terms.json
    c. Character/relationship updates → auto-commit
    d. Save chapter summary
    e. If significant event triggers arc update → regenerate arc summary (extra LLM call)
    f. If chapters since last arc update >= 15 → fallback arc regeneration
12. Snapshot glossary
13. Save assembled prompts
14. Update manifest and checkpoint

### Context Builder — `core/context_builder.py`

4-tier context assembly:
- **Tier 1 (Global):** Style guide + matched glossary entries + `always_include` characters
- **Tier 2 (Story):** Overall story progression summary
- **Tier 3 (Arc):** Current arc summary + last 5 chapter summaries
- **Tier 4 (Immediate):** Last 2 full translated chapters

### Glossary Matcher — `glossary/matcher.py`

Two-stage matching:
1. Aho-Corasick (`ahocorasick-rs`): O(N) exact matching
2. Fuzzy fallback (`rapidfuzz`): 85% similarity threshold for Korean text variants

Output: filtered glossary subset for current chapter + `always_include` characters.

### QA Checker — `core/qa_checker.py`

No-LLM automated checks:
- Language-aware untranslated text detection using per-language Unicode ranges:
  - Korean (`ko`): `[\uAC00-\uD7A3]+`
  - Japanese (`ja`): `[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+`
  - Chinese (`zh`): `[\u4E00-\u9FFF\u3400-\u4DBF]+`
- Glossary term consistency check
- Output length range check
- Repetition loop detection (TF-IDF similarity)
- Hallucinated LLM filler phrase detection

### EPUB Builder — `epub/builder.py`

Uses `ebooklib`: EPUB3 with metadata, markdown→HTML conversion, CSS styling, generic chapter titles, partial builds.

### CLI Commands

- `noveltrans init <path> [--language ko|ja|zh]` — scaffold project (default: `ko`)
- `noveltrans translate run [--chapters TEXT] [--force] [--dry-run] [--project PATH]`
- `noveltrans glossary seed [--chapters TEXT] [--project PATH]`
- `noveltrans glossary show [--project PATH]`
- `noveltrans glossary approve [--project PATH]`
- `noveltrans style analyze [--chapters TEXT] [--project PATH]`
- `noveltrans arc update [--project PATH]`
- `noveltrans story update [--project PATH]`
- `noveltrans epub build [--chapters TEXT] [--title TEXT] [--author TEXT] [--project PATH]`
- `noveltrans status [--project PATH]`

### Prompt Templates

6 Jinja2 templates in `prompts/`: `translator.jinja2`, `analyzer.jinja2`, `seeder.jinja2`, `style_analyzer.jinja2`, `arc_summary.jinja2`, `story_summary.jinja2`. Copied to each project on init.

Templates must use `{{ source_language }}` and `{{ source_language_name }}` (e.g., "Korean", "Japanese", "Chinese") context variables rather than hardcoding the language. The `translator.jinja2` template must include a conditional honorifics block:
- If `source_language == "ja"`: preserve honorifics (-san, -sama, -kun, -chan, -sensei, etc.) as-is in the translation
- If `source_language in ("ko", "zh")`: fully translate all honorifics into natural English equivalents

For Chinese projects, `seeder.jinja2` and `analyzer.jinja2` should note the Simplified vs Traditional distinction and instruct the LLM to be consistent with the source text's variant.

### Configuration

- Global: `~/.config/noveltrans/.env` (API key, base URL, model, temperature, retries, structured output toggle, log level)
- Per-project: `.env` overrides + `project.json` (title, author, languages, directory paths, context settings)
</USER_REQUEST>
