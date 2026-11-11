import 'package:shared_preferences/shared_preferences.dart';

import 'app_settings.dart';
import 'hotkey_chord.dart';

class SettingsStore {
  static const _delay = 'startDelay';
  static const _speed = 'defaultSpeed';
  static const _frequency = 'mistakeFrequency';
  static const _length = 'mistakeLength';
  static const _start = 'startPauseHotkey';
  static const _reset = 'resetHotkey';
  static const _top = 'alwaysOnTop';

  static Future<AppSettings> load() async {
    final prefs = await SharedPreferences.getInstance();
    final defaults = AppSettings.defaults;
    return AppSettings(
      startDelay: prefs.getInt(_delay) ?? defaults.startDelay,
      defaultSpeed: prefs.getInt(_speed) ?? defaults.defaultSpeed,
      mistakeFrequency: prefs.getInt(_frequency) ?? defaults.mistakeFrequency,
      mistakeLength: prefs.getInt(_length) ?? defaults.mistakeLength,
      startPause: HotkeyChord.decode(prefs.getString(_start)) ?? defaults.startPause,
      reset: HotkeyChord.decode(prefs.getString(_reset)) ?? defaults.reset,
      alwaysOnTop: prefs.getBool(_top) ?? defaults.alwaysOnTop,
    );
  }

  static Future<void> save(AppSettings settings) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_delay, settings.startDelay);
    await prefs.setInt(_speed, settings.defaultSpeed);
    await prefs.setInt(_frequency, settings.mistakeFrequency);
    await prefs.setInt(_length, settings.mistakeLength);
    await prefs.setString(_start, settings.startPause.encode());
    await prefs.setString(_reset, settings.reset.encode());
    await prefs.setBool(_top, settings.alwaysOnTop);
  }
}
