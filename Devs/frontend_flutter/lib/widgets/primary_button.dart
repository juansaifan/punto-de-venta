import 'package:flutter/material.dart';

class BotonPrimario extends StatelessWidget {
  const BotonPrimario({
    super.key,
    required this.texto,
    required this.onPressed,
    this.icono,
    this.color,
  });

  final String texto;
  final VoidCallback? onPressed;
  final IconData? icono;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: color ?? esquema.primary,
          foregroundColor: esquema.onPrimary,
        ),
        icon: icono != null ? Icon(icono) : const SizedBox.shrink(),
        label: Text(texto),
      ),
    );
  }
}

