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

_ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


def browser_path() -> str | None:
    roots = [
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    names = (
        r"Microsoft\Edge\Application\msedge.exe",
        r"Google\Chrome\Application\chrome.exe",
    )
    for root in roots:
        if not root:
            continue
        for name in names:
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


def _keep_large_enough(hwnd: int, stop: list[bool]) -> None:
    user32 = _user32()
    rect = wintypes.RECT()
    while not stop[0]:
        if not user32.IsWindow(hwnd):
            return
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if 0 < width < 640 or 0 < height < 420:
                user32.SetWindowPos(
                    hwnd,
                    None,
                    rect.left,
                    rect.top,
                    max(width, 640),
                    max(height, 420),
                    0x0004 | 0x0010,
                )
        time.sleep(0.2)


def run_edge_window(url: str, on_top: bool) -> bool:
    global APP_HWND
    executable = browser_path()
    if executable is None:
        return False
    profile = Path(os.environ.get("LOCALAPPDATA", ".")) / "AutoTyper" / "autotyper-shell"
    arguments = " ".join(
        [
            f"--app={url}",
            f'--user-data-dir="{profile}"',
            "--window-size=1040,660",
            "--no-first-run",
            "--no-default-browser-check",
        ]
    )
    hwnd = 0
    for attempt in range(2):
        profile.mkdir(parents=True, exist_ok=True)
        if not _open_browser(executable, arguments):
            return False
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline and not hwnd:
            hwnd = _window_for_pids(_profile_pids("autotyper-shell"))
            if not hwnd:
                time.sleep(0.4)
        if hwnd:
            break
        shutil.rmtree(profile, ignore_errors=True)
    if not hwnd:
        return False
    APP_HWND = hwnd
    set_topmost(on_top)
    stop = [False]
    import threading

    threading.Thread(target=_keep_large_enough, args=(hwnd, stop), name="window-size", daemon=True).start()
    user32 = _user32()
    while True:
        if user32.IsWindow(hwnd):
            time.sleep(0.3)
            continue
        replacement = 0
        again = time.monotonic() + 4
        while time.monotonic() < again and not replacement:
            replacement = _window_for_pids(_profile_pids("autotyper-shell"))
            if not replacement:
                time.sleep(0.4)
        if not replacement:
            break
        hwnd = replacement
        APP_HWND = hwnd
        set_topmost(on_top)
    stop[0] = True
    APP_HWND = 0
    return True
