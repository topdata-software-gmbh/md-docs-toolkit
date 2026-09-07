# md-docs-toolkit

A config-agnostic themed Markdown docs browser core for the terminal.
Shared library consumed by host projects (currently `wm`, later `tt`/`sb`) via `DocsSettings` + an injected `SettingsReader`.

## Features

- **Interactive tree browser** — cursor-navigable folder/file tree using InquirerPy
- **Direct slug access** — open any doc by slug (e.g. `md-docs about`)
- **8 bundled themes** — Dracula, GitHub Dark, Monokai, Nord, One Dark, Solarized Dark/Light, Topdata
- **Themed rendering** — Markdown + code blocks styled via rich + Pygments
- **Config-agnostic** — hosts supply config through a `SettingsReader` callable; no coupling to any config library
- **Non-TTY mode** — lists available docs when stdin is not a terminal (CI/piping friendly)

## Requirements

- Python >= 3.12

## Installation

```sh
uv add md-docs-toolkit
```

Or install from source:

```sh
git clone <repo-url>
cd md-docs-toolkit
uv sync
```

## Development

```sh
uv sync --all-extras   # installs dev deps (pytest, ruff, mypy)
uv run pytest           # run tests
uv run ruff check src   # lint
uv run mypy src         # type check (strict mode)
```

## Usage

### Standalone CLI

```sh
# Interactive browser (opens docs/browser.py with theme selection)
uv run md-docs --docs-dir ./docs

# Open a specific doc by slug
uv run md-docs getting-started --docs-dir ./docs

# List available docs
uv run md-docs --list --docs-dir ./docs

# List available themes
uv run md-docs --list-themes
```

### As a library

```python
from pathlib import Path
from md_docs.browser import discover_docs, collect_slugs, render_doc
from md_docs.themes import resolve_theme
from md_docs.cli import DocsSettings, run_docs

# Discover docs
root = discover_docs(Path("./docs"))
slugs = collect_slugs(root)

# Render a doc
render_doc(slugs["getting-started"])

# Or use the full orchestration with host config
settings = DocsSettings(docs_dir=Path("./docs"))
run_docs(settings, slug="getting-started")
```

### Integrating into a host project

Host projects provide a `DocsSettings` and optionally a `SettingsReader`:

```python
from md_docs.cli import DocsSettings, run_docs

settings = DocsSettings(
    docs_dir=Path("./docs"),
    theme="dracula",
    default_theme="monokai",
    prefix="my-app",
)

# SettingsReader reads from your config (e.g. TOML, YAML, env)
def reader(key: str) -> str | None:
    config = {"ui.theme": "nord"}
    return config.get(key)

run_docs(settings, settings_reader=reader)
```

Resolution precedence: explicit argument > `settings_reader` config > `DocsSettings` defaults.

## Theme system

Themes are TOML files in `src/md_docs/themes/builtin/`. Each defines:

- `[styles]` — rich markdown rendering colors (heading, link, code_block, etc.)
- `[prompt_styles]` — InquirerPy interactive prompt colors
- `pygments_theme` — Pygments code block theme name

To add a theme, place a new `.toml` in the `builtin/` directory following the existing format.

## License

MIT
