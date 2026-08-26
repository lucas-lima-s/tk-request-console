from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from tk_request_console.errors import ProfileError
from tk_request_console.protocol import RequestSpec


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
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

    def to_request_spec(self) -> RequestSpec:
        return RequestSpec(
            host=self.host,
            port=self.port,
            group=self.group,
            action=self.action,
            token=self.token,
            fmt=self.fmt,
            timeout=self.timeout,
            base64_encode=self.base64_encode,
            interpret_escapes=self.interpret_escapes,
            payload=self.payload,
        )


_FIELD_NAMES = [f.name for f in fields(Profile)]
_KEY_ORDER = [
    "name",
    "description",
    "host",
    "port",
    "group",
    "action",
    "token",
    "fmt",
    "timeout",
    "base64_encode",
    "interpret_escapes",
    "payload",
]


def list_profiles(directory: Path | str) -> list[Profile]:
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return [load_profile(path) for path in sorted(directory.glob("*.json"))]


def load_profile(path: Path | str) -> Profile:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileError(f"invalid JSON in profile '{path}': {exc}") from exc

    unknown = set(data) - set(_FIELD_NAMES)
    if unknown:
        raise ProfileError(f"unknown field in profile '{path}': {sorted(unknown)[0]}")

    missing = set(_FIELD_NAMES) - set(data)
    if missing:
        raise ProfileError(f"missing field in profile '{path}': {sorted(missing)[0]}")

    return Profile(**data)


def save_profile(path: Path | str, profile: Profile) -> None:
    path = Path(path)
    data = asdict(profile)
    ordered = {key: data[key] for key in _KEY_ORDER}
    path.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")
