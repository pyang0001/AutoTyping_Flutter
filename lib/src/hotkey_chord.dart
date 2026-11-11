import 'package:flutter/services.dart';

class HotkeyChord {
  const HotkeyChord({
    required this.control,
    required this.shift,
    required this.alt,
    required this.meta,
    required this.keyId,
  });

  final bool control;
  final bool shift;
  final bool alt;
  final bool meta;
  final int keyId;

  static HotkeyChord ctrl(LogicalKeyboardKey key) {
    return HotkeyChord(
      control: true,
      shift: false,
      alt: false,
      meta: false,
      keyId: key.keyId,
    );
  }

  LogicalKeyboardKey get logicalKey =>
      LogicalKeyboardKey.findKeyByKeyId(keyId) ?? LogicalKeyboardKey.arrowUp;

  bool sameAs(HotkeyChord other) {
    return control == other.control &&
        shift == other.shift &&
        alt == other.alt &&
        meta == other.meta &&
        keyId == other.keyId;
  }

  String encode() =>
      '${control ? 1 : 0},${shift ? 1 : 0},${alt ? 1 : 0},${meta ? 1 : 0},$keyId';

  static HotkeyChord? decode(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    final parts = raw.split(',');
    if (parts.length != 5) return null;
    final id = int.tryParse(parts[4]);
    if (id == null) return null;
    return HotkeyChord(
      control: parts[0] == '1',
      shift: parts[1] == '1',
      alt: parts[2] == '1',
      meta: parts[3] == '1',
      keyId: id,
    );
  }

  String get label {
    final names = <String>[
      if (control) 'Ctrl',
      if (shift) 'Shift',
      if (alt) 'Alt',
      if (meta) 'Win',
      keyLabel(logicalKey),
    ];
    return names.join('+');
  }
}

String keyLabel(LogicalKeyboardKey key) {
  if (key == LogicalKeyboardKey.arrowUp) return 'Up';
  if (key == LogicalKeyboardKey.arrowDown) return 'Down';
  if (key == LogicalKeyboardKey.arrowLeft) return 'Left';
  if (key == LogicalKeyboardKey.arrowRight) return 'Right';
  if (key == LogicalKeyboardKey.space) return 'Space';
  if (key == LogicalKeyboardKey.enter) return 'Enter';
  if (key == LogicalKeyboardKey.tab) return 'Tab';
  if (key == LogicalKeyboardKey.escape) return 'Esc';
  if (key == LogicalKeyboardKey.backspace) return 'Backspace';
  if (key == LogicalKeyboardKey.delete) return 'Delete';
  if (key == LogicalKeyboardKey.pageUp) return 'Page Up';
  if (key == LogicalKeyboardKey.pageDown) return 'Page Down';
  if (key == LogicalKeyboardKey.home) return 'Home';
  if (key == LogicalKeyboardKey.end) return 'End';
  final label = key.keyLabel;
  if (label.length == 1) return label.toUpperCase();
  return label;
}

bool isModifierKey(LogicalKeyboardKey key) {
  return key == LogicalKeyboardKey.controlLeft ||
      key == LogicalKeyboardKey.controlRight ||
      key == LogicalKeyboardKey.shiftLeft ||
      key == LogicalKeyboardKey.shiftRight ||
      key == LogicalKeyboardKey.altLeft ||
      key == LogicalKeyboardKey.altRight ||
      key == LogicalKeyboardKey.metaLeft ||
      key == LogicalKeyboardKey.metaRight;
}
