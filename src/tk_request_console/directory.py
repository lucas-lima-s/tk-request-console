from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from tk_request_console.config import AppConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HostEntry:
    code: str
    name: str
    host: str

    @property
    def label(self) -> str:
        return f"{self.code} - {self.name}"


def fetch_hosts(cfg: AppConfig) -> list[HostEntry]:
    directory = cfg.directory
    if not directory.enabled:
        return []

    try:
        response = requests.get(directory.url, timeout=directory.timeout_s)
        response.raise_for_status()
        data = response.json()
        return [
            HostEntry(
                code=str(item[directory.code_field]),
                name=str(item[directory.name_field]),
                host=str(item[directory.host_field]),
            )
            for item in data
        ]
    except Exception:
        logger.warning("Failed to fetch host directory from %s", directory.url, exc_info=True)
        return []
