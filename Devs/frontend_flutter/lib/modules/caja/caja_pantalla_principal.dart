import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import 'pagar_factura_dialog.dart';

/// Pantalla principal de Caja — alineada a `submodulo_caja.md` y `wireframe_caja_v6.md`.
/// Cola de tickets, escáner, resumen y pestañas inferiores (mock / API local).
class CajaPantallaPrincipal extends StatefulWidget {
  const CajaPantallaPrincipal({super.key});

  @override
  State<CajaPantallaPrincipal> createState() => _CajaPantallaPrincipalState();
}

class _CajaPantallaPrincipalState extends State<CajaPantallaPrincipal> {
  final _api = ClienteApi();
  final _controlBuscar = TextEditingController();
  final _focusBuscar = FocusNode();
  final _observacionesTicketCtrl = TextEditingController();

  bool _cargando = true;
  List<TicketMock> _tickets = [];
  int? _filaSeleccionada;
  int _pestanaInferior = 0;

  /// Impresión automática del ticket al cobrar (UI; integración pendiente).
  bool _impresionAutomaticaTicket = false;
  /// Enviar factura por correo al finalizar (UI; integración pendiente).
  bool _envioFacturaPorEmail = false;

  static const _bordePanel = Color(0xFFE1E3E8);
  static const _fondoApp = Color(0xFFF4F5F8);
  static const _cabeceraTabla = Color(0xFFE4E7EC);
  static const _zebraClara = Colors.white;
  /// Zebra más suave que la anterior para menos contraste entre filas.
  static const _zebraOscura = Color(0xFFF5F7FA);
  static const _bordeGrilla = Color(0xFFB8C0CC);
  static const _iconoOpcionInactivo = Color(0xFF9CA3AF);
  static const _iconoOpcionActivo = Color(0xFF22C55E);

  @override
  void initState() {
    super.initState();
    _cargarTickets();
  }

  @override
  void dispose() {
    _controlBuscar.dispose();
    _focusBuscar.dispose();
    _observacionesTicketCtrl.dispose();
    super.dispose();
  }

  Future<void> _cargarTickets() async {
    setState(() {
      _cargando = true;
      _filaSeleccionada = null;
    });
    try {
      final lista = await _api.listarTicketsPendientesVenta();
      if (!mounted) return;
      setState(() {
        _tickets = lista.isNotEmpty ? lista : _ticketsDemo();
        _cargando = false;
        _filaSeleccionada = _tickets.isNotEmpty ? 0 : null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _tickets = _ticketsDemo();
        _cargando = false;
        _filaSeleccionada = _tickets.isNotEmpty ? 0 : null;
      });
    }
  }

  /// Datos de ejemplo (wireframe v6) si la API no devuelve filas.
  List<TicketMock> _ticketsDemo() {
    TicketItemMock linea(
      int pid,
      String nombre,
      double cant,
      double pu,
      double sub,
    ) {
      return TicketItemMock(
        productoId: pid,
        nombre: nombre,
        cantidad: cant,
        precioUnitario: pu,
        subtotal: sub,
      );
    }

    TicketMock fila({
      required int id,
      required String nombre,
      required String doc,
      required DateTime fecha,
      required double total,
      required List<TicketItemMock> items,
      String vendedor = 'Ana López',
      String cajero = 'Caja principal',
    }) {
      return TicketMock(
        ticketId: id,
        clienteId: id,
        clienteNombre: nombre,
        documento: doc,
        estado: TicketEstado.pendiente,
        fecha: fecha,
        items: items,
        total: total,
        saldoPendiente: total,
        vendedorNombre: vendedor,
        cajeroNombre: cajero,
      );
    }

    final base = DateTime.now();
    return [
      fila(
        id: 124,
        nombre: 'Victoria Perez',
        doc: '32911452',
        fecha: DateTime(base.year, base.month, base.day, 18, 3),
        total: 3630,
        vendedor: 'Ana López',
        cajero: 'María Gómez',
        items: [
          linea(1, 'Jamón cocido', 1, 2100, 2100),
          linea(2, 'Queso cremoso', 0.5, 3060, 1530),
        ],
      ),
      fila(
        id: 125,
        nombre: 'Consumidor Final',
        doc: '',
        fecha: DateTime(base.year, base.month, base.day, 18, 4),
        total: 2200,
        vendedor: 'Carlos Ruiz',
        cajero: 'María Gómez',
        items: [
          linea(3, 'Pan francés', 10, 220, 2200),
        ],
      ),
      fila(
        id: 126,
        nombre: 'Juan Gomez',
        doc: '30111452',
        fecha: DateTime(base.year, base.month, base.day, 18, 5),
        total: 8400,
        vendedor: 'Ana López',
        cajero: 'Lucía Fernández',
        items: [
          linea(4, 'Carne picada', 2, 2800, 5600),
          linea(5, 'Tomate perita', 1.5, 1200, 1800),
          linea(6, 'Cebolla', 1, 1000, 1000),
        ],
      ),
      fila(
        id: 127,
        nombre: 'Maria Rodriguez',
        doc: '27911252',
        fecha: DateTime(base.year, base.month, base.day, 18, 6),
        total: 9700,
        vendedor: 'Pedro Sánchez',
        cajero: 'Lucía Fernández',
        items: [
          linea(7, 'Leche entera', 12, 450, 5400),
          linea(8, 'Yogur natural', 6, 550, 3300),
          linea(9, 'Manteca', 2, 500, 1000),
        ],
      ),
      fila(
        id: 128,
        nombre: 'Luis Alvarez',
        doc: '22543936',
        fecha: DateTime(base.year, base.month, base.day, 18, 9),
        total: 58370,
        vendedor: 'Carlos Ruiz',
        cajero: 'María Gómez',
        items: [
          linea(10, 'Aceite girasol', 4, 3200, 12800),
          linea(11, 'Arroz 1kg', 15, 1800, 27000),
          linea(12, 'Fideos', 20, 450, 9000),
          linea(13, 'Azúcar', 5, 1914, 9570),
        ],
      ),
    ];
  }

  double get _montoTotalPendiente =>
      _tickets.fold<double>(0, (a, t) => a + t.saldoPendiente);

  static String _formatoTicket(int id) => id.toString().padLeft(6, '0');

  static String _formatoMonto(double v) {
    final n = v.round().abs();
    final s = n.toString();
    final buf = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      final desdeElFinal = s.length - i;
      if (i > 0 && desdeElFinal % 3 == 0) buf.write(',');
      buf.write(s[i]);
    }
    return '\$$buf';
  }

  static String _formatoHora(DateTime d) =>
      '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

  void _onEscanearOCodigo(String raw) {
    final t = raw.trim();
    if (t.isEmpty) return;
    final id = int.tryParse(t.replaceAll(RegExp(r'[^0-9]'), ''));
    if (id == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Código no reconocido: $t')),
      );
      return;
    }
    final idx = _tickets.indexWhere((e) => e.ticketId == id);
    if (idx < 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Ticket ${_formatoTicket(id)} no está en la cola.',
          ),
        ),
      );
      return;
    }
    setState(() => _filaSeleccionada = idx);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Ticket seleccionado: ${_formatoTicket(id)}')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);

    return Shortcuts(
      shortcuts: const {
        SingleActivator(LogicalKeyboardKey.f2): _IntentBuscarCaja(),
      },
      child: Actions(
        actions: {
          _IntentBuscarCaja: CallbackAction<_IntentBuscarCaja>(
            onInvoke: (_) {
              _focusBuscar.requestFocus();
              return null;
            },
          ),
        },
        child: Focus(
          autofocus: false,
          child: Container(
            color: _fondoApp,
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    border: Border.all(color: _bordePanel),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Text(
                        'Caja',
                        style: tema.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: const Color(0xFF303645),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        flex: 7,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                border: Border.all(color: _bordePanel),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: TextField(
                                controller: _controlBuscar,
                                focusNode: _focusBuscar,
                                decoration: const InputDecoration(
                                  hintText:
                                      'Escanear código de ticket o ingresar número',
                                  prefixIcon: Icon(Icons.search),
                                  isDense: true,
                                ),
                                onSubmitted: _onEscanearOCodigo,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Expanded(
                              child: Container(
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: _bordePanel),
                                ),
                                clipBehavior: Clip.antiAlias,
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    Padding(
                                      padding: const EdgeInsets.fromLTRB(
                                          16, 14, 16, 10),
                                      child: _resumenColaTexto(),
                                    ),
                                    Expanded(
                                      child: Padding(
                                        padding: const EdgeInsets.fromLTRB(
                                            16, 0, 16, 16),
                                        child: _cargando
                                            ? const Center(
                                                child:
                                                    CircularProgressIndicator(),
                                              )
                                            : _tablaTickets(),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      SizedBox(
                        width: 360,
                        child: _panelResumenTicketDerecho(),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                _barraPestanasInferior(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Panel derecho alineado a Pesables (ancho fijo 360): detalle del ticket.
  Widget _panelResumenTicketDerecho() {
    final idx = _filaSeleccionada;
    final t = (idx != null && idx >= 0 && idx < _tickets.length)
        ? _tickets[idx]
        : null;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFDDE1E9)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: t == null
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'Seleccione un ticket en la tabla o escanee su código.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Color(0xFF6E7380),
                    fontSize: 14,
                    height: 1.35,
                  ),
                ),
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    const Expanded(
                      child: Text(
                        'Resumen del ticket',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                          color: Color(0xFF303645),
                        ),
                      ),
                    ),
                    _iconoToggleResumen(
                      activo: _impresionAutomaticaTicket,
                      icono: Icons.print_rounded,
                      tooltip: 'Impresión automática del ticket',
                      onTap: () => setState(() {
                        _impresionAutomaticaTicket =
                            !_impresionAutomaticaTicket;
                      }),
                    ),
                    const SizedBox(width: 2),
                    _iconoToggleResumen(
                      activo: _envioFacturaPorEmail,
                      icono: Icons.mark_email_read_outlined,
                      tooltip: 'Enviar factura por correo',
                      onTap: () => setState(() {
                        _envioFacturaPorEmail = !_envioFacturaPorEmail;
                      }),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                const Text(
                  'Observaciones',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: Color(0xFF5D6778),
                  ),
                ),
                const SizedBox(height: 6),
                SizedBox(
                  height: 100,
                  child: TextField(
                    controller: _observacionesTicketCtrl,
                    maxLines: null,
                    expands: true,
                    textAlignVertical: TextAlignVertical.top,
                    decoration: InputDecoration(
                      hintText: 'Notas u observaciones del ticket…',
                      isDense: true,
                      contentPadding: const EdgeInsets.all(12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: _bordePanel),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: _bordePanel),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(
                          color: Color(0xFF0D9488),
                          width: 1.2,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                const Text(
                  'Productos',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: Color(0xFF5D6778),
                  ),
                ),
                const SizedBox(height: 6),
                Expanded(
                  child: t.items.isEmpty
                      ? const Center(
                          child: Text(
                            'Sin ítems en este ticket.',
                            style: TextStyle(
                              color: Color(0xFF6E7380),
                              fontSize: 13,
                            ),
                          ),
                        )
                      : ListView.separated(
                          itemCount: t.items.length,
                          separatorBuilder: (_, __) =>
                              const Divider(height: 1),
                          itemBuilder: (context, i) {
                            final it = t.items[i];
                            final sub = _formatoMonto(it.subtotal);
                            final detalle =
                                '${_formatoCantidadLinea(it.cantidad)} × ${_formatoMonto(it.precioUnitario)}';
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 6),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          it.nombre,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w600,
                                            fontSize: 14,
                                            color: Color(0xFF303645),
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          detalle,
                                          style: const TextStyle(
                                            fontSize: 12,
                                            color: Color(0xFF6E7380),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Text(
                                    sub,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                      fontSize: 14,
                                      color: Color(0xFF303645),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ),
                const SizedBox(height: 10),
                const Divider(height: 1),
                const SizedBox(height: 10),
                FilledButton(
                  style: estiloBotonBarraCaja(),
                  onPressed: () async {
                    final esConsumidorFinal = t.documento.isEmpty;
                    final resultado = await PagarFacturaDialog.show(
                      context,
                      t.saldoPendiente,
                      esConsumidorFinal: esConsumidorFinal,
                    );
                    if (!mounted) return;
                    if (resultado != null) {
                      final obsTicket = _observacionesTicketCtrl.text.trim();
                      final buf = StringBuffer()
                        ..write(
                          'Ticket ${_formatoTicket(t.ticketId)} · '
                          '${resultado.forma.etiqueta}',
                        );
                      if (resultado.montoRecibidoEfectivo != null) {
                        buf.write(
                          ' · Recibido: '
                          '${formatoTotalFacturaConDecimales(resultado.montoRecibidoEfectivo!)}',
                        );
                      }
                      if (resultado.saldoACuenta > 0.009) {
                        buf.write(
                          ' · Saldo a cuenta: '
                          '${formatoTotalFacturaConDecimales(resultado.saldoACuenta)}',
                        );
                      }
                      if (resultado.clienteAsignado != null) {
                        buf.write(
                          ' · Cliente asignado: '
                          '${resultado.clienteAsignado!.nombreCompleto}',
                        );
                      }
                      if (resultado.sinVueltoAcreditarEnCuenta) {
                        buf.write(' · Sin vuelto (acreditar en cuenta)');
                      }
                      if (obsTicket.isNotEmpty) {
                        buf.write(' · Obs. ticket: $obsTicket');
                      }
                      if (resultado.observaciones.isNotEmpty) {
                        buf.write(' · Obs. cobro: ${resultado.observaciones}');
                      }
                      buf.write(' — siguiente paso pendiente.');
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(buf.toString())),
                      );
                    }
                  },
                  child: Row(
                    children: [
                      const Text(
                        'Total a pagar',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        _formatoMonto(t.saldoPendiente),
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 18,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  /// Icono pequeño conmutado: gris inactivo, verde activo.
  Widget _iconoToggleResumen({
    required bool activo,
    required IconData icono,
    required String tooltip,
    required VoidCallback onTap,
  }) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(6),
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Icon(
            icono,
            size: 20,
            color: activo ? _iconoOpcionActivo : _iconoOpcionInactivo,
          ),
        ),
      ),
    );
  }

  static String _formatoCantidadLinea(double c) {
    if ((c - c.round()).abs() < 1e-9) {
      return c.round().toString();
    }
    return c.toStringAsFixed(2);
  }

  Widget _resumenColaTexto() {
    final n = _tickets.length;
    final monto = _formatoMonto(_montoTotalPendiente);
    return Text.rich(
      TextSpan(
        style: const TextStyle(
          fontSize: 15,
          color: Color(0xFF4E586B),
          height: 1.4,
        ),
        children: [
          const TextSpan(
            text: 'Tickets en espera: ',
            style: TextStyle(fontWeight: FontWeight.w500),
          ),
          TextSpan(
            text: '$n',
            style: const TextStyle(
              fontWeight: FontWeight.w800,
              color: Color(0xFF303645),
            ),
          ),
          const TextSpan(
            text: ' - Monto total pendiente: ',
            style: TextStyle(fontWeight: FontWeight.w500),
          ),
          TextSpan(
            text: monto,
            style: const TextStyle(
              fontWeight: FontWeight.w800,
              color: Color(0xFF303645),
            ),
          ),
        ],
      ),
    );
  }

  Widget _tablaTickets() {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: _bordeGrilla),
        borderRadius: BorderRadius.circular(8),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _filaEncabezadoTabla(),
          Expanded(
            child: _tickets.isEmpty
                ? const Center(
                    child: Text(
                      'No hay tickets pendientes.',
                      style: TextStyle(
                        color: Color(0xFF6E7380),
                        fontSize: 14,
                      ),
                    ),
                  )
                : ListView.builder(
                    itemCount: _tickets.length,
                    itemBuilder: (context, i) => _filaDatosTabla(context, i),
                  ),
          ),
        ],
      ),
    );
  }

  static const _estiloEncabezadoTabla = TextStyle(
    fontWeight: FontWeight.w700,
    fontSize: 14,
    color: Color(0xFF3D4555),
  );

  static const _estiloCeldaTabla = TextStyle(
    fontSize: 14,
    color: Color(0xFF303645),
  );

  Widget _celdaGrilla({
    required Widget child,
    int flex = 2,
    TextAlign align = TextAlign.left,
    bool ultimaColumna = false,
    bool esEncabezado = false,
  }) {
    return Expanded(
      flex: flex,
      child: Container(
        decoration: BoxDecoration(
          border: Border(
            right: ultimaColumna
                ? BorderSide.none
                : const BorderSide(color: _bordeGrilla, width: 1),
            bottom: const BorderSide(color: _bordeGrilla, width: 1),
          ),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        alignment: align == TextAlign.right
            ? Alignment.centerRight
            : Alignment.centerLeft,
        child: DefaultTextStyle(
          style: esEncabezado ? _estiloEncabezadoTabla : _estiloCeldaTabla,
          textAlign: align,
          child: child,
        ),
      ),
    );
  }

  Widget _filaEncabezadoTabla() {
    return Container(
      color: _cabeceraTabla,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          _celdaGrilla(
            esEncabezado: true,
            child: const Text('Ticket'),
          ),
          _celdaGrilla(
            flex: 3,
            esEncabezado: true,
            child: const Text('Cliente'),
          ),
          _celdaGrilla(
            esEncabezado: true,
            child: const Text('DNI'),
          ),
          _celdaGrilla(
            esEncabezado: true,
            child: const Text('Hora'),
          ),
          _celdaGrilla(
            esEncabezado: true,
            ultimaColumna: true,
            align: TextAlign.right,
            child: const Text('Total'),
          ),
        ],
      ),
    );
  }

  Widget _filaDatosTabla(BuildContext context, int i) {
    final t = _tickets[i];
    final sel = _filaSeleccionada == i;
    final zebra = i.isEven ? _zebraClara : _zebraOscura;
    return Material(
      color: sel ? const Color(0xFFD6EAF8) : zebra,
      child: InkWell(
        onTap: () => setState(() => _filaSeleccionada = i),
        onDoubleTap: () {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Detalle ticket ${_formatoTicket(t.ticketId)}: próximamente.',
              ),
            ),
          );
        },
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            _celdaGrilla(
              child: Text(
                _formatoTicket(t.ticketId),
                style: _estiloCeldaTabla.copyWith(
                  fontWeight: FontWeight.w600,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ),
            _celdaGrilla(
              flex: 3,
              child: Text(t.clienteNombre),
            ),
            _celdaGrilla(
              child: Text(t.documento.isEmpty ? '—' : t.documento),
            ),
            _celdaGrilla(
              child: Text(_formatoHora(t.fecha)),
            ),
            _celdaGrilla(
              ultimaColumna: true,
              align: TextAlign.right,
              child: Text(
                _formatoMonto(t.saldoPendiente),
                style: _estiloCeldaTabla.copyWith(fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Mismo patrón que Ventas / Pesables (`_TabVenta` / `_TabPes`).
  Widget _barraPestanasInferior() {
    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _bordePanel),
      ),
      child: Row(
        children: [
          _TabCaja(
            texto: 'Pendiente ${_tickets.length}',
            seleccionado: _pestanaInferior == 0,
            onTap: () => setState(() => _pestanaInferior = 0),
          ),
          _TabCaja(
            texto: 'Victoria',
            seleccionado: _pestanaInferior == 1,
            onTap: () => setState(() => _pestanaInferior = 1),
          ),
          IconButton(
            tooltip: 'Nueva pestaña',
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text('Nueva sesión de caja: pendiente.')),
              );
            },
            icon: const Icon(Icons.add),
          ),
        ],
      ),
    );
  }
}

class _TabCaja extends StatelessWidget {
  const _TabCaja({
    required this.texto,
    required this.seleccionado,
    required this.onTap,
  });

  final String texto;
  final bool seleccionado;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: seleccionado ? const Color(0xFFF4F6FA) : Colors.transparent,
          border: const Border(
            right: BorderSide(color: Color(0xFFE1E3E8)),
          ),
        ),
        alignment: Alignment.center,
        child: Text(
          texto,
          style: TextStyle(
            fontWeight: seleccionado ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ),
    );
  }
}

class _IntentBuscarCaja extends Intent {
  const _IntentBuscarCaja();
}
