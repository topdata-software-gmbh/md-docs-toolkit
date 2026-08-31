"""md_docs.browser — tree discovery, slugs, and rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_docs.browser import (
    available_slugs,
    collect_slugs,
    discover_docs,
    render_doc,
)


def _write_tree(root: Path) -> None:
    (root / "convert.md").write_text("# md convert\n\nText.\n", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "themes.md").write_text(
        "# md themes\n\n```python\nx = 1\n```\n", encoding="utf-8"
    )


def test_discover_docs_flat_and_nested(tmp_path: Path) -> None:
    _write_tree(tmp_path)
    root = discover_docs(tmp_path)
    names = {child.name for child in root.children}
    assert names == {"convert", "sub"}
    sub = next(child for child in root.children if child.name == "sub")
    assert [leaf.name for leaf in sub.children] == ["themes"]


def test_discover_docs_missing_dir_is_empty(tmp_path: Path) -> None:
    root = discover_docs(tmp_path / "nope")
    assert root.path is None
    assert root.children == ()


def test_collect_slugs(tmp_path: Path) -> None:
    _write_tree(tmp_path)
    slugs = collect_slugs(discover_docs(tmp_path))
    assert slugs == {
        "convert": tmp_path / "convert.md",
        "sub/themes": tmp_path / "sub" / "themes.md",
    }


def test_available_slugs_sorted(tmp_path: Path) -> None:
    _write_tree(tmp_path)
    assert available_slugs(tmp_path) == ["convert", "sub/themes"]


def test_render_doc_ok(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    doc = tmp_path / "x.md"
    doc.write_text("# Hello\n\nBody text.\n", encoding="utf-8")
    render_doc(doc)
    out = capsys.readouterr().out
    assert "Hello" in out and "Body text." in out
