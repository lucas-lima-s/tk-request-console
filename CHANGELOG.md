# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-26

### Added

- Config-driven endpoint model (`config.py`): scheme, host/port, HTTP
  method, `path_template`, a `query` placeholder map, `format_codes`,
  `bool_style`, and `token_mode`, with `.env` expansion via `${VAR_NAME}`
  and an explicit no-config-file fallback so the app always starts.
- Pure, unit-tested protocol core (`protocol.py`): token normalization
  (`auto`/`upper`/`int`/`raw`), format code lookup, boolean literal
  rendering, payload encoding (UTF-8, escape interpretation, base64), and
  URL building with full percent-encoding and empty-parameter omission.
- `client.py`: threaded-safe HTTP send with a client-side timeout mapping
  (`timeout <= 0` becomes no timeout) and a token-redacting logger — the
  token value never reaches a log record.
- Optional, disabled-by-default host directory (`directory.py`) that
  resolves an autocomplete host list from a configurable JSON endpoint,
  never raising into the UI.
- Named request profiles (`profiles.py`) with round-trip JSON
  load/save and three shipped examples: `echo`, `json-post`, `form-post`.
- Tkinter GUI (`app.py`): resizable grid layout, an always-live URL
  preview with the token masked, threaded send that doesn't freeze the
  window, and a rewritten `AutocompleteEntry` dropdown positioned from the
  entry's real screen coordinates.
- Headless CLI (`cli.py`) with `gui`, `url`, `send`, `profiles`, and
  `config-check` subcommands, and matching exit codes for scripting.
- Bundled stdlib echo server (`scripts/echo_server.py`) and a screenshot
  capture script (`scripts/capture_screenshot.py`) so the project is
  runnable and demonstrable without any external service.
- Full pytest suite covering the protocol core, config validation,
  profiles, the client, the directory feature, the CLI, the autocomplete
  widget, and repository hygiene (no leftover internal references, no
  Python 2 syntax).
- GitHub Actions CI on Linux (Python 3.11/3.12/3.13, under `xvfb`) and
  Windows (Python 3.12, native Tk).
