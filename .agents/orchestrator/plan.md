# Execution Plan for noveltrans

## Overview
`noveltrans` is being developed following the Project Pattern dual-track methodology:
- **E2E Testing Track**: Requirement-driven unit/integration/E2E tests (Tiers 1-4) and published `TEST_READY.md`.
- **Implementation Track**: Milestones 1 through 5 are completed & verified. Milestone 6 (CLI Interface & R5 Multi-Language Support) is in progress, followed by Milestone 7 (Final 100% E2E test pass + Tier 5 white-box hardening + Forensic Audit).

## Milestones Breakdown

### E2E Testing Track (`.agents/sub_orch_e2e`) — DONE
- Published `TEST_READY.md` with 147 test cases.

### Milestone 1: Foundation & Models — DONE & AUDITED
- Models, config, dependencies, project structure verified. Audit: CLEAN.

### Milestone 2: Glossary System & Matcher — DONE & AUDITED
- Glossary models, manager, Aho-Corasick/fuzzy matcher, seeder. Audit: CLEAN.

### Milestone 3: LLM Layer & Context Builder — DONE & AUDITED
- LLM client, parsers, Jinja2 renderer, 4-tier context builder. Audit: CLEAN.

### Milestone 4: Core Pipeline, QA Checker & State Engine — DONE
- Translator pipeline, analyzer, QA checker, checkpoint, manifest.

### Milestone 5: EPUB Builder — DONE & AUDITED
- `epub/builder.py` with ebooklib EPUB3 compiler. Audit: CLEAN.

### Milestone 6: CLI Interface & Multi-Language Support (R5) (`.agents/worker_m6_r5`) — DONE & AUDITED
- All CLI subcommands (`init`, `translate`, `glossary`, `epub`, `style`, `summary`, `status`, `arc`, `story`) implemented with Typer & Rich.
- Multi-Language support (Korean `ko`, Japanese `ja`, Chinese `zh`) implemented across config, QA checker regexes, Jinja2 prompts, honorifics policy, and `init --language`.
- Verified CLEAN by Forensic Auditor `auditor_m6_r5`.

### Milestone 7: Integration, Hardening & Audit (`.agents/worker_m7`, `.agents/auditor_m7`) — DONE & AUDITED
- 169 unit & E2E tests pass (100%).
- Type checker (`basedpyright`) 0 errors.
- Linter (`ruff`) 0 violations.
- CLI (`noveltrans --help`) 0 errors.
- Project ready for Sentinel victory claim and independent Victory Audit.

## Verification Gate Criteria
1. Implementation worker completes code and tests.
2. Reviewers independently check code & run tests.
3. Challenger tests edge cases & multi-language scenarios.
4. Forensic Auditor verifies no cheating/hardcoding/facades (verdict: CLEAN).
