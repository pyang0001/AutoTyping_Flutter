// The 0.6 API replaced this bridge. The legacy surface still matches the
// window calls this desktop shell needs.
// ignore_for_file: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:hotkey_manager/hotkey_manager.dart';
import 'package:window_manager/legacy.dart';

import 'src/settings_store.dart';
import 'src/theme.dart';
import 'src/typer_controller.dart';
import 'src/home_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await hotKeyManager.unregisterAll();
  await windowManager.ensureInitialized();
  await windowManager.setPreventClose(true);
  windowManager.addListener(_AppLifecycle());

  const options = WindowOptions(
    size: Size(1040, 660),
    minimumSize: Size(900, 600),
    center: true,
    backgroundColor: AppColors.bg,
    titleBarStyle: TitleBarStyle.hidden,
    title: 'Auto Typer',
    windowButtonVisibility: false,
  );

  final settings = await SettingsStore.load();
  final controller = TyperController(settings);
  await controller.bindHotkeys();

  windowManager.waitUntilReadyToShow(options, () async {
    await windowManager.show();
    await windowManager.focus();
    if (controller.alwaysOnTop) {
      await windowManager.setAlwaysOnTop(true);
    }
  });

  runApp(AutoTyperApp(controller: controller));
}

class AutoTyperApp extends StatelessWidget {
  const AutoTyperApp({super.key, required this.controller});

  final TyperController controller;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Auto Typer',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: HomePage(controller: controller),
    );
  }
}

class _AppLifecycle with WindowListener {
  bool _closing = false;

  @override
  void onWindowClose() {
    if (_closing) return;
    _closing = true;
    hotKeyManager.unregisterAll().whenComplete(() async {
      await windowManager.setPreventClose(false);
      await windowManager.close();
    });
  }
}
