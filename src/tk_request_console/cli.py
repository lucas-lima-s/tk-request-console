from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from tk_request_console.client import send_request
from tk_request_console.config import AppConfig, load_config
from tk_request_console.errors import AppError, ConfigError, TransportError
from tk_request_console.logging_setup import configure_logging
from tk_request_console.profiles import list_profiles, load_profile
from tk_request_console.protocol import RequestSpec, build_url


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tk-request-console")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--profile", type=Path, default=None)
    sub = parser.add_subparsers(dest="command")

    gui_parser = sub.add_parser("gui", help="Launch the graphical console")
    gui_parser.add_argument("--config", type=Path, default=None)
    gui_parser.add_argument("--profile", type=Path, default=None)

    url_parser = sub.add_parser("url", help="Print the URL for a profile without sending it")
    url_parser.add_argument("--profile", type=Path, required=True)
    url_parser.add_argument("--host", default=None)
    url_parser.add_argument("--json", action="store_true")

    send_parser = sub.add_parser("send", help="Send a profile's request")
    send_parser.add_argument("--profile", type=Path, required=True)
    send_parser.add_argument("--host", default=None)
    send_parser.add_argument("--port", type=int, default=None)
    payload_group = send_parser.add_mutually_exclusive_group()
    payload_group.add_argument("--payload", default=None)
    payload_group.add_argument("--payload-file", type=Path, default=None)
    send_parser.add_argument("--json", action="store_true")

    profiles_parser = sub.add_parser("profiles", help="List available profiles")
    profiles_parser.add_argument("--dir", type=Path, default=Path("profiles"))

    config_check_parser = sub.add_parser("config-check", help="Validate a config file")
    config_check_parser.add_argument("--config", type=Path, default=None)

    return parser


def _load_spec(
    profile_path: Path,
    *,
    host: str | None = None,
    port: int | None = None,
    payload: str | None = None,
) -> RequestSpec:
    profile = load_profile(profile_path)
    spec = profile.to_request_spec()
    if host is None and port is None and payload is None:
        return spec
    return RequestSpec(
        host=host if host is not None else spec.host,
        port=port if port is not None else spec.port,
        group=spec.group,
        action=spec.action,
        token=spec.token,
        fmt=spec.fmt,
        timeout=spec.timeout,
        base64_encode=spec.base64_encode,
        interpret_escapes=spec.interpret_escapes,
        payload=payload if payload is not None else spec.payload,
    )


def _cmd_url(cfg: AppConfig, args: argparse.Namespace) -> int:
    spec = _load_spec(args.profile, host=args.host)
    url = build_url(cfg.endpoint, spec)
    if args.json:
        print(json.dumps({"url": url}))
    else:
        print(url)
    return 0


def _cmd_send(cfg: AppConfig, args: argparse.Namespace) -> int:
    payload = args.payload
    if args.payload_file is not None:
        payload = args.payload_file.read_text(encoding="utf-8")
    spec = _load_spec(args.profile, host=args.host, port=args.port, payload=payload)

    try:
        response = send_request(cfg, spec)
    except TransportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "url": response.url,
                    "status": response.status_code,
                    "elapsed_ms": response.elapsed_ms,
                    "body": response.text,
                }
            )
        )
    else:
        print(f"{response.status_code} {response.text}")
    return 0 if 200 <= response.status_code < 300 else 1


def _cmd_profiles(args: argparse.Namespace) -> int:
    for profile in list_profiles(args.dir):
        print(f"{profile.name}: {profile.description}")
    return 0


def _config_to_dict(cfg: AppConfig) -> dict:
    return asdict(cfg)


def _cmd_config_check(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(_config_to_dict(cfg), indent=2))
    return 0


def _cmd_gui(cfg: AppConfig, args: argparse.Namespace) -> int:
    from tk_request_console.app import build_root

    profile_path = getattr(args, "profile", None)
    profile = load_profile(profile_path) if profile_path else None
    root = build_root(cfg, config_path=getattr(args, "config", None), profile=profile)
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command or "gui"

    if command == "config-check":
        return _cmd_config_check(args)

    try:
        cfg = load_config(getattr(args, "config", None))
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    configure_logging(cfg.log_file, verbose=False)

    try:
        if command == "gui":
            return _cmd_gui(cfg, args)
        if command == "url":
            return _cmd_url(cfg, args)
        if command == "send":
            return _cmd_send(cfg, args)
        if command == "profiles":
            return _cmd_profiles(args)
    except AppError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
