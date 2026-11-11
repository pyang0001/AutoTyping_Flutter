// ignore_for_file: deprecated_member_use
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:hotkey_manager/hotkey_manager.dart';
import 'package:window_manager/legacy.dart';

import 'app_settings.dart';
import 'hotkey_chord.dart';
import 'key_sender.dart';
import 'settings_store.dart';
import 'typing_plan.dart';

enum TyperPhase { ready, waiting, typing, paused, done }

extension TyperPhaseLabel on TyperPhase {
  String get label {
    switch (this) {
      case TyperPhase.ready:
        return 'Ready';
      case TyperPhase.waiting:
        return 'Waiting';
      case TyperPhase.typing:
        return 'Typing';
      case TyperPhase.paused:
        return 'Paused';
      case TyperPhase.done:
        return 'Done';
    }
  }
}

class TyperController extends ChangeNotifier {
  TyperController(this.settings)
      : speed = settings.defaultSpeed.clamp(1, 10),
        alwaysOnTop = settings.alwaysOnTop;

  AppSettings settings;
  String source = '';
  int index = 0;
  int speed;
  bool alwaysOnTop;
  TyperPhase phase = TyperPhase.ready;

  final _random = Random();
  int _generation = 0;
  bool _hotkeysOn = false;

  int get total => source.length;

  double get fraction {
    if (source.isEmpty || index <= 0) return 0;
    return (index / source.length).clamp(0, 1);
  }

  bool get running =>
      phase == TyperPhase.waiting || phase == TyperPhase.typing;

  Future<void> bindHotkeys() => _bindHotkeys();

  void setSpeed(int value) {
    final next = value.clamp(1, 10);
    if (next == speed) return;
    speed = next;
    notifyListeners();
  }

  void onTextChanged(String value) {
    if (running) return;
    source = value;
    index = 0;
    phase = TyperPhase.ready;
    notifyListeners();
  }

  Future<void> toggle() async {
    if (running) {
      _generation++;
      phase = TyperPhase.paused;
      notifyListeners();
      return;
    }
    if (source.isEmpty) return;
    if (phase == TyperPhase.done || index >= source.length) {
      index = 0;
    }

    final generation = ++_generation;
    phase = TyperPhase.waiting;
    notifyListeners();

    final slices = max(1, (settings.startDelay * 1000) ~/ 50);
    for (var i = 0; i < slices; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 50));
      if (!_alive(generation, TyperPhase.waiting)) return;
    }

    final giveUp = DateTime.now().add(const Duration(seconds: 30));
    while (KeySender.thisAppIsForeground()) {
      if (!_alive(generation, TyperPhase.waiting)) return;
      if (DateTime.now().isAfter(giveUp)) {
        phase = TyperPhase.paused;
        notifyListeners();
        return;
      }
      await Future<void>.delayed(const Duration(milliseconds: 80));
    }

    phase = TyperPhase.typing;
    notifyListeners();
    await _typeLoop(generation);
  }

  void reset() {
    _generation++;
    index = 0;
    phase = TyperPhase.ready;
    notifyListeners();
  }

  Future<void> setAlwaysOnTop(bool value) async {
    alwaysOnTop = value;
    settings = settings.copyWith(alwaysOnTop: value);
    await windowManager.setAlwaysOnTop(value);
    await SettingsStore.save(settings);
    notifyListeners();
  }

  Future<void> suspendHotkeys() async {
    _hotkeysOn = false;
    await hotKeyManager.unregisterAll();
  }

  Future<void> resumeHotkeys() => _bindHotkeys();

  Future<void> applySettings(AppSettings next) async {
    final topChanged = next.alwaysOnTop != alwaysOnTop;
    settings = next.copyWith(alwaysOnTop: alwaysOnTop);
    await SettingsStore.save(settings);
    await _bindHotkeys();
    if (topChanged) {
      await windowManager.setAlwaysOnTop(alwaysOnTop);
    }
    notifyListeners();
  }

  Future<void> _typeLoop(int generation) async {
    while (index < source.length) {
      if (!_alive(generation, TyperPhase.typing)) return;
      if (KeySender.thisAppIsForeground()) {
        phase = TyperPhase.paused;
        notifyListeners();
        return;
      }
      if (!await _waitUntilModifiersReleased(generation)) return;

      final unit = readUnit(source, index);
      if (unit.isEmpty) break;

      try {
        if (shouldMistake(_random, settings.mistakeFrequency, unit)) {
          final mistakes = sampleMistakeLength(_random, settings.mistakeLength);
          for (var i = 0; i < mistakes; i++) {
            KeySender.typeCharacter(wrongCharacter(_random, unit));
            if (!await _pause(generation, 1)) return;
          }
          if (!await _pause(generation, 1.35)) return;
          for (var i = 0; i < mistakes; i++) {
            KeySender.backspace();
            if (!await _pause(generation, 0.45)) return;
          }
        }
        KeySender.typeCharacter(unit);
      } catch (error, stack) {
        debugPrint('Typing stopped: $error\n$stack');
        phase = TyperPhase.paused;
        notifyListeners();
        return;
      }

      index = min(source.length, index + unit.length);
      notifyListeners();
      if (index >= source.length) break;
      if (!await _pause(generation, 1)) return;
    }

    if (_alive(generation, TyperPhase.typing)) {
      phase = TyperPhase.done;
      notifyListeners();
    }
  }

  Future<bool> _waitUntilModifiersReleased(int generation) async {
    var spins = 0;
    while (KeySender.modifiersHeld()) {
      if (!_alive(generation, TyperPhase.typing)) return false;
      if (spins++ > 80) return false;
      await Future<void>.delayed(const Duration(milliseconds: 25));
    }
    return true;
  }

  Future<bool> _pause(int generation, double factor) async {
    final base = (1000 / speed.clamp(1, 10)) * factor;
    final ms = (base * (0.82 + _random.nextDouble() * 0.36)).round().clamp(8, 5000);
    final steps = max(1, ms ~/ 30);
    final slice = ms / steps;
    for (var i = 0; i < steps; i++) {
      await Future<void>.delayed(
        Duration(microseconds: (slice * 1000).round()),
      );
      if (!_alive(generation, TyperPhase.typing)) return false;
    }
    return true;
  }

  bool _alive(int generation, TyperPhase expected) =>
      generation == _generation && phase == expected;

  Future<void> _bindHotkeys() async {
    await hotKeyManager.unregisterAll();
    _hotkeysOn = true;
    await _register(settings.startPause, 'start-pause', toggle);
    await _register(settings.reset, 'reset', () async => reset());
  }

  Future<void> _register(
    HotkeyChord chord,
    String identifier,
    Future<void> Function() onPressed,
  ) async {
    if (!_hotkeysOn) return;
    final modifiers = <HotKeyModifier>[
      if (chord.control) HotKeyModifier.control,
      if (chord.shift) HotKeyModifier.shift,
      if (chord.alt) HotKeyModifier.alt,
      if (chord.meta) HotKeyModifier.meta,
    ];
    final hotKey = HotKey(
      identifier: identifier,
      key: chord.logicalKey,
      modifiers: modifiers.isEmpty ? null : modifiers,
      scope: HotKeyScope.system,
    );
    try {
      await hotKeyManager.register(
        hotKey,
        keyDownHandler: (_) {
          onPressed();
        },
      );
    } on PlatformException catch (error) {
      debugPrint('Could not register $identifier: $error');
    }
  }
}
