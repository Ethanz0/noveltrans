## 2026-07-30T05:09:36Z
You are the Glossary System & Matcher Worker for noveltrans (Milestone 2).
Working Directory: /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_m2
Parent Conversation ID: 16dd66f1-bb4c-4ce2-a9f2-262bf935b0a2

Mission: Implement Milestone 2 according to the technical spec in /Users/ethanzhang/Documents/Personal/repositories/noveltrans/ORIGINAL_REQUEST.md.

Scope of work:
1. `src/noveltrans/glossary/manager.py` (& export in `src/noveltrans/glossary/__init__.py`):
   - `GlossaryManager`: Load/save `glossary.json`, create default empty glossary, approve pending terms from `pending_terms.json` (merge pending terms into glossary and clear pending file).
2. `src/noveltrans/glossary/matcher.py`:
   - `GlossaryMatcher`:
     - O(N) exact pattern matching using `ahocorasick-rs` (`AhoCorasick` or `Automaton`) on Korean source text for character canonical names, character aliases (source field), and term source strings.
     - Fuzzy fallback matching using `rapidity` / `rapidfuzz` (`fuzz.ratio` or `fuzz.partial_ratio` >= 85.0 threshold) for Korean text variants.
     - `always_include` guarantee: Characters with `always_include=True` must ALWAYS be included in the matched glossary subset regardless of whether their names appear in the source text.
     - Output: Matched subset of `Glossary` containing matched characters, matched terms, and relevant relationships.
3. `src/noveltrans/core/seeder.py` (& export in `src/noveltrans/core/__init__.py`):
   - `GlossarySeeder`: Seeding logic to build initial glossary and initial story/arc summaries from initial chapters using LLM seed calls.

Verification steps:
1. Run `uv run basedpyright src/` (must pass 0 errors)
2. Run `uv run ruff check src/` (must pass 0 violations)

Write handoff.md in /Users/ethanzhang/Documents/Personal/repositories/noveltrans/.agents/worker_m2/handoff.md with all execution and verification outputs, and send a message back to parent (16dd66f1-bb4c-4ce2-a9f2-262bf935b0a2).
