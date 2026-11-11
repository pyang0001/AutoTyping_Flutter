import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_settings.dart';
import 'hotkey_chord.dart';
import 'theme.dart';

enum _HotkeyField { start, reset }

class SettingsDialog extends StatefulWidget {
  const SettingsDialog({super.key, required this.initial});

  final AppSettings initial;

  @override
  State<SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends State<SettingsDialog> {
  late final TextEditingController _delay;
  late final TextEditingController _speed;
  late final TextEditingController _frequency;
  late final TextEditingController _length;
  late HotkeyChord _start;
  late HotkeyChord _reset;
  final _capture = FocusNode(skipTraversal: true);
  _HotkeyField? _listening;
  String? _error;

  @override
  void initState() {
    super.initState();
    final initial = widget.initial;
    _delay = TextEditingController(text: '${initial.startDelay}');
    _speed = TextEditingController(text: '${initial.defaultSpeed}');
    _frequency = TextEditingController(text: '${initial.mistakeFrequency}');
    _length = TextEditingController(text: '${initial.mistakeLength}');
    _start = initial.startPause;
    _reset = initial.reset;
  }

  @override
  void dispose() {
    _delay.dispose();
    _speed.dispose();
    _frequency.dispose();
    _length.dispose();
    _capture.dispose();
    super.dispose();
  }

  void _listen(_HotkeyField field) {
    setState(() {
      _listening = _listening == field ? null : field;
      _error = null;
    });
    if (_listening != null) _capture.requestFocus();
  }

  KeyEventResult _onKey(KeyEvent event) {
    if (_listening == null) return KeyEventResult.ignored;
    if (event is! KeyDownEvent && event is! KeyRepeatEvent) {
      return KeyEventResult.ignored;
    }
    final key = event.logicalKey;
    if (key == LogicalKeyboardKey.escape) {
      setState(() => _listening = null);
      return KeyEventResult.handled;
    }
    if (isModifierKey(key)) return KeyEventResult.handled;

    final pressed = HardwareKeyboard.instance.logicalKeysPressed;
    bool held(LogicalKeyboardKey left, LogicalKeyboardKey right) =>
        pressed.contains(left) || pressed.contains(right);

    final chord = HotkeyChord(
      control: held(LogicalKeyboardKey.controlLeft, LogicalKeyboardKey.controlRight),
      shift: held(LogicalKeyboardKey.shiftLeft, LogicalKeyboardKey.shiftRight),
      alt: held(LogicalKeyboardKey.altLeft, LogicalKeyboardKey.altRight),
      meta: held(LogicalKeyboardKey.metaLeft, LogicalKeyboardKey.metaRight),
      keyId: key.keyId,
    );
    setState(() {
      if (_listening == _HotkeyField.start) {
        _start = chord;
      } else {
        _reset = chord;
      }
      _listening = null;
      _error = null;
    });
    return KeyEventResult.handled;
  }

  int _read(TextEditingController controller, int min, int max, int fallback) {
    final parsed = int.tryParse(controller.text.trim());
    if (parsed == null) return fallback;
    return parsed.clamp(min, max);
  }

  void _save() {
    if (_start.sameAs(_reset)) {
      setState(() => _error = 'Start and reset need different shortcuts.');
      return;
    }
    final initial = widget.initial;
    Navigator.of(context).pop(
      initial.copyWith(
        startDelay: _read(_delay, 0, 120, initial.startDelay),
        defaultSpeed: _read(_speed, 1, 10, initial.defaultSpeed),
        mistakeFrequency: _read(_frequency, 0, 100, initial.mistakeFrequency),
        mistakeLength: _read(_length, 1, 20, initial.mistakeLength),
        startPause: _start,
        reset: _reset,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Focus(
      focusNode: _capture,
      onKeyEvent: (_, event) => _onKey(event),
      child: Dialog(
        insetPadding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
        backgroundColor: AppColors.bg,
        surfaceTintColor: Colors.transparent,
        elevation: 18,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFF2E3344)),
        ),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 700),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(28, 16, 20, 22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    const AppMark(size: 16),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Text(
                        'Settings',
                        style: TextStyle(
                          color: AppColors.text,
                          fontSize: 22,
                          fontWeight: FontWeight.w600,
                          letterSpacing: -0.2,
                        ),
                      ),
                    ),
                    _CloseButton(onTap: () => Navigator.of(context).pop()),
                  ],
                ),
                const SizedBox(height: 22),
                _SettingRow(
                  title: 'Start delay',
                  subtitle: 'Seconds to wait before typing begins',
                  child: _NumberBox(controller: _delay),
                ),
                _SettingRow(
                  title: 'Default speed',
                  subtitle: 'Characters per second when the app opens',
                  child: _NumberBox(controller: _speed),
                ),
                _SettingRow(
                  title: 'Mistake frequency',
                  subtitle: 'Mistakes per 100 characters; 0 turns them off',
                  child: _NumberBox(controller: _frequency),
                ),
                _SettingRow(
                  title: 'Mistake length',
                  subtitle: 'Average wrong characters before correcting',
                  child: _NumberBox(controller: _length),
                ),
                _SettingRow(
                  title: 'Start / Pause hotkey',
                  subtitle: 'Click, then press the keys',
                  child: _HotkeyBox(
                    label: _listening == _HotkeyField.start ? 'Press keys' : _start.label,
                    active: _listening == _HotkeyField.start,
                    onTap: () => _listen(_HotkeyField.start),
                  ),
                ),
                _SettingRow(
                  title: 'Reset hotkey',
                  subtitle: 'Click, then press the keys',
                  child: _HotkeyBox(
                    label: _listening == _HotkeyField.reset ? 'Press keys' : _reset.label,
                    active: _listening == _HotkeyField.reset,
                    onTap: () => _listen(_HotkeyField.reset),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    if (_error != null)
                      Expanded(
                        child: Text(
                          _error!,
                          style: const TextStyle(color: Color(0xFFF07178), fontSize: 13),
                        ),
                      )
                    else
                      const Spacer(),
                    const SizedBox(width: 12),
                    _DialogButton(
                      label: 'Cancel',
                      filled: false,
                      onTap: () => Navigator.of(context).pop(),
                    ),
                    const SizedBox(width: 12),
                    _DialogButton(label: 'Save', filled: true, onTap: _save),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class AppMark extends StatelessWidget {
  const AppMark({super.key, this.size = 16});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.green,
        borderRadius: BorderRadius.circular(size * 0.24),
      ),
      child: Icon(
        Icons.keyboard_alt_outlined,
        size: size * 0.72,
        color: const Color(0xFF062814),
      ),
    );
  }
}

class _SettingRow extends StatelessWidget {
  const _SettingRow({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8, bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: AppColors.text,
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: AppColors.muted,
                    fontSize: 13,
                    height: 1.25,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 24),
          child,
        ],
      ),
    );
  }
}

class _NumberBox extends StatelessWidget {
  const _NumberBox({required this.controller});

  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 188,
      height: 46,
      child: TextField(
        controller: controller,
        textAlign: TextAlign.center,
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        style: const TextStyle(color: AppColors.text, fontSize: 16),
        cursorColor: AppColors.caret,
        decoration: _boxDecoration(false),
      ),
    );
  }
}

class _HotkeyBox extends StatelessWidget {
  const _HotkeyBox({
    required this.label,
    required this.active,
    required this.onTap,
  });

  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 188,
      height: 46,
      child: Material(
        color: AppColors.field,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: BorderSide(
            color: active ? AppColors.green : AppColors.fieldBorder,
            width: active ? 1.4 : 1,
          ),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: onTap,
          child: Center(
            child: Text(
              label,
              style: const TextStyle(color: AppColors.text, fontSize: 15),
            ),
          ),
        ),
      ),
    );
  }
}

InputDecoration _boxDecoration(bool active) {
  final side = BorderSide(color: active ? AppColors.green : AppColors.fieldBorder);
  final border = OutlineInputBorder(
    borderRadius: BorderRadius.circular(10),
    borderSide: side,
  );
  return InputDecoration(
    filled: true,
    fillColor: AppColors.field,
    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
    border: border,
    enabledBorder: border,
    focusedBorder: border,
  );
}

class _DialogButton extends StatelessWidget {
  const _DialogButton({
    required this.label,
    required this.filled,
    required this.onTap,
  });

  final String label;
  final bool filled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(10);
    return Material(
      color: filled ? AppColors.green : AppColors.control,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: filled
            ? BorderSide.none
            : const BorderSide(color: AppColors.fieldBorder),
      ),
      child: InkWell(
        borderRadius: radius,
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: filled ? 28 : 22, vertical: 10),
          child: Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}

class _CloseButton extends StatelessWidget {
  const _CloseButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: onTap,
      icon: const Icon(Icons.close, size: 20, color: AppColors.textSecondary),
      splashRadius: 18,
    );
  }
}
