import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';
import 'modules/dashboard/dashboard_screen.dart';
import 'modules/caja/caja_screen.dart';
import 'modules/inventario/inventario_screen.dart';
import 'modules/ventas/ventas_screen.dart';
import 'modules/pesables/pesables_screen.dart';
import 'widgets/responsive_scaffold.dart';

void main() {
  runApp(const AplicacionPos());
}

class AplicacionPos extends StatelessWidget {
  const AplicacionPos({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'La Casona – POS',
      debugShowCheckedModeBanner: false,
      theme: construirTemaPos(),
      home: const ShellPrincipal(),
    );
  }
}

class ShellPrincipal extends StatefulWidget {
  const ShellPrincipal({super.key});

  @override
  State<ShellPrincipal> createState() => _ShellPrincipalState();
}

class _ShellPrincipalState extends State<ShellPrincipal> {
  int _indice = 1;

  @override
  Widget build(BuildContext context) {
    return DisenoResponsivoPos(
      indiceSeleccionado: _indice,
      onCambiarIndice: (nuevo) {
        setState(() => _indice = nuevo);
      },
      construirContenido: (context) {
        switch (_indice) {
          case 0:
            return const PantallaDashboard();
          case 1:
            return const PantallaVentas();
          case 2:
            return const PantallaPesables();
          case 3:
            return const PantallaCaja();
          case 4:
            return const _PantallaPlaceholder(
              titulo: 'Punto de Venta / Operaciones Comerciales',
            );
          case 5:
            return const _PantallaPlaceholder(
              titulo: 'Tesoreria',
            );
          case 6:
            return const _PantallaPlaceholder(
              titulo: 'Finanzas',
            );
          case 7:
            return const PantallaInventario();
          case 8:
            return const _PantallaPlaceholder(
              titulo: 'Personas',
            );
          case 9:
            return const _PantallaPlaceholder(
              titulo: 'Reportes',
            );
          case 10:
            return const _PantallaPlaceholder(
              titulo: 'Integraciones',
            );
          case 11:
            return const _PantallaPlaceholder(
              titulo: 'Configuraciones',
            );
          default:
            return const PantallaDashboard();
        }
      },
    );
  }
}

class _PantallaPlaceholder extends StatelessWidget {
  const _PantallaPlaceholder({required this.titulo});

  final String titulo;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        width: 520,
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          border: Border.all(color: const Color(0xFFD8DDE8)),
          borderRadius: BorderRadius.circular(12),
          color: Colors.white,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.construction_outlined, size: 38),
            const SizedBox(height: 10),
            Text(
              titulo,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 6),
            const Text(
              'Submodulo en preparacion frontend.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
