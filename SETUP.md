# Setup

This document covers everything needed to get `tk-request-console` running
locally for development: prerequisites, environment variables, first run,
and the commands used to validate a change before committing.

## Prerequisites

- Python 3.11, 3.12, or 3.13 (see `.python-version` for the version this
  repo was developed against).
- [`uv`](https://docs.astral.sh/uv/) for dependency management and running
  scripts.
- Tkinter, which ships with the standard CPython installer on Windows and
  macOS. On Debian/Ubuntu, install it separately: `sudo apt-get install
  python3-tk`. On Linux without a display (e.g. CI or a headless VM), the
  GUI-marked tests still run under a virtual framebuffer — see below.

No account, API key, or external service is required to build, test, or run
this project end to end; the bundled echo server (`scripts/echo_server.py`)
is a self-contained target for both the GUI and the CLI.

## Install dependencies

```bash
uv sync --frozen --dev
```

This creates `.venv/` and installs the pinned versions from `uv.lock`,
including the `dev` group (`pytest`, `ruff`, `pillow`).

## Environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

`.env` is loaded automatically (via `python-dotenv`) before config
resolution. Any `${VAR_NAME}` reference inside a string value in
`config.json` is expanded from the environment, so a real token or an
internal hostname never has to be committed. The shipped
`config.example.json` does not require any environment variable to be set;
`.env.example` documents the variable names a real deployment would use.

## Application config

Copy `config.example.json` to `config.json` and edit it to describe your own
endpoint, or run against the example config directly (most commands below
default to it). See the README's "The config model" section for the full
field reference and placeholder table.

## Run it

```bash
uv run python scripts/echo_server.py            # terminal 1: a local target
uv run tk-request-console --profile profiles/echo.json   # terminal 2: the GUI
```

or headless:

```bash
uv run tk-request-console send --profile profiles/echo.json --json
```

## Validate a change

Run these before committing, in order:

```bash
uv run ruff check .            # lint
uv run ruff format --check .   # formatting
uv run pytest -q               # unit + GUI tests (Windows: native Tk)
```

On Linux, the GUI-marked tests (`AutocompleteEntry` behavior, headless
import checks) need a display; run the suite under a virtual framebuffer so
they execute instead of skipping:

```bash
sudo apt-get install -y xvfb
xvfb-run -a uv run pytest -q
```

`tests/test_hygiene.py` also runs as part of `pytest`; it scans every
git-tracked file for banned internal references and Python-2 syntax and
does not need network access.

## Optional: a local executable

Not something this repo ships or commits (see the README's "Development"
section for why), but if you want one:

```bash
uv run pyinstaller --onefile --name tk-request-console src/tk_request_console/__main__.py
```

## Troubleshooting

- **`_tkinter` import error on Linux** — install `python3-tk` for your
  distribution's Python version, then re-run `uv sync`.
- **GUI tests reported as skipped, not passed** — no Tk display was
  available to the test process; run under `xvfb-run` (Linux) or on a
  machine with a real desktop session (Windows/macOS).
- **`ConfigError` on startup** — the message names the offending key; check
  it against the field reference in `README.md` and the dataclasses in
  `src/tk_request_console/config.py`.
