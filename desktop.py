"""Open Auto Typer in its own window. This path does not use the blocked .NET runtime."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

APP_HWND = 0
MIN_WIDTH = 681
MIN_HEIGHT = 453

_ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


def browser_path() -> str | None:
    roots = [
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    names = (
        r"Google\Chrome\Application\chrome.exe",
        r"Microsoft\Edge\Application\msedge.exe",
    )
    for name in names:
        for root in roots:
            if not root:
                continue
            candidate = Path(root) / name
            if candidate.is_file():
                return str(candidate)
    return None


def _user32():
    user32 = ctypes.windll.user32
    user32.EnumWindows.argtypes = [_ENUM, ctypes.c_void_p]
    user32.EnumWindows.restype = ctypes.c_bool
    user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
    user32.IsWindowVisible.restype = ctypes.c_bool
    user32.IsWindow.argtypes = [ctypes.c_void_p]
    user32.IsWindow.restype = ctypes.c_bool
    user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
    user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = ctypes.c_bool
    user32.SetWindowPos.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = ctypes.c_bool
    return user32


def _title(user32, hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _image_path(pid: int) -> str:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.QueryFullProcessImageNameW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    kernel32.QueryFullProcessImageNameW.restype = ctypes.c_bool
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return ""
    try:
        size = ctypes.c_ulong(1024)
        buffer = ctypes.create_unicode_buffer(1024)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return buffer.value
    finally:
        kernel32.CloseHandle(handle)


def _browser_window() -> int:
    user32 = _user32()
    found: list[int] = []

    def visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if _title(user32, hwnd) != "Auto Typer":
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        image = _image_path(pid.value).lower()
        if image.endswith("\\msedge.exe") or image.endswith("\\chrome.exe"):
            found.append(int(hwnd))
        return True

    user32.EnumWindows(_ENUM(visit), None)
    return found[-1] if found else 0


def _profile_pids(token: str) -> set[int]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { ($_.Name -eq 'msedge.exe' -or $_.Name -eq 'chrome.exe') "
        f"-and $_.CommandLine -like '*{token}*' }} | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        text = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            timeout=8,
        )
    except (subprocess.SubprocessError, OSError):
        return set()
    return {int(line) for line in text.split() if line.strip().isdigit()}


def _window_for_pids(pids: set[int]) -> int:
    if not pids:
        return 0
    user32 = _user32()
    exact = 0
    other = 0

    def visit(hwnd, _lparam):
        nonlocal exact, other
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value not in pids:
            return True
        title = _title(user32, hwnd)
        if title == "Auto Typer":
            exact = int(hwnd)
        elif title and not other:
            other = int(hwnd)
        return True

    user32.EnumWindows(_ENUM(visit), None)
    return exact or other


def _open_browser(executable: str, arguments: str) -> bool:
    shell32 = ctypes.windll.shell32
    shell32.ShellExecuteW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_int,
    ]
    shell32.ShellExecuteW.restype = ctypes.c_void_p
    return int(shell32.ShellExecuteW(None, "open", executable, arguments, None, 1)) > 32


def _place_on_screen(hwnd: int, on_top: bool) -> None:
    user32 = _user32()
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.ShowWindow.restype = ctypes.c_bool
    user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    user32.SetForegroundWindow.restype = ctypes.c_bool
    user32.ShowWindow(hwnd, 9)
    user32.SetWindowPos(
        hwnd,
        ctypes.c_void_p(-1 if on_top else 0),
        100,
        80,
        1040,
        660,
        0x0040,
    )
    user32.SetForegroundWindow(hwnd)


def set_topmost(enabled: bool) -> None:
    if not APP_HWND:
        return
    _user32().SetWindowPos(
        APP_HWND,
        ctypes.c_void_p(-1 if enabled else -2),
        0,
        0,
        0,
        0,
        0x0001 | 0x0002 | 0x0010,
    )


def set_run_style(active: bool) -> None:
    if not APP_HWND:
        return
    user32 = _user32()
    get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    get_long.argtypes = [ctypes.c_void_p, ctypes.c_int]
    get_long.restype = ctypes.c_ssize_t
    set_long.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
    set_long.restype = ctypes.c_ssize_t
    style = get_long(APP_HWND, -20)
    noactivate = 0x08000000
    style = style | noactivate if active else style & ~noactivate
    set_long(APP_HWND, -20, style)
    user32.SetWindowPos(APP_HWND, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)


_EVENT_PROC = None


def _cursor_point(user32):
    point = wintypes.POINT()
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = ctypes.c_bool
    if not user32.GetCursorPos(ctypes.byref(point)):
        return None
    return point


def _clip_resize(user32, hwnd: int, edges: dict) -> None:
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return
    point = _cursor_point(user32)
    if point is None:
        return
    margin = 18
    edges["left"] = point.x <= rect.left + margin
    edges["right"] = point.x >= rect.right - margin
    edges["top"] = point.y <= rect.top + margin
    edges["bottom"] = point.y >= rect.bottom - margin
    if not any(edges.values()):
        return
    clip = wintypes.RECT()
    clip.left = user32.GetSystemMetrics(76)
    clip.top = user32.GetSystemMetrics(77)
    clip.right = clip.left + user32.GetSystemMetrics(78)
    clip.bottom = clip.top + user32.GetSystemMetrics(79)
    if edges["right"]:
        clip.left = max(clip.left, rect.left + MIN_WIDTH)
    if edges["left"]:
        clip.right = min(clip.right, rect.right - MIN_WIDTH)
    if edges["bottom"]:
        clip.top = max(clip.top, rect.top + MIN_HEIGHT)
    if edges["top"]:
        clip.bottom = min(clip.bottom, rect.bottom - MIN_HEIGHT)
    if clip.left >= clip.right or clip.top >= clip.bottom:
        return
    user32.ClipCursor.argtypes = [ctypes.c_void_p]
    user32.ClipCursor.restype = ctypes.c_bool
    user32.ClipCursor(ctypes.byref(clip))


def _snap_minimum(user32, hwnd: int, edges: dict | None) -> None:
    if not hwnd or not user32.IsWindow(hwnd):
        return
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width >= MIN_WIDTH and height >= MIN_HEIGHT:
        return
    if width <= 0 or height <= 0:
        return
    new_width = max(width, MIN_WIDTH)
    new_height = max(height, MIN_HEIGHT)
    left, top = rect.left, rect.top
    if edges and edges.get("left") and width < MIN_WIDTH:
        left = rect.right - new_width
    if edges and edges.get("top") and height < MIN_HEIGHT:
        top = rect.bottom - new_height
    user32.SetWindowPos(
        hwnd,
        None,
        left,
        top,
        new_width,
        new_height,
        0x0004 | 0x0010,
    )


def _keep_large_enough(stop: list[bool]) -> None:
    global _EVENT_PROC
    user32 = _user32()
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.ClipCursor.argtypes = [ctypes.c_void_p]
    user32.ClipCursor.restype = ctypes.c_bool
    user32.SetWinEventHook.restype = ctypes.c_void_p
    user32.UnhookWinEvent.argtypes = [ctypes.c_void_p]
    user32.UnhookWinEvent.restype = ctypes.c_bool
    user32.PeekMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG),
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    user32.PeekMessageW.restype = ctypes.c_bool
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.MsgWaitForMultipleObjects.argtypes = [
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_bool,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    user32.MsgWaitForMultipleObjects.restype = ctypes.c_uint
    edges = {"left": False, "right": False, "top": False, "bottom": False}
    sizing = {"on": False}

    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetAncestor.restype = ctypes.c_void_p

    def same_window(hwnd) -> bool:
        target = int(APP_HWND or 0)
        current = int(hwnd or 0)
        if not target or not current:
            return False
        if current == target:
            return True
        return int(user32.GetAncestor(current, 2) or 0) == target

    def on_event(_hook, event, hwnd, _id_object, _id_child, _thread, _clock):
        try:
            if not same_window(hwnd):
                return
            target = int(APP_HWND or 0)
            if event == 0x000A:
                sizing["on"] = True
                _clip_resize(user32, target, edges)
            elif event == 0x000B:
                sizing["on"] = False
                user32.ClipCursor(None)
                _snap_minimum(user32, target, edges)
        except Exception:
            return

    proc_type = ctypes.WINFUNCTYPE(
        None,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_long,
        ctypes.c_long,
        ctypes.c_uint,
        ctypes.c_uint,
    )
    _EVENT_PROC = proc_type(on_event)
    user32.SetWinEventHook.argtypes = [
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
        proc_type,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_uint,
    ]
    hook = user32.SetWinEventHook(0x000A, 0x000B, None, _EVENT_PROC, 0, 0, 0)
    message = wintypes.MSG()
    try:
        while not stop[0]:
            user32.MsgWaitForMultipleObjects(0, None, False, 50, 0x04FF)
            while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
            button_down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
            if sizing["on"] and not button_down:
                sizing["on"] = False
                user32.ClipCursor(None)
                _snap_minimum(user32, int(APP_HWND or 0), edges)
            elif not button_down:
                _snap_minimum(user32, int(APP_HWND or 0), None)
    finally:
        user32.ClipCursor(None)
        if hook:
            user32.UnhookWinEvent(hook)


def _launch_profile(executable: str, url: str, folder: str) -> int:
    profile = Path(os.environ.get("LOCALAPPDATA", ".")) / "AutoTyper" / folder
    profile.mkdir(parents=True, exist_ok=True)
    arguments = " ".join(
        [
            f"--app={url}",
            f'--user-data-dir="{profile}"',
            "--window-size=1040,660",
            "--window-position=100,80",
            "--no-first-run",
            "--no-default-browser-check",
        ]
    )
    if not _open_browser(executable, arguments):
        return 0
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        hwnd = _window_for_pids(_profile_pids(folder))
        if hwnd:
            return hwnd
        time.sleep(0.3)
    return 0


def run_edge_window(url: str, on_top: bool, on_ready=None) -> bool:
    global APP_HWND
    executable = browser_path()
    if executable is None:
        return False
    folder = "chrome-window" if executable.lower().endswith("chrome.exe") else "edge-window"
    hwnd = _launch_profile(executable, url, folder)
    if not hwnd:
        profile = Path(os.environ.get("LOCALAPPDATA", ".")) / "AutoTyper" / folder
        broken = profile.with_name(folder + "-reset")
        shutil.rmtree(broken, ignore_errors=True)
        try:
            if profile.exists():
                profile.rename(broken)
        except OSError:
            shutil.rmtree(profile, ignore_errors=True)
        hwnd = _launch_profile(executable, url, folder)
    if not hwnd:
        return False
    APP_HWND = hwnd
    _place_on_screen(hwnd, on_top)
    if on_ready is not None:
        on_ready()
    stop = [False]
    import threading

    threading.Thread(target=_keep_large_enough, args=(stop,), name="window-size", daemon=True).start()
    user32 = _user32()
    missing_since = 0.0
    while True:
        current = hwnd if user32.IsWindow(hwnd) else 0
        if not current:
            current = _browser_window()
        if current:
            if current != hwnd:
                hwnd = current
                APP_HWND = hwnd
                _place_on_screen(hwnd, on_top)
            missing_since = 0.0
            time.sleep(0.3)
            continue
        if not missing_since:
            missing_since = time.monotonic()
        if time.monotonic() - missing_since > 8:
            break
        time.sleep(0.3)
    stop[0] = True
    APP_HWND = 0
    return True
