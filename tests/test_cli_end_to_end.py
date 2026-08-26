from __future__ import annotations

import json
from pathlib import Path

from tk_request_console.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = REPO_ROOT / "profiles"


def test_cli_url_prints_expected(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    exit_code = main(["url", "--profile", str(PROFILES_DIR / "echo.json"), "--json"])
    out = capsys.readouterr().out.strip()
    assert exit_code == 0
    payload = json.loads(out)
    assert payload["url"].startswith("http://127.0.0.1:8099/api/echo/ping?")
    assert "_ts=" in payload["url"]


def test_cli_send_against_echo_server(tmp_path, monkeypatch, capsys, echo_server):
    monkeypatch.chdir(tmp_path)
    port = echo_server.server_port
    exit_code = main(
        [
            "send",
            "--profile",
            str(PROFILES_DIR / "echo.json"),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--json",
        ]
    )
    out = capsys.readouterr().out.strip()
    assert exit_code == 0
    payload = json.loads(out)
    body = json.loads(payload["body"])
    assert body["body_utf8"] == "hello"
    assert payload["status"] == 200


def test_cli_send_form_post_escapes_reach_server(tmp_path, monkeypatch, capsys, echo_server):
    monkeypatch.chdir(tmp_path)
    port = echo_server.server_port
    exit_code = main(
        [
            "send",
            "--profile",
            str(PROFILES_DIR / "form-post.json"),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--json",
        ]
    )
    out = capsys.readouterr().out.strip()
    assert exit_code == 0
    payload = json.loads(out)
    body = json.loads(payload["body"])
    assert "\x00" in body["body_utf8"]


def test_cli_send_non_2xx_exit_code(tmp_path, monkeypatch, capsys, echo_server):
    monkeypatch.chdir(tmp_path)
    port = echo_server.server_port
    profile_path = tmp_path / "fail.json"
    profile_data = json.loads((PROFILES_DIR / "echo.json").read_text(encoding="utf-8"))
    profile_data["name"] = "fail"
    profile_data["action"] = "fail"
    profile_path.write_text(json.dumps(profile_data), encoding="utf-8")

    exit_code = main(
        [
            "send",
            "--profile",
            str(profile_path),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--json",
        ]
    )
    out = capsys.readouterr().out.strip()
    assert exit_code == 1
    payload = json.loads(out)
    assert payload["status"] == 500


def test_cli_send_transport_error_exit_code(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    exit_code = main(
        [
            "send",
            "--profile",
            str(PROFILES_DIR / "echo.json"),
            "--host",
            "127.0.0.1",
            "--port",
            "1",
        ]
    )
    err = capsys.readouterr().err.strip()
    assert exit_code == 2
    assert len(err.splitlines()) == 1


def test_cli_config_check_exit_codes(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    example = REPO_ROOT / "config.example.json"
    exit_code = main(["config-check", "--config", str(example)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert '"scheme": "http"' in out

    bad_config = tmp_path / "bad.json"
    data = json.loads(example.read_text(encoding="utf-8"))
    data["endpoint"]["scheme"] = "ftp"
    bad_config.write_text(json.dumps(data), encoding="utf-8")
    exit_code = main(["config-check", "--config", str(bad_config)])
    err = capsys.readouterr().err
    assert exit_code != 0
    assert "scheme" in err


def test_cli_profiles_lists_shipped_profiles(monkeypatch, capsys):
    monkeypatch.chdir(REPO_ROOT)
    exit_code = main(["profiles"])
    out = capsys.readouterr().out
    assert exit_code == 0
    for name in ("echo", "json-post", "form-post"):
        assert name in out
