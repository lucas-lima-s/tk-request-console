from __future__ import annotations

import argparse
import base64
import contextlib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit


class EchoHandler(BaseHTTPRequestHandler):
    def _handle(self) -> None:
        parsed = urlsplit(self.path)
        query = {
            key: values[0] if len(values) == 1 else values
            for key, values in parse_qs(parsed.query).items()
        }
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""

        status = 500 if parsed.path.rstrip("/").endswith("/fail") else 200
        payload = {
            "method": self.command,
            "path": parsed.path,
            "query": query,
            "headers_subset": {
                "content-type": self.headers.get("Content-Type", ""),
                "content-length": self.headers.get("Content-Length", ""),
            },
            "body_utf8": body.decode("utf-8", errors="replace"),
            "body_base64": base64.b64encode(body).decode("ascii"),
            "length": length,
        }
        encoded = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_PUT(self) -> None:
        self._handle()

    def do_PATCH(self) -> None:
        self._handle()

    def do_DELETE(self) -> None:
        self._handle()

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(port: int) -> HTTPServer:
    return HTTPServer(("127.0.0.1", port), EchoHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stdlib HTTP echo server for local testing.")
    parser.add_argument("--port", type=int, default=8099, help="use 0 for an ephemeral port")
    args = parser.parse_args(argv)

    server = serve(args.port)
    print(f"Echo server listening on http://127.0.0.1:{server.server_port}")
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
