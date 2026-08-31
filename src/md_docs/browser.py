"""Discovery and rendering for a Markdown docs browser.

Single Responsibility: walk a docs directory into a tree, map slugs to files,
and render a Markdown file to the terminal with a themed rich console. No
Typer / CLI concerns and no host configuration access here — resolution of the
docs directory and theme is left to the calling application.

This is the shared, project-agnostic core extracted from the ``tt`` and ``sb``
projects' ``docs_browser.py`` (which were near-identical copies of each other).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown


@dataclass(frozen=True)
class DocNode:
    """One node in the docs tree: a folder (``path is None``) or a Markdown file."""

    name: str
    path: Path | None
    children: tuple["DocNode", ...] = ()


def discover_docs(docs_dir: Path) -> DocNode:
    """Build a tree of Markdown files under ``docs_dir`` (folders = branches).

    Returns an empty folder node when ``docs_dir`` does not exist so callers
    degrade gracefully.
    """
    if not docs_dir.is_dir():
        return DocNode(name=docs_dir.name, path=None, children=())
    return DocNode(name=docs_dir.name, path=None, children=_build_children(docs_dir))


def _build_children(directory: Path) -> tuple[DocNode, ...]:
    nodes: list[DocNode] = []
    for entry in sorted(directory.iterdir()):
        if entry.is_dir():
            nodes.append(DocNode(entry.name, None, _build_children(entry)))
        elif entry.is_file() and entry.suffix == ".md":
            nodes.append(DocNode(entry.stem, entry))
    return tuple(nodes)


def collect_slugs(root: DocNode) -> dict[str, Path]:
    """Return ``slug -> file path`` for every Markdown leaf in the tree.

    A slug is the relative path without the ``.md`` extension, e.g. ``about``
    for ``docs/about.md`` or ``sub/x`` for ``docs/sub/x.md``.
    """
    result: dict[str, Path] = {}

    def walk(node: DocNode, prefix: str) -> None:
        if node.path is not None:
            result[prefix + node.name] = node.path
            return
        for child in node.children:
            walk(child, prefix + node.name + "/")

    for child in root.children:
        walk(child, "")
    return result


def available_slugs(docs_dir: Path) -> list[str]:
    """Sorted slug list for error/non-TTY output."""
    return sorted(collect_slugs(discover_docs(docs_dir)).keys())


def render_doc(
    path: Path,
    console: Console | None = None,
    pygments_theme: str = "monokai",
) -> None:
    """Render a Markdown file to the terminal with ``rich.Markdown``.

    ``pygments_theme`` selects the Pygments lexer theme used for fenced code
    blocks (e.g. ``monokai``, ``dracula``, ``github-dark``).
    """
    console = console or Console()
    console.print(Markdown(path.read_text(encoding="utf-8"), code_theme=pygments_theme))
