"""md_docs.themes — bundled theme loading, validation, and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_docs.themes import (
    DEFAULT_THEME,
    PROMPT_KEYS,
    STYLE_KEYS,
    SettingsReader,
    ThemeSpec,
    all_themes,
    load_builtin_themes,
    resolve_pygments_theme,
    resolve_theme,
    theme_names,
)


def _reader(values: dict[str, str]) -> SettingsReader:
    """Build a SettingsReader returning *values* (or None for unknown keys)."""

    def reader(key: str) -> str | None:
        return values.get(key)

    return reader


def test_default_theme_exists() -> None:
    assert DEFAULT_THEME in all_themes()


def test_all_builtin_themes_are_valid_specs() -> None:
    for spec in all_themes().values():
        assert isinstance(spec, ThemeSpec)
        assert set(spec.styles) == set(STYLE_KEYS)
        assert set(spec.prompt_styles) == set(PROMPT_KEYS)
        assert all(spec.styles.values())
        assert all(spec.prompt_styles.values())
        assert spec.pygments_theme


def test_expected_theme_names() -> None:
    assert theme_names() == [
        "dracula",
        "github-dark",
        "monokai",
        "nord",
        "one-dark",
        "solarized-dark",
        "solarized-light",
        "topdata",
    ]


def test_rich_styles_maps_markdown_names() -> None:
    spec = all_themes()["monokai"]
    mapped = spec.rich_styles()
    assert mapped["markdown.heading"] == spec.styles["heading"]
    assert mapped["markdown.h1"] == spec.styles["heading"]
    assert mapped["markdown.code_block"] == spec.styles["code_block"]
    assert mapped["markdown.strong"] == spec.styles["strong"]


def test_resolve_theme_default_is_monokai() -> None:
    assert resolve_theme(None, None).name == DEFAULT_THEME


def test_resolve_theme_explicit_name() -> None:
    assert resolve_theme("dracula", None).name == "dracula"


def test_resolve_theme_unknown_falls_back_with_warning(
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = resolve_theme("no-such-theme", None)
    assert spec.name == DEFAULT_THEME
    captured = capsys.readouterr()
    assert f"falling back to '{DEFAULT_THEME}'" in captured.err


def test_resolve_theme_from_settings_reader() -> None:
    spec = resolve_theme(None, _reader({"ui.theme": "nord"}))
    assert spec.name == "nord"


def test_resolve_theme_respects_host_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = resolve_theme("nope", None, default="topdata", prefix="wm")
    assert spec.name == "topdata"
    assert "wm: theme 'nope' not found" in capsys.readouterr().err


def test_resolve_pygments_theme_unknown_falls_back(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert resolve_pygments_theme("no-such-pygments", None) == DEFAULT_THEME
    assert "falling back to 'monokai'" in capsys.readouterr().err


def test_resolve_pygments_from_settings_reader() -> None:
    got = resolve_pygments_theme(None, _reader({"ui.pygments_theme": "dracula"}))
    assert got == "dracula"


def test_load_builtin_themes_skips_invalid_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import md_docs.themes as themes_mod

    bogus_dir = tmp_path / "bogus"
    bogus_dir.mkdir()
    (bogus_dir / "bad.toml").write_text("no equals sign here", encoding="utf-8")
    monkeypatch.setattr(themes_mod, "THEMES_DIR", bogus_dir)
    loaded = load_builtin_themes()
    assert loaded == {}
    assert "skipping invalid theme bad.toml" in capsys.readouterr().err


def test_validate_theme_rejects_bad_shapes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import md_docs.themes as themes_mod

    bogus_dir = tmp_path / "bogus"
    bogus_dir.mkdir()
    (bogus_dir / "obj.toml").write_text('name = "obj"', encoding="utf-8")
    (bogus_dir / "missing.toml").write_text(
        "[styles]\n[prompt_styles]\n", encoding="utf-8"
    )
    monkeypatch.setattr(themes_mod, "THEMES_DIR", bogus_dir)
    loaded = load_builtin_themes()
    assert loaded == {}
    err = capsys.readouterr().err
    assert "skipping invalid theme obj.toml" in err
    assert "skipping invalid theme missing.toml" in err
    assert "must define 'styles' and 'prompt_styles'" in err
    assert "missing style keys" in err
