# noveltrans

A production-quality Python CLI tool for high-quality AI-powered web novel translation (Korean, Japanese, Chinese → English) with persistent context, enriched character modeling, glossary management, and EPUB output.

## Features

- **Multi-tier persistent context** — 4-tier context system (style guide → story summary → arc summary → recent chapters) ensures coherent translation across an entire novel
- **Enriched character modeling** — Per-alias gender tracking, `knows_identity` for pronoun-aware translation, relationship graphs, and `always_include` for major characters
- **High-performance glossary matching** — Aho-Corasick O(N) exact matching + RapidFuzz fuzzy fallback (85% threshold) for morphological variants
- **CJK multi-language support** — Korean (`ko`), Japanese (`ja`), Chinese (`zh`) with language-specific honorific policies and QA detection
- **EPUB3 compilation** — Styled ebook output with metadata, TOC, and CSS. Supports partial chapter builds
- **Robust state management** — Checkpoint resume, glossary snapshots per chapter, prompt archiving, force-retranslation
- **Non-blocking QA** — Automated quality checks (untranslated text, filler detection, repetition loops) logged to manifest without blocking translation
- **Model-agnostic** — Works with any OpenAI-compatible API (OpenAI, Gemini, Anthropic via proxy, local models)

## Installation

```bash
# Clone and install
git clone https://github.com/Ethanz0/noveltrans.git && cd noveltrans
uv sync

# Set up API key
mkdir -p ~/.config/noveltrans
cat > ~/.config/noveltrans/.env << 'EOF'
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
MODEL_NAME=gemini-2.5-pro
EOF
```

## Quick Start

```bash
# 1. Create a new translation project
noveltrans init ./my_novel --language ko    # ko | ja | zh

# 2. Drop source chapters into the source directory
cp ~/chapters/*.txt ./my_novel/source/      # Files must be numbered: 001.txt, 002.txt, ...

# 3. Bootstrap glossary and summaries from initial chapters
noveltrans glossary seed --chapters 1-10 --project ./my_novel

# 4. Review and edit the generated glossary
# Edit ./my_novel/glossary.json — fix names, set always_include, add notes

# 5. Optionally generate a style guide
noveltrans style analyze --chapters 1-10 --project ./my_novel
# Edit ./my_novel/style_guide.md to taste

# 6. Preview prompts without calling the LLM
noveltrans translate run --chapters 1-2 --dry-run --project ./my_novel

# 7. Translate!
noveltrans translate run --chapters 1-10 --project ./my_novel

# 8. Check progress and QA issues
noveltrans status --project ./my_novel

# 9. Interactively review new terms and get LLM-suggested alternatives
# noveltrans glossary review --project ./my_novel

# 10. Build an EPUB
noveltrans epub build --title "My Novel" --author "Author" --project ./my_novel
```

## CLI Commands

| Command | Description |
|---|---|
| `noveltrans init <path> [--language ko\|ja\|zh]` | Scaffold a new translation project |
| `noveltrans translate run [--chapters 1-5] [--force] [--dry-run] [--skip-glossary]` | Translate chapters |
| `noveltrans glossary seed [--chapters 1-10] [--update-summaries]` | Bootstrap glossary from raw chapters |
| `noveltrans glossary show` | Pretty-print the current glossary |
| `noveltrans glossary review` | Interactively review newly extracted terms (LLM alternatives) |
| `noveltrans style analyze [--chapters 1-10]` | Generate/update style guide |
| `noveltrans arc update` | Regenerate arc summary |
| `noveltrans story update` | Regenerate story summary |
| `noveltrans epub build [--chapters 1-50] [--title TEXT] [--author TEXT]` | Compile EPUB |
| `noveltrans status` | Show translation progress and QA issues |

All commands accept `--project PATH` (defaults to current directory).

## Translation Pipeline

Each chapter is processed with exactly **2 LLM calls**:

1. **Translation call** — Translates the chapter using 4-tier context (style guide, story/arc summaries, recent translations, matched glossary entries)
2. **Analysis call** — Extracts new terms, generates chapter summary, detects significant events, flags QA issues

After each chapter: glossary snapshot saved, prompts archived, manifest updated, checkpoint saved. If interrupted, `translate run` resumes from the last completed chapter.

## Project Structure

After `noveltrans init`, your translation project looks like:

```
my_novel/
├── source/              # Drop .txt files here (001.txt, 002.txt, ...)
├── output/
│   ├── txt/             # Translated markdown chapters
│   └── epub/            # Compiled EPUB files
├── state/               # All persistent state
├── prompts/             # Editable Jinja2 prompt templates
├── glossary.json        # Active glossary (characters, terms, relationships)
├── style_guide.md       # Translation style guide
├── project.json         # Project configuration
└── .env                 # Optional per-project API overrides
```

## Configuration

| Level | File | What it controls |
|---|---|---|
| Global | `~/.config/noveltrans/.env` | API key, base URL, model, temperature, retries |
| Project | `./project/.env` | Per-project API overrides |
| Project | `./project/project.json` | Title, author, language, context window sizes |

## Development

```bash
# Run tests (169 tests, all mocked — no API calls)
uv run pytest tests/ -v

# Type checking
uv run basedpyright src/

# Linting
uv run ruff check src/ tests/
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for comprehensive technical documentation including:
- Module dependency graph
- 14-step translation pipeline data flow
- Data model reference (glossary, state, LLM responses)
- 4-tier context system details
- Extension guide for adding commands, languages, QA checks, and templates

## License

MIT
