"""Interactive themed Markdown docs browser orchestration.

Provides the host-agnostic ``DocsSettings`` dataclass and ``run_docs()``, the
pure orchestration (direct slug render, ``--list``, ``--list-themes``, non-TTY
listing, and the interactive InquirerPy tree browser). No Typer here — hosts
own their CLI/help and call ``run_docs()``; a standalone ``md-docs`` Typer
entrypoint (:func:`main`) is provided for ad-hoc use.

Design: hosts supply a ``DocsSettings`` (docs dir, theme/pygments overrides,
default theme, message prefix) plus a ``SettingsReader`` callable mapping their
own config keys (``ui.theme``, ``ui.pygments_theme``) to strings. All project
coupling (config file, docs dir default, branding) lives in the host, not here.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from InquirerPy import get_style, inquirer  # type: ignore[attr-defined]
from rich.console import Console
from rich.theme import Theme

from md_docs.browser import (
    DocNode,
    available_slugs,
    collect_slugs,
    discover_docs,
    render_doc,
)
from md_docs.themes import (
    SettingsReader,
    ThemeSpec,
    all_themes,
    resolve_pygments_theme,
    resolve_theme,
)

_EXIT = object()


@dataclass(frozen=True)
class DocsSettings:
    """Host-supplied configuration for a docs-browser run."""

    docs_dir: Path
    theme: str | None = None
    pygments: str | None = None
    default_theme: str = "monokai"
    prefix: str = "md-docs"


def _themed_console(theme: ThemeSpec) -> Console:
    """Rich console themed with the given spec's markdown styles."""
    return Console(theme=Theme(theme.rich_styles()))


def _interactive_browse(root: DocNode, theme: ThemeSpec, pygments_theme: str) -> None:
    """Cursor-navigable tree: arrow keys move, Enter opens a file, .. up, exit quits.

    A stack tracks the current path so that ``.. (up)`` returns exactly one
    level rather than unwinding the whole tree. Selecting a Markdown file
    renders it and exits the browser.
    """
    console = _themed_console(theme)
    style = get_style(theme.prompt_styles)
    stack: list[tuple[DocNode, str]] = [(root, "")]
    while stack:
        node, breadcrumb = stack[-1]
        choices: list[dict[str, object]] = []
        for child in node.children:
            label = f"📂 {child.name}" if child.path is None else f"📄 {child.name}"
            choices.append({"name": label, "value": child})
        if len(stack) > 1:
            choices.append({"name": ".. (up)", "value": None})
        choices.append({"name": "exit", "value": _EXIT})
        if not choices:
            return
        answer = inquirer.select(  # type: ignore[attr-defined]
            message=f"docs {breadcrumb}".strip() or "docs",
            choices=choices,
            style=style,
            qmark="",
        ).execute()
        if answer is _EXIT:
            return
        if answer is None:  # .. (up)
            stack.pop()
            continue
        if answer.path is None:  # descend into folder
            stack.append((answer, f"{breadcrumb}/{answer.name}".strip("/")))
        else:  # render the file, then exit the browser
            render_doc(answer.path, console=console, pygments_theme=pygments_theme)
            return


def print_themes(prefix: str = "md-docs") -> None:
    """Print available theme names+descriptions to stdout."""
    for name, spec in sorted(all_themes().items()):
        print(f"{name:16} {spec.description}")


def run_docs(
    settings: DocsSettings,
    settings_reader: SettingsReader | None = None,
    *,
    slug: str | None = None,
    docs_dir: Path | None = None,
    theme: str | None = None,
    pygments: str | None = None,
    list_docs: bool = False,
    list_themes: bool = False,
) -> None:
    """Run the docs browser over the configured docs directory.

    Resolution precedence per option: explicit argument > injected
    ``settings_reader`` config > ``DocsSettings`` fields (theme default from
    ``default_theme``). ``list_themes`` > ``list_docs`` > ``slug`` > interactive.
    """
    theme_spec = resolve_theme(
        theme or settings.theme,
        settings_reader,
        default=settings.default_theme,
        prefix=settings.prefix,
    )
    pyg = resolve_pygments_theme(
        pygments or settings.pygments,
        settings_reader,
        default=settings.default_theme,
        prefix=settings.prefix,
    )
    root_dir = docs_dir or settings.docs_dir
    root = discover_docs(root_dir)

    if list_themes:
        print_themes(settings.prefix)
        return

    if list_docs:
        for s in available_slugs(root_dir):
            print(s)
        return

    if slug is not None:
        slugs = collect_slugs(root)
        target = slugs.get(slug)
        if target is None:
            console = _themed_console(theme_spec)
            console.print(f"[red]Unknown doc '{slug}'.[/red]")
            console.print("Available docs: " + ", ".join(slugs) or "(none)")
            raise SystemExit(1)
        render_doc(target, console=_themed_console(theme_spec), pygments_theme=pyg)
        return

    if not sys.stdin.isatty():
        print("Available docs:")
        for s in available_slugs(root_dir):
            print(f"  {s}")
        return

    _interactive_browse(root, theme_spec, pyg)


def main() -> None:
    """Standalone ``md-docs`` entrypoint (documents the shared core)."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="md-docs", description="Browse Markdown docs."
    )
    parser.add_argument("slug", nargs="?", help="Doc slug to open directly.")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument("--theme")
    parser.add_argument("--pygments-theme")
    parser.add_argument("--list", action="store_true", dest="list_docs")
    parser.add_argument("--list-themes", action="store_true")
    args = parser.parse_args()
    settings = DocsSettings(docs_dir=args.docs_dir, prefix="md-docs")
    run_docs(
        settings,
        slug=args.slug,
        theme=args.theme,
        pygments=args.pygments_theme,
        list_docs=args.list_docs,
        list_themes=args.list_themes,
    )


if __name__ == "__main__":
    main()
