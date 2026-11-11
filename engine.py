"""Typing session, saved settings, and Windows key injection."""

from __future__ import annotations

import json
import math
import random
import sys
import threading
import time
from pathlib import Path

from plan import (
    is_newline,
    read_unit,
    sample_mistake_length,
    should_mistake,
    wrong_character,
)

VERSION = "1.0.0"


def install_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", install_dir()))
    return Path(__file__).resolve().parent


SETTINGS_PATH = install_dir() / "settings.json"

DEFAULTS = {
    "start_delay": 1,
    "default_speed": 4,
    "mistake_frequency": 2,
    "mistake_length": 3,
    "start_hotkey": "Ctrl+Up",
    "reset_hotkey": "Ctrl+Down",
    "always_on_top": False,
}


def whole_number(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.startswith("-"):
        digits = text[1:]
        sign = -1
    else:
        digits = text
        sign = 1
    if not digits.isdigit():
        return None
    return sign * int(digits)


def is_hotkey_chord(label: object) -> bool:
    parsed = _parse_hotkey(str(label).strip())
    return parsed is not None and parsed[0] != 0


def settings_problems(raw: dict) -> list[str]:
    problems: list[str] = []
    if whole_number(raw.get("start_delay")) not in (1, 2, 3):
        problems.append("Start delay must be 1, 2, or 3.")
    speed = whole_number(raw.get("default_speed"))
    if speed is None or not 1 <= speed <= 30:
        problems.append("Default speed must be a number from 1 to 30.")
    frequency = whole_number(raw.get("mistake_frequency"))
    if frequency is None or not 0 <= frequency <= 10:
        problems.append("Mistake frequency must be a number from 0 to 10.")
    length = whole_number(raw.get("mistake_length"))
    if length is None or not 0 <= length <= 5:
        problems.append("Mistake length must be a number from 0 to 5.")
    start = str(raw.get("start_hotkey", "")).strip()
    reset = str(raw.get("reset_hotkey", "")).strip()
    if not is_hotkey_chord(start):
        problems.append(
            "Start / Pause hotkey must be a shortcut like Ctrl+Up, not a single character like s."
        )
    if not is_hotkey_chord(reset):
        problems.append(
            "Reset hotkey must be a shortcut like Ctrl+Down, not a single character like s."
        )
    if is_hotkey_chord(start) and is_hotkey_chord(reset) and start.lower() == reset.lower():
        problems.append("Start and reset need different shortcuts.")
    return problems


def accepted_settings(raw: dict) -> dict:
    return {
        "start_delay": whole_number(raw.get("start_delay")),
        "default_speed": whole_number(raw.get("default_speed")),
        "mistake_frequency": whole_number(raw.get("mistake_frequency")),
        "mistake_length": whole_number(raw.get("mistake_length")),
        "start_hotkey": str(raw.get("start_hotkey", "")).strip(),
        "reset_hotkey": str(raw.get("reset_hotkey", "")).strip(),
        "always_on_top": bool(raw.get("always_on_top")),
    }


def load_settings() -> dict:
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    data = dict(DEFAULTS)
    for key in ("start_delay", "default_speed", "mistake_frequency", "mistake_length"):
        if key in saved and settings_problems({**DEFAULTS, key: saved[key]}) == []:
            data[key] = whole_number(saved[key])
    for key in ("start_hotkey", "reset_hotkey"):
        if key in saved and is_hotkey_chord(saved[key]):
            data[key] = str(saved[key]).strip()
    if data["start_hotkey"].lower() == data["reset_hotkey"].lower():
        data["reset_hotkey"] = DEFAULTS["reset_hotkey"]
    if "always_on_top" in saved:
        data["always_on_top"] = bool(saved["always_on_top"])
    return data


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


class TyperEngine:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.text = ""
        self.index = 0
        self.speed = self.settings["default_speed"]
        self.phase = "ready"
        self._seconds_left = 0
        self._pause_reason = ""
        self._typo = ""
        self._speed_changed_at = 0.0
        self._generation = 0
        self._run_hook = None
        self._rng = random.Random()
        self._lock = threading.Lock()
        self._hotkeys_suspended = False
        self._hotkey_thread = None
        if sys.platform == "win32":
            self._hotkey_thread = threading.Thread(
                target=self._hotkey_loop, name="hotkeys", daemon=True
            )
            self._hotkey_thread.start()

    def snapshot(self) -> dict:
        with self._lock:
            total = len(self.text)
            fraction = 0 if total == 0 or self.index <= 0 else min(1, self.index / total)
            return {
                "phase": self.phase,
                "index": self.index,
                "total": total,
                "fraction": fraction,
                "speed": self.speed,
                "text": self.text,
                "running": self.phase in ("waiting", "typing"),
                "seconds_left": self._seconds_left if self.phase == "waiting" else 0,
                "pause_reason": self._pause_reason if self.phase == "paused" else "",
                "typo": self._typo if self.phase == "typing" else "",
                "settings": dict(self.settings),
                "can_type": sys.platform == "win32",
                "version": VERSION,
            }

    def set_text(self, value: str, _index: int | None = None) -> None:
        with self._lock:
            if self.phase in ("waiting", "typing"):
                return
            prefix = self.text[: self.index]
            if not value.startswith(prefix):
                return
            self.text = value
            self.index = min(self.index, len(self.text))
            self._place_phase()

    def set_index(self, value: int) -> None:
        with self._lock:
            if self.phase in ("waiting", "typing"):
                return
            self.index = self._clamp_index(value)
            self._place_phase()

    def _clamp_index(self, value: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = self.index
        return max(0, min(len(self.text), number))

    def _place_phase(self) -> None:
        if self.phase in ("waiting", "typing"):
            return
        if not self.text or self.index <= 0:
            self.phase = "ready"
            return
        if self.index >= len(self.text):
            if self.phase == "paused":
                self.phase = "done"
            return
        if self.phase in ("ready", "done"):
            self.phase = "paused"

    def set_run_hook(self, hook) -> None:
        self._run_hook = hook

    def set_speed(self, value: int) -> None:
        with self._lock:
            self.speed = max(1, min(30, int(value)))
            self._speed_changed_at = time.monotonic()

    def _speed_is_live(self) -> bool:
        with self._lock:
            changed = self._speed_changed_at
        return changed > 0 and time.monotonic() - changed < 1.5

    def _note_run(self, active: bool) -> None:
        hook = self._run_hook
        if hook is None:
            return
        try:
            hook(active)
        except Exception:
            return

    def toggle(self, text: str | None = None, speed: int | None = None) -> None:
        with self._lock:
            if self.phase in ("waiting", "typing"):
                self._generation += 1
                self.phase = "paused"
                self._pause_reason = "user"
                self._seconds_left = 0
                self._typo = ""
                return
            if text is not None and self.phase not in ("waiting", "typing"):
                if text != self.text:
                    prefix = self.text[: self.index]
                    if text.startswith(prefix):
                        self.text = text
                        self.index = min(self.index, len(self.text))
                    else:
                        self.text = text
                        self.index = 0
                        self.phase = "ready"
            if speed is not None:
                self.speed = max(1, min(30, int(speed)))
            if not self.text:
                return
            if self.index >= len(self.text):
                self.index = 0
            self._generation += 1
            generation = self._generation
            self.phase = "waiting"
            self._pause_reason = ""
            self._typo = ""
            delay = self.settings["start_delay"]
            self._seconds_left = max(1, int(delay))
            frequency = self.settings["mistake_frequency"]
            length = self.settings["mistake_length"]
        threading.Thread(
            target=self._run,
            args=(generation, delay, frequency, length),
            name="typer",
            daemon=True,
        ).start()

    def reset(self) -> None:
        with self._lock:
            self._generation += 1
            self.index = 0
            self.phase = "ready"
            self._pause_reason = ""
            self._typo = ""
            self._seconds_left = 0

    def set_always_on_top(self, value: bool) -> None:
        with self._lock:
            self.settings["always_on_top"] = bool(value)
            current = dict(self.settings)
        save_settings(current)

    def update_settings(self, raw: dict) -> str | None:
        problems = settings_problems(raw)
        if problems:
            return "\n".join(problems)
        nxt = accepted_settings(raw)
        with self._lock:
            self.settings = nxt
        save_settings(nxt)
        self._request_rebind()
        return None

    def suspend_hotkeys(self, suspended: bool) -> None:
        self._hotkeys_suspended = suspended
        self._request_rebind()

    def _mark_paused(self, generation: int, reason: str) -> bool:
        with self._lock:
            if self._generation != generation or self.phase not in ("waiting", "typing"):
                return False
            self.phase = "paused"
            self._pause_reason = reason
            self._seconds_left = 0
            self._typo = ""
            return True

    def _run(self, generation: int, delay: int, frequency: int, length: int) -> None:
        self._note_run(True)
        try:
            self._run_body(generation, delay, frequency, length)
        finally:
            self._note_run(False)

    def _run_body(self, generation: int, delay: int, frequency: int, length: int) -> None:
        deadline = time.monotonic() + max(0, delay)
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            with self._lock:
                if not self._alive(generation, "waiting"):
                    return
                self._seconds_left = max(1, math.ceil(remaining))
            time.sleep(0.05)
        give_up = time.monotonic() + 30
        while _this_process_is_foreground():
            if not self._alive(generation, "waiting"):
                return
            if time.monotonic() > give_up:
                self._mark_paused(generation, "focus")
                return
            time.sleep(0.08)
        target = _foreground_hwnd()
        with self._lock:
            if not self._alive(generation, "waiting"):
                return
            self.phase = "typing"
            self._seconds_left = 0
        self._type_loop(generation, frequency, length, target)

    def _type_loop(self, generation: int, frequency: int, length: int, target: int) -> None:
        while True:
            with self._lock:
                if not self._alive(generation, "typing"):
                    return
                if self.index >= len(self.text):
                    self.phase = "done"
                    self._typo = ""
                    return
                unit = read_unit(self.text, self.index)
                speed = self.speed
            if not unit:
                break
            current = _foreground_hwnd()
            ours = _this_process_is_foreground()
            action = focus_action(ours, current, target, self._speed_is_live())
            if action == "pause" and ours:
                time.sleep(0.15)
                action = focus_action(
                    _this_process_is_foreground(),
                    _foreground_hwnd(),
                    target,
                    self._speed_is_live(),
                )
            if action == "restore":
                _focus_hwnd(target)
                time.sleep(0.02)
                if _this_process_is_foreground() or _foreground_hwnd() != target:
                    time.sleep(0.04)
                    continue
            elif action == "pause":
                self._mark_paused(generation, "focus")
                return
            if not self._wait_modifiers(generation):
                return
            try:
                if should_mistake(self._rng, frequency, unit):
                    mistakes = sample_mistake_length(self._rng, length)
                    for _ in range(mistakes):
                        wrong = wrong_character(self._rng, unit)
                        with self._lock:
                            if not self._alive(generation, "typing"):
                                return
                            self._typo += wrong
                        _type_unit(wrong)
                        if not self._pause(generation, speed, 1):
                            return
                    if not self._pause(generation, speed, 1.35):
                        return
                    for _ in range(mistakes):
                        with self._lock:
                            if not self._alive(generation, "typing"):
                                return
                            self._typo = self._typo[:-1]
                        _backspace()
                        if not self._pause(generation, speed, 0.45):
                            return
                _type_unit(unit)
            except OSError:
                self._mark_paused(generation, "user")
                return
            with self._lock:
                if not self._alive(generation, "typing"):
                    return
                self.index = min(len(self.text), self.index + len(unit))
                finished = self.index >= len(self.text)
                if finished:
                    self.phase = "done"
                    self._typo = ""
                    return
            if not self._pause(generation, speed, 1):
                return

    def _pause(self, generation: int, speed: int, factor: float) -> bool:
        jitter = 0.82 + self._rng.random() * 0.36
        spent = 0.0
        while True:
            with self._lock:
                if not self._alive(generation, "typing"):
                    return False
                current = self.speed or speed
            total = (1 / max(1, min(30, int(current)))) * factor * jitter
            total = max(0.008, min(5.0, total))
            if spent >= total - 0.001:
                return True
            slice_s = min(0.03, total - spent)
            time.sleep(slice_s)
            spent += slice_s

    def _wait_modifiers(self, generation: int) -> bool:
        spins = 0
        while _modifiers_held():
            if not self._alive(generation, "typing"):
                return False
            spins += 1
            if spins > 80:
                return False
            time.sleep(0.025)
        return True

    def _alive(self, generation: int, expected: str) -> bool:
        return self._generation == generation and self.phase == expected

    def on_hotkey(self, hotkey_id: int) -> None:
        if self._hotkeys_suspended:
            return
        if hotkey_id == 1:
            self.toggle()
        elif hotkey_id == 2:
            self.reset()

    def _request_rebind(self) -> None:
        if sys.platform != "win32":
            return
        thread_id = getattr(self, "_hotkey_thread_id", 0)
        if thread_id:
            ctypes_post(thread_id)

    def _rebind_hotkeys(self) -> None:
        user32, _kernel32 = _win32()
        user32.UnregisterHotKey(None, 1)
        user32.UnregisterHotKey(None, 2)
        if self._hotkeys_suspended:
            return
        with self._lock:
            start = self.settings["start_hotkey"]
            reset = self.settings["reset_hotkey"]
        _register(user32, 1, start)
        _register(user32, 2, reset)

    def _hotkey_loop(self) -> None:
        import ctypes
        from ctypes import wintypes

        user32, kernel32 = _win32()
        self._hotkey_thread_id = kernel32.GetCurrentThreadId()
        self._rebind_hotkeys()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312:
                self.on_hotkey(int(msg.wParam))
            elif msg.message == 0x8000:
                self._rebind_hotkeys()


def ctypes_post(thread_id: int) -> None:
    user32, _kernel32 = _win32()
    user32.PostThreadMessageW(thread_id, 0x8000, 0, 0)


def _register(user32, hotkey_id: int, label: str) -> None:
    parsed = _parse_hotkey(label)
    if parsed is None:
        return
    modifiers, vk = parsed
    user32.RegisterHotKey(None, hotkey_id, modifiers, vk)


def _parse_hotkey(label: str) -> tuple[int, int] | None:
    parts = [part.strip().lower() for part in label.split("+") if part.strip()]
    if not parts:
        return None
    modifiers = 0
    key = None
    for part in parts:
        if part in ("ctrl", "control"):
            modifiers |= 0x0002
        elif part == "shift":
            modifiers |= 0x0004
        elif part in ("alt", "option"):
            modifiers |= 0x0001
        elif part in ("meta", "win", "cmd"):
            modifiers |= 0x0008
        else:
            key = part
    if key is None:
        return None
    vk = _virtual_key(key)
    if vk is None:
        return None
    return modifiers, vk


def _virtual_key(name: str) -> int | None:
    named = {
        "up": 0x26,
        "down": 0x28,
        "left": 0x25,
        "right": 0x27,
        "space": 0x20,
        "enter": 0x0D,
        "tab": 0x09,
        "esc": 0x1B,
        "escape": 0x1B,
        "backspace": 0x08,
        "delete": 0x2E,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
    }
    if name in named:
        return named[name]
    if len(name) == 1 and name.isalnum():
        return ord(name.upper())
    if name.startswith("f") and name[1:].isdigit():
        number = int(name[1:])
        if 1 <= number <= 12:
            return 0x70 + number - 1
    return None


def _win32():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if getattr(_win32, "ready", False):
        return user32, kernel32
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.UnregisterHotKey.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.GetMessageW.restype = ctypes.c_int
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostThreadMessageW.restype = wintypes.BOOL
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    kernel32.GetCurrentProcessId.restype = wintypes.DWORD
    _win32.ready = True
    return user32, kernel32


def focus_action(ours: bool, current: int, target: int, speed_live: bool) -> str:
    if ours:
        return "restore" if speed_live and target else "pause"
    if target and current and current != target:
        return "pause"
    return "type"


def _focus_hwnd(hwnd: int) -> None:
    if sys.platform != "win32" or not hwnd:
        return
    import ctypes

    user32, _kernel32 = _win32()
    user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    user32.SetForegroundWindow.restype = ctypes.c_int
    user32.SetForegroundWindow(hwnd)


def _foreground_hwnd() -> int:
    if sys.platform != "win32":
        return 0
    user32, _kernel32 = _win32()
    return int(user32.GetForegroundWindow() or 0)


def _this_process_is_foreground() -> bool:
    if sys.platform != "win32":
        return False
    import ctypes

    user32, kernel32 = _win32()
    hwnd = _foreground_hwnd()
    if not hwnd:
        return False
    pid = wintypes_dword()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == kernel32.GetCurrentProcessId()


def wintypes_dword():
    import ctypes
    from ctypes import wintypes

    return wintypes.DWORD()


def _modifiers_held() -> bool:
    if sys.platform != "win32":
        return False
    user32, _kernel32 = _win32()
    for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C):
        if user32.GetAsyncKeyState(vk) & 0x8000:
            return True
    return False


def _type_unit(unit: str) -> None:
    if is_newline(unit):
        _tap(0x0D)
        return
    if unit == "\t":
        _tap(0x09)
        return
    for char in unit:
        _unicode(char)


def _backspace() -> None:
    _tap(0x08)


def _tap(vk: int) -> None:
    _send_key(vk, 0)
    _send_key(vk, 0x0002)


def _unicode(char: str) -> None:
    code = ord(char)
    if code > 0xFFFF:
        code -= 0x10000
        _send_unicode(0xD800 + (code >> 10))
        _send_unicode(0xDC00 + (code & 0x3FF))
        return
    _send_unicode(code)


def _send_unicode(scan: int) -> None:
    _send_key(0, 0x0004, scan)
    _send_key(0, 0x0004 | 0x0002, scan)


def _send_key(vk: int, flags: int, scan: int = 0) -> None:
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    user32, _kernel32 = _win32()

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = (
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        )

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = (
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        )

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = (
            ("uMsg", wintypes.DWORD),
            ("wParamL", wintypes.WORD),
            ("wParamH", wintypes.WORD),
        )

    class INPUTUNION(ctypes.Union):
        _fields_ = (("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT))

    class INPUT(ctypes.Structure):
        _fields_ = (("type", wintypes.DWORD), ("union", INPUTUNION))

    if not getattr(_send_key, "ready", False):
        user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        user32.SendInput.restype = wintypes.UINT
        _send_key.input_cls = INPUT
        _send_key.ready = True
    event = _send_key.input_cls()
    event.type = 1
    event.union.ki.wVk = vk
    event.union.ki.wScan = scan
    event.union.ki.dwFlags = flags
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))
    if sent != 1:
        raise OSError("SendInput failed")
