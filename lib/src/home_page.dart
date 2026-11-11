// ignore_for_file: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:window_manager/legacy.dart';

import 'app_settings.dart';
import 'settings_dialog.dart';
import 'theme.dart';
import 'typer_controller.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.controller});

  final TyperController controller;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  late final TextEditingController _text;
  late final ScrollController _scroll;
  bool _overflow = false;

  TyperController get controller => widget.controller;

  @override
  void initState() {
    super.initState();
    _text = TextEditingController();
    _scroll = ScrollController()..addListener(_checkOverflow);
    controller.addListener(_onController);
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkOverflow());
  }

  @override
  void dispose() {
    controller.removeListener(_onController);
    _text.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _onController() {
    if (mounted) setState(() {});
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkOverflow());
  }

  void _checkOverflow() {
    if (!mounted || !_scroll.hasClients) return;
    final overflow = _scroll.position.maxScrollExtent > 0;
    if (overflow != _overflow) setState(() => _overflow = overflow);
  }

  Future<void> _openSettings() async {
    await controller.suspendHotkeys();
    if (!mounted) return;
    final result = await showDialog<AppSettings>(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.55),
      builder: (_) => SettingsDialog(initial: controller.settings),
    );
    if (result != null) {
      await controller.applySettings(result);
    } else {
      await controller.resumeHotkeys();
    }
  }

  @override
  Widget build(BuildContext context) {
    final phase = controller.phase;
    final active = controller.running;
    return Scaffold(
      backgroundColor: AppColors.bg,
      body: Column(
        children: [
          const _TitleBar(),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 14),
              child: Column(
                children: [
                  _Header(
                    label: phase.label,
                    onSettings: _openSettings,
                  ),
                  const SizedBox(height: 14),
                  Expanded(child: _editor(active)),
                  const SizedBox(height: 16),
                  _Controls(controller: controller),
                  const SizedBox(height: 12),
                  _Footer(controller: controller),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _editor(bool active) {
    final shown = controller.source.isEmpty || controller.fraction == 0
        ? 8.0
        : null;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.editor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.editorBorder),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(11),
        child: Stack(
          children: [
            RawScrollbar(
              controller: _scroll,
              thumbVisibility: _overflow,
              thickness: 8,
              radius: const Radius.circular(8),
              thumbColor: const Color(0xFF46506A),
              padding: const EdgeInsets.fromLTRB(0, 8, 4, 14),
              child: TextField(
                controller: _text,
                scrollController: _scroll,
                readOnly: active,
                expands: true,
                minLines: null,
                maxLines: null,
                keyboardType: TextInputType.multiline,
                textAlignVertical: TextAlignVertical.top,
                cursorColor: AppColors.caret,
                cursorWidth: 2,
                cursorHeight: 22,
                style: const TextStyle(
                  color: AppColors.text,
                  fontSize: 15,
                  height: 1.45,
                ),
                decoration: const InputDecoration(
                  isCollapsed: true,
                  filled: false,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: EdgeInsets.fromLTRB(16, 14, 28, 36),
                ),
                onChanged: (value) {
                  controller.onTextChanged(value);
                  WidgetsBinding.instance.addPostFrameCallback((_) => _checkOverflow());
                },
              ),
            ),
            if (!_overflow)
              const Positioned(
                top: 8,
                bottom: 14,
                right: 5,
                child: IgnorePointer(
                  child: SizedBox(
                    width: 8,
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Color(0xFF2A3144),
                        borderRadius: BorderRadius.all(Radius.circular(8)),
                      ),
                    ),
                  ),
                ),
              ),
            Positioned(
              right: 18,
              bottom: 10,
              child: IgnorePointer(
                child: Text(
                  '${controller.index}/${controller.total}',
                  style: const TextStyle(
                    color: AppColors.muted,
                    fontSize: 12,
                    fontFeatures: [FontFeature.tabularFigures()],
                  ),
                ),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              height: 3,
              child: _ProgressBar(fraction: controller.fraction, idleWidth: shown),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProgressBar extends StatelessWidget {
  const _ProgressBar({required this.fraction, required this.idleWidth});

  final double fraction;
  final double? idleWidth;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final filled = idleWidth ?? (fraction * width).clamp(4.0, width);
        return Stack(
          fit: StackFit.expand,
          children: [
            const ColoredBox(color: AppColors.line),
            Align(
              alignment: Alignment.centerLeft,
              child: SizedBox(
                width: filled,
                child: const ColoredBox(color: AppColors.green),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.label, required this.onSettings});

  final String label;
  final VoidCallback onSettings;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Text(
          'Auto Typer',
          style: TextStyle(
            color: AppColors.text,
            fontSize: 22,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(width: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
          decoration: BoxDecoration(
            color: AppColors.badge,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            label,
            style: const TextStyle(
              color: Color(0xFFD0D4E0),
              fontSize: 13,
              fontWeight: FontWeight.w500,
              height: 1.1,
            ),
          ),
        ),
        const Spacer(),
        _OutlineButton(
          icon: Icons.settings_outlined,
          label: 'Settings',
          onTap: onSettings,
        ),
      ],
    );
  }
}

class _OutlineButton extends StatelessWidget {
  const _OutlineButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: const Color(0xFF232838),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.fieldBorder),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Row(
            children: [
              Icon(icon, size: 18, color: AppColors.textSecondary),
              const SizedBox(width: 8),
              Text(
                label,
                style: const TextStyle(color: AppColors.text, fontSize: 14),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Controls extends StatelessWidget {
  const _Controls({required this.controller});

  final TyperController controller;

  @override
  Widget build(BuildContext context) {
    final active = controller.running;
    return Row(
      children: [
        _RoundButton(
          diameter: 54,
          color: AppColors.green,
          onTap: controller.toggle,
          child: Padding(
            padding: EdgeInsets.only(left: active ? 0 : 2),
            child: Icon(
              active ? Icons.pause_rounded : Icons.play_arrow_rounded,
              color: const Color(0xFF062814),
              size: active ? 28 : 34,
            ),
          ),
        ),
        const SizedBox(width: 12),
        _RoundButton(
          diameter: 42,
          color: AppColors.control,
          border: const BorderSide(color: AppColors.fieldBorder),
          onTap: controller.reset,
          child: const Icon(
            Icons.power_settings_new,
            color: AppColors.textSecondary,
            size: 20,
          ),
        ),
        const SizedBox(width: 18),
        const Text(
          'Speed',
          style: TextStyle(color: AppColors.text, fontSize: 14.5),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _SpeedSlider(
            speed: controller.speed,
            onChanged: controller.setSpeed,
          ),
        ),
        const SizedBox(width: 8),
        _SpeedBox(speed: controller.speed, onChanged: controller.setSpeed),
        const SizedBox(width: 8),
        const Text(
          'chars/sec',
          style: TextStyle(color: AppColors.muted, fontSize: 13.5),
        ),
      ],
    );
  }
}

class _RoundButton extends StatelessWidget {
  const _RoundButton({
    required this.diameter,
    required this.color,
    required this.onTap,
    required this.child,
    this.border,
  });

  final double diameter;
  final Color color;
  final VoidCallback onTap;
  final Widget child;
  final BorderSide? border;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: diameter,
      height: diameter,
      child: Material(
        color: color,
        shape: CircleBorder(side: border ?? BorderSide.none),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: onTap,
          child: Center(child: child),
        ),
      ),
    );
  }
}

class _SpeedSlider extends StatelessWidget {
  const _SpeedSlider({required this.speed, required this.onChanged});

  final int speed;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    final t = ((speed - 1) / 9).clamp(0.0, 1.0);
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        void update(double dx) {
          final next = (1 + (dx / width).clamp(0.0, 1.0) * 9).round().clamp(1, 10);
          onChanged(next);
        }

        final thumbLeft = (t * width - 8).clamp(-2.0, width - 14);
        return MouseRegion(
          cursor: SystemMouseCursors.click,
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTapDown: (details) => update(details.localPosition.dx),
            onHorizontalDragUpdate: (details) => update(details.localPosition.dx),
            child: SizedBox(
              height: 28,
              child: Center(
                child: SizedBox(
                  height: 4,
                  child: Stack(
                    clipBehavior: Clip.none,
                    alignment: Alignment.centerLeft,
                    children: [
                      const DecoratedBox(
                        decoration: BoxDecoration(
                          color: AppColors.track,
                          borderRadius: BorderRadius.all(Radius.circular(4)),
                        ),
                        child: SizedBox.expand(),
                      ),
                      FractionallySizedBox(
                        widthFactor: t,
                        child: const DecoratedBox(
                          decoration: BoxDecoration(
                            color: AppColors.green,
                            borderRadius: BorderRadius.all(Radius.circular(4)),
                          ),
                          child: SizedBox.expand(),
                        ),
                      ),
                      Positioned(
                        left: thumbLeft,
                        top: -6,
                        child: Container(
                          width: 16,
                          height: 16,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.35),
                                blurRadius: 3,
                                offset: const Offset(0, 1),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _SpeedBox extends StatefulWidget {
  const _SpeedBox({required this.speed, required this.onChanged});

  final int speed;
  final ValueChanged<int> onChanged;

  @override
  State<_SpeedBox> createState() => _SpeedBoxState();
}

class _SpeedBoxState extends State<_SpeedBox> {
  late final TextEditingController _text;
  late final FocusNode _focus;

  @override
  void initState() {
    super.initState();
    _text = TextEditingController(text: '${widget.speed}');
    _focus = FocusNode();
  }

  @override
  void didUpdateWidget(covariant _SpeedBox oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_focus.hasFocus && _text.text != '${widget.speed}') {
      _text.text = '${widget.speed}';
    }
  }

  @override
  void dispose() {
    _text.dispose();
    _focus.dispose();
    super.dispose();
  }

  void _commit(String raw) {
    final parsed = int.tryParse(raw.trim());
    final next = (parsed ?? widget.speed).clamp(1, 10);
    widget.onChanged(next);
    _text.text = '$next';
    _text.selection = TextSelection(baseOffset: 0, extentOffset: _text.text.length);
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 52,
      height: 36,
      child: TextField(
        controller: _text,
        focusNode: _focus,
        textAlign: TextAlign.center,
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        style: const TextStyle(color: AppColors.text, fontSize: 15),
        cursorColor: AppColors.caret,
        decoration: InputDecoration(
          filled: true,
          fillColor: AppColors.control,
          contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
          border: _border,
          enabledBorder: _border,
          focusedBorder: _border,
        ),
        onTap: () {
          _text.selection = TextSelection(
            baseOffset: 0,
            extentOffset: _text.text.length,
          );
        },
        onSubmitted: _commit,
        onEditingComplete: () => _commit(_text.text),
      ),
    );
  }
}

final _border = OutlineInputBorder(
  borderRadius: BorderRadius.circular(8),
  borderSide: const BorderSide(color: AppColors.fieldBorder),
);

class _Footer extends StatelessWidget {
  const _Footer({required this.controller});

  final TyperController controller;

  @override
  Widget build(BuildContext context) {
    final style = const TextStyle(color: AppColors.muted, fontSize: 12.5);
    return Row(
      children: [
        Transform.scale(
          scale: 0.78,
          child: Switch(
            value: controller.alwaysOnTop,
            onChanged: (value) => controller.setAlwaysOnTop(value),
          ),
        ),
        const Text(
          'Always on top',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 13.5),
        ),
        const Spacer(),
        Text('${controller.settings.startPause.label}  Start / Pause', style: style),
        const SizedBox(width: 28),
        Text('${controller.settings.reset.label}  Reset', style: style),
      ],
    );
  }
}

class _TitleBar extends StatefulWidget {
  const _TitleBar();

  @override
  State<_TitleBar> createState() => _TitleBarState();
}

class _TitleBarState extends State<_TitleBar> with WindowListener {
  bool _maximized = false;

  @override
  void initState() {
    super.initState();
    windowManager.addListener(this);
    windowManager.isMaximized().then((value) {
      if (mounted) setState(() => _maximized = value);
    });
  }

  @override
  void dispose() {
    windowManager.removeListener(this);
    super.dispose();
  }

  @override
  void onWindowMaximize() {
    if (mounted) setState(() => _maximized = true);
  }

  @override
  void onWindowUnmaximize() {
    if (mounted) setState(() => _maximized = false);
  }

  Future<void> _toggleMax() async {
    if (await windowManager.isMaximized()) {
      await windowManager.unmaximize();
    } else {
      await windowManager.maximize();
    }
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 40,
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onPanStart: (_) => windowManager.startDragging(),
              onDoubleTap: _toggleMax,
              child: const Row(
                children: [
                  SizedBox(width: 14),
                  AppMark(size: 16),
                  SizedBox(width: 8),
                  Text(
                    'Auto Typer',
                    style: TextStyle(
                      color: AppColors.text,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
          _WindowButton(
            icon: Icons.remove,
            onTap: windowManager.minimize,
          ),
          _WindowButton(
            icon: _maximized ? Icons.filter_none : Icons.crop_square,
            iconSize: _maximized ? 14 : 15,
            onTap: _toggleMax,
          ),
          _WindowButton(
            icon: Icons.close,
            danger: true,
            onTap: windowManager.close,
          ),
        ],
      ),
    );
  }
}

class _WindowButton extends StatefulWidget {
  const _WindowButton({
    required this.icon,
    required this.onTap,
    this.iconSize = 16,
    this.danger = false,
  });

  final IconData icon;
  final VoidCallback onTap;
  final double iconSize;
  final bool danger;

  @override
  State<_WindowButton> createState() => _WindowButtonState();
}

class _WindowButtonState extends State<_WindowButton> {
  bool _hover = false;

  @override
  Widget build(BuildContext context) {
    final background = _hover
        ? (widget.danger ? AppColors.danger : const Color(0xFF2A3042))
        : Colors.transparent;
    return MouseRegion(
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 46,
          height: 40,
          color: background,
          alignment: Alignment.center,
          child: Icon(
            widget.icon,
            size: widget.iconSize,
            color: _hover && widget.danger ? Colors.white : const Color(0xFFD5D8E2),
          ),
        ),
      ),
    );
  }
}
