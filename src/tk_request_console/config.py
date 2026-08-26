from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from tk_request_console.errors import ConfigError

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_]+)\}")

_ALLOWED_SCHEMES = {"http", "https"}
_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_ALLOWED_BOOL_STYLES = {"true_false", "one_zero", "yes_no"}
_ALLOWED_TOKEN_MODES = {"auto", "upper", "int", "raw"}
_ALLOWED_PLACEHOLDERS = {
    "host",
    "port",
    "group",
    "action",
    "token",
    "format",
    "timeout",
    "encoded",
    "timestamp",
}


def _default_query() -> dict[str, str]:
    return {
        "token": "{token}",
        "format": "{format}",
        "timeout": "{timeout}",
        "encoded": "{encoded}",
        "_ts": "{timestamp}",
    }


def _default_format_codes() -> dict[str, int]:
    return {"text": 0, "json": 1, "xml": 2, "form": 3}


@dataclass(frozen=True)
class EndpointConfig:
    scheme: str = "http"
    default_host: str = "127.0.0.1"
    default_port: int = 8080
    method: str = "POST"
    path_template: str = "/api/{group}/{action}"
    query: dict[str, str] = field(default_factory=_default_query)
    format_codes: dict[str, int] = field(default_factory=_default_format_codes)
    bool_style: str = "true_false"
    token_mode: str = "auto"
    omit_empty_params: bool = True
    verify_tls: bool = True


@dataclass(frozen=True)
class FieldLabels:
    host: str = "Host"
    group: str = "Group"
    action: str = "Action"
    token: str = "Token"
    fmt: str = "Format"
    timeout: str = "Timeout (ms, -1 = none)"


@dataclass(frozen=True)
class HostDirectoryConfig:
    enabled: bool = False
    url: str = ""
    code_field: str = "code"
    name_field: str = "name"
    host_field: str = "host"
    timeout_s: float = 5.0


@dataclass(frozen=True)
class AppConfig:
    endpoint: EndpointConfig = field(default_factory=EndpointConfig)
    labels: FieldLabels = field(default_factory=FieldLabels)
    directory: HostDirectoryConfig = field(default_factory=HostDirectoryConfig)
    profiles_dir: str = "profiles"
    log_file: str = ""


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def _reject_unknown_keys(data: dict, allowed: set, section: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"unknown key in '{section}': {sorted(unknown)[0]}")


def _extract_placeholders(text: str) -> set[str]:
    return set(_PLACEHOLDER_RE.findall(text))


def _build_endpoint(data: dict) -> EndpointConfig:
    defaults = EndpointConfig()
    allowed = {f.name for f in fields(EndpointConfig)}
    _reject_unknown_keys(data, allowed, "endpoint")

    scheme = data.get("scheme", defaults.scheme)
    if scheme not in _ALLOWED_SCHEMES:
        raise ConfigError(f"invalid 'endpoint.scheme': {scheme!r}")

    method = data.get("method", defaults.method)
    if method not in _ALLOWED_METHODS:
        raise ConfigError(f"invalid 'endpoint.method': {method!r}")

    default_port = data.get("default_port", defaults.default_port)
    if (
        not isinstance(default_port, int)
        or isinstance(default_port, bool)
        or not (1 <= default_port <= 65535)
    ):
        raise ConfigError(f"invalid 'endpoint.default_port': {default_port!r}")

    bool_style = data.get("bool_style", defaults.bool_style)
    if bool_style not in _ALLOWED_BOOL_STYLES:
        raise ConfigError(f"invalid 'endpoint.bool_style': {bool_style!r}")

    token_mode = data.get("token_mode", defaults.token_mode)
    if token_mode not in _ALLOWED_TOKEN_MODES:
        raise ConfigError(f"invalid 'endpoint.token_mode': {token_mode!r}")

    path_template = data.get("path_template", defaults.path_template)
    query = data.get("query", defaults.query)
    placeholders = _extract_placeholders(path_template)
    for value in query.values():
        placeholders |= _extract_placeholders(value)
    unknown_placeholders = placeholders - _ALLOWED_PLACEHOLDERS
    if unknown_placeholders:
        raise ConfigError(
            f"unknown placeholder in endpoint template: {sorted(unknown_placeholders)[0]}"
        )

    return EndpointConfig(
        scheme=scheme,
        default_host=data.get("default_host", defaults.default_host),
        default_port=default_port,
        method=method,
        path_template=path_template,
        query=dict(query),
        format_codes=dict(data.get("format_codes", defaults.format_codes)),
        bool_style=bool_style,
        token_mode=token_mode,
        omit_empty_params=data.get("omit_empty_params", defaults.omit_empty_params),
        verify_tls=data.get("verify_tls", defaults.verify_tls),
    )


def _build_labels(data: dict) -> FieldLabels:
    defaults = FieldLabels()
    allowed = {f.name for f in fields(FieldLabels)}
    _reject_unknown_keys(data, allowed, "labels")
    return FieldLabels(**{**defaults.__dict__, **data})


def _build_directory(data: dict) -> HostDirectoryConfig:
    defaults = HostDirectoryConfig()
    allowed = {f.name for f in fields(HostDirectoryConfig)}
    _reject_unknown_keys(data, allowed, "directory")
    return HostDirectoryConfig(**{**defaults.__dict__, **data})


_ALLOWED_TOP_LEVEL = {"endpoint", "labels", "directory", "profiles_dir", "log_file"}


def load_config(path: Path | None = None) -> AppConfig:
    load_dotenv()

    if path is None:
        default_path = Path("config.json")
        path = default_path if default_path.is_file() else None

    if path is None:
        return AppConfig()

    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in config file '{path}': {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"config file '{path}' must contain a JSON object")

    raw = _expand_env(raw)
    _reject_unknown_keys(raw, _ALLOWED_TOP_LEVEL, "config")

    return AppConfig(
        endpoint=_build_endpoint(raw.get("endpoint", {})),
        labels=_build_labels(raw.get("labels", {})),
        directory=_build_directory(raw.get("directory", {})),
        profiles_dir=raw.get("profiles_dir", "profiles"),
        log_file=raw.get("log_file", ""),
    )
