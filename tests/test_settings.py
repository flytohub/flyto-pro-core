"""Behavioral tests for environment and YAML configuration precedence."""

from __future__ import annotations

from pathlib import Path

import pytest

from flyto_pro_core.config.settings import Settings


def test_yaml_values_are_applied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify yaml values are applied."""
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("API_PORT", raising=False)
    config = tmp_path / "settings.yml"
    config.write_text(
        "database:\n  host: db.internal\napi:\n  port: 9000\ndebug: true\n",
        encoding="utf-8",
    )

    settings = Settings.from_yaml(config)

    assert settings.database.host == "db.internal"
    assert settings.api.port == 9000
    assert settings.debug is True


def test_environment_takes_precedence_over_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify environment takes precedence over yaml."""
    monkeypatch.setenv("API_PORT", "8123")
    config = tmp_path / "settings.yml"
    config.write_text("api:\n  port: 9000\n", encoding="utf-8")

    assert Settings.from_yaml(config).api.port == 8123


@pytest.mark.parametrize(
    "content, message",
    [
        ("unknown_section: true\n", "unknown settings section"),
        ("api:\n  unknown_field: true\n", "unknown setting"),
        ("- not\n- a\n- mapping\n", "mapping at the root"),
    ],
)
def test_yaml_rejects_unknown_or_invalid_shape(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    """Verify yaml rejects unknown or invalid shape."""
    config = tmp_path / "settings.yml"
    config.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        Settings.from_yaml(config)
