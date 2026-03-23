import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import '../../widgets/selector_cliente_como_ventas.dart';

/// Opciones de forma de pago en el modal «Pagar factura» (Caja).
enum FormaPagoFactura {
  efectivo,
  transferencia,
  tarjetaCreditoDebito,
  qr,
  combinado,
  cuentaCorriente,
}

extension FormaPagoFacturaX on FormaPagoFactura {
  String get etiqueta => switch (this) {
        FormaPagoFactura.efectivo => 'Efectivo',
        FormaPagoFactura.transferencia => 'Transferencia',
        FormaPagoFactura.tarjetaCreditoDebito => 'Tarjeta crédito / débito',
        FormaPagoFactura.qr => 'QR',
        FormaPagoFactura.combinado => 'Combinado',
        FormaPagoFactura.cuentaCorriente => 'Cuenta Corriente',
      };

  IconData get icono => switch (this) {
        FormaPagoFactura.efectivo => Icons.payments_rounded,
        FormaPagoFactura.transferencia => Icons.account_balance_outlined,
        FormaPagoFactura.tarjetaCreditoDebito => Icons.credit_card_rounded,
        FormaPagoFactura.qr => Icons.qr_code_2_rounded,
        FormaPagoFactura.combinado => Icons.layers_rounded,
        FormaPagoFactura.cuentaCorriente => Icons.request_quote_outlined,
      };
}

String formatoTotalFacturaConDecimales(double valor) {
  final neg = valor < 0;
  final v = valor.abs();
  final s = v.toStringAsFixed(2);
  final dot = s.indexOf('.');
  final intPart = s.substring(0, dot);
  final dec = s.substring(dot + 1);
  final buf = StringBuffer();
  for (var i = 0; i < intPart.length; i++) {
    if (i > 0 && (intPart.length - i) % 3 == 0) buf.write(',');
    buf.write(intPart[i]);
  }
  return '${neg ? '-' : ''}\$${buf.toString()}.$dec';
}

/// Resultado al confirmar el modal de cobro.
class PagoFacturaResult {
  const PagoFacturaResult({
    required this.forma,
    this.montoRecibidoEfectivo,
    this.observaciones = '',
    this.sinVueltoAcreditarEnCuenta = false,
    this.saldoACuenta = 0.0,
    this.clienteAsignado,
  });

  final FormaPagoFactura forma;
  final double? montoRecibidoEfectivo;
  final String observaciones;
  /// Si es true, el vuelto no se entrega en efectivo y se acredita al cliente.
  final bool sinVueltoAcreditarEnCuenta;
  /// Monto que no se cobró en efectivo y se acredita en cuenta corriente del cliente.
  final double saldoACuenta;
  /// Cliente asignado durante el cobro (si el ticket era consumidor final).
  final ClienteMock? clienteAsignado;
}

/// Mismo estilo que el botón «Total a pagar» en Caja (incl. hover web).
ButtonStyle estiloBotonBarraCaja() {
  return ButtonStyle(
    backgroundColor: WidgetStateProperty.resolveWith<Color>((states) {
      if (states.contains(WidgetState.pressed)) {
        return const Color(0xFF2563EB);
      }
      if (states.contains(WidgetState.hovered)) {
        return const Color(0xFF22C55E);
      }
      return const Color(0xFF4A5568);
    }),
    foregroundColor: WidgetStateProperty.all(Colors.white),
    padding: WidgetStateProperty.all(
      const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
    shape: WidgetStateProperty.all(
      RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    ),
    elevation: WidgetStateProperty.all(0),
    // Overlay suave: en web, transparente total a veces impide ver bien el hover.
    overlayColor: WidgetStateProperty.resolveWith<Color?>((states) {
      if (states.contains(WidgetState.pressed)) {
        return Colors.white.withValues(alpha: 0.12);
      }
      if (states.contains(WidgetState.hovered)) {
        return Colors.white.withValues(alpha: 0.08);
      }
      return null;
    }),
  );
}

/// Modal para elegir forma de pago y, si aplica, detalle en efectivo.
class PagarFacturaDialog extends StatefulWidget {
  const PagarFacturaDialog({
    super.key,
    required this.total,
    this.esConsumidorFinal = false,
  });

  final double total;
  /// True si el ticket no tiene cliente asignado (consumidor final).
  final bool esConsumidorFinal;

  static Future<PagoFacturaResult?> show(
    BuildContext context,
    double total, {
    bool esConsumidorFinal = false,
  }) {
    return showDialog<PagoFacturaResult>(
      context: context,
      barrierDismissible: true,
      builder: (context) => PagarFacturaDialog(
        total: total,
        esConsumidorFinal: esConsumidorFinal,
      ),
    );
  }

  @override
  State<PagarFacturaDialog> createState() => _PagarFacturaDialogState();
}

enum _PasoPago { elegirMetodo, detalleEfectivo }

class _PagarFacturaDialogState extends State<PagarFacturaDialog> {
  static const _borde = Color(0xFFE1E3E8);
  static const _bordeSeleccion = Color(0xFF0D9488);
  static const _iconoInactivo = Color(0xFF6B7280);
  static const _tealAccion = Color(0xFF0D9488);
  static const _alturaCeldaMetodo = 96.0;
  FormaPagoFactura _seleccion = FormaPagoFactura.efectivo;
  _PasoPago _paso = _PasoPago.elegirMetodo;
  bool _sinVueltoActivo = false;
  /// Cliente asignado durante el cobro (si el ticket inició como consumidor final).
  ClienteMock? _clienteAsignado;

  /// True mientras no se haya asignado un cliente real a un ticket consumidor final.
  bool get _esConsumidorFinalEfectivo =>
      widget.esConsumidorFinal && _clienteAsignado == null;

  final _ctrlEfectivo = TextEditingController();
  final _focusEfectivo = FocusNode();
  final _ctrlObsDialogo = TextEditingController();

  @override
  void dispose() {
    _ctrlEfectivo.dispose();
    _focusEfectivo.dispose();
    _ctrlObsDialogo.dispose();
    super.dispose();
  }

  double? _parseMontoIngresado() {
    final raw = _ctrlEfectivo.text.trim().replaceAll(',', '');
    if (raw.isEmpty) return null;
    return double.tryParse(raw);
  }

  List<double> _montosRapidos() {
    final t = widget.total;
    final alCentena = (t / 100).ceil() * 100.0;
    final segundo = alCentena <= t ? t + 100 : alCentena;
    final tercero = (t / 500).ceil() * 500.0;
    final terceroFinal = tercero < 4000 && t < 4000 ? 4000.0 : tercero;
    return [
      t,
      segundo,
      terceroFinal,
      5000.0,
      10000.0,
      20000.0,
    ];
  }

  void _asignarMontoRapidoAlCampo(double m) {
    final s = m.toStringAsFixed(2);
    final parts = s.split('.');
    final ip = parts[0];
    final dec = parts[1];
    final buf = StringBuffer();
    for (var i = 0; i < ip.length; i++) {
      if (i > 0 && (ip.length - i) % 3 == 0) buf.write(',');
      buf.write(ip[i]);
    }
    setState(() {
      _ctrlEfectivo.text = '$buf.$dec';
    });
  }

  /// 2 columnas × 3 filas (6 montos).
  Widget _gridOpcionesTipicas(List<double> rapidos) {
    assert(rapidos.length == 6);
    return Column(
      children: [
        for (var r = 0; r < 3; r++) ...[
          if (r > 0) const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(child: _botonMontoRapido(rapidos[r * 2])),
              const SizedBox(width: 8),
              Expanded(child: _botonMontoRapido(rapidos[r * 2 + 1])),
            ],
          ),
        ],
      ],
    );
  }

  Widget _botonMontoRapido(double m) {
    return OutlinedButton(
      onPressed: () => _asignarMontoRapidoAlCampo(m),
      style: OutlinedButton.styleFrom(
        foregroundColor: const Color(0xFF374151),
        side: const BorderSide(color: _borde),
        padding: const EdgeInsets.symmetric(vertical: 12),
        minimumSize: const Size(0, 44),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      child: Text(formatoTotalFacturaConDecimales(m)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: _paso == _PasoPago.detalleEfectivo ? 720 : 480,
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 12, 16),
          child: _paso == _PasoPago.elegirMetodo
              ? _buildElegirMetodo(context)
              : _buildDetalleEfectivo(context),
        ),
      ),
    );
  }

  Widget _buildElegirMetodo(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Pagar factura (${_seleccion.etiqueta})',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF303645),
                ),
              ),
            ),
            IconButton(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.close, color: Color(0xFF9CA3AF)),
              tooltip: 'Cerrar',
              visualDensity: VisualDensity.compact,
            ),
          ],
        ),
        const SizedBox(height: 8),
        _bloqueTotalYVuelto(mostrarLineaRoja: false),
        const SizedBox(height: 22),
        _filaOpciones(const [
          FormaPagoFactura.efectivo,
          FormaPagoFactura.transferencia,
          FormaPagoFactura.tarjetaCreditoDebito,
        ]),
        const SizedBox(height: 18),
        _separadorOtrosMetodos(),
        const SizedBox(height: 18),
        _filaOpciones(const [
          FormaPagoFactura.qr,
          FormaPagoFactura.combinado,
          FormaPagoFactura.cuentaCorriente,
        ]),
        const SizedBox(height: 22),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              style: TextButton.styleFrom(
                foregroundColor: const Color(0xFF6B7280),
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
              ),
              child: const Text(
                'Cancelar',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(
              style: estiloBotonBarraCaja(),
              onPressed: () {
                if (_seleccion == FormaPagoFactura.efectivo) {
                  setState(() {
                    _paso = _PasoPago.detalleEfectivo;
                    _ctrlEfectivo.text = '';
                    _sinVueltoActivo = false;
                  });
                } else {
                  Navigator.of(context).pop(
                    PagoFacturaResult(forma: _seleccion),
                  );
                }
              },
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                  'Continuar',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildDetalleEfectivo(BuildContext context) {
    final pago = _parseMontoIngresado();
    final total = widget.total;
    final pagoInsuficiente = pago != null && pago > 0 && pago < total - 0.009;
    final bloqueadoPorConsumidorFinal =
        pagoInsuficiente && _esConsumidorFinalEfectivo;
    final canFinalizar = pago != null &&
        pago > 0 &&
        (pago >= total || (pagoInsuficiente && !_esConsumidorFinalEfectivo));

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(
              child: Text(
                'Pagar factura (Efectivo)',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF303645),
                ),
              ),
            ),
            TextButton.icon(
              onPressed: () {
                setState(() {
                  _paso = _PasoPago.elegirMetodo;
                  _sinVueltoActivo = false;
                });
              },
              icon: const Icon(Icons.swap_vert_rounded, size: 18),
              label: const Text('Cambiar método'),
              style: TextButton.styleFrom(
                foregroundColor: _tealAccion,
                textStyle: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            IconButton(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.close, color: Color(0xFF9CA3AF)),
              tooltip: 'Cerrar',
              visualDensity: VisualDensity.compact,
            ),
          ],
        ),
        const SizedBox(height: 8),
        _bloqueTotalYVuelto(
          mostrarLineaRoja: true,
          pago: pago,
          total: total,
          sinVueltoActivo: _sinVueltoActivo,
          esConsumidorFinal: _esConsumidorFinalEfectivo,
        ),
        const SizedBox(height: 10),
        Align(
          alignment: Alignment.centerRight,
          child: _toggleSinVuelto(),
        ),
        const SizedBox(height: 14),
        SizedBox(
          height: (MediaQuery.of(context).size.height * 0.40).clamp(260.0, 380.0),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                flex: 5,
                child: _columnaEfectivoIzquierda(),
              ),
              const SizedBox(width: 14),
              Container(
                width: 1,
                color: Colors.grey.shade300,
              ),
              const SizedBox(width: 14),
              Expanded(
                flex: 4,
                child: _columnaObservaciones(),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        if (bloqueadoPorConsumidorFinal) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF7ED),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFFED7AA)),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.warning_amber_rounded,
                  size: 18,
                  color: Color(0xFFD97706),
                ),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Para acreditar el saldo restante en cuenta debe asignar un cliente al ticket.',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF92400E),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: () async {
                    final cliente =
                        await SelectorClienteComoVentas.mostrarDialogoSeleccion(
                      context,
                    );
                    if (cliente != null && mounted) {
                      setState(() => _clienteAsignado = cliente);
                    }
                  },
                  style: TextButton.styleFrom(
                    foregroundColor: const Color(0xFFD97706),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    textStyle: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                    ),
                  ),
                  child: const Text('Asignar cliente'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
        ] else
          const SizedBox(height: 6),
        Row(
          children: [
            OutlinedButton(
              onPressed: () => Navigator.of(context).pop(),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF374151),
                side: const BorderSide(color: _borde),
                padding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 14,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: const Text(
                'Cancelar',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            const Spacer(),
            FilledButton(
              style: estiloBotonBarraCaja(),
              onPressed: canFinalizar
                  ? () {
                      Navigator.of(context).pop(
                        PagoFacturaResult(
                          forma: FormaPagoFactura.efectivo,
                          montoRecibidoEfectivo: pago,
                          observaciones: _ctrlObsDialogo.text.trim(),
                          sinVueltoAcreditarEnCuenta:
                              pago >= total ? _sinVueltoActivo : false,
                          saldoACuenta: pagoInsuficiente ? total - pago : 0.0,
                          clienteAsignado: _clienteAsignado,
                        ),
                      );
                    }
                  : null,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Finalizar',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      formatoTotalFacturaConDecimales(total),
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  static const _amarilloSinVueltoFondo = Color(0xFFFEF9C3);
  static const _amarilloSinVueltoBorde = Color(0xFFEAB308);
  static const _amarilloSinVueltoTexto = Color(0xFF854D0E);

  Widget _toggleSinVuelto() {
    final a = _sinVueltoActivo;
    return Tooltip(
      message:
          'Sin vuelto: el excedente se acredita en cuenta corriente del cliente.',
      child: InkWell(
        onTap: () => setState(() => _sinVueltoActivo = !a),
        borderRadius: BorderRadius.circular(6),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: a ? _amarilloSinVueltoFondo : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: a ? _amarilloSinVueltoBorde : const Color(0xFFE5E7EB),
              width: 1,
            ),
          ),
          child: Text(
            'Sin vuelto',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: a ? _amarilloSinVueltoTexto : _iconoInactivo,
            ),
          ),
        ),
      ),
    );
  }

  Widget _bloqueTotalYVuelto({
    required bool mostrarLineaRoja,
    double? pago,
    double? total,
    bool sinVueltoActivo = false,
    bool esConsumidorFinal = false,
  }) {
    return Column(
      children: [
        Text(
          'TOTAL',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
            color: Colors.grey.shade500,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          formatoTotalFacturaConDecimales(widget.total),
          style: const TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w800,
            color: Color(0xFF111827),
          ),
        ),
        if (mostrarLineaRoja && pago != null && total != null && pago > 0) ...[
          const SizedBox(height: 8),
          if (pago > total + 0.009)
            Text(
              sinVueltoActivo
                  ? 'A cuenta: ${formatoTotalFacturaConDecimales(pago - total)}'
                  : 'Vuelto: ${formatoTotalFacturaConDecimales(pago - total)}',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: sinVueltoActivo
                    ? const Color(0xFF16A34A)
                    : const Color(0xFFDC2626),
              ),
            )
          else if (pago < total - 0.009)
            Text(
              esConsumidorFinal
                  ? 'Saldo a cuenta: ${formatoTotalFacturaConDecimales(total - pago)} · sin cliente'
                  : 'Saldo a cuenta: ${formatoTotalFacturaConDecimales(total - pago)}',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: esConsumidorFinal
                    ? const Color(0xFFDC2626)
                    : const Color(0xFFF59E0B),
              ),
            ),
        ],
      ],
    );
  }

  Widget _columnaEfectivoIzquierda() {
    final rapidos = _montosRapidos();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Valor del pago en efectivo *',
          style: TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13,
            color: Color(0xFF374151),
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: _ctrlEfectivo,
          focusNode: _focusEfectivo,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[\d.,]')),
          ],
          onChanged: (_) => setState(() {}),
          decoration: InputDecoration(
            isDense: true,
            hintText: '0.00',
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 14,
            ),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: _bordeSeleccion, width: 1.2),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(
                color: _bordeSeleccion.withValues(alpha: 0.65),
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: _bordeSeleccion, width: 1.6),
            ),
          ),
        ),
        const SizedBox(height: 16),
        _separadorOpcionesTipicas(),
        const SizedBox(height: 12),
        Expanded(
          child: SingleChildScrollView(
            physics: const ClampingScrollPhysics(),
            child: _gridOpcionesTipicas(rapidos),
          ),
        ),
      ],
    );
  }

  Widget _columnaObservaciones() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Observaciones',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: Color(0xFF5D6778),
          ),
        ),
        const SizedBox(height: 6),
        Expanded(
          child: TextField(
            controller: _ctrlObsDialogo,
            maxLines: null,
            expands: true,
            textAlignVertical: TextAlignVertical.top,
            decoration: InputDecoration(
              hintText: 'Ingresa tu observación',
              alignLabelWithHint: true,
              contentPadding: const EdgeInsets.all(12),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: _borde),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: _borde),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: _bordeSeleccion, width: 1.2),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _separadorOpcionesTipicas() {
    return Row(
      children: [
        Expanded(child: Divider(height: 1, color: Colors.grey.shade300)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Text(
            'Opciones típicas',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade600,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        Expanded(child: Divider(height: 1, color: Colors.grey.shade300)),
      ],
    );
  }

  Widget _separadorOtrosMetodos() {
    return Row(
      children: [
        Expanded(child: Divider(height: 1, color: Colors.grey.shade300)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text(
            'Otros métodos',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade600,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        Expanded(child: Divider(height: 1, color: Colors.grey.shade300)),
      ],
    );
  }

  Widget _filaOpciones(List<FormaPagoFactura> opciones) {
    return SizedBox(
      height: _alturaCeldaMetodo,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < opciones.length; i++) ...[
            if (i > 0) const SizedBox(width: 10),
            Expanded(child: _celdaFormaPago(opciones[i])),
          ],
        ],
      ),
    );
  }

  Widget _celdaFormaPago(FormaPagoFactura forma) {
    final sel = _seleccion == forma;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => setState(() => _seleccion = forma),
        borderRadius: BorderRadius.circular(8),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          height: _alturaCeldaMetodo,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: sel ? _bordeSeleccion : _borde,
              width: sel ? 2 : 1,
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  forma.icono,
                  size: 26,
                  color: sel ? _bordeSeleccion : _iconoInactivo,
                ),
                const SizedBox(height: 6),
                Text(
                  forma.etiqueta,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 11,
                    height: 1.15,
                    fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
                    color: sel
                        ? const Color(0xFF0F766E)
                        : const Color(0xFF4B5563),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

