import 'package:flutter/services.dart';

import 'hotkey_chord.dart';

class AppSettings {
  const AppSettings({
    required this.startDelay,
    required this.defaultSpeed,
    required this.mistakeFrequency,
    required this.mistakeLength,
    required this.startPause,
    required this.reset,
    required this.alwaysOnTop,
  });

  final int startDelay;
  final int defaultSpeed;
  final int mistakeFrequency;
  final int mistakeLength;
  final HotkeyChord startPause;
  final HotkeyChord reset;
  final bool alwaysOnTop;

  static final defaults = AppSettings(
    startDelay: 1,
    defaultSpeed: 4,
    mistakeFrequency: 2,
    mistakeLength: 3,
    startPause: HotkeyChord.ctrl(LogicalKeyboardKey.arrowUp),
    reset: HotkeyChord.ctrl(LogicalKeyboardKey.arrowDown),
    alwaysOnTop: false,
  );

  AppSettings copyWith({
    int? startDelay,
    int? defaultSpeed,
    int? mistakeFrequency,
    int? mistakeLength,
    HotkeyChord? startPause,
    HotkeyChord? reset,
    bool? alwaysOnTop,
  }) {
    return AppSettings(
      startDelay: startDelay ?? this.startDelay,
      defaultSpeed: defaultSpeed ?? this.defaultSpeed,
      mistakeFrequency: mistakeFrequency ?? this.mistakeFrequency,
      mistakeLength: mistakeLength ?? this.mistakeLength,
      startPause: startPause ?? this.startPause,
      reset: reset ?? this.reset,
      alwaysOnTop: alwaysOnTop ?? this.alwaysOnTop,
    );
  }
}
