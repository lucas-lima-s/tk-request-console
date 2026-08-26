# Contributing

Thanks for considering a contribution. This is a small personal project, but
issues and pull requests are welcome.

## Getting set up

See [SETUP.md](SETUP.md) for prerequisites, installing dependencies, and
running the app and its test suite locally.

## Reporting a bug

Open an issue with:

- What you ran (GUI, or the exact CLI command) and what you expected.
- What happened instead — the full error output, not a paraphrase.
- Your OS and Python version (`python --version`).
- Whether it reproduces against the bundled echo server
  (`scripts/echo_server.py`) with one of the shipped `profiles/*.json`, so
  the report doesn't depend on a config or endpoint only you have.

## Proposing a change

1. Open an issue first for anything beyond a small fix, so the direction is
   agreed before you invest time in it.
2. Fork the repo and create a branch off `main`.
3. Make the change, keeping it focused — unrelated cleanups belong in a
   separate PR.
4. Add or update tests. `protocol.py` and `client.py` are the unit-tested
   core; a behavior change there should come with an exact-value assertion,
   not just a smoke test.
5. Run the full check locally before opening the PR:

   ```bash
   uv run ruff check .
   uv run ruff format --check .
   uv run pytest -q            # or: xvfb-run -a uv run pytest -q on Linux
   ```

6. Open a pull request describing what changed and why. Link the issue it
   addresses.

## Code style

- Python, formatted and linted with `ruff` (config in `pyproject.toml`);
  `uv run ruff format .` before committing.
- `from __future__ import annotations` as the first statement in every
  module, and real PEP 484 type hints rather than string annotations.
- No inline comments. If a piece of logic needs explaining, that belongs in
  the commit message or the PR description, or the code should be
  restructured to make the intent obvious on its own.
- User-facing text (CLI output, GUI labels, error messages) is English.
- New config fields, placeholders, or CLI subcommands need a corresponding
  update to `README.md` (and `docs/protocol.md` for anything touching the
  endpoint template).

## Commit messages

Plain, imperative, present tense ("Add token redaction to client logger",
not "Added" or "Adding"). Keep the subject line under ~72 characters; use
the body for anything that needs more explanation.

## What CI checks

Every push and pull request runs `.github/workflows/ci.yml`: `ruff check`,
`ruff format --check`, and the full `pytest` suite on Linux (Python
3.11/3.12/3.13, under `xvfb`) and Windows (Python 3.12, native Tk). A PR
should be green on both jobs before review.
