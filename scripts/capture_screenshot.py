from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tk_request_console.app import build_root  # noqa: E402
from tk_request_console.config import load_config  # noqa: E402
from tk_request_console.profiles import load_profile  # noqa: E402


def _display_available() -> bool:
    import tkinter as tk

    try:
        probe = tk.Tk()
    except tk.TclError:
        return False
    probe.destroy()
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture a screenshot of the running app against the bundled echo server."
    )
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "docs" / "images" / "app.png")
    args = parser.parse_args(argv)

    try:
        from PIL import ImageGrab
    except ImportError:
        print(
            "Screenshot capture requires Pillow (install the dev dependency group).",
            file=sys.stderr,
        )
        return 1

    if not _display_available():
        print(
            "Screenshot capture requires an interactive desktop session; no display found.",
            file=sys.stderr,
        )
        return 1

    from echo_server import serve

    server = serve(0)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        cfg = load_config(REPO_ROOT / "config.example.json")
        profile = load_profile(REPO_ROOT / "profiles" / "echo.json")
        root = build_root(cfg, profile=profile)
        console = root.winfo_children()[0]
        console.host_var.set("127.0.0.1")
        console.port_var.set(str(port))

        def do_send() -> None:
            console.send()
            root.after(1500, capture)

        def capture() -> None:
            root.update_idletasks()
            x = root.winfo_rootx()
            y = root.winfo_rooty()
            width = root.winfo_width()
            height = root.winfo_height()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            image.save(args.output)
            root.destroy()

        root.after(300, do_send)
        root.mainloop()
    finally:
        server.shutdown()

    print(f"Saved screenshot to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
