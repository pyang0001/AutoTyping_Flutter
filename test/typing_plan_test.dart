import 'package:auto_typer/src/app_settings.dart';
import 'package:auto_typer/src/hotkey_chord.dart';
import 'package:auto_typer/src/typing_plan.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'dart:math';

void main() {
  test('defaults match the settings dialog', () {
    final settings = AppSettings.defaults;
    expect(settings.startDelay, 1);
    expect(settings.defaultSpeed, 4);
    expect(settings.mistakeFrequency, 2);
    expect(settings.mistakeLength, 3);
    expect(settings.startPause.label, 'Ctrl+Up');
    expect(settings.reset.label, 'Ctrl+Down');
    expect(settings.alwaysOnTop, isFalse);
  });

  test('hotkey chords round-trip and reject duplicates', () {
    final chord = HotkeyChord.ctrl(LogicalKeyboardKey.arrowUp);
    final decoded = HotkeyChord.decode(chord.encode());
    expect(decoded, isNotNull);
    expect(decoded!.sameAs(chord), isTrue);
    expect(decoded.label, 'Ctrl+Up');
    expect(chord.sameAs(HotkeyChord.ctrl(LogicalKeyboardKey.arrowDown)), isFalse);
  });

  test('mistakes stay off at frequency zero and skip whitespace', () {
    final random = Random(1);
    expect(shouldMistake(random, 0, 'a'), isFalse);
    expect(shouldMistake(random, 50, ' '), isFalse);
    expect(shouldMistake(random, 50, '\n'), isFalse);
  });

  test('mistake length stays near the requested average', () {
    final random = Random(2);
    for (var i = 0; i < 30; i++) {
      final length = sampleMistakeLength(random, 3);
      expect(length, inInclusiveRange(2, 4));
    }
    expect(sampleMistakeLength(random, 1), 1);
  });

  test('wrong characters keep case and are a single key', () {
    final random = Random(3);
    for (var i = 0; i < 20; i++) {
      final lower = wrongCharacter(random, 'a');
      final upper = wrongCharacter(random, 'A');
      expect(lower.length, 1);
      expect(lower, isNot('a'));
      expect(upper, upper.toUpperCase());
      expect(upper.toLowerCase(), isNot('a'));
    }
  });

  test('newline pairs are one typing unit', () {
    expect(readUnit('a\r\nb', 1), '\r\n');
    expect(readUnit('ab', 0), 'a');
    expect(isNewline('\n'), isTrue);
  });
}
