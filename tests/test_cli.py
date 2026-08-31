"""md_docs.cli — run_docs orchestration modes (list, theme list, slug, unknown)."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_docs.cli import DocsSettings, run_docs
from md_docs.themes import SettingsReader


def _reader(values: dict[str, str]) -> SettingsReader:
    def reader(key: str) -> str | None:
        return values.get(key)

    return reader


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    (tmp_path / "wm.md").write_text("# wm\n\nBody.\n", encoding="utf-8")
    (tmp_path / "configuration.md").write_text(
        "# Configuration\n\nText.\n", encoding="utf-8"
    )
    return tmp_path


def test_run_docs_list(docs_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_docs(DocsSettings(docs_dir=docs_dir), list_docs=True)
    out = capsys.readouterr().out
    assert "configuration" in out
    assert "wm" in out


def test_run_docs_list_themes(capsys: pytest.CaptureFixture[str]) -> None:
    run_docs(DocsSettings(docs_dir=Path(".")), list_themes=True)
    out = capsys.readouterr().out
    assert "monokai" in out
    assert "topdata" in out


def test_run_docs_slug(docs_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_docs(DocsSettings(docs_dir=docs_dir), slug="configuration")
    assert "Configuration" in capsys.readouterr().out


def test_run_docs_unknown_slug_raises(docs_dir: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        run_docs(DocsSettings(docs_dir=docs_dir), slug="no-such-doc")
    assert exc.value.code == 1


def test_run_docs_null_reader_is_ok(docs_dir: Path) -> None:
    run_docs(DocsSettings(docs_dir=docs_dir), None, list_docs=True)
