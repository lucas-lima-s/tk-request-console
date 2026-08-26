from __future__ import annotations

from dataclasses import replace

import pytest

from tk_request_console.config import EndpointConfig
from tk_request_console.errors import TemplateError
from tk_request_console.protocol import RequestSpec, build_url

DEFAULT_CFG = EndpointConfig()


def make_spec(**overrides) -> RequestSpec:
    base = dict(
        host="127.0.0.1",
        port=8080,
        group="echo",
        action="ping",
        token="42",
        fmt="json",
        timeout=5000,
        base64_encode=False,
        interpret_escapes=False,
        payload="hi",
    )
    base.update(overrides)
    return RequestSpec(**base)


def test_build_url_exact():
    url = build_url(DEFAULT_CFG, make_spec(), timestamp=1700000000000)
    assert url == (
        "http://127.0.0.1:8080/api/echo/ping"
        "?token=42&format=1&timeout=5000&encoded=false&_ts=1700000000000"
    )


def test_build_url_omits_empty_params():
    url = build_url(DEFAULT_CFG, make_spec(token=""), timestamp=1700000000000)
    query_params = [pair.split("=", 1)[0] for pair in url.split("?", 1)[1].split("&")]
    assert "token" not in query_params


def test_build_url_percent_encodes():
    cfg = replace(DEFAULT_CFG, token_mode="raw")
    url = build_url(cfg, make_spec(token="a b&c"), timestamp=1700000000000)
    assert "token=a+b%26c" in url


def test_build_url_unknown_placeholder_raises():
    cfg = replace(DEFAULT_CFG, path_template="/api/{bogus}")
    with pytest.raises(TemplateError, match="bogus"):
        build_url(cfg, make_spec())


def test_build_url_rejects_unknown_query_placeholder():
    cfg = replace(DEFAULT_CFG, query={"weird": "{nonexistent}"})
    with pytest.raises(TemplateError, match="nonexistent"):
        build_url(cfg, make_spec())


def test_build_url_injected_timestamp():
    url = build_url(DEFAULT_CFG, make_spec(), timestamp=123456789)
    assert "_ts=123456789" in url
