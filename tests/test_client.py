from __future__ import annotations

import logging

import pytest
import requests

from tk_request_console.client import send_request
from tk_request_console.errors import TransportError
from tk_request_console.protocol import RequestSpec


def make_spec(**overrides) -> RequestSpec:
    base = dict(
        host="127.0.0.1",
        port=8080,
        group="echo",
        action="ping",
        token="sample-token-fixture",
        fmt="text",
        timeout=5000,
        base64_encode=False,
        interpret_escapes=False,
        payload="hello",
    )
    base.update(overrides)
    return RequestSpec(**base)


class _FakeResponse:
    def __init__(self, status_code=200, text="ok", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def test_client_calls_requests_with_expected_args(cfg, monkeypatch):
    captured = {}

    def fake_request(method, url, *, data, timeout, verify):
        captured.update(method=method, url=url, data=data, timeout=timeout, verify=verify)
        return _FakeResponse()

    monkeypatch.setattr(requests, "request", fake_request)
    spec = make_spec()
    response = send_request(cfg, spec, timestamp=1700000000000)

    assert captured["method"] == cfg.endpoint.method
    assert captured["url"] == response.url
    assert captured["data"] == b"hello"
    assert captured["timeout"] == pytest.approx(5.0)
    assert captured["verify"] == cfg.endpoint.verify_tls


def test_client_negative_timeout_becomes_none(cfg, monkeypatch):
    captured = {}

    def fake_request(method, url, *, data, timeout, verify):
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(requests, "request", fake_request)
    send_request(cfg, make_spec(timeout=-1))
    assert captured["timeout"] is None


def test_client_wraps_transport_error(cfg, monkeypatch):
    def fake_request(*_args, **_kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(requests, "request", fake_request)
    with pytest.raises(TransportError):
        send_request(cfg, make_spec())


def test_client_does_not_log_token_value(cfg, monkeypatch, caplog):
    def fake_request(*_args, **_kwargs):
        return _FakeResponse()

    monkeypatch.setattr(requests, "request", fake_request)
    with caplog.at_level(logging.DEBUG):
        send_request(cfg, make_spec(token="sample-token-fixture"))

    for record in caplog.records:
        assert "sample-token-fixture" not in record.getMessage()
