import 'package:flutter/material.dart';

import 'caja_pantalla_principal.dart';

/// Submódulo Caja — pantalla principal (wireframe v6).
///
/// La implementación anterior muy extensa quedó en [PantallaCajaLegacy]
/// (`caja_screen_legacy.dart`) por si necesitás recuperar prototipos viejos.
class PantallaCaja extends StatelessWidget {
  const PantallaCaja({super.key});

  @override
  Widget build(BuildContext context) {
    return const CajaPantallaPrincipal();
  }
}
