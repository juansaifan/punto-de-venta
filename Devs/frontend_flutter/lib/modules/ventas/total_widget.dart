import 'package:flutter/material.dart';

import '../../widgets/primary_button.dart';

class TotalesVentaWidget extends StatelessWidget {
  const TotalesVentaWidget({
    super.key,
    required this.subtotal,
    required this.descuento,
    required this.onCambiarDescuento,
    required this.onCobrar,
    required this.onCancelar,
  });

  final double subtotal;
  final double descuento;
  final ValueChanged<double> onCambiarDescuento;
  final VoidCallback onCobrar;
  final VoidCallback onCancelar;

  double get total => (subtotal - descuento).clamp(0, double.infinity);

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    final estiloValor = const TextStyle(fontSize: 22, fontWeight: FontWeight.bold);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          margin: const EdgeInsets.all(8),
          elevation: 1,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _linea('Subtotal', subtotal, estiloValor),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'Descuento',
                        style: TextStyle(fontSize: 16),
                      ),
                    ),
                    SizedBox(
                      width: 140,
                      child: TextFormField(
                        initialValue: descuento.toStringAsFixed(2),
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                        onChanged: (value) {
                          final parsed = double.tryParse(value.replaceAll(',', '.')) ?? 0;
                          onCambiarDescuento(parsed);
                        },
                        decoration: const InputDecoration(
                          prefixText: 'S/ ',
                        ),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'TOTAL',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Text(
                      'S/ ${total.toStringAsFixed(2)}',
                      style: estiloValor.copyWith(
                        fontSize: 26,
                        color: esquema.primary,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: BotonPrimario(
            texto: 'COBRAR',
            icono: Icons.check_circle,
            onPressed: onCobrar,
          ),
        ),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: BotonPrimario(
            texto: 'CANCELAR VENTA',
            icono: Icons.cancel,
            color: Colors.red.shade600,
            onPressed: onCancelar,
          ),
        ),
      ],
    );
  }

  Widget _linea(String etiqueta, double valor, TextStyle estiloValor) {
    return Row(
      children: [
        Expanded(
          child: Text(
            etiqueta,
            style: const TextStyle(fontSize: 16),
          ),
        ),
        Text(
          'S/ ${valor.toStringAsFixed(2)}',
          style: estiloValor,
        ),
      ],
    );
  }
}

