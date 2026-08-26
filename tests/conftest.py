from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _display_available(attempts: int = 3) -> bool:
    import tkinter as tk

    for attempt in range(attempts):
        try:
            probe = tk.Tk()
        except tk.TclError:
            if attempt == attempts - 1:
                return False
            time.sleep(0.2)
            continue
        probe.destroy()
        return True
    return False


_DISPLAY_AVAILABLE = _display_available()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _DISPLAY_AVAILABLE:
        return
    skip_gui = pytest.mark.skip(reason="no Tk display available")
    for item in items:
        if "gui" in item.keywords:
            item.add_marker(skip_gui)


@pytest.fixture
def cfg():
    from tk_request_console.config import load_config

    return load_config(REPO_ROOT / "config.example.json")


@pytest.fixture
def echo_server():
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from echo_server import serve

    server = serve(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
