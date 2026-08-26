from __future__ import annotations

import base64
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlencode

from tk_request_console.config import EndpointConfig
from tk_request_console.errors import TemplateError, TokenError

_DECIMAL_RE = re.compile(r"[+-]?\d+")
_HEX_RE = re.compile(r"0[xX]([0-9a-fA-F]+)")
_ESCAPE_SEQUENCES = {
    "\\0": "\0",
    "\\n": "\n",
    "\\r": "\r",
    "\\t": "\t",
}


@dataclass(frozen=True)
class RequestSpec:
    host: str
    port: int
    group: str
    action: str
    token: str
    fmt: str
    timeout: int
    base64_encode: bool
    interpret_escapes: bool
    payload: str


def normalize_token(raw: str, mode: str = "auto") -> str | int | None:
    text = (raw or "").strip()

    if mode == "upper":
        return text.upper() if text else None
    if mode == "int":
        if not text:
            return None
        try:
            return int(text)
        except ValueError as exc:
            raise TokenError(f"token is not numeric: {raw!r}") from exc
    if mode == "raw":
        return text if text else None
    if mode != "auto":
        raise TokenError(f"unknown token mode: {mode!r}")

    if not text:
        return None
    if _DECIMAL_RE.fullmatch(text):
        return int(text)
    hex_match = _HEX_RE.fullmatch(text)
    if hex_match:
        return "0x" + hex_match.group(1).upper()
    return text.upper()


def format_code(name: str, codes: Mapping[str, int]) -> int | str:
    return codes.get(name, name)


def bool_literal(value: bool, style: str) -> str:
    if style == "true_false":
        return "true" if value else "false"
    if style == "one_zero":
        return "1" if value else "0"
    if style == "yes_no":
        return "yes" if value else "no"
    raise ValueError(f"unknown bool style: {style!r}")


def encode_payload(text: str, *, base64_encode: bool, interpret_escapes: bool) -> bytes:
    if interpret_escapes:
        for sequence, char in _ESCAPE_SEQUENCES.items():
            text = text.replace(sequence, char)
    data = text.encode("utf-8")
    if base64_encode:
        data = base64.b64encode(data)
    return data


def render_response(text: str, *, render_control_chars: bool = True) -> str:
    if render_control_chars:
        return text.replace("\0", "\n")
    return text


def build_url(cfg: EndpointConfig, req: RequestSpec, *, timestamp: int | None = None) -> str:
    if timestamp is None:
        timestamp = int(time.time() * 1000)

    token = normalize_token(req.token, cfg.token_mode)
    fmt = format_code(req.fmt, cfg.format_codes)
    encoded = bool_literal(req.base64_encode, cfg.bool_style)

    values = {
        "host": req.host,
        "port": req.port,
        "group": req.group,
        "action": req.action,
        "token": token if token is not None else "",
        "format": fmt,
        "timeout": req.timeout,
        "encoded": encoded,
        "timestamp": timestamp,
    }

    try:
        path = cfg.path_template.format_map(values)
    except KeyError as exc:
        raise TemplateError(f"unknown placeholder in path_template: {exc}") from exc

    query_items: list[tuple[str, str]] = []
    for key, template in cfg.query.items():
        try:
            rendered = str(template).format_map(values)
        except KeyError as exc:
            raise TemplateError(f"unknown placeholder in query.{key}: {exc}") from exc
        if cfg.omit_empty_params and rendered == "":
            continue
        query_items.append((key, rendered))

    query_string = urlencode(query_items)
    base = f"{cfg.scheme}://{req.host}:{req.port}{path}"
    return f"{base}?{query_string}" if query_string else base
