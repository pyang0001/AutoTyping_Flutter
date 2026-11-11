import 'dart:ffi';

import 'package:ffi/ffi.dart';
import 'package:win32/win32.dart';

import 'typing_plan.dart';

class KeySender {
  static void typeCharacter(String unit) {
    if (isNewline(unit)) {
      _tap(VK_RETURN);
      return;
    }
    if (unit == '\t') {
      _tap(VK_TAB);
      return;
    }
    for (final codeUnit in unit.codeUnits) {
      _unicode(codeUnit);
    }
  }

  static void backspace() => _tap(VK_BACK);

  static bool thisAppIsForeground() {
    final foreground = GetForegroundWindow();
    if (foreground.address == 0) return false;
    final pid = calloc<Uint32>();
    try {
      GetWindowThreadProcessId(foreground, pid);
      return pid.value == GetCurrentProcessId();
    } finally {
      calloc.free(pid);
    }
  }

  static bool modifiersHeld() {
    return _down(VK_CONTROL) ||
        _down(VK_SHIFT) ||
        _down(VK_MENU) ||
        _down(VK_LWIN) ||
        _down(VK_RWIN);
  }

  static bool _down(VIRTUAL_KEY virtualKey) {
    final state = GetAsyncKeyState(virtualKey);
    return (state & 0x8000) != 0;
  }

  static void _tap(VIRTUAL_KEY virtualKey) {
    final input = calloc<INPUT>();
    try {
      input.ref.type = INPUT_KEYBOARD;
      input.ref.ki.wVk = virtualKey;
      SendInput(1, input, sizeOf<INPUT>());
      input.ref.ki.dwFlags = KEYEVENTF_KEYUP;
      SendInput(1, input, sizeOf<INPUT>());
    } finally {
      calloc.free(input);
    }
  }

  static void _unicode(int codeUnit) {
    final input = calloc<INPUT>();
    try {
      input.ref
        ..type = INPUT_KEYBOARD
        ..ki.wVk = const VIRTUAL_KEY(0)
        ..ki.wScan = codeUnit
        ..ki.dwFlags = KEYEVENTF_UNICODE;
      SendInput(1, input, sizeOf<INPUT>());
      input.ref.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;
      SendInput(1, input, sizeOf<INPUT>());
    } finally {
      calloc.free(input);
    }
  }
}
