# TEST_INFRA.md — NovelTrans Test Infrastructure & Verification Architecture

## 1. Test Philosophy

`noveltrans` is an AI-powered Korean web novel translation engine that handles multi-chapter persistence, context building, glossary resolution, automated QA, and EPUB compilation. The test infrastructure strictly enforces three core testing principles:

1. **Opaque-Box Testing**: Tests verify public CLI interfaces, output artifacts (markdown, JSON manifests, EPUB files), and Pydantic model contracts without relying on internal private state or monkey-patching implementation details.
2. **Requirement-Driven Verification**: Every test case directly maps to specific functional requirements (R1–R5) and detailed specifications outlined in `ORIGINAL_REQUEST.md`.
3. **Deterministic Mock LLM Strategy**: Zero real external network calls. LLM responses for translation (`TranslationResult`), post-translation analysis (`AnalysisResult`), and initial seeding (`SeedResult`) are mock-driven, returning structured JSON/text models under varied conditions (valid outputs, edge cases, schema variations, retry failures).

---

## 2. Feature Inventory

The test suite systematically exercises every feature module in `noveltrans`:

| Feature Module | Responsibilities & Test Scope | Key Artifacts / Models |
| :--- | :--- | :--- |
| **CLI Commands** | Execution of `init`, `translate run`, `glossary seed`, `glossary show`, `glossary approve`, `style analyze`, `arc update`, `story update`, `epub build`, `status`. Options, defaults, error flags, exit codes. | Typer CLI runner, exit codes, stdout/stderr formatting via Rich |
| **Translation Pipeline** | 14-step per-chapter pipeline execution, 2 LLM calls per chapter (translation + merged analysis), dry-run flag, force-retranslate flag, retry logic on LLM failure. | `translator.py`, `analyzer.py`, `output/txt/*.md`, `state/prompts/` |
| **Glossary System** | Enriched character modeling (aliases with per-alias gender, `knows_identity`, `always_include`), top-level `Relationship`, `GlossaryTerm` confidence scores, auto-commit vs pending queue approval workflow, two-stage matcher (Aho-Corasick exact + rapidfuzz fuzzy fallback). | `Glossary`, `Character`, `CharacterAlias`, `Relationship`, `GlossaryTerm`, `glossary.json`, `pending_terms.json` |
| **Context Building** | 4-tier context assembly: Tier 1 (Style guide + matched terms + `always_include`), Tier 2 (Story summary), Tier 3 (Arc summary + 5 recent chapter summaries), Tier 4 (Last 2 full translated chapters). | `context_builder.py`, `state/summaries/`, `story_summary.json`, `arc_summary.json` |
| **QA System** | Deterministic non-LLM checks: untranslated Korean regex (`[\uAC00-\uD7A3]+`), missing glossary terms, repetition loops (TF-IDF), hallucinated filler phrases, output length anomaly. Manifest logging. | `qa_checker.py`, `QAIssue`, `state/manifest.json` |
| **Prompt Rendering** | Jinja2 template rendering for 6 core templates (`translator`, `analyzer`, `seeder`, `style_analyzer`, `arc_summary`, `story_summary`) with context variables. | `prompt_renderer.py`, `prompts/*.jinja2` |
| **EPUB Builder** | Compilation of translated markdown chapters into valid EPUB3 files with metadata, table of contents, CSS styling, generic titles ("Chapter X"), and partial chapter range filtering. | `epub/builder.py`, `output/epub/*.epub`, `ebooklib` |
| **State Management** | Atomic persistence: `CheckpointData` (save/load/resume), `TranslationManifest` (`ChapterManifestEntry`, `QAIssue`, `SignificantEvent`), per-chapter glossary snapshots, prompt archiving. | `checkpoint.json`, `manifest.json`, `state/glossary_snapshots/` |

---

## 3. 4-Tier Test Architecture

The `noveltrans` verification methodology is organized into four distinct tiers:

```
+-------------------------------------------------------------------+
| Tier 4: Real-world Application Scenarios (Multi-chapter lifecycle) |
+-------------------------------------------------------------------+
| Tier 3: End-to-End CLI & Pipeline Integration                     |
+-------------------------------------------------------------------+
| Tier 2: Component Interactions & State Persistence                |
+-------------------------------------------------------------------+
| Tier 1: Isolated Unit Tests (Data Models, Parsers, Algorithms)    |
+-------------------------------------------------------------------+
```

### Tier 1: Unit Tests
- **Focus**: Pure logic, data model validation, string/regex utilities, individual Jinja2 template renders.
- **Components**:
  - `Glossary`, `Character`, `CharacterAlias`, `GlossaryTerm`, `Relationship` Pydantic v2 validation.
  - `ChapterManifestEntry`, `TranslationManifest`, `CheckpointData`, `QAIssue`, `SignificantEvent` serialization.
  - `EnvSettings` and `ProjectConfig` default values and .env override logic.
  - `qa_checker.py` rules (untranslated Korean regex, repetition loop scoring, filler phrase matching).
  - Aho-Corasick trie construction & rapidfuzz ratio calculation in `matcher.py`.
- **Criteria**: Fast execution (<0.01s per test), zero filesystem/I/O side effects, 100% deterministic.

### Tier 2: Component Integration Tests
- **Focus**: Cross-module interactions, disk state round-tripping, context assembly.
- **Components**:
  - `ContextBuilder`: Assembly of 4 tiers, verifying correct number of recent chapter summaries (5) and recent full chapters (2) are injected, plus `always_include` characters.
  - `GlossaryManager`: Adding terms, merging low-confidence terms into `pending_terms.json`, approving pending terms into `glossary.json`.
  - `Checkpoint` and `Manifest`: Save/load round-trips, updating status from `pending` -> `in_progress` -> `completed`, recording duration and QA issues.
  - `PromptRenderer`: Variable injection into Jinja2 templates for translator and analyzer prompts.
- **Criteria**: Disk reads/writes confined to isolated `temp_project_dir` fixtures.

### Tier 3: CLI & System Integration Tests
- **Focus**: Full CLI command invocations via `typer.testing.CliRunner`.
- **Commands Tested**:
  - `noveltrans init <path>`: Verifies full directory scaffold creation, default Jinja2 template copying, `project.json`, empty `glossary.json`, `style_guide.md`.
  - `noveltrans translate run --dry-run`: Verifies assembled prompts saved to `state/prompts/` without invoking mock LLM.
  - `noveltrans translate run --force`: Retranslates existing chapters and updates manifest entries.
  - `noveltrans glossary approve`: Merges `pending_terms.json` into `glossary.json` and clears pending queue.
  - `noveltrans epub build --chapters 1-3`: Generates readable `.epub` artifact containing selected chapters.
  - `noveltrans status`: Displays Rich status table summarizing chapter progress and logged QA issues.
- **Criteria**: Tests execute complete CLI commands, check return code == 0, and verify expected stdout text and filesystem artifacts.

### Tier 4: Real-world Application Scenarios
- **Focus**: End-to-end multi-chapter workflow simulation under real novel translation conditions.
- **Scenarios**:
  - See Section 4 for explicit scenario specifications.

---

## 4. Real-world Application Scenarios (Tier 4)

### Scenario A: Interrupted Multi-Chapter Run & Checkpoint Resume
- **Workflow**:
  1. A project with 10 source chapters is initialized.
  2. `translate run` is executed. Mock LLM completes Chapters 1 through 4, then fails on Chapter 5 (simulating network timeout or API rate limit).
  3. Verification confirms `checkpoint.json` records `last_completed_chapter: 4`.
  4. `translate run` is re-invoked. Pipeline skips Chapters 1–4, resumes at Chapter 5, and completes through Chapter 10.
  5. Final `manifest.json` shows all 10 chapters completed with correct timestamps and metadata.

### Scenario B: Dynamic Character Identity Reveal & Arc Summary Regeneration
- **Workflow**:
  1. Chapter 15 analysis returns a `SignificantEvent` of type `identity_reveal` ("Mysterious Scholar revealed as Emperor") with `triggers_arc_update: True`.
  2. Pipeline detects event, triggers immediate arc summary update via LLM analyzer call.
  3. Updated `arc_summary.json` is saved and injected into Tier 3 context for Chapter 16 onwards.
  4. Glossary snapshot for Chapter 15 records character alias update.

### Scenario C: Low-Confidence Term Mining & Approval Workflow
- **Workflow**:
  1. During Chapter 2 translation analysis, LLM extracts a new term with `confidence: 0.6` (< 0.8 threshold).
  2. Term is written to `state/pending_terms.json` instead of auto-committing to `glossary.json`.
  3. User runs `noveltrans glossary show` to inspect pending terms.
  4. User runs `noveltrans glossary approve`. Term is merged into `glossary.json`, and `pending_terms.json` is reset to empty.
  5. Subsequent translation of Chapter 3 matches the newly approved term via Aho-Corasick matcher.

### Scenario D: Non-Blocking QA Anomaly Detection
- **Workflow**:
  1. Chapter 7 translation output contains untranslated Korean text (`"그는 칼을 들었다"`) and a repetitive phrase loop.
  2. `qa_checker.py` evaluates output, flags `untranslated_korean` and `repetition_loop` issues.
  3. Issues are appended to `ChapterManifestEntry.qa_issues` in `manifest.json`.
  4. Translation pipeline completes Chapter 7 without crashing.
  5. `noveltrans status` displays yellow warning alerts for Chapter 7 QA issues.

### Scenario E: Partial EPUB Compilation for Distribution
- **Workflow**:
  1. Project has 20 chapters translated to `output/txt/ch001.md` ... `ch020.md`.
  2. Command `noveltrans epub build --chapters 1-5 --title "Volume 1"` is executed.
  3. EPUB builder parses chapters 1 to 5, constructs table of contents with generic titles ("Chapter 1" ... "Chapter 5"), applies standard CSS stylesheet, and generates `output/epub/Volume 1.epub`.
  4. Generated file is validated as a valid EPUB3 structure containing expected HTML content files.

---

## 5. Coverage Thresholds & Verification Checklist

### Coverage Thresholds

| Metric | Target Minimum Threshold |
| :--- | :--- |
| **Line Coverage (Overall)** | **>= 85%** |
| **Pydantic Model Validation** | **100%** |
| **CLI Command Routes** | **100%** |
| **Context Assembly Tiers** | **100%** |
| **QA Rule Checkers** | **100%** |

### Acceptance Criteria Verification Checklist

- [ ] **Project Setup**:
  - `uv run noveltrans --help` displays all subcommands cleanly.
  - `uv run basedpyright src/` passes with 0 errors.
  - `uv run ruff check src/ tests/` passes with 0 violations.
- [ ] **Init Command (`test_init.py`)**:
  - Scaffolds `source/`, `output/txt/`, `output/epub/`, `state/summaries/`, `state/glossary_snapshots/`, `state/prompts/`, `prompts/`.
  - Copies Jinja2 prompt templates to project directory.
  - Creates `project.json`, empty `glossary.json`, starter `style_guide.md`.
- [ ] **Glossary System (`test_glossary_matcher.py`)**:
  - Aho-Corasick exact matching for terms and character canonical names/aliases.
  - Rapidfuzz fallback for Korean morphological variations (85% threshold).
  - `always_include` characters injected regardless of text occurrences.
  - `glossary approve` merges `pending_terms.json` into `glossary.json`.
- [ ] **Context Building (`test_context_builder.py`)**:
  - 4-tier context assembly correctly orders global style guide, story summary, arc summary + 5 recent chapter summaries, and 2 recent full chapters.
- [ ] **State & Checkpoints (`test_checkpoint.py`, `test_manifest.py`)**:
  - Atomic read/write of `checkpoint.json` and `manifest.json`.
  - Resume from interrupted chapter.
  - Retranslation with `--force` updates manifest metadata.
- [ ] **QA Checker (`test_qa_checker.py`)**:
  - Untranslated Korean regex (`[\uAC00-\uD7A3]+`).
  - Repetition loop detection.
  - Hallucinated filler phrase detection.
  - Length anomaly check.
- [ ] **Prompt Rendering (`test_prompt_renderer.py`)**:
  - Jinja2 rendering with all character alias genders, knows_identity, matched terms, and summaries.
- [ ] **EPUB Builder (`test_epub_builder.py`)**:
  - EPUB3 generation using `ebooklib`.
  - Partial chapter range building (`--chapters 1-5`).
  - Markdown to clean HTML conversion.
- [ ] **Full Suite Execution**:
  - `uv run pytest tests/ -v` passes completely with zero API calls.
