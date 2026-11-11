import 'package:flutter/material.dart';

class AppColors {
  static const bg = Color(0xFF1C1F2B);
  static const editor = Color(0xFF141722);
  static const editorBorder = Color(0xFF2A2F3E);
  static const field = Color(0xFF262A38);
  static const fieldBorder = Color(0xFF3A4154);
  static const control = Color(0xFF232735);
  static const green = Color(0xFF22C55E);
  static const text = Color(0xFFF4F6FB);
  static const textSecondary = Color(0xFFC8CDD8);
  static const muted = Color(0xFF8E95A8);
  static const caret = Color(0xFFF5B027);
  static const track = Color(0xFF3A4154);
  static const badge = Color(0xFF2C3142);
  static const line = Color(0xFF2C3344);
  static const danger = Color(0xFFE81123);
}

ThemeData buildAppTheme() {
  const border = OutlineInputBorder(
    borderRadius: BorderRadius.all(Radius.circular(10)),
    borderSide: BorderSide(color: AppColors.fieldBorder),
  );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    fontFamily: 'Segoe UI',
    scaffoldBackgroundColor: AppColors.bg,
    splashFactory: InkRipple.splashFactory,
    colorScheme: const ColorScheme.dark(
      surface: AppColors.bg,
      primary: AppColors.green,
    ),
    dialogTheme: const DialogThemeData(
      backgroundColor: AppColors.bg,
      surfaceTintColor: Colors.transparent,
    ),
    inputDecorationTheme: const InputDecorationTheme(
      filled: true,
      fillColor: AppColors.field,
      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      border: border,
      enabledBorder: border,
      focusedBorder: border,
      hintStyle: TextStyle(color: AppColors.muted),
    ),
    switchTheme: SwitchThemeData(
      thumbColor: const WidgetStatePropertyAll(Colors.white),
      trackColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) return AppColors.green;
        return const Color(0xFF3A4052);
      }),
      trackOutlineColor: const WidgetStatePropertyAll(Colors.transparent),
      trackOutlineWidth: const WidgetStatePropertyAll(0),
      overlayColor: const WidgetStatePropertyAll(Colors.transparent),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    ),
    textSelectionTheme: TextSelectionThemeData(
      cursorColor: AppColors.caret,
      selectionColor: AppColors.green.withValues(alpha: 0.28),
    ),
  );
}
