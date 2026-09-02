# AGENTS.md

Shared, config-agnostic themed Markdown docs browser **core** (Python ≥ 3.12).
This is a library, not an app: host projects (`wm`, later `tt`/`sb`) consume it
via `DocsSettings` + an injected `SettingsReader`. Keep all host coupling
(config loading, docs-dir defaults, branding) in the host, never here.

## Development environment

Tooling is managed by `uv`. Dev deps (pytest/ruff/mypy) live under
`[project.optional-dependencies].dev` and are **not** installed by a plain
`uv sync` — the committed/recreated `.venv` only gets the project itself.

```sh
uv sync --all-extras   # required first: installs pytest/ruff/mypy into .venv
uv run pytest          # tests (23 in tests/, import md_docs)
uv run ruff check src  # line-length 88, select E,F,W,I
uv run mypy src        # strict = true
```

Without `--all-extras`, `uv run pytest` silently falls back to a system pytest
that lacks the editable `md_docs` install (`ModuleNotFoundError: No module
named 'md_docs'`). If you hit that, run `uv sync --all-extras`.

## Layout & architecture

- `src/md_docs/browser.py` — `discover_docs` tree (folders as `DocNode`s, `.md`
  leaves), `collect_slugs`/`available_slugs` (slug = rel path without `.md`),
  `render_doc` (rich Markdown w/ Pygments `code_theme`). No CLI/config here.
- `src/md_docs/themes.py` — TOML theme loader + validation + resolution.
  Defines `SettingsReader` (`Callable[[str], str | None]`) the host provides to
  read dotted keys like `ui.theme` / `ui.pygments_theme`. Never imports a host
  settings module.
- `src/md_docs/cli.py` — host-agnostic `run_docs()` orchestration (resolution
  precedence: explicit arg > injected settings_reader > `DocsSettings`) and the
  standalone `md-docs` Typer/argparse entrypoint (ad-hoc use only).
- `src/md_docs/themes/builtin/*.toml` — the 8 bundled themes (single tier, never
  user-overridable at runtime).

## Invariants that are easy to break

- **`monokai` must always exist** as a bundled theme — it is `DEFAULT_THEME`,
  the guaranteed fallback for missing/invalid themes and pygments themes.
- Every theme TOML must define **all** `STYLE_KEYS` (under `[styles]`) and
  **all** `PROMPT_KEYS` (under `[prompt_styles]`). Invalid files are skipped at
  load with a stderr warning; the loader is defensive by design.
- Adding a theme = adding a `.toml` under `themes/builtin/`. `test_themes.py`
  asserts the exact expected theme-name list — update it too.
- `hatch` wheel config must keep `packages = ["src/md_docs"]` and
  `artifacts = ["src/md_docs/themes/builtin/*.toml"]` so bundled themes ship.

## Conventions

- `mypy` is strict; type-annotate everything. `InquirerPy` is excluded via
  `ignore_missing_imports` override — add no other ignores.
- `_ai/` holds the AI knowledge base: `backlog/{active,archive,epics}` and
  `technical_decisions/` (ADR-style). Update these rather than inline legend.
- `README.md` is boilerplate/stale; treat the module docstrings
  (`cli.py`/`themes.py`/`browser.py`) as the authoritative design description.
