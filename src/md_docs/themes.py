"""Built-in UI themes for the Markdown docs browser.

Themes are TOML files bundled in ``md_docs/themes/builtin/`` (single tier — no
user/project discovery). A theme maps rich style names (``styles``), InquirerPy
prompt styles (``prompt_styles``), and a Pygments code-block theme
(``pygments_theme``).

This module is **config-agnostic**: it never imports a host's settings module.
Hosts resolve the active theme's name via an injected ``settings_reader``
callable (``Callable[[str], str | None]``) that reads dotted keys such as
``"ui.theme"`` / ``"ui.pygments_theme"`` from their own configuration. The host
also supplies the default theme name and a message prefix for stderr warnings.

Extracted from the ``tt`` and ``sb`` projects' theme layers (``tt/themes`` and
``sb/core/themes.py``, which were near-identical copies).
"""

from __future__ import annotations

import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pygments.styles import get_all_styles

#: Bundled theme folder (single tier; never user-overridable).
THEMES_DIR = Path(__file__).parent / "themes" / "builtin"

#: Name of the guaranteed fallback theme (must exist as a bundled file).
DEFAULT_THEME = "monokai"

#: Generic style keys every theme must define. ``rich_styles()`` maps the
#: markdown-related ones onto rich's ``markdown.*`` names; the rest are
#: consumed directly (e.g. ``Panel(border_style=theme.styles["panel_border"])``).
STYLE_KEYS = (
    "heading",
    "link",
    "link_url",
    "code_block",
    "block_quote",
    "list_item",
    "strong",
    "emphasis",
    "hr",
    "muted",
    "table_header",
    "table_border",
    "panel_border",
    "panel_title",
)

#: InquirerPy prompt style keys every theme must define.
PROMPT_KEYS = (
    "question",
    "pointer",
    "highlighted",
    "instruction",
    "text",
    "answer",
    "questionmark",
)

#: Generic key -> rich style name(s) for the markdown renderer.
_MARKDOWN_MAP: dict[str, tuple[str, ...]] = {
    "heading": ("markdown.heading", *(f"markdown.h{i}" for i in range(1, 7))),
    "link": ("markdown.link",),
    "link_url": ("markdown.link_url",),
    "code_block": ("markdown.code_block", "markdown.code"),
    "block_quote": ("markdown.block_quote",),
    "list_item": ("markdown.item", "markdown.bullet"),
    "strong": ("markdown.strong",),
    "emphasis": ("markdown.emph",),
    "hr": ("markdown.hr", "markdown.rule"),
}

#: Callable hosts provide to read a dotted config key (e.g. ``ui.theme``).
SettingsReader = Callable[[str], str | None]


@dataclass(frozen=True)
class ThemeSpec:
    """One built-in theme: rich styles + InquirerPy styles + pygments theme."""

    name: str
    dark: bool
    description: str
    styles: dict[str, str]
    prompt_styles: dict[str, str]
    pygments_theme: str

    def rich_styles(self) -> dict[str, str]:
        """Map generic style keys onto rich's ``markdown.*`` names."""
        result: dict[str, str] = {}
        for key, targets in _MARKDOWN_MAP.items():
            for target in targets:
                result[target] = self.styles[key]
        return result


_themes: dict[str, ThemeSpec] | None = None
_pygments_styles: set[str] | None = None


def _available_pygments() -> set[str]:
    """Names of all Pygments styles known to this environment (cached)."""
    global _pygments_styles
    if _pygments_styles is None:
        _pygments_styles = set(get_all_styles())
    return _pygments_styles


def load_builtin_themes() -> dict[str, ThemeSpec]:
    """Load every ``*.toml`` in :data:`THEMES_DIR`; invalid files are
    skipped with a stderr warning (the default theme must still load)."""
    themes: dict[str, ThemeSpec] = {}
    for path in sorted(THEMES_DIR.glob("*.toml")):
        try:
            with path.open("rb") as fh:
                data = tomllib.load(fh)
            spec = _validate_theme(data, path.stem)
        except (
            OSError,
            tomllib.TOMLDecodeError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            print(
                f"md-docs: skipping invalid theme {path.name}: {exc}",
                file=sys.stderr,
            )
            continue
        themes[spec.name] = spec
    return themes


def _validate_theme(data: object, fallback_name: str) -> ThemeSpec:
    """Validate a parsed TOML document into a :class:`ThemeSpec`.

    Raises ValueError/KeyError on any schema violation so the loader can
    skip the file.
    """
    if not isinstance(data, dict):
        raise ValueError("theme root must be a table")
    styles = data.get("styles")
    prompt_styles = data.get("prompt_styles")
    if not isinstance(styles, dict) or not isinstance(prompt_styles, dict):
        raise ValueError("theme must define 'styles' and 'prompt_styles' tables")
    missing_styles = [k for k in STYLE_KEYS if not isinstance(styles.get(k), str)]
    missing_prompts = [
        k for k in PROMPT_KEYS if not isinstance(prompt_styles.get(k), str)
    ]
    if missing_styles or missing_prompts:
        raise ValueError(f"missing style keys: {missing_styles + missing_prompts}")
    name = data.get("name", fallback_name)
    if not isinstance(name, str):
        raise ValueError("'name' must be a string")
    dark = data.get("dark", True)
    description = data.get("description", "")
    pygments_theme = data.get("pygments_theme", DEFAULT_THEME)
    if not isinstance(pygments_theme, str):
        raise ValueError("'pygments_theme' must be a string")
    return ThemeSpec(
        name=name,
        dark=bool(dark),
        description=str(description),
        styles={k: str(styles[k]) for k in STYLE_KEYS},
        prompt_styles={k: str(prompt_styles[k]) for k in PROMPT_KEYS},
        pygments_theme=pygments_theme,
    )


def all_themes() -> dict[str, ThemeSpec]:
    """All bundled themes by name (loaded once, cached)."""
    global _themes
    if _themes is None:
        _themes = load_builtin_themes()
    return _themes


def theme_names() -> list[str]:
    """Sorted names of all bundled themes."""
    return sorted(all_themes())


def _read(
    settings_reader: SettingsReader | None,
    key: str,
    default: str,
    prefix: str,
) -> str:
    """Resolve a single config string via the injected reader, falling back
    to *default* (no warning — resolution success is not an error)."""
    if settings_reader is not None:
        value = settings_reader(key)
        if value:
            return value
    return default


def resolve_theme(
    name: str | None,
    settings_reader: SettingsReader | None,
    default: str = DEFAULT_THEME,
    prefix: str = "md-docs",
) -> ThemeSpec:
    """Resolve a theme: *name* > ``settings_reader("ui.theme")`` > *default*.

    An unknown name prints a warning to stderr and falls back to *default*
    (which must exist as a bundled theme). ``settings_reader`` may be ``None``
    to ignore config entirely.
    """
    requested = name or _read(settings_reader, "ui.theme", default, prefix)
    theme = all_themes().get(requested)
    if theme is None:
        print(
            f"{prefix}: theme '{requested}' not found, falling back to '{default}'",
            file=sys.stderr,
        )
        return all_themes()[default]
    return theme


def resolve_pygments_theme(
    name: str | None,
    settings_reader: SettingsReader | None,
    default: str = DEFAULT_THEME,
    prefix: str = "md-docs",
) -> str:
    """Resolve a Pygments code-block theme: *name* > ``settings_reader`` >
    *default*. Unknown names warn and fall back to *default*."""
    requested = name or _read(
        settings_reader, "ui.pygments_theme", default, prefix
    )
    if requested in _available_pygments():
        return requested
    print(
        f"{prefix}: pygments theme '{requested}' not found, falling back to "
        f"'{default}'",
        file=sys.stderr,
    )
    return default
