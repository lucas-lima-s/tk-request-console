from __future__ import annotations

import json
from pathlib import Path

import pytest

from tk_request_console.errors import ProfileError
from tk_request_console.profiles import Profile, list_profiles, load_profile, save_profile

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = REPO_ROOT / "profiles"


def make_profile(**overrides) -> Profile:
    base = dict(
        name="sample",
        description="A sample profile.",
        host="127.0.0.1",
        port=8080,
        group="echo",
        action="ping",
        token="",
        fmt="text",
        timeout=-1,
        base64_encode=False,
        interpret_escapes=False,
        payload="hello",
    )
    base.update(overrides)
    return Profile(**base)


def test_profile_round_trip(tmp_path):
    profile = make_profile()
    path = tmp_path / "sample.json"
    save_profile(path, profile)
    loaded = load_profile(path)
    assert loaded == profile


def test_profile_round_trip_key_order(tmp_path):
    profile = make_profile()
    path = tmp_path / "sample.json"
    save_profile(path, profile)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert list(data.keys()) == [
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


def test_profile_unknown_field_raises(tmp_path):
    path = tmp_path / "bad.json"
    data = json.loads(json.dumps(make_profile().__dict__))
    data["bogus_field"] = "x"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProfileError, match="bogus_field"):
        load_profile(path)


def test_profile_missing_field_raises(tmp_path):
    path = tmp_path / "incomplete.json"
    data = json.loads(json.dumps(make_profile().__dict__))
    del data["payload"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProfileError, match="payload"):
        load_profile(path)


def test_all_shipped_profiles_load():
    profiles = list_profiles(PROFILES_DIR)
    names = {p.name for p in profiles}
    assert names == {"echo", "json-post", "form-post"}
