import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import 'carrito_widget.dart';
import 'models/pos_context.dart';

class PantallaVentas extends StatefulWidget {
  const PantallaVentas({super.key});

  @override
  State<PantallaVentas> createState() => _PantallaVentasState();
}

class _PantallaVentasState extends State<PantallaVentas> {
  final _clienteApi = ClienteApi();
  final _controlBusqueda = TextEditingController();
  final _controlCodigoBarras = TextEditingController();
  final _focusBusqueda = FocusNode();
  final _focusCodigoBarras = FocusNode();

  final List<Map<String, dynamic>> _resultados = [];
  final List<ItemCarrito> _carrito = [];
  double _descuento = 0;
  bool _cargandoCatalogo = true;
  bool _teuOn =
      false; // TEU ON: cobro inmediato. TEU OFF: ticket enviado a Caja.
  bool _cargandoClientes = true;
  List<ClienteMock> _clientes = const [];
  int _clienteIdSeleccionado = 0;
  MetodoPago _metodoPago = MetodoPago.efectivo;
  bool _procesandoCobro = false;
  String _listaPrecioSeleccionada = 'General';
  String _tipoComprobanteSeleccionado = 'Ticket';
  int _pestanaVentaSeleccionada = 0;
  final _controlTicketSuspenso = TextEditingController();
  bool _cargandoTicketsSuspenso = false;
  List<TicketMock> _ticketsPendientesVenta = [];
  List<TicketMock> _ticketsSuspendidosVenta = [];
  TicketMock? _ticketSeleccionadoSuspenso;
  final List<POS> _puntosVenta = const [
    POS(id: 'pos-1', nombre: 'Punto de venta 1', activo: true),
    POS(id: 'pos-2', nombre: 'Punto de venta 2', activo: true),
  ];
  POSSession? _sesionPos;
  final Map<String, String> _vendedoresPorId = const {
    'vendedor-1': 'Victoria',
    'vendedor-2': 'Carlos',
  };

  @override
  void initState() {
    super.initState();
    _clienteApi.cargarCatalogo().then((_) {
      if (mounted) setState(() => _cargandoCatalogo = false);
    }).catchError((_) {
      if (mounted) setState(() => _cargandoCatalogo = false);
    });

    _clienteApi.listarClientes().then((lista) {
      if (!mounted) return;
      setState(() {
        _clientes = lista;
        _clienteIdSeleccionado = lista.any((c) => c.clienteId == 0)
            ? 0
            : (lista.firstOrNull?.clienteId ?? 0);
        _cargandoClientes = false;
      });
    }).catchError((_) {
      if (!mounted) return;
      setState(() => _cargandoClientes = false);
    });

    _refrescarTicketsSuspenso();
  }

  @override
  void dispose() {
    _controlBusqueda.dispose();
    _controlCodigoBarras.dispose();
    _controlTicketSuspenso.dispose();
    _focusBusqueda.dispose();
    _focusCodigoBarras.dispose();
    super.dispose();
  }

  double get _totalPendienteVentas => _ticketsPendientesVenta.fold<double>(
      0, (acc, t) => acc + t.saldoPendiente);

  double get _totalSuspendidaVentas => _ticketsSuspendidosVenta.fold<double>(
      0, (acc, t) => acc + t.saldoPendiente);

  Future<void> _refrescarTicketsSuspenso() async {
    setState(() => _cargandoTicketsSuspenso = true);
    try {
      _ticketsPendientesVenta =
          await _clienteApi.listarTicketsPendientesVenta();
      _ticketsSuspendidosVenta =
          await _clienteApi.listarTicketsSuspendidosVenta();

      final lista = _ticketsPendientesVenta + _ticketsSuspendidosVenta;
      if (_ticketSeleccionadoSuspenso == null ||
          !lista.any(
              (t) => t.ticketId == _ticketSeleccionadoSuspenso?.ticketId)) {
        _ticketSeleccionadoSuspenso = lista.isNotEmpty ? lista.first : null;
      }
    } catch (_) {
      // Los chips fallan silenciosamente; el cobro principal debe seguir funcionando.
    } finally {
      if (!mounted) return;
      setState(() => _cargandoTicketsSuspenso = false);
    }
  }

  List<TicketMock> get _ticketsSuspensoTotales =>
      [..._ticketsPendientesVenta, ..._ticketsSuspendidosVenta];

  bool get _posSeleccionado => _sesionPos != null;

  String get _nombreVendedorActivo {
    final vendedorId = _sesionPos?.vendedorId;
    if (vendedorId == null) return 'Vendedor: Sin seleccionar';
    final nombre = _vendedoresPorId[vendedorId] ?? 'Sin nombre';
    return 'Vendedor: $nombre';
  }

  static const List<_CategoriaPos> _categoriasPos = [
    _CategoriaPos('Bebidas', Icons.wine_bar_outlined),
    _CategoriaPos('Lacteos', Icons.local_drink_outlined),
    _CategoriaPos('Fiambres', Icons.set_meal_outlined),
    _CategoriaPos('Panaderia', Icons.bakery_dining_outlined),
    _CategoriaPos('Snacks', Icons.cookie_outlined),
    _CategoriaPos('Limpieza', Icons.cleaning_services_outlined),
    _CategoriaPos('Despensa', Icons.shopping_basket_outlined),
    _CategoriaPos('Carniceria', Icons.kebab_dining_outlined),
  ];

  Future<void> _suspenderTicketSeleccionadoSuspenso() async {
    final t = _ticketSeleccionadoSuspenso;
    if (t == null) return;
    if (t.estado != TicketEstado.pendiente) return;
    try {
      await _clienteApi.suspenderTicketVenta(ticketId: t.ticketId);
      await _refrescarTicketsSuspenso();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Error al suspender: $e')));
    }
  }

  Future<void> _reanudarTicketSeleccionadoSuspenso() async {
    final t = _ticketSeleccionadoSuspenso;
    if (t == null) return;
    if (t.estado != TicketEstado.suspendida) return;
    try {
      await _clienteApi.reanudarTicketVenta(ticketId: t.ticketId);
      await _refrescarTicketsSuspenso();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Error al reanudar: $e')));
    }
  }

  Future<void> _suspenderTicketPorId() async {
    final raw = _controlTicketSuspenso.text.trim();
    final ticketId = int.tryParse(raw);
    if (ticketId == null) return;
    final ticket = await _clienteApi.obtenerTicket(ticketId);
    if (ticket == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Ticket no encontrado')));
      return;
    }
    if (ticket.estado != TicketEstado.pendiente) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Solo se puede suspender un ticket PENDIENTE')));
      return;
    }
    try {
      await _clienteApi.suspenderTicketVenta(ticketId: ticketId);
      await _refrescarTicketsSuspenso();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Error al suspender: $e')));
    }
  }

  Future<void> _reanudarTicketPorId() async {
    final raw = _controlTicketSuspenso.text.trim();
    final ticketId = int.tryParse(raw);
    if (ticketId == null) return;
    final ticket = await _clienteApi.obtenerTicket(ticketId);
    if (ticket == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Ticket no encontrado')));
      return;
    }
    if (ticket.estado != TicketEstado.suspendida) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Solo se puede reanudar un ticket SUSPENDIDA')));
      return;
    }
    try {
      await _clienteApi.reanudarTicketVenta(ticketId: ticketId);
      await _refrescarTicketsSuspenso();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Error al reanudar: $e')));
    }
  }

  void _buscarProductos(String texto) {
    _clienteApi
        .listarProductos(busqueda: texto.isEmpty ? null : texto)
        .then((lista) {
      if (!mounted) return;
      setState(() {
        _resultados
          ..clear()
          ..addAll(lista);
      });
    }).catchError((e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al buscar: $e')),
      );
    });
  }

  Future<void> _agregarPorCodigoBarras(String codigo) async {
    if (codigo.trim().isEmpty) return;
    try {
      final producto = await _clienteApi.buscarProductoPorCodigo(codigo);
      if (!mounted) return;
      if (producto == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Producto no encontrado')),
        );
        return;
      }
      _agregarProductoCarritoDesdeJson(producto);
      _controlCodigoBarras.clear();
      _focusCodigoBarras.requestFocus();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  void _agregarProductoCarritoDesdeJson(Map<String, dynamic> json) {
    final id = json['id'] as int;
    final nombre = json['nombre'] as String? ?? 'Producto';
    final precio = (json['precio_venta'] as num?)?.toDouble() ?? 0;
    final existente = _carrito.where((e) => e.idProducto == id).toList();
    setState(() {
      if (existente.isNotEmpty) {
        existente.first.cantidad += 1;
      } else {
        _carrito.add(
          ItemCarrito(
            idProducto: id,
            nombre: nombre,
            precioUnitario: precio,
          ),
        );
      }
    });
  }

  double get _subtotal =>
      _carrito.fold(0.0, (prev, item) => prev + item.subtotal);

  String _labelMetodoPago(MetodoPago metodo) {
    switch (metodo) {
      case MetodoPago.efectivo:
        return 'Efectivo';
      case MetodoPago.tarjetaCredito:
        return 'Tarjeta de credito';
      case MetodoPago.transferencia:
        return 'Transferencia';
      case MetodoPago.cuentaCorriente:
        return 'Cuenta corriente';
    }
  }

  ClienteMock get _clienteSeleccionado {
    return _clientes.firstWhere(
      (c) => c.clienteId == _clienteIdSeleccionado,
      orElse: () => _clientes.firstWhere(
        (c) => c.clienteId == 0,
        orElse: () => ClienteMock(
          clienteId: 0,
          personaId: 0,
          nombreCompleto: 'Consumidor final',
          documento: '',
          limiteCredito: 0,
        ),
      ),
    );
  }

  bool _coincideCliente(ClienteMock cliente, String busqueda) {
    final q = busqueda.trim().toLowerCase();
    if (q.isEmpty) return true;
    return cliente.nombreCompleto.toLowerCase().contains(q) ||
        cliente.documento.toLowerCase().contains(q) ||
        cliente.clienteId.toString().contains(q) ||
        cliente.personaId.toString().contains(q);
  }

  Future<void> _abrirSelectorCliente() async {
    String busqueda = '';
    final seleccionado = await showDialog<int>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            final filtrados = _clientes
                .where((c) => c.clienteId != 0 && _coincideCliente(c, busqueda))
                .toList();
            return AlertDialog(
              title: const Text('Seleccionar cliente'),
              content: SizedBox(
                width: 520,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text(
                      'Buscar cliente',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 6),
                    TextField(
                      autofocus: true,
                      decoration: const InputDecoration(
                        isDense: true,
                        hintText: 'Nombre, documento o código',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onChanged: (value) =>
                          setStateDialog(() => busqueda = value),
                    ),
                    const SizedBox(height: 10),
                    Flexible(
                      child: ListView(
                        shrinkWrap: true,
                        children: [
                          ListTile(
                            dense: true,
                            leading: const Icon(Icons.person_outline),
                            title: const Text('Consumidor final'),
                            subtitle: const Text('Valor predefinido'),
                            onTap: () => Navigator.of(context).pop(0),
                          ),
                          const Divider(height: 1),
                          if (filtrados.isEmpty)
                            const ListTile(
                              dense: true,
                              title: Text('Sin clientes coincidentes'),
                            )
                          else
                            ...filtrados.map(
                              (cliente) => ListTile(
                                dense: true,
                                title: Text(cliente.nombreCompleto),
                                subtitle: Text(
                                  cliente.documento.isEmpty
                                      ? 'Sin documento'
                                      : 'Doc: ${cliente.documento}',
                                ),
                                onTap: () => Navigator.of(context)
                                    .pop(cliente.clienteId),
                              ),
                            ),
                          const Divider(height: 1),
                          ListTile(
                            dense: true,
                            leading:
                                const Icon(Icons.person_add_alt_1_outlined),
                            title: const Text('+ Nuevo cliente'),
                            onTap: () => Navigator.of(context).pop(-1),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cerrar'),
                ),
              ],
            );
          },
        );
      },
    );

    if (!mounted || seleccionado == null) return;
    if (seleccionado == -1) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Pendiente: abrir flujo de creación de nuevo cliente.'),
        ),
      );
      return;
    }
    setState(() => _clienteIdSeleccionado = seleccionado);
  }

  Widget _construirSelectorCliente() {
    final cliente = _clienteSeleccionado;
    return InkWell(
      onTap: _abrirSelectorCliente,
      borderRadius: BorderRadius.circular(6),
      child: InputDecorator(
        decoration: const InputDecoration(isDense: true),
        child: Row(
          children: [
            Expanded(
              child: Text(
                cliente.nombreCompleto,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const Icon(Icons.arrow_drop_down),
          ],
        ),
      ),
    );
  }

  Future<void> _cobrar() async {
    if (_carrito.isEmpty) return;
    if (_procesandoCobro) return;
    final descuentoAplicado = _descuento.clamp(0.0, _subtotal).toDouble();
    final items = _carrito
        .map((e) => {
              'producto_id': e.idProducto,
              'cantidad': e.cantidad,
              'precio_unitario': e.precioUnitario,
            })
        .toList();

    try {
      setState(() => _procesandoCobro = true);

      if (_teuOn) {
        final id = await _clienteApi.crearVentaTeuOn(
          items: items,
          descuento: descuentoAplicado,
          clienteId: _clienteIdSeleccionado,
          metodoPago: _metodoPago,
        );
        if (!mounted) return;
        setState(() {
          _carrito.clear();
          _descuento = 0;
          _procesandoCobro = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              _metodoPago == MetodoPago.cuentaCorriente
                  ? 'Venta fiada registrada (ticket #$id)'
                  : 'Venta registrada correctamente (ticket #$id)',
            ),
          ),
        );
      } else {
        final ticketId = await _clienteApi.crearTicketTeuOff(
          items: items,
          descuento: descuentoAplicado,
          clienteId: _clienteIdSeleccionado,
        );
        if (!mounted) return;
        setState(() {
          _carrito.clear();
          _descuento = 0;
          _procesandoCobro = false;
        });
        await _refrescarTicketsSuspenso();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Ticket enviado a Caja (#$ticketId)'),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _procesandoCobro = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al cobrar: $e')),
      );
    }
  }

  void _cancelarVenta() {
    setState(() {
      _carrito.clear();
      _descuento = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Shortcuts(
      shortcuts: <ShortcutActivator, Intent>{
        const SingleActivator(LogicalKeyboardKey.f2): _IntentFocusBusqueda(),
        const SingleActivator(LogicalKeyboardKey.f4): _IntentCobrar(),
        const SingleActivator(LogicalKeyboardKey.escape): _IntentCancelar(),
      },
      child: Actions(
        actions: <Type, Action<Intent>>{
          _IntentFocusBusqueda: CallbackAction<_IntentFocusBusqueda>(
            onInvoke: (_) {
              _focusBusqueda.requestFocus();
              return null;
            },
          ),
          _IntentCobrar: CallbackAction<_IntentCobrar>(
            onInvoke: (_) {
              _cobrar();
              return null;
            },
          ),
          _IntentCancelar: CallbackAction<_IntentCancelar>(
            onInvoke: (_) {
              _cancelarVenta();
              return null;
            },
          ),
        },
        child: Focus(
          autofocus: true,
          child: _cargandoCatalogo
              ? const Center(child: CircularProgressIndicator())
              : _construirContenido(context),
        ),
      ),
    );
  }

  Widget _construirContenido(BuildContext context) {
    final tema = Theme.of(context);
    final subtotalNeto =
        ((_subtotal - _descuento).clamp(0.0, double.infinity)).toDouble();
    final iva = subtotalNeto * 0.21;
    final total = subtotalNeto + iva;
    final posHabilitados = _puntosVenta.where((p) => p.activo).toList();

    return Container(
      color: const Color(0xFFF4F5F8),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: const Color(0xFFE1E3E8)),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Text(
                  'Ventas',
                  style: tema.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF303645),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 220,
                  child: DropdownButtonFormField<String>(
                    isExpanded: true,
                    value: _sesionPos?.posId,
                    hint: const Text('Seleccionar POS'),
                    decoration: const InputDecoration(
                      isDense: true,
                      labelText: 'Punto de venta',
                    ),
                    items: posHabilitados
                        .map(
                          (p) => DropdownMenuItem<String>(
                            value: p.id,
                            child: Text(p.nombre),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      setState(() {
                        if (value == null) {
                          _sesionPos = null;
                          return;
                        }
                        final vendedorId =
                            value == 'pos-2' ? 'vendedor-2' : 'vendedor-1';
                        _sesionPos = POSSession(
                          posId: value,
                          vendedorId: vendedorId,
                        );
                      });
                    },
                  ),
                ),
                const Spacer(),
                _TeuToggleHeader(
                  teuOn: _teuOn,
                  onCambiar: (valor) => setState(() => _teuOn = valor),
                ),
                const SizedBox(width: 8),
                IconButton(
                  tooltip: 'Configuración rápida de venta',
                  visualDensity: VisualDensity.compact,
                  onPressed: () {},
                  icon: const Icon(
                    Icons.tune_rounded,
                    size: 18,
                    color: Color(0xFF4E586B),
                  ),
                ),
                const SizedBox(width: 2),
                _IconoAccionCarrito(
                  icono: Icons.refresh,
                  tooltip: 'Actualizar carrito',
                  onTap: () => setState(() {}),
                ),
                const SizedBox(width: 6),
                _IconoAccionCarrito(
                  icono: Icons.receipt_long_outlined,
                  tooltip: 'Ver detalle de comprobante',
                  onTap: () {},
                ),
                const SizedBox(width: 6),
                _IconoAccionCarrito(
                  icono: Icons.help_outline,
                  tooltip: 'Ayuda',
                  onTap: () {},
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          Expanded(
            child: Stack(
              children: [
                Row(
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
                              border:
                                  Border.all(color: const Color(0xFFE1E3E8)),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: TextField(
                                    enabled: _posSeleccionado,
                                    focusNode: _focusBusqueda,
                                    controller: _controlBusqueda,
                                    decoration: const InputDecoration(
                                      hintText:
                                          'Buscar producto o código de barras...',
                                      prefixIcon: Icon(Icons.search),
                                      isDense: true,
                                    ),
                                    onSubmitted: _buscarProductos,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                SizedBox(
                                  width: 190,
                                  child: DropdownButtonFormField<String>(
                                    value: 'Nuevo producto',
                                    decoration:
                                        const InputDecoration(isDense: true),
                                    items: const [
                                      DropdownMenuItem(
                                        value: 'Nuevo producto',
                                        child: Text('Nuevo producto'),
                                      ),
                                    ],
                                    onChanged: _posSeleccionado ? (_) {} : null,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 10),
                          Expanded(
                            child: Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                border:
                                    Border.all(color: const Color(0xFFE1E3E8)),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: GridView.builder(
                                itemCount: _categoriasPos.length,
                                gridDelegate:
                                    const SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount: 4,
                                  crossAxisSpacing: 10,
                                  mainAxisSpacing: 10,
                                  childAspectRatio: 1.7,
                                ),
                                itemBuilder: (context, index) {
                                  final categoria = _categoriasPos[index];
                                  return Opacity(
                                    opacity: _posSeleccionado ? 1 : 0.55,
                                    child: InkWell(
                                      borderRadius: BorderRadius.circular(8),
                                      onTap: _posSeleccionado
                                          ? () =>
                                              _buscarProductos(categoria.nombre)
                                          : null,
                                      child: Ink(
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFF8F9FB),
                                          border: Border.all(
                                              color: const Color(0xFFE2E5EC)),
                                          borderRadius:
                                              BorderRadius.circular(8),
                                        ),
                                        child: Column(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            Icon(
                                              categoria.icono,
                                              size: 28,
                                              color: const Color(0xFF8A8F9D),
                                            ),
                                            const SizedBox(height: 8),
                                            Text(
                                              categoria.nombre,
                                              style: const TextStyle(
                                                fontSize: 15,
                                                fontWeight: FontWeight.w500,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              OutlinedButton.icon(
                                onPressed: _cancelarVenta,
                                icon: const Icon(Icons.layers_clear_outlined),
                                label: const Text('Cancelar venta'),
                              ),
                              const SizedBox(width: 8),
                              OutlinedButton.icon(
                                onPressed: () => setState(() => _descuento =
                                    (_descuento + 1).clamp(0.0, _subtotal)),
                                icon: const Icon(Icons.discount_outlined),
                                label: const Text('Aplicar descuento'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Container(
                            height: 44,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              border:
                                  Border.all(color: const Color(0xFFE1E3E8)),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                _TabVenta(
                                  texto: 'Venta principal',
                                  seleccionado: _pestanaVentaSeleccionada == 0,
                                  onTap: () => setState(
                                      () => _pestanaVentaSeleccionada = 0),
                                ),
                                _TabVenta(
                                  texto: 'Victoria',
                                  seleccionado: _pestanaVentaSeleccionada == 1,
                                  onTap: () => setState(
                                      () => _pestanaVentaSeleccionada = 1),
                                ),
                                IconButton(
                                  onPressed: () => setState(
                                      () => _pestanaVentaSeleccionada = 1),
                                  icon: const Icon(Icons.add),
                                  tooltip: 'Nueva pestaña',
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    SizedBox(
                      width: 340,
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          border: Border.all(color: const Color(0xFFDDE1E9)),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text(
                              _nombreVendedorActivo,
                              style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: Color(0xFF5D6778),
                              ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.stretch,
                                    children: [
                                      const Text('Lista de precios'),
                                      const SizedBox(height: 4),
                                      DropdownButtonFormField<String>(
                                        isExpanded: true,
                                        value: _listaPrecioSeleccionada,
                                        decoration: const InputDecoration(
                                            isDense: true),
                                        items: const [
                                          DropdownMenuItem(
                                            value: 'General',
                                            child: Text('General'),
                                          ),
                                        ],
                                        onChanged: (v) {
                                          if (v == null) return;
                                          setState(() =>
                                              _listaPrecioSeleccionada = v);
                                        },
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.stretch,
                                    children: [
                                      const Text('Tipo comprobante'),
                                      const SizedBox(height: 4),
                                      DropdownButtonFormField<String>(
                                        isExpanded: true,
                                        value: _tipoComprobanteSeleccionado,
                                        decoration: const InputDecoration(
                                            isDense: true),
                                        items: const [
                                          DropdownMenuItem(
                                            value: 'Ticket',
                                            child: Text('Ticket'),
                                          ),
                                          DropdownMenuItem(
                                            value: 'Factura',
                                            child: Text('Factura'),
                                          ),
                                        ],
                                        onChanged: (v) {
                                          if (v == null) return;
                                          setState(() =>
                                              _tipoComprobanteSeleccionado = v);
                                        },
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),
                            if (_teuOn)
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.stretch,
                                      children: [
                                        const Text('Cliente'),
                                        const SizedBox(height: 4),
                                        _construirSelectorCliente(),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.stretch,
                                      children: [
                                        const Text('Metodo de pago'),
                                        const SizedBox(height: 4),
                                        DropdownButtonFormField<MetodoPago>(
                                          isExpanded: true,
                                          value: _metodoPago,
                                          decoration: const InputDecoration(
                                              isDense: true),
                                          items: MetodoPago.values
                                              .map(
                                                (m) => DropdownMenuItem(
                                                  value: m,
                                                  child:
                                                      Text(_labelMetodoPago(m)),
                                                ),
                                              )
                                              .toList(),
                                          onChanged: (v) {
                                            if (v == null) return;
                                            setState(() => _metodoPago = v);
                                          },
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              )
                            else
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  const Text('Cliente'),
                                  const SizedBox(height: 4),
                                  _construirSelectorCliente(),
                                ],
                              ),
                            const SizedBox(height: 12),
                            Expanded(
                              child: Container(
                                decoration: BoxDecoration(
                                  border: Border.all(
                                      color: const Color(0xFFE1E3E8)),
                                  borderRadius: BorderRadius.circular(8),
                                  color: const Color(0xFFFCFCFD),
                                ),
                                child: _carrito.isEmpty
                                    ? const Center(
                                        child: Text(
                                          'El carrito está vacío',
                                          style: TextStyle(
                                            color: Color(0xFF6E7380),
                                          ),
                                        ),
                                      )
                                    : ListView.separated(
                                        itemCount: _carrito.length,
                                        separatorBuilder: (_, __) =>
                                            const Divider(height: 1),
                                        itemBuilder: (context, index) {
                                          final item = _carrito[index];
                                          return ListTile(
                                            dense: true,
                                            title: Text(
                                              '${item.nombre} S/ ${item.subtotal.toStringAsFixed(2)}',
                                            ),
                                            subtitle: Text(
                                              'ALM-02-${item.idProducto.toString().padLeft(4, '0')}',
                                            ),
                                            trailing: Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                IconButton(
                                                  visualDensity:
                                                      VisualDensity.compact,
                                                  onPressed: () {
                                                    setState(() {
                                                      item.cantidad =
                                                          (item.cantidad - 1)
                                                              .clamp(1, 999)
                                                              .toInt();
                                                    });
                                                  },
                                                  icon:
                                                      const Icon(Icons.remove),
                                                ),
                                                Text(item.cantidad.toString()),
                                                IconButton(
                                                  visualDensity:
                                                      VisualDensity.compact,
                                                  onPressed: () {
                                                    setState(() =>
                                                        item.cantidad += 1);
                                                  },
                                                  icon: const Icon(Icons.add),
                                                ),
                                              ],
                                            ),
                                          );
                                        },
                                      ),
                              ),
                            ),
                            const SizedBox(height: 10),
                            _FilaTotal(
                              label: 'Subtotal',
                              valor: 'S/ ${subtotalNeto.toStringAsFixed(2)}',
                            ),
                            const SizedBox(height: 6),
                            _FilaTotal(
                              label: 'IVA (21.00%)',
                              valor: 'S/ ${iva.toStringAsFixed(2)}',
                            ),
                            const SizedBox(height: 6),
                            _FilaTotal(
                              label: 'TOTAL',
                              valor: 'S/ ${total.toStringAsFixed(2)}',
                              fuerte: true,
                            ),
                            const SizedBox(height: 10),
                            SizedBox(
                              height: 46,
                              child: FilledButton(
                                onPressed:
                                    (!_posSeleccionado || _procesandoCobro)
                                        ? null
                                        : _cobrar,
                                style: FilledButton.styleFrom(
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  backgroundColor: const Color(0xFF5A6474),
                                ),
                                child: Text(
                                  _procesandoCobro ? 'PROCESANDO...' : 'VENDER',
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
                if (!_posSeleccionado)
                  Positioned.fill(
                    child: Container(
                      color: Colors.white.withValues(alpha: 0.62),
                      alignment: Alignment.center,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFFD8DDE7)),
                        ),
                        child: const Text(
                          'Seleccione un Punto de Venta para comenzar',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CategoriaPos {
  const _CategoriaPos(this.nombre, this.icono);

  final String nombre;
  final IconData icono;
}

class _TabVenta extends StatelessWidget {
  const _TabVenta({
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
          border: const Border(right: BorderSide(color: Color(0xFFE1E3E8))),
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

class _IconoAccionCarrito extends StatelessWidget {
  const _IconoAccionCarrito({
    required this.icono,
    required this.tooltip,
    required this.onTap,
  });

  final IconData icono;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        borderRadius: BorderRadius.circular(6),
        onTap: onTap,
        child: Ink(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: const Color(0xFFF7F8FB),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: const Color(0xFFDDE1E9)),
          ),
          child: Icon(icono, size: 17, color: const Color(0xFF5B6576)),
        ),
      ),
    );
  }
}

class _TeuToggleHeader extends StatelessWidget {
  const _TeuToggleHeader({
    required this.teuOn,
    required this.onCambiar,
  });

  final bool teuOn;
  final ValueChanged<bool> onCambiar;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFC9CED9)),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 8),
            child: Text(
              'TEU',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          _TeuPillButton(
            label: 'On',
            selected: teuOn,
            onTap: () => onCambiar(true),
          ),
          _TeuPillButton(
            label: 'OFF',
            selected: !teuOn,
            onTap: () => onCambiar(false),
          ),
        ],
      ),
    );
  }
}

class _TeuPillButton extends StatelessWidget {
  const _TeuPillButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final bg = switch (label) {
      'On' => const Color(0xFFDFF3E1),
      'OFF' => const Color(0xFFFCE5E5),
      _ => const Color(0xFFE9ECF3),
    };
    final fg = switch (label) {
      'On' => const Color(0xFF2E7D32),
      'OFF' => const Color(0xFFC44545),
      _ => const Color(0xFF2D3440),
    };
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        color: selected ? bg : Colors.transparent,
        child: Text(
          label,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: selected ? fg : const Color(0xFF6F7683),
          ),
        ),
      ),
    );
  }
}

class _FilaTotal extends StatelessWidget {
  const _FilaTotal({
    required this.label,
    required this.valor,
    this.fuerte = false,
  });

  final String label;
  final String valor;
  final bool fuerte;

  @override
  Widget build(BuildContext context) {
    final estilo = TextStyle(
      fontSize: fuerte ? 30 : 18,
      fontWeight: fuerte ? FontWeight.w800 : FontWeight.w600,
      color: fuerte ? const Color(0xFF1F2C44) : const Color(0xFF2D3A52),
    );
    return Row(
      children: [
        Text(
          label,
          style: TextStyle(
            fontWeight: fuerte ? FontWeight.w800 : FontWeight.w500,
            fontSize: fuerte ? 18 : 14,
          ),
        ),
        const Spacer(),
        Text(valor, style: estilo),
      ],
    );
  }
}

class _IntentFocusBusqueda extends Intent {
  const _IntentFocusBusqueda();
}

class _IntentCobrar extends Intent {
  const _IntentCobrar();
}

class _IntentCancelar extends Intent {
  const _IntentCancelar();
}

extension FirstOrNullExt<T> on Iterable<T> {
  T? get firstOrNull {
    final it = iterator;
    if (!it.moveNext()) return null;
    return it.current;
  }
}
