"""Auto Typer as a Windows window, or in the browser with --web."""

from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from engine import VERSION, TyperEngine, bundle_dir

WEB = bundle_dir() / "web"
ENGINE = TyperEngine()
WINDOW = None

FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/favicon.ico": ("favicon.ico", "image/x-icon"),
    "/favicon.png": ("favicon.png", "image/png"),
    "/favicon-256.png": ("favicon-256.png", "image/png"),
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
            raw_drag = payload.get("dragging")
            slider = payload.get("slider")
            span = None
            if isinstance(slider, dict) and "left" in slider and "right" in slider:
                span = (slider.get("left"), slider.get("right"))
            ENGINE.set_speed(
                int(payload.get("speed", 4)),
                None if raw_drag is None else bool(raw_drag),
                span,
            )
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
            else:
                import desktop

                desktop.set_topmost(value)
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


def _keep_target_focused(active: bool) -> None:
    if sys.platform != "win32":
        return
    native = getattr(WINDOW, "native", None) if WINDOW is not None else None
    if native is None:
        import desktop

        desktop.set_run_style(active)
        return

    def apply() -> None:
        try:
            hwnd = int(native.Handle.ToInt64())
        except Exception:
            hwnd = int(native.Handle)
        user32 = ctypes.windll.user32
        get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
        get_long.argtypes = [ctypes.c_void_p, ctypes.c_int]
        get_long.restype = ctypes.c_ssize_t
        set_long.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
        set_long.restype = ctypes.c_ssize_t
        style = get_long(hwnd, -20)
        noactivate = 0x08000000
        appwindow = 0x00040000
        if active:
            style = style | noactivate | appwindow
        else:
            style = style & ~noactivate
        set_long(hwnd, -20, style)
        user32.SetWindowPos.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = ctypes.c_int
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)

    try:
        if bool(getattr(native, "InvokeRequired", False)):
            from System import Action

            native.BeginInvoke(Action(apply))
            return
    except Exception:
        pass
    apply()


def _run_webview(local: str) -> bool:
    try:
        module = __import__("web" + "view")
    except Exception:
        return False
    global WINDOW
    try:
        WINDOW = module.create_window(
            f"Auto Typer {VERSION}",
            local,
            width=1040,
            height=660,
            min_size=(681, 453),
            background_color="#1C1F2B",
            text_select=True,
            on_top=bool(ENGINE.settings.get("always_on_top")),
        )
        module.start()
    except Exception:
        WINDOW = None
        return False
    return True


def main() -> None:
    web = "--web" in sys.argv[1:]
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
    print(f"Auto Typer {VERSION}", flush=True)
    print(f"  {'Web' if web else 'Window'}:  {local}", flush=True)
    threading.Thread(target=server.serve_forever, name="autotyper-http", daemon=True).start()
    try:
        if web:
            import webbrowser

            webbrowser.open(local)
            if getattr(sys, "frozen", False) and sys.stdout is None:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    "Auto Typer is open in your browser.\nClose this message to quit.",
                    f"Auto Typer {VERSION}",
                    0,
                )
            else:
                try:
                    while True:
                        threading.Event().wait(0.5)
                except KeyboardInterrupt:
                    pass
            return
        ENGINE.set_run_hook(_keep_target_focused)
        if os.environ.get("AUTOTYPER_EDGE") == "1" or not _run_webview(local):
            import desktop

            if not desktop.run_edge_window(
                local,
                bool(ENGINE.settings.get("always_on_top")),
                on_ready=ENGINE.start_hotkeys,
            ):
                ctypes.windll.user32.MessageBoxW(
                    None,
                    "Auto Typer could not open its window.",
                    f"Auto Typer {VERSION}",
                    0,
                )
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
