from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from tk_request_console.config import AppConfig
from tk_request_console.errors import TransportError
from tk_request_console.protocol import RequestSpec, build_url, encode_payload

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Response:
    url: str
    status_code: int
    elapsed_ms: float
    text: str
    headers: dict[str, str]


def _redact_url(url: str) -> str:
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    redacted = [(key, "***" if key == "token" else value) for key, value in pairs]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(redacted), parts.fragment))


def send_request(
    cfg: AppConfig,
    req: RequestSpec,
    *,
    session: requests.Session | None = None,
    timestamp: int | None = None,
) -> Response:
    url = build_url(cfg.endpoint, req, timestamp=timestamp)
    data = encode_payload(
        req.payload,
        base64_encode=req.base64_encode,
        interpret_escapes=req.interpret_escapes,
    )
    timeout = req.timeout / 1000 if req.timeout > 0 else None

    logger.info("Sending %s request to %s", cfg.endpoint.method, _redact_url(url))
    logger.debug("Payload size: %d bytes", len(data))

    requester = session.request if session is not None else requests.request
    started = time.monotonic()
    try:
        response = requester(
            cfg.endpoint.method,
            url,
            data=data,
            timeout=timeout,
            verify=cfg.endpoint.verify_tls,
        )
    except requests.RequestException as exc:
        raise TransportError(str(exc), url) from exc
    elapsed_ms = (time.monotonic() - started) * 1000

    return Response(
        url=url,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
        text=response.text,
        headers=dict(response.headers),
    )
