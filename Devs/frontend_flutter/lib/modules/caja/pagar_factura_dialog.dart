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

/// Tipo de tarjeta para pago con tarjeta crédito/débito.
enum TipoTarjeta { credito, debito }

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
    this.numeroComprobante,
    this.tipoTarjeta,
    this.ultimosCuatroDigitos,
    this.codigoAutorizacion,
    this.metodo2,
    this.montoMetodo1,
  });

  final FormaPagoFactura forma;
  final double? montoRecibidoEfectivo;
  final String observaciones;
  final bool sinVueltoAcreditarEnCuenta;
  final double saldoACuenta;
  final ClienteMock? clienteAsignado;
  /// Transferencia: N° de comprobante / referencia.
  final String? numeroComprobante;
  /// Tarjeta: tipo (crédito o débito).
  final TipoTarjeta? tipoTarjeta;
  /// Tarjeta: últimos 4 dígitos (opcional).
  final String? ultimosCuatroDigitos;
  /// Tarjeta: código de autorización (opcional).
  final String? codigoAutorizacion;
  /// Combinado: segundo método de pago.
  final FormaPagoFactura? metodo2;
  /// Combinado: monto abonado con el método principal.
  final double? montoMetodo1;
}

/// Mismo estilo que el botón «Total a pagar» en Caja (incl. hover web).
ButtonStyle estiloBotonBarraCaja() {
  return ButtonStyle(
    backgroundColor: WidgetStateProperty.resolveWith<Color>((states) {
      if (states.contains(WidgetState.pressed)) return const Color(0xFF2563EB);
      if (states.contains(WidgetState.hovered)) return const Color(0xFF22C55E);
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

/// Modal para elegir forma de pago y detalle del método elegido.
class PagarFacturaDialog extends StatefulWidget {
  const PagarFacturaDialog({
    super.key,
    required this.total,
    this.esConsumidorFinal = false,
  });

  final double total;
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

enum _PasoPago { elegirMetodo, detalleMetodo }

class _PagarFacturaDialogState extends State<PagarFacturaDialog> {
  static const _borde = Color(0xFFE1E3E8);
  static const _bordeSeleccion = Color(0xFF0D9488);
  static const _iconoInactivo = Color(0xFF6B7280);
  static const _tealAccion = Color(0xFF0D9488);
  static const _alturaCeldaMetodo = 96.0;

  FormaPagoFactura _seleccion = FormaPagoFactura.efectivo;
  _PasoPago _paso = _PasoPago.elegirMetodo;
  bool _sinVueltoActivo = false;
  ClienteMock? _clienteAsignado;

  bool get _esConsumidorFinalEfectivo =>
      widget.esConsumidorFinal && _clienteAsignado == null;

  // ── Efectivo ──────────────────────────────────────────────
  final _ctrlEfectivo = TextEditingController();
  final _focusEfectivo = FocusNode();

  // ── Transferencia ─────────────────────────────────────────
  final _ctrlComprobante = TextEditingController();

  // ── Tarjeta ───────────────────────────────────────────────
  TipoTarjeta _tipoTarjeta = TipoTarjeta.debito;
  final _ctrlUltimosDigitos = TextEditingController();
  final _ctrlCodAutorizacion = TextEditingController();

  // ── Combinado ─────────────────────────────────────────────
  FormaPagoFactura _metodoCombinado1 = FormaPagoFactura.efectivo;
  FormaPagoFactura _metodoCombinado2 = FormaPagoFactura.transferencia;
  final _ctrlMontoCombinado1 = TextEditingController();

  // ── Compartido ────────────────────────────────────────────
  final _ctrlObsDialogo = TextEditingController();

  @override
  void dispose() {
    _ctrlEfectivo.dispose();
    _focusEfectivo.dispose();
    _ctrlComprobante.dispose();
    _ctrlUltimosDigitos.dispose();
    _ctrlCodAutorizacion.dispose();
    _ctrlMontoCombinado1.dispose();
    _ctrlObsDialogo.dispose();
    super.dispose();
  }

  void _resetDetalles() {
    _ctrlEfectivo.clear();
    _ctrlComprobante.clear();
    _ctrlUltimosDigitos.clear();
    _ctrlCodAutorizacion.clear();
    _ctrlMontoCombinado1.clear();
    _ctrlObsDialogo.clear();
    _sinVueltoActivo = false;
    _tipoTarjeta = TipoTarjeta.debito;
    _metodoCombinado1 = FormaPagoFactura.efectivo;
    _metodoCombinado2 = FormaPagoFactura.transferencia;
    _clienteAsignado = null;
  }

  double? _parseMontoIngresado() {
    final raw = _ctrlEfectivo.text.trim().replaceAll(',', '');
    if (raw.isEmpty) return null;
    return double.tryParse(raw);
  }

  double? _parseMontoCombinado1() {
    final raw = _ctrlMontoCombinado1.text.trim().replaceAll(',', '');
    if (raw.isEmpty) return null;
    return double.tryParse(raw);
  }

  List<double> _montosRapidos() {
    final t = widget.total;
    final alCentena = (t / 100).ceil() * 100.0;
    final segundo = alCentena <= t ? t + 100 : alCentena;
    final tercero = (t / 500).ceil() * 500.0;
    final terceroFinal = tercero < 4000 && t < 4000 ? 4000.0 : tercero;
    return [t, segundo, terceroFinal, 5000.0, 10000.0, 20000.0];
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
    setState(() => _ctrlEfectivo.text = '$buf.$dec');
  }

  // ────────────────────────────────────────────────────────────
  // Build root
  // ────────────────────────────────────────────────────────────

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
          maxWidth: _paso == _PasoPago.detalleMetodo ? 720 : 480,
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 12, 16),
          child: _paso == _PasoPago.elegirMetodo
              ? _buildElegirMetodo(context)
              : _buildDetalleMetodo(context),
        ),
      ),
    );
  }

  // ────────────────────────────────────────────────────────────
  // Paso 1: elegir método
  // ────────────────────────────────────────────────────────────

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
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
                setState(() {
                  _resetDetalles();
                  _paso = _PasoPago.detalleMetodo;
                });
              },
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                  'Continuar',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ────────────────────────────────────────────────────────────
  // Paso 2: despachador
  // ────────────────────────────────────────────────────────────

  Widget _buildDetalleMetodo(BuildContext context) {
    return switch (_seleccion) {
      FormaPagoFactura.efectivo => _buildDetalleEfectivo(context),
      FormaPagoFactura.transferencia => _buildDetalleTransferencia(context),
      FormaPagoFactura.tarjetaCreditoDebito => _buildDetalleTarjeta(context),
      FormaPagoFactura.qr => _buildDetalleQr(context),
      FormaPagoFactura.cuentaCorriente => _buildDetalleCuentaCorriente(context),
      FormaPagoFactura.combinado => _buildDetalleCombinado(context),
    };
  }

  // ────────────────────────────────────────────────────────────
  // Shared layout helpers
  // ────────────────────────────────────────────────────────────

  Widget _headerDetalle(BuildContext context, String titulo) {
    return Row(
      children: [
        Expanded(
          child: Text(
            titulo,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: Color(0xFF303645),
            ),
          ),
        ),
        TextButton.icon(
          onPressed: () => setState(() {
            _resetDetalles();
            _paso = _PasoPago.elegirMetodo;
          }),
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
    );
  }

  Widget _filaBotonesAccion(
    BuildContext context, {
    required bool canFinalizar,
    required VoidCallback onFinalizar,
    required double total,
  }) {
    return Row(
      children: [
        OutlinedButton(
          onPressed: () => Navigator.of(context).pop(),
          style: OutlinedButton.styleFrom(
            foregroundColor: const Color(0xFF374151),
            side: const BorderSide(color: _borde),
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          child: const Text('Cancelar', style: TextStyle(fontWeight: FontWeight.w600)),
        ),
        const Spacer(),
        FilledButton(
          style: estiloBotonBarraCaja(),
          onPressed: canFinalizar ? onFinalizar : null,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Finalizar',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                ),
                const SizedBox(width: 12),
                Text(
                  formatoTotalFacturaConDecimales(total),
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _contenedorDosColumnas(
    BuildContext context, {
    required Widget left,
    required Widget right,
    int flexLeft = 5,
    int flexRight = 4,
  }) {
    return SizedBox(
      height: (MediaQuery.of(context).size.height * 0.40).clamp(260.0, 380.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(flex: flexLeft, child: left),
          const SizedBox(width: 14),
          Container(width: 1, color: Colors.grey.shade300),
          const SizedBox(width: 14),
          Expanded(flex: flexRight, child: right),
        ],
      ),
    );
  }

  Widget _bannerBloqueoCuenta(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFFED7AA)),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded, size: 18, color: Color(0xFFD97706)),
          const SizedBox(width: 8),
          const Expanded(
            child: Text(
              'Para acreditar el saldo en cuenta debe asignar un cliente al ticket.',
              style: TextStyle(fontSize: 12, color: Color(0xFF92400E)),
            ),
          ),
          const SizedBox(width: 8),
          TextButton(
            onPressed: () async {
              final cliente =
                  await SelectorClienteComoVentas.mostrarDialogoSeleccion(context);
              if (cliente != null && mounted) {
                setState(() => _clienteAsignado = cliente);
              }
            },
            style: TextButton.styleFrom(
              foregroundColor: const Color(0xFFD97706),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
            ),
            child: const Text('Asignar cliente'),
          ),
        ],
      ),
    );
  }

  // ────────────────────────────────────────────────────────────
  // Detalle: Efectivo
  // ────────────────────────────────────────────────────────────

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
        _headerDetalle(context, 'Pagar factura (Efectivo)'),
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
        _contenedorDosColumnas(
          context,
          left: _columnaEfectivoIzquierda(),
          right: _columnaObservaciones(),
        ),
        const SizedBox(height: 14),
        if (bloqueadoPorConsumidorFinal) ...[
          _bannerBloqueoCuenta(context),
          const SizedBox(height: 12),
        ] else
          const SizedBox(height: 6),
        _filaBotonesAccion(
          context,
          canFinalizar: canFinalizar,
          total: total,
          onFinalizar: () => Navigator.of(context).pop(
            PagoFacturaResult(
              forma: FormaPagoFactura.efectivo,
              montoRecibidoEfectivo: pago,
              observaciones: _ctrlObsDialogo.text.trim(),
              sinVueltoAcreditarEnCuenta: pago! >= total ? _sinVueltoActivo : false,
              saldoACuenta: pagoInsuficiente ? total - pago : 0.0,
              clienteAsignado: _clienteAsignado,
            ),
          ),
        ),
      ],
    );
  }

  // ────────────────────────────────────────────────────────────
  // Detalle: Transferencia
  // ────────────────────────────────────────────────────────────

  Widget _buildDetalleTransferencia(BuildContext context) {
    final total = widget.total;
    final canFinalizar = _ctrlComprobante.text.trim().isNotEmpty;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _headerDetalle(context, 'Pagar factura (Transferencia)'),
        const SizedBox(height: 8),
        _bloqueTotalYVuelto(mostrarLineaRoja: false),
        const SizedBox(height: 14),
        _contenedorDosColumnas(
          context,
          left: _columnaTransferenciaIzquierda(total),
          right: _columnaObservaciones(),
        ),
        const SizedBox(height: 20),
        _filaBotonesAccion(
          context,
          canFinalizar: canFinalizar,
          total: total,
          onFinalizar: () => Navigator.of(context).pop(
            PagoFacturaResult(
              forma: FormaPagoFactura.transferencia,
              observaciones: _ctrlObsDialogo.text.trim(),
              numeroComprobante: _ctrlComprobante.text.trim(),
            ),
          ),
        ),
      ],
    );
  }

  Widget _columnaTransferenciaIzquierda(double total) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'N° de comprobante *',
          style: TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13,
            color: Color(0xFF374151),
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: _ctrlComprobante,
          autofocus: true,
          onChanged: (_) => setState(() {}),
          decoration: InputDecoration(
            isDense: true,
            hintText: 'Ej.: 0001234567890',
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: _bordeSeleccion, width: 1.2),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide:
                  BorderSide(color: _bordeSeleccion.withValues(alpha: 0.65)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: _bordeSeleccion, width: 1.6),
            ),
          ),
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(child: Divider(height: 1, color: Colors.grey.shade300)),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Text(
                'Monto a transferir',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey.shade600,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            Expanded(child: Divider(height: 1, color: Colors.grey.shade300)),
          ],
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            color: const Color(0xFFF0FDF4),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF86EFAC)),
          ),
          child: Text(
            formatoTotalFacturaConDecimales(total),
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: Color(0xFF15803D),
            ),
          ),
        ),
      ],
    );
  }

  // ────────────────────────────────────────────────────────────
  // Detalle: Tarjeta
  // ────────────────────────────────────────────────────────────

  Widget _buildDetalleTarjeta(BuildContext context) {
    final total = widget.total;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _headerDetalle(context, 'Pagar factura (Tarjeta)'),
        const SizedBox(height: 8),
        _bloqueTotalYVuelto(mostrarLineaRoja: false),
        const SizedBox(height: 14),
        _contenedorDosColumnas(
          context,
          left: _columnaTarjetaIzquierda(total),
          right: _columnaObservaciones(),
        ),
        const SizedBox(height: 20),
        _filaBotonesAccion(
          context,
          canFinalizar: true,
          total: total,
          onFinalizar: () => Navigator.of(context).pop(
            PagoFacturaResult(
              forma: FormaPagoFactura.tarjetaCreditoDebito,
              observaciones: _ctrlObsDialogo.text.trim(),
              tipoTarjeta: _tipoTarjeta,
              ultimosCuatroDigitos: _ctrlUltimosDigitos.text.trim().isEmpty
                  ? null
                  : _ctrlUltimosDigitos.text.trim(),
              codigoAutorizacion: _ctrlCodAutorizacion.text.trim().isEmpty
                  ? null
                  : _ctrlCodAutorizacion.text.trim(),
            ),
          ),
        ),
      ],
    );
  }

  Widget _columnaTarjetaIzquierda(double total) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Tipo de tarjeta',
          style: TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13,
            color: Color(0xFF374151),
          ),
        ),
        const SizedBox(height: 8),
        SegmentedButton<TipoTarjeta>(
          segments: const [
            ButtonSegment(
              value: TipoTarjeta.debito,
              label: Text('Débito'),
              icon: Icon(Icons.credit_card_rounded),
            ),
            ButtonSegment(
              value: TipoTarjeta.credito,
              label: Text('Crédito'),
              icon: Icon(Icons.credit_score_rounded),
            ),
          ],
          selected: {_tipoTarjeta},
          onSelectionChanged: (s) => setState(() => _tipoTarjeta = s.first),
          style: SegmentedButton.styleFrom(
            selectedBackgroundColor: const Color(0xFFCCFBF1),
            selectedForegroundColor: const Color(0xFF0F766E),
          ),
        ),
        const SizedBox(height: 16),
        _campoTextoOpcional(
          ctrl: _ctrlUltimosDigitos,
          label: 'Últimos 4 dígitos (opcional)',
          hint: '0000',
          formatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(4),
          ],
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: 12),
        _campoTextoOpcional(
          ctrl: _ctrlCodAutorizacion,
          label: 'Código de autorización (opcional)',
          hint: 'Ej.: 123456',
        ),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            color: const Color(0xFFF0FDF4),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF86EFAC)),
          ),
          child: Text(
            formatoTotalFacturaConDecimales(total),
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: Color(0xFF15803D),
            ),
          ),
        ),
      ],
    );
  }

  Widget _campoTextoOpcional({
    required TextEditingController ctrl,
    required String label,
    required String hint,
    List<TextInputFormatter>? formatters,
    TextInputType? keyboardType,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13,
            color: Color(0xFF374151),
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: ctrl,
          inputFormatters: formatters,
          keyboardType: keyboardType,
          decoration: InputDecoration(
            isDense: true,
            hintText: hint,
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
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
      ],
    );
  }

  // ────────────────────────────────────────────────────────────
  // Detalle: QR
  // ────────────────────────────────────────────────────────────

  Widget _buildDetalleQr(BuildContext context) {
    final total = widget.total;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _headerDetalle(context, 'Pagar factura (QR)'),
        const SizedBox(height: 16),
        const Icon(Icons.qr_code_2_rounded, size: 72, color: _bordeSeleccion),
        const SizedBox(height: 12),
        Text(
          formatoTotalFacturaConDecimales(total),
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w800,
            color: Color(0xFF111827),
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Presentá el código QR al cliente y confirmá cuando el pago sea aprobado.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 13, color: Color(0xFF6B7280), height: 1.4),
        ),
        const SizedBox(height: 20),
        SizedBox(height: 110, child: _columnaObservaciones()),
        const SizedBox(height: 20),
        _filaBotonesAccion(
          context,
          canFinalizar: true,
          total: total,
          onFinalizar: () => Navigator.of(context).pop(
            PagoFacturaResult(
              forma: FormaPagoFactura.qr,
              observaciones: _ctrlObsDialogo.text.trim(),
            ),
          ),
        ),
      ],
    );
  }

  // ────────────────────────────────────────────────────────────
  // Detalle: Cuenta Corriente
  // ────────────────────────────────────────────────────────────

  Widget _buildDetalleCuentaCorriente(BuildContext context) {
    final total = widget.total;
    final canFinalizar = !_esConsumidorFinalEfectivo;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _headerDetalle(context, 'Pagar factura (Cuenta Corriente)'),
        const SizedBox(height: 8),
        _bloqueTotalYVuelto(mostrarLineaRoja: false),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0xFFEFF6FF),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFFBFDBFE)),
          ),
          child: Row(
            children: [
              const Icon(
                Icons.info_outline_rounded,
                size: 16,
                color: Color(0xFF2563EB),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'El total ${formatoTotalFacturaConDecimales(total)} se acreditará en la cuenta corriente del cliente.',
                  style: const TextStyle(fontSize: 12, color: Color(0xFF1D4ED8)),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (_esConsumidorFinalEfectivo) ...[
          _bannerBloqueoCuenta(context),
          const SizedBox(height: 12),
        ],
        SizedBox(height: 140, child: _columnaObservaciones()),
        const SizedBox(height: 20),
        _filaBotonesAccion(
          context,
          canFinalizar: canFinalizar,
          total: total,
          onFinalizar: () => Navigator.of(context).pop(
            PagoFacturaResult(
              forma: FormaPagoFactura.cuentaCorriente,
              observaciones: _ctrlObsDialogo.text.trim(),
              saldoACuenta: total,
              clienteAsignado: _clienteAsignado,
            ),
          ),
        ),
      ],
    );
  }

  // ────────────────────────────────────────────────────────────
  // Detalle: Combinado
  // ────────────────────────────────────────────────────────────

  static const _opcionesMetodoCombinado = [
    FormaPagoFactura.efectivo,
    FormaPagoFactura.transferencia,
    FormaPagoFactura.tarjetaCreditoDebito,
    FormaPagoFactura.qr,
  ];

  Widget _buildDetalleCombinado(BuildContext context) {
    final total = widget.total;
    final monto1 = _parseMontoCombinado1();
    final monto2 = monto1 != null ? total - monto1 : null;
    final canFinalizar =
        monto1 != null && monto1 > 0.009 && monto1 < total - 0.009;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _headerDetalle(context, 'Pagar factura (Combinado)'),
        const SizedBox(height: 8),
        _bloqueTotalYVuelto(mostrarLineaRoja: false),
        const SizedBox(height: 14),
        _contenedorDosColumnas(
          context,
          left: _columnaCombinado1(monto1, monto2),
          right: _columnaCombinado2(monto2),
        ),
        const SizedBox(height: 20),
        _filaBotonesAccion(
          context,
          canFinalizar: canFinalizar,
          total: total,
          onFinalizar: () => Navigator.of(context).pop(
            PagoFacturaResult(
              forma: FormaPagoFactura.combinado,
              observaciones: _ctrlObsDialogo.text.trim(),
              montoMetodo1: monto1,
              metodo2: _metodoCombinado2,
            ),
          ),
        ),
      ],
    );
  }

  Widget _columnaCombinado1(double? monto1, double? monto2) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Método principal',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: Color(0xFF5D6778),
          ),
        ),
        const SizedBox(height: 8),
        _gridMetodosCombinado(
          seleccion: _metodoCombinado1,
          onSelect: (f) => setState(() => _metodoCombinado1 = f),
        ),
        const SizedBox(height: 14),
        const Text(
          'Monto *',
          style: TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13,
            color: Color(0xFF374151),
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: _ctrlMontoCombinado1,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[\d.,]')),
          ],
          onChanged: (_) => setState(() {}),
          decoration: InputDecoration(
            isDense: true,
            hintText: '0.00',
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: _bordeSeleccion, width: 1.2),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide:
                  BorderSide(color: _bordeSeleccion.withValues(alpha: 0.65)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: _bordeSeleccion, width: 1.6),
            ),
          ),
        ),
        if (monto2 != null && monto2 > 0.009) ...[
          const SizedBox(height: 8),
          Text(
            'Resto con ${_metodoCombinado2.etiqueta}: ${formatoTotalFacturaConDecimales(monto2)}',
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: Color(0xFFF59E0B),
            ),
          ),
        ],
      ],
    );
  }

  Widget _columnaCombinado2(double? monto2) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Segundo método',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: Color(0xFF5D6778),
          ),
        ),
        const SizedBox(height: 8),
        _gridMetodosCombinado(
          seleccion: _metodoCombinado2,
          onSelect: (f) => setState(() => _metodoCombinado2 = f),
        ),
        const SizedBox(height: 14),
        if (monto2 != null) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: monto2 > 0.009
                  ? const Color(0xFFF0FDF4)
                  : const Color(0xFFFEF2F2),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: monto2 > 0.009
                    ? const Color(0xFF86EFAC)
                    : const Color(0xFFFCA5A5),
              ),
            ),
            child: Text(
              monto2 > 0.009
                  ? 'Monto: ${formatoTotalFacturaConDecimales(monto2)}'
                  : 'El monto del método principal cubre el total',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: monto2 > 0.009
                    ? const Color(0xFF15803D)
                    : const Color(0xFFDC2626),
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
        Expanded(child: _columnaObservaciones()),
      ],
    );
  }

  Widget _gridMetodosCombinado({
    required FormaPagoFactura seleccion,
    required void Function(FormaPagoFactura) onSelect,
  }) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var r = 0; r < 2; r++) ...[
          if (r > 0) const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: _celdaMetodoCombinado(
                  _opcionesMetodoCombinado[r * 2],
                  seleccionado: seleccion == _opcionesMetodoCombinado[r * 2],
                  onTap: () => onSelect(_opcionesMetodoCombinado[r * 2]),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _celdaMetodoCombinado(
                  _opcionesMetodoCombinado[r * 2 + 1],
                  seleccionado:
                      seleccion == _opcionesMetodoCombinado[r * 2 + 1],
                  onTap: () => onSelect(_opcionesMetodoCombinado[r * 2 + 1]),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _celdaMetodoCombinado(
    FormaPagoFactura forma, {
    required bool seleccionado,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          height: 64,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: seleccionado ? _bordeSeleccion : _borde,
              width: seleccionado ? 2 : 1,
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  forma.icono,
                  size: 20,
                  color: seleccionado ? _bordeSeleccion : _iconoInactivo,
                ),
                const SizedBox(height: 4),
                Text(
                  forma.etiqueta,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 9,
                    height: 1.15,
                    fontWeight:
                        seleccionado ? FontWeight.w700 : FontWeight.w500,
                    color: seleccionado
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

  // ────────────────────────────────────────────────────────────
  // Widgets compartidos de columna
  // ────────────────────────────────────────────────────────────

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
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: _bordeSeleccion, width: 1.2),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide:
                  BorderSide(color: _bordeSeleccion.withValues(alpha: 0.65)),
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
                borderSide:
                    const BorderSide(color: _bordeSeleccion, width: 1.2),
              ),
            ),
          ),
        ),
      ],
    );
  }

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
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      child: Text(formatoTotalFacturaConDecimales(m)),
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
