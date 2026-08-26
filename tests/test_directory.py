from __future__ import annotations

from dataclasses import replace

import requests

from tk_request_console.directory import fetch_hosts


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_directory_disabled_returns_empty(cfg, monkeypatch):
    called = []

    def fake_get(*args, **kwargs):
        called.append((args, kwargs))
        raise AssertionError("no HTTP call should be attempted when disabled")

    monkeypatch.setattr(requests, "get", fake_get)
    assert fetch_hosts(cfg) == []
    assert called == []


def test_directory_parses_entries(cfg, monkeypatch):
    directory = replace(cfg.directory, enabled=True, url="http://directory.test/hosts")
    enabled_cfg = replace(cfg, directory=directory)

    def fake_get(url, timeout):
        assert url == "http://directory.test/hosts"
        return _FakeResponse(
            [
                {"code": "A1", "name": "Store One", "host": "10.0.0.1"},
                {"code": "A2", "name": "Store Two", "host": "10.0.0.2"},
            ]
        )

    monkeypatch.setattr(requests, "get", fake_get)
    entries = fetch_hosts(enabled_cfg)
    assert [e.label for e in entries] == ["A1 - Store One", "A2 - Store Two"]
    assert entries[0].host == "10.0.0.1"


def test_directory_swallows_errors(cfg, monkeypatch):
    directory = replace(cfg.directory, enabled=True, url="http://directory.test/hosts")
    enabled_cfg = replace(cfg, directory=directory)

    def fake_get(*_args, **_kwargs):
        raise requests.ConnectionError("unreachable")

    monkeypatch.setattr(requests, "get", fake_get)
    assert fetch_hosts(enabled_cfg) == []
