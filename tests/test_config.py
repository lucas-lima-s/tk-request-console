from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from tk_request_console.config import (
    AppConfig,
    EndpointConfig,
    FieldLabels,
    HostDirectoryConfig,
    load_config,
)
from tk_request_console.errors import ConfigError

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CONFIG = REPO_ROOT / "config.example.json"


def test_config_defaults_without_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config(None)
    assert cfg == AppConfig()


def test_config_loads_example():
    cfg = load_config(EXAMPLE_CONFIG)
    assert cfg.endpoint.scheme == "http"
    assert cfg.endpoint.path_template == "/api/{group}/{action}"
    assert cfg.directory.enabled is False
    assert cfg.profiles_dir == "profiles"


def test_config_rejects_unknown_key(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"bogus_top_level": True}), encoding="utf-8")
    with pytest.raises(ConfigError, match="bogus_top_level"):
        load_config(path)


def test_config_rejects_bad_scheme(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"endpoint": {"scheme": "ftp"}}), encoding="utf-8")
    with pytest.raises(ConfigError, match="scheme"):
        load_config(path)


def test_config_rejects_bad_port(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"endpoint": {"default_port": 99999}}), encoding="utf-8")
    with pytest.raises(ConfigError, match="default_port"):
        load_config(path)


def test_config_expands_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_DIRECTORY_URL", "http://internal.example.test/hosts")
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"directory": {"enabled": True, "url": "${TEST_DIRECTORY_URL}"}}),
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.directory.url == "http://internal.example.test/hosts"


def test_example_config_covers_every_dataclass_field():
    raw = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    for section, dataclass_type in (
        ("endpoint", EndpointConfig),
        ("labels", FieldLabels),
        ("directory", HostDirectoryConfig),
    ):
        declared = set(raw[section])
        expected = {f.name for f in fields(dataclass_type)}
        assert declared == expected, f"{section} does not cover every field"

    top_level = set(raw)
    expected_top_level = {f.name for f in fields(AppConfig)}
    assert top_level == expected_top_level
