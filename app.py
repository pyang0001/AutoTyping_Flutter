"""Auto Typer as a Windows window. The page is drawn inside that window."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import webview

from engine import TyperEngine

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
ENGINE = TyperEngine()
WINDOW = None

FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self._json(200, ENGINE.snapshot())
            return
        spec = FILES.get(path)
        if spec is None:
            self.send_error(404)
            return
        name, content_type = spec
        body = (WEB / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        payload = self._read_json()
        if path == "/api/text":
            ENGINE.set_text(str(payload.get("text", "")), payload.get("index"))
            self._json(200, ENGINE.snapshot())
            return
        if path == "/api/index":
            ENGINE.set_index(payload.get("index", 0))
            self._json(200, ENGINE.snapshot())
            return
        if path == "/api/toggle":
            text = payload.get("text")
            speed = payload.get("speed")
            ENGINE.toggle(
                None if text is None else str(text),
                None if speed is None else int(speed),
            )
            self._json(200, ENGINE.snapshot())
            return
        if path == "/api/reset":
            ENGINE.reset()
            self._json(200, ENGINE.snapshot())
            return
        if path == "/api/speed":
            ENGINE.set_speed(int(payload.get("speed", 4)))
            self._json(200, ENGINE.snapshot())
            return
        if path == "/api/settings":
            error = ENGINE.update_settings(payload)
            if error:
                self._json(400, {"error": error})
                return
            self._json(200, ENGINE.snapshot())
            return
        if path == "/api/hotkeys":
            ENGINE.suspend_hotkeys(bool(payload.get("suspended")))
            self._json(200, {"ok": True})
            return
        if path == "/api/ontop":
            value = bool(payload.get("always_on_top"))
            ENGINE.set_always_on_top(value)
            if WINDOW is not None:
                WINDOW.on_top = value
            self._json(200, ENGINE.snapshot())
            return
        self.send_error(404)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = 8765
    server = None
    for candidate in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        print("Could not open a port for Auto Typer.")
        sys.exit(1)
    local = f"http://127.0.0.1:{port}"
    print("Auto Typer", flush=True)
    print(f"  Window:  {local}", flush=True)
    threading.Thread(target=server.serve_forever, name="autotyper-http", daemon=True).start()
    global WINDOW
    WINDOW = webview.create_window(
        "Auto Typer",
        local,
        width=1040,
        height=660,
        min_size=(640, 420),
        background_color="#1C1F2B",
        text_select=True,
        on_top=bool(ENGINE.settings.get("always_on_top")),
    )
    try:
        webview.start()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
