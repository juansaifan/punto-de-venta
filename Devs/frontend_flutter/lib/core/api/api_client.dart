import 'dart:math';

/// Cliente API para el frontend POS.
///
/// Nota: en este agente el frontend debe funcionar sin backend.
/// Por eso, este cliente opera en modo mock (en memoria) por defecto.
class ClienteApi {
  ClienteApi();

  /// Cache del catálogo (para búsquedas rápidas).
  List<Map<String, dynamic>>? _cacheProductos;

  // ---- Mock storage ----
  static final List<Map<String, dynamic>> _productos = [
    {
      'id': 1,
      'sku': 'FDS-500-SPAG',
      'nombre': 'Fideos Spaghetti Verizzia 500g',
      'codigo_barra': 'FDS-500-SPAG-BAR',
      'precio_venta': 3630.00,
      'activo': true,
      'stockPorUbicacion': {'GONDOLA': 18, 'DEPOSITO': 80},
      'stock_minimo': 10,
    },
    {
      'id': 2,
      'sku': 'SLV-TOM-200',
      'nombre': 'Salsa Tomate Tradicional',
      'codigo_barra': 'SLV-TOM-200-BAR',
      'precio_venta': 1200.00,
      'activo': true,
      'stockPorUbicacion': {'GONDOLA': 6, 'DEPOSITO': 35},
      'stock_minimo': 8,
    },
    {
      'id': 3,
      'sku': 'ACE-OLV-1L',
      'nombre': 'Aceite de Oliva 1L',
      'codigo_barra': 'ACE-OLV-1L-BAR',
      'precio_venta': 9200.00,
      'activo': true,
      'stockPorUbicacion': {'GONDOLA': 3, 'DEPOSITO': 22},
      'stock_minimo': 6,
    },
    {
      'id': 4,
      'sku': 'YRB-MAT-500',
      'nombre': 'Yerba Mate 500g',
      'codigo_barra': 'YRB-MAT-500-BAR',
      'precio_venta': 5600.00,
      'activo': true,
      'stockPorUbicacion': {'GONDOLA': 14, 'DEPOSITO': 60},
      'stock_minimo': 10,
    },
    {
      'id': 5,
      'sku': 'AZC-1KG',
      'nombre': 'Azúcar 1kg',
      'codigo_barra': 'AZC-1KG-BAR',
      'precio_venta': 2200.00,
      'activo': true,
      'stockPorUbicacion': {'GONDOLA': 2, 'DEPOSITO': 18},
      'stock_minimo': 5,
    },
  ];

  static int _nextProductoId() => (_productos.map((e) => e['id'] as int).fold(0, max) + 1);

  Future<void> cargarCatalogo() async {
    // En mock: simplemente carga el cache desde _productos.
    if (_cacheProductos != null) return;
    _cacheProductos = _productos
        .map((p) => {
              'id': p['id'],
              'sku': p['sku'],
              'nombre': p['nombre'],
              'codigo_barra': p['codigo_barra'],
              'precio_venta': p['precio_venta'],
              'activo': p['activo'],
            })
        .toList(growable: false);
  }

  void invalidarCacheProductos() {
    _cacheProductos = null;
  }

  Future<List<Map<String, dynamic>>> listarProductos({String? busqueda}) async {
    await cargarCatalogo();
    final cache = _cacheProductos ?? [];
    final q = busqueda?.trim().toLowerCase() ?? '';
    if (q.isEmpty) return List.from(cache);

    return cache
        .where((p) {
          final nombre = (p['nombre'] as String? ?? '').toLowerCase();
          final sku = (p['sku'] as String? ?? '').toLowerCase();
          final codigo = (p['codigo_barra'] as String? ?? '').toLowerCase();
          return nombre.contains(q) || sku.contains(q) || codigo.contains(q);
        })
        .map((p) => Map<String, dynamic>.from(p))
        .toList();
  }

  Future<Map<String, dynamic>?> buscarProductoPorCodigo(String codigo) async {
    await cargarCatalogo();
    final c = codigo.trim();
    if (c.isEmpty) return null;

    final cache = _cacheProductos ?? [];
    try {
      return cache.firstWhere((p) {
        final codigoBarra = (p['codigo_barra'] as String? ?? '').trim();
        final sku = (p['sku'] as String? ?? '').trim();
        return codigoBarra == c || sku == c;
      });
    } catch (_) {
      return null;
    }
  }

  Future<double> obtenerStockDisponibleProducto(int productoId) async {
    await cargarCatalogo();
    final prod = _productos.firstWhere((p) => (p['id'] as int) == productoId);
    final stockPorUbicacion = Map<String, dynamic>.from(prod['stockPorUbicacion'] as Map);
    final actual = (stockPorUbicacion['GONDOLA'] as num?)?.toDouble() ?? 0;
    return actual;
  }

  Future<Map<String, dynamic>> crearVenta({
    required List<Map<String, dynamic>> items,
    double descuento = 0,
    String metodoPago = 'EFECTIVO',
  }) async {
    // Para esta iteración, ventas_screen siempre usa EFECTIVO.
    if (items.isEmpty) {
      throw Exception('La venta debe tener al menos un ítem.');
    }

    // Recalcular total con lo que recibe la pantalla.
    double subtotal = 0;
    for (final it in items) {
      final cantidad = (it['cantidad'] as num?)?.toDouble() ?? 0;
      final precio = (it['precio_unitario'] as num?)?.toDouble() ?? 0;
      subtotal += cantidad * precio;
    }
    final total = (subtotal - descuento).clamp(0, double.infinity);

    // Side-effect: descontar stock en GONDOLA por simplicidad.
    for (final it in items) {
      final productoId = it['producto_id'] as int;
      final cantidad = (it['cantidad'] as num?)?.toDouble() ?? 0;
      final prod = _productos.firstWhere((p) => (p['id'] as int) == productoId);
      final stockPorUbicacion = Map<String, dynamic>.from(prod['stockPorUbicacion'] as Map);
      final actual = (stockPorUbicacion['GONDOLA'] as num?)?.toDouble() ?? 0;
      if (actual < cantidad) {
        throw Exception('stock insuficiente');
      }
      stockPorUbicacion['GONDOLA'] = actual - cantidad;
      prod['stockPorUbicacion'] = stockPorUbicacion;
    }

    final ventaId = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    return {
      'venta_id': ventaId,
      'total': total,
      'metodo_pago': metodoPago,
    };
  }

  Future<Map<String, dynamic>> consultarStock(
    int productoId, {
    String ubicacion = 'GONDOLA',
  }) async {
    final prod = _productos.firstWhere((p) => (p['id'] as int) == productoId);
    final stockPorUbicacion = prod['stockPorUbicacion'] as Map<String, dynamic>;
    final cantidad = (stockPorUbicacion[ubicacion] as num?)?.toDouble() ?? 0;
    return {
      'producto_id': productoId,
      'ubicacion': ubicacion,
      'cantidad': cantidad,
    };
  }

  Future<Map<String, dynamic>> crearProducto({
    required String sku,
    required String nombre,
    required double precioVenta,
    String? codigoBarra,
    String? descripcion,
  }) async {
    // Validación simple de unicidad de SKU.
    final exists = _productos.any((p) => (p['sku'] as String?) == sku);
    if (exists) throw Exception('SKU ya existe');

    final id = _nextProductoId();
    _productos.add({
      'id': id,
      'sku': sku,
      'nombre': nombre,
      'codigo_barra': codigoBarra ?? '',
      'precio_venta': precioVenta,
      'activo': true,
      'descripcion': descripcion ?? '',
      'stockPorUbicacion': {'GONDOLA': 0, 'DEPOSITO': 0},
      'stock_minimo': 5,
    });
    invalidarCacheProductos();
    return {
      'id': id,
      'sku': sku,
      'nombre': nombre,
      'precio_venta': precioVenta,
      'codigo_barra': codigoBarra ?? '',
      'activo': true,
    };
  }

  Future<Map<String, dynamic>> actualizarProducto({
    required int productoId,
    String? nombre,
    double? precioVenta,
    String? codigoBarra,
    String? descripcion,
    bool? activo,
  }) async {
    final prod = _productos.firstWhere((p) => (p['id'] as int) == productoId);

    if (nombre != null) prod['nombre'] = nombre;
    if (precioVenta != null) prod['precio_venta'] = precioVenta;
    if (codigoBarra != null) prod['codigo_barra'] = codigoBarra;
    if (descripcion != null) prod['descripcion'] = descripcion;
    if (activo != null) prod['activo'] = activo;

    invalidarCacheProductos();
    return Map<String, dynamic>.from(prod);
  }

  Future<Map<String, dynamic>> ajustarStock({
    required int productoId,
    required double cantidad,
    String ubicacion = 'GONDOLA',
    String? referencia,
  }) async {
    final prod = _productos.firstWhere((p) => (p['id'] as int) == productoId);
    final stockPorUbicacion = Map<String, dynamic>.from(prod['stockPorUbicacion'] as Map);
    final actual = (stockPorUbicacion[ubicacion] as num?)?.toDouble() ?? 0;
    stockPorUbicacion[ubicacion] = (actual + cantidad).clamp(0, double.infinity);
    prod['stockPorUbicacion'] = stockPorUbicacion;

    return {
      'producto_id': productoId,
      'ubicacion': ubicacion,
      'referencia': referencia,
      'cantidad_ajustada': cantidad,
      'cantidad_nueva': stockPorUbicacion[ubicacion],
    };
  }

  // =========================================================================
  // POS TEU OFF / Caja / Cobros (MOCKS)
  // =========================================================================

  // DTOs para operaciones de Caja/Cobros.
  static final List<ClienteMock> _clientes = [
    ClienteMock(
      clienteId: 0,
      personaId: 0,
      nombreCompleto: 'Consumidor final',
      documento: '',
      limiteCredito: 0,
    ),
    ClienteMock(
      clienteId: 201,
      personaId: 301,
      nombreCompleto: 'Victoria Perez',
      documento: '32911452',
      limiteCredito: 120000,
      activo: true,
    ),
    ClienteMock(
      clienteId: 202,
      personaId: 302,
      nombreCompleto: 'Juan Gomez',
      documento: '30111452',
      limiteCredito: 80000,
      activo: true,
    ),
    ClienteMock(
      clienteId: 203,
      personaId: 303,
      nombreCompleto: 'Maria Rodriguez',
      documento: '27911252',
      limiteCredito: 200000,
      activo: true,
    ),
  ];

  static final Map<int, TicketMock> _tickets = <int, TicketMock>{};
  static final Map<int, double> _creditosFavorCliente = <int, double>{};
  static final List<OperacionComercialLogMock> _operacionesComercialesLog = <OperacionComercialLogMock>[];
  static int _nextTicketId = 10000;

  Future<List<ClienteMock>> listarClientes({String? busqueda}) async {
    final q = busqueda?.trim().toLowerCase() ?? '';
    if (q.isEmpty) return List<ClienteMock>.from(_clientes);
    return _clientes
        .where((c) =>
            c.nombreCompleto.toLowerCase().contains(q) ||
            c.documento.toLowerCase().contains(q))
        .toList();
  }

  ClienteMock _clientePorId(int clienteId) {
    return _clientes.firstWhere(
      (c) => c.clienteId == clienteId,
      orElse: () => _clientes.firstWhere((c) => c.clienteId == 0),
    );
  }

  double _saldoDeCliente(int clienteId) {
    return _tickets.values
        .where((t) => t.clienteId == clienteId && t.estado == TicketEstado.fiada)
        .fold<double>(0, (acc, t) => acc + t.saldoPendiente);
  }

  double _saldoFavorCliente(int clienteId) {
    return _creditosFavorCliente[clienteId] ?? 0.0;
  }

  double _disponibleCliente(int clienteId) {
    final c = _clientePorId(clienteId);
    final saldo = _saldoDeCliente(clienteId);
    return (c.limiteCredito ?? 0) - saldo;
  }

  double _totalDesdeItems(List<Map<String, dynamic>> items, double descuento) {
    double subtotal = 0;
    for (final it in items) {
      final cantidad = (it['cantidad'] as num?)?.toDouble() ?? 0;
      final precio = (it['precio_unitario'] as num?)?.toDouble() ?? 0;
      subtotal += cantidad * precio;
    }
    final total = (subtotal - descuento).clamp(0.0, double.infinity);
    return total.toDouble();
  }

  void _decrementarStockPorItems(List<Map<String, dynamic>> items) {
    for (final it in items) {
      final productoId = it['producto_id'] as int;
      final cantidad = (it['cantidad'] as num?)?.toDouble() ?? 0;
      if (cantidad <= 0) continue;

      final prod = _productos.firstWhere((p) => (p['id'] as int) == productoId);
      final stockPorUbicacion = Map<String, dynamic>.from(prod['stockPorUbicacion'] as Map);
      final actual = (stockPorUbicacion['GONDOLA'] as num?)?.toDouble() ?? 0;
      if (actual < cantidad) {
        throw Exception('stock insuficiente');
      }
      stockPorUbicacion['GONDOLA'] = actual - cantidad;
      prod['stockPorUbicacion'] = stockPorUbicacion;
    }
  }

  Future<int> crearTicketTeuOff({
    required List<Map<String, dynamic>> items,
    required double descuento,
    required int clienteId,
  }) async {
    if (items.isEmpty) throw Exception('La venta debe tener al menos un ítem.');
    _decrementarStockPorItems(items);

    final total = _totalDesdeItems(items, descuento);
    final ventaId = _nextTicketId++;
    final cliente = _clientePorId(clienteId);
    final fecha = DateTime.now();

    final ticketItems = items.map((it) {
      final productoId = it['producto_id'] as int;
      final cantidad = (it['cantidad'] as num?)?.toDouble() ?? 0;
      final precio = (it['precio_unitario'] as num?)?.toDouble() ?? 0;
      final prod = _productos.firstWhere((p) => (p['id'] as int) == productoId);
      return TicketItemMock(
        productoId: productoId,
        nombre: prod['nombre'] as String? ?? 'Producto',
        cantidad: cantidad,
        precioUnitario: precio,
        subtotal: precio * cantidad,
      );
    }).toList();

    _tickets[ventaId] = TicketMock(
      ticketId: ventaId,
      clienteId: clienteId,
      clienteNombre: cliente.nombreCompleto,
      documento: cliente.documento,
      estado: TicketEstado.pendiente,
      fecha: fecha,
      items: ticketItems,
      total: total,
      saldoPendiente: total,
    );

    return ventaId;
  }

  Future<int> crearVentaTeuOn({
    required List<Map<String, dynamic>> items,
    required double descuento,
    required int clienteId,
    required MetodoPago metodoPago,
  }) async {
    if (items.isEmpty) throw Exception('La venta debe tener al menos un ítem.');
    _decrementarStockPorItems(items);

    final total = _totalDesdeItems(items, descuento);
    final ventaId = _nextTicketId++;
    final cliente = _clientePorId(clienteId);
    final fecha = DateTime.now();

    if (metodoPago == MetodoPago.cuentaCorriente) {
      if (cliente.clienteId == 0) {
        throw Exception('Para cuenta corriente, seleccioná un cliente.');
      }
      final disponible = _disponibleCliente(clienteId);
      if (total > disponible) {
        throw Exception('límite de crédito excedido');
      }
    }

    final ticketItems = items.map((it) {
      final productoId = it['producto_id'] as int;
      final cantidad = (it['cantidad'] as num?)?.toDouble() ?? 0;
      final precio = (it['precio_unitario'] as num?)?.toDouble() ?? 0;
      final prod = _productos.firstWhere((p) => (p['id'] as int) == productoId);
      return TicketItemMock(
        productoId: productoId,
        nombre: prod['nombre'] as String? ?? 'Producto',
        cantidad: cantidad,
        precioUnitario: precio,
        subtotal: precio * cantidad,
      );
    }).toList();

    final estado = metodoPago == MetodoPago.cuentaCorriente ? TicketEstado.fiada : TicketEstado.pagada;
    _tickets[ventaId] = TicketMock(
      ticketId: ventaId,
      clienteId: clienteId,
      clienteNombre: cliente.nombreCompleto,
      documento: cliente.documento,
      estado: estado,
      fecha: fecha,
      items: ticketItems,
      total: total,
      saldoPendiente: estado == TicketEstado.fiada ? total : 0,
    );

    return ventaId;
  }

  Future<List<TicketMock>> listarTicketsPendientesVenta() async {
    return _tickets.values
        .where((t) => t.estado == TicketEstado.pendiente && t.saldoPendiente > 0)
        .toList()
      ..sort((a, b) => a.fecha.compareTo(b.fecha));
  }

  Future<List<TicketMock>> listarTicketsSuspendidosVenta() async {
    return _tickets.values
        .where((t) => t.estado == TicketEstado.suspendida && t.saldoPendiente > 0)
        .toList()
      ..sort((a, b) => a.fecha.compareTo(b.fecha));
  }

  Future<void> suspenderTicketVenta({required int ticketId}) async {
    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado != TicketEstado.pendiente) throw Exception('ticket no está pendiente');
    ticket.estado = TicketEstado.suspendida;
  }

  Future<void> reanudarTicketVenta({required int ticketId}) async {
    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado != TicketEstado.suspendida) throw Exception('ticket no está suspendido');
    ticket.estado = TicketEstado.pendiente;
  }

  Future<TicketMock?> obtenerTicket(int ticketId) async {
    return _tickets[ticketId];
  }

  Future<void> pagarTicketVenta({
    required int ticketId,
    required MetodoPago metodoPago,
    double? valorRecibido,
  }) async {
    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado != TicketEstado.pendiente) throw Exception('ticket no pendiente');

    if (metodoPago == MetodoPago.cuentaCorriente) {
      final clienteId = ticket.clienteId;
      final disponible = _disponibleCliente(clienteId);
      if (clienteId == 0 || totalExcede(total: ticket.total, disponible: disponible)) {
        throw Exception('límite de crédito excedido');
      }
      ticket.estado = TicketEstado.fiada;
      ticket.saldoPendiente = ticket.total;
      return;
    }

    // Pagos parciales (si valorRecibido < total) convierten el saldo remanente en FIADA,
    // para que el resto pueda cobrarse luego en "Cobros de deuda".
    final recibido = valorRecibido ?? ticket.total;
    if (recibido >= ticket.total) {
      ticket.estado = TicketEstado.pagada;
      ticket.saldoPendiente = 0;
      return;
    }
    if (recibido <= 0) {
      throw Exception('importe recibido inválido');
    }
    ticket.estado = TicketEstado.fiada;
    ticket.saldoPendiente = (ticket.total - recibido).clamp(0.0, ticket.total);
  }

  Future<void> pagarTicketVentaCombinado({
    required int ticketId,
    required List<PagoLineaMock> pagos,
  }) async {
    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado != TicketEstado.pendiente) throw Exception('ticket no pendiente');

    if (pagos.isEmpty) throw Exception('debe incluir al menos un método de pago');
    final totalPendiente = ticket.saldoPendiente;

    final inmediato = pagos
        .where((p) => p.metodoPago != MetodoPago.cuentaCorriente)
        .fold<double>(0.0, (acc, p) => acc + p.monto);

    final cuentaCorrienteMonto = pagos
        .where((p) => p.metodoPago == MetodoPago.cuentaCorriente)
        .fold<double>(0.0, (acc, p) => acc + p.monto);

    if (inmediato - totalPendiente > 0.0001) {
      throw Exception('el pago inmediato excede el total');
    }

    if (inmediato >= totalPendiente) {
      if (cuentaCorrienteMonto > 0.0001) {
        throw Exception('Cuenta corriente debe ser 0 si el pago inmediato cubre el total');
      }
      ticket.estado = TicketEstado.pagada;
      ticket.saldoPendiente = 0;
      return;
    }

    final deuda = (totalPendiente - inmediato).clamp(0.0, totalPendiente);
    if (deuda <= 0.0001) {
      if (cuentaCorrienteMonto > 0.0001) {
        throw Exception('Cuenta corriente debe ser 0 si el saldo resultante es 0');
      }
      ticket.estado = TicketEstado.pagada;
      ticket.saldoPendiente = 0;
      return;
    }

    if (cuentaCorrienteMonto > 0.0001) {
      // En este mock, `Cuenta corriente` representa el monto que queda como FIADA.
      if ((deuda - cuentaCorrienteMonto).abs() > 0.0001) {
        throw Exception(
          'Cuenta corriente no coincide con el saldo a FIADA. Esperado: ${deuda.toStringAsFixed(2)}',
        );
      }
    }

    final clienteId = ticket.clienteId;
    if (clienteId == 0) {
      throw Exception('Para generar FIADA debe seleccionar un cliente.');
    }

    final disponible = _disponibleCliente(clienteId);
    if (totalExcede(total: deuda, disponible: disponible)) {
      throw Exception('límite de crédito excedido');
    }

    ticket.estado = TicketEstado.fiada;
    ticket.saldoPendiente = deuda;
  }

  bool totalExcede({required double total, required double disponible}) => total > disponible;

  void _revertirStockPorTicket(TicketMock ticket) {
    for (final it in ticket.items) {
      final prod = _productos.firstWhere((p) => (p['id'] as int) == it.productoId);
      final stockPorUbicacion = Map<String, dynamic>.from(prod['stockPorUbicacion'] as Map);
      final actual = (stockPorUbicacion['GONDOLA'] as num?)?.toDouble() ?? 0;
      stockPorUbicacion['GONDOLA'] = actual + it.cantidad;
      prod['stockPorUbicacion'] = stockPorUbicacion;
    }
  }

  Future<void> anularTicketOperacion({required int ticketId}) async {
    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado == TicketEstado.anulada) return;

    // En este mock revertimos stock y anulamos saldo.
    if (ticket.items.isNotEmpty) {
      _revertirStockPorTicket(ticket);
    }
    final importe = ticket.saldoPendiente;
    ticket.estado = TicketEstado.anulada;
    ticket.saldoPendiente = 0;

    _operacionesComercialesLog.insert(
      0,
      OperacionComercialLogMock(
        operacionId: 'ANU-${DateTime.now().microsecondsSinceEpoch}',
        tipo: 'Anulación',
        ticketId: ticketId,
        clienteNombre: ticket.clienteNombre,
        importe: importe,
        reintegroMetodo: 'n/a',
        motivo: 'Anulación operativa',
        detalle: 'Ticket anulado por operación comercial.',
        fecha: DateTime.now(),
      ),
    );
  }

  Future<void> registrarNotaCreditoCuentaCorriente({
    required int ticketId,
    required double importe,
  }) async {
    if (importe <= 0) throw Exception('importe inválido');
    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado != TicketEstado.fiada) throw Exception('nota de crédito aplica solo a FIADA en mock');

    final aplicar = importe.clamp(0, ticket.saldoPendiente);
    ticket.saldoPendiente -= aplicar;
    if (ticket.saldoPendiente <= 0.0001) {
      ticket.saldoPendiente = 0;
      ticket.estado = TicketEstado.pagada;
    }

    // Mantener coherencia mínima con el total.
    ticket.total = max(0, ticket.total - aplicar);

    _operacionesComercialesLog.insert(
      0,
      OperacionComercialLogMock(
        operacionId: 'NCR-${DateTime.now().microsecondsSinceEpoch}',
        tipo: 'Nota de crédito',
        ticketId: ticketId,
        clienteNombre: ticket.clienteNombre,
        importe: aplicar.toDouble(),
        reintegroMetodo: 'credito_cc',
        motivo: 'Ajuste de crédito',
        detalle: 'Aplicado sobre deuda FIADA por nota de crédito.',
        fecha: DateTime.now(),
      ),
    );
  }

  Future<void> registrarDevolucionOperacion({
    required int ticketId,
    required int productoId,
    required double cantidad,
    required String reintegroMetodo,
    String? motivo,
  }) async {
    if (cantidad <= 0) throw Exception('cantidad inválida');
    final motivoNormalizado = (motivo ?? '').trim();
    if (motivoNormalizado.length < 3) {
      throw Exception('motivo inválido (mínimo 3 caracteres)');
    }
    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado == TicketEstado.anulada) throw Exception('ticket anulada');

    final oldEstado = ticket.estado;
    final oldTotal = ticket.total;
    final oldSaldoPendiente = ticket.saldoPendiente;

    // Reingreso de stock: devolvemos cantidad del producto.
    // En mock, asumimos devoluciones al depósito/ubicación principal GONDOLA.
    final devStock = cantidad;
    final prodDev = _productos.firstWhere((p) => (p['id'] as int) == productoId);
    final stockPorUbicacion = Map<String, dynamic>.from(prodDev['stockPorUbicacion'] as Map);
    final actual = (stockPorUbicacion['GONDOLA'] as num?)?.toDouble() ?? 0;
    stockPorUbicacion['GONDOLA'] = actual + devStock;
    prodDev['stockPorUbicacion'] = stockPorUbicacion;

    final idx = ticket.items.indexWhere((it) => it.productoId == productoId);
    if (idx < 0) throw Exception('producto no está en el ticket');

    final item = ticket.items[idx];
    final importeDevuelto = item.precioUnitario * cantidad;
    if (cantidad - item.cantidad > 0.0001) {
      throw Exception('cantidad de devolución supera cantidad en el ticket');
    }
    final nuevaCantidad =
        (item.cantidad - cantidad).clamp(0.0, double.infinity).toDouble();
    if (nuevaCantidad <= 0.0001) {
      ticket.items.removeAt(idx);
    } else {
      ticket.items[idx] = TicketItemMock(
        productoId: item.productoId,
        nombre: item.nombre,
        cantidad: nuevaCantidad,
        precioUnitario: item.precioUnitario,
        subtotal: nuevaCantidad * item.precioUnitario,
      );
    }

    _recalcularTicketTrasOperacion(
      ticket: ticket,
      oldTotal: oldTotal,
      oldSaldoPendiente: oldSaldoPendiente,
    );

    // Mock financiero básico por reintegro:
    // - efectivo / medio original: no persistimos "movimientos", solo se refleja en total/saldo.
    // - credito_cc: registramos saldo a favor del cliente cuando corresponde.
    if (reintegroMetodo == 'credito_cc') {
      final clienteId = ticket.clienteId;
      if (clienteId == 0) {
        throw Exception('devolución con crédito requiere cliente asociado');
      }

      double creditoFavor = 0.0;
      if (oldEstado == TicketEstado.pagada) {
        creditoFavor = importeDevuelto;
      } else if (oldEstado == TicketEstado.fiada) {
        // Primero compensa deuda previa; el excedente se registra como saldo a favor.
        final deudaAntes = oldSaldoPendiente;
        creditoFavor = max(0.0, importeDevuelto - deudaAntes);
      }

      if (creditoFavor > 0.0001) {
        _creditosFavorCliente[clienteId] = _saldoFavorCliente(clienteId) + creditoFavor;
      }
    }

    _operacionesComercialesLog.insert(
      0,
      OperacionComercialLogMock(
        operacionId: 'DEV-${DateTime.now().microsecondsSinceEpoch}',
        tipo: 'Devolución',
        ticketId: ticketId,
        clienteNombre: ticket.clienteNombre,
        importe: importeDevuelto,
        reintegroMetodo: reintegroMetodo,
        motivo: motivoNormalizado,
        detalle: 'Producto #$productoId · Cantidad: ${cantidad.toStringAsFixed(2)}',
        fecha: DateTime.now(),
      ),
    );
  }

  Future<void> registrarCambioOperacion({
    required int ticketId,
    required int productoDevueltoId,
    required double cantidadDevuelta,
    required int productoNuevoId,
    required double cantidadNueva,
  }) async {
    if (cantidadDevuelta <= 0 || cantidadNueva <= 0) throw Exception('cantidades inválidas');

    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado == TicketEstado.anulada) throw Exception('ticket anulada');

    final oldTotal = ticket.total;
    final oldSaldoPendiente = ticket.saldoPendiente;

    // Devolución parcial del producto viejo: reingresa stock.
    final prodViejo = _productos.firstWhere((p) => (p['id'] as int) == productoDevueltoId);
    final stockViejo = Map<String, dynamic>.from(prodViejo['stockPorUbicacion'] as Map);
    final actualViejo = (stockViejo['GONDOLA'] as num?)?.toDouble() ?? 0;
    stockViejo['GONDOLA'] = actualViejo + cantidadDevuelta;
    prodViejo['stockPorUbicacion'] = stockViejo;

    // Consumo del producto nuevo: descuenta stock.
    final prodNuevo = _productos.firstWhere((p) => (p['id'] as int) == productoNuevoId);
    final stockNuevo = Map<String, dynamic>.from(prodNuevo['stockPorUbicacion'] as Map);
    final actualNuevo = (stockNuevo['GONDOLA'] as num?)?.toDouble() ?? 0;
    if (actualNuevo < cantidadNueva) throw Exception('stock insuficiente para cambio');
    stockNuevo['GONDOLA'] = actualNuevo - cantidadNueva;
    prodNuevo['stockPorUbicacion'] = stockNuevo;

    // Actualizar items del ticket (viejo -> se reduce o elimina).
    final idxViejo = ticket.items.indexWhere((it) => it.productoId == productoDevueltoId);
    if (idxViejo < 0) throw Exception('producto devuelto no está en el ticket');
    final itemViejo = ticket.items[idxViejo];
    if (cantidadDevuelta - itemViejo.cantidad > 0.0001) {
      throw Exception('cantidad devuelta supera cantidad en el ticket');
    }
    final nuevaCantidadViejo = (itemViejo.cantidad - cantidadDevuelta)
        .clamp(0.0, double.infinity)
        .toDouble();
    if (nuevaCantidadViejo <= 0.0001) {
      ticket.items.removeAt(idxViejo);
    } else {
      ticket.items[idxViejo] = TicketItemMock(
        productoId: itemViejo.productoId,
        nombre: itemViejo.nombre,
        cantidad: nuevaCantidadViejo,
        precioUnitario: itemViejo.precioUnitario,
        subtotal: nuevaCantidadViejo * itemViejo.precioUnitario,
      );
    }

    // Agregar/ajustar item del producto nuevo.
    final precioNuevo = (prodNuevo['precio_venta'] as num?)?.toDouble() ?? 0;
    final nombreNuevo = prodNuevo['nombre'] as String? ?? 'Producto';
    final idxNuevo = ticket.items.indexWhere((it) => it.productoId == productoNuevoId);
    if (idxNuevo < 0) {
      ticket.items.add(
        TicketItemMock(
          productoId: productoNuevoId,
          nombre: nombreNuevo,
          cantidad: cantidadNueva,
          precioUnitario: precioNuevo,
          subtotal: precioNuevo * cantidadNueva,
        ),
      );
    } else {
      final itemAct = ticket.items[idxNuevo];
      final cantidadSumada = itemAct.cantidad + cantidadNueva;
      ticket.items[idxNuevo] = TicketItemMock(
        productoId: itemAct.productoId,
        nombre: itemAct.nombre,
        cantidad: cantidadSumada,
        precioUnitario: itemAct.precioUnitario,
        subtotal: itemAct.precioUnitario * cantidadSumada,
      );
    }

    _recalcularTicketTrasOperacion(
      ticket: ticket,
      oldTotal: oldTotal,
      oldSaldoPendiente: oldSaldoPendiente,
    );

    final diferencia = ticket.total - oldTotal;
    _operacionesComercialesLog.insert(
      0,
      OperacionComercialLogMock(
        operacionId: 'CAM-${DateTime.now().microsecondsSinceEpoch}',
        tipo: 'Cambio',
        ticketId: ticketId,
        clienteNombre: ticket.clienteNombre,
        importe: diferencia.abs(),
        reintegroMetodo: diferencia >= 0 ? 'cliente_paga_diferencia' : 'comercio_devuelve_diferencia',
        motivo: 'Cambio de producto',
        detalle:
            'Devuelto #$productoDevueltoId x${cantidadDevuelta.toStringAsFixed(2)} -> Nuevo #$productoNuevoId x${cantidadNueva.toStringAsFixed(2)}',
        fecha: DateTime.now(),
      ),
    );
  }

  Future<void> registrarNotaDebitoOperacion({
    required int ticketId,
    required double importe,
  }) async {
    if (importe <= 0) throw Exception('importe inválido');
    final ticket = _tickets[ticketId];
    if (ticket == null) throw Exception('ticket no encontrado');
    if (ticket.estado == TicketEstado.anulada) throw Exception('ticket anulada');

    // Nota de débito: incrementa total y saldo pendiente como deuda.
    ticket.total += importe;
    if (ticket.estado == TicketEstado.pagada) {
      // Si ya estaba pagada, en mock la convertimos a deuda parcial.
      ticket.estado = TicketEstado.fiada;
      ticket.saldoPendiente = importe;
    } else {
      ticket.saldoPendiente += importe;
      if (ticket.estado == TicketEstado.pagada) {
        ticket.estado = TicketEstado.fiada;
      }
    }

    _operacionesComercialesLog.insert(
      0,
      OperacionComercialLogMock(
        operacionId: 'NDB-${DateTime.now().microsecondsSinceEpoch}',
        tipo: 'Nota de débito',
        ticketId: ticketId,
        clienteNombre: ticket.clienteNombre,
        importe: importe,
        reintegroMetodo: 'n/a',
        motivo: 'Recargo / ajuste',
        detalle: 'Incremento de importe por nota de débito.',
        fecha: DateTime.now(),
      ),
    );
  }

  void _recalcularTicketTrasOperacion({
    required TicketMock ticket,
    double? oldTotal,
    double? oldSaldoPendiente,
  }) {
    ticket.total = ticket.items.fold<double>(0, (acc, it) => acc + it.subtotal);
    if (ticket.estado == TicketEstado.anulada) {
      ticket.saldoPendiente = 0;
      return;
    }
    if (ticket.estado == TicketEstado.pagada) {
      ticket.saldoPendiente = 0;
      return;
    }
    if (ticket.estado == TicketEstado.fiada) {
      // En FIADA, mantenemos constante el monto ya pagado:
      // pagado = total viejo - saldo viejo.
      // saldo nuevo = total nuevo - pagado.
      final totalViejo = oldTotal ?? ticket.total;
      final saldoViejo = oldSaldoPendiente ?? ticket.saldoPendiente;
      final pagado = totalViejo - saldoViejo;
      ticket.saldoPendiente = (ticket.total - pagado).clamp(0.0, ticket.total).toDouble();
    } else {
      ticket.saldoPendiente = ticket.total;
    }
    if (ticket.saldoPendiente <= 0.0001) {
      ticket.saldoPendiente = 0;
      ticket.estado = TicketEstado.pagada;
    }
  }

  Future<List<ClienteDeudaSummary>> listarClientesConDeuda() async {
    final idsConSaldo = _tickets.values
        .where((t) => t.estado == TicketEstado.fiada && t.saldoPendiente > 0)
        .map((t) => t.clienteId)
        .toSet();

    final list = idsConSaldo.map((clienteId) {
      final cliente = _clientePorId(clienteId);
      final saldo = _saldoDeCliente(clienteId);
      final saldoFavor = _saldoFavorCliente(clienteId);
      final limite = cliente.limiteCredito ?? 0;
      final vencimientosHoy = 0; // simplificado en mock
      return ClienteDeudaSummary(
        clienteId: cliente.clienteId,
        personaId: cliente.personaId,
        clienteNombre: cliente.nombreCompleto,
        documento: cliente.documento,
        ticketsPendientes: _tickets.values
            .where((t) => t.estado == TicketEstado.fiada && t.clienteId == clienteId && t.saldoPendiente > 0)
            .length,
        deudaTotal: saldo,
        saldoFavor: saldoFavor,
        limiteCredito: limite,
        disponible: limite - saldo,
        vencimientoHoy: vencimientosHoy,
      );
    }).toList();

    list.sort((a, b) => b.deudaTotal.compareTo(a.deudaTotal));
    return list;
  }

  Future<List<TicketMock>> listarTicketsPendientesCliente(int clienteId) async {
    final list = _tickets.values
        .where((t) => t.estado == TicketEstado.fiada && t.clienteId == clienteId && t.saldoPendiente > 0)
        .toList()
      ..sort((a, b) => a.fecha.compareTo(b.fecha));
    return list;
  }

  /// Listado unificado para el submódulo de Operaciones Comerciales.
  /// Filtra por: ticketId (si es numérico), nombre/documento del cliente o nombre de producto.
  Future<List<TicketMock>> listarTicketsOperaciones({String? busqueda}) async {
    final q = busqueda?.trim().toLowerCase() ?? '';
    final base = _tickets.values.where((t) => t.estado != TicketEstado.anulada).toList();
    base.sort((a, b) => b.fecha.compareTo(a.fecha));

    if (q.isEmpty) return base;

    final ticketId = int.tryParse(q);
    return base.where((t) {
      final byTicket = ticketId != null && t.ticketId == ticketId;
      final byCliente = t.clienteNombre.toLowerCase().contains(q) || t.documento.toLowerCase().contains(q);
      final byProducto = t.items.any((it) => it.nombre.toLowerCase().contains(q));
      return byTicket || byCliente || byProducto;
    }).toList();
  }

  Future<void> aplicarPagoCuentaCorriente({
    required int clienteId,
    required MetodoPago metodoPago,
    required double monto,
  }) async {
    if (monto <= 0) throw Exception('Monto inválido');
    final tickets = await listarTicketsPendientesCliente(clienteId);
    var restante = monto;
    for (final t in tickets) {
      if (restante <= 0) break;
      final aplicar = min(restante, t.saldoPendiente);
      t.saldoPendiente -= aplicar;
      if (t.saldoPendiente <= 0.0001) {
        t.saldoPendiente = 0;
        t.estado = TicketEstado.pagada;
      }
      restante -= aplicar;
    }
  }

  Future<void> aplicarCreditoFavorCuentaCorriente({
    required int clienteId,
    double? monto,
  }) async {
    final saldoFavorActual = _saldoFavorCliente(clienteId);
    if (saldoFavorActual <= 0.0001) throw Exception('cliente sin saldo a favor');

    final aplicarTotal = (monto ?? saldoFavorActual).clamp(0.0, saldoFavorActual).toDouble();
    if (aplicarTotal <= 0.0001) throw Exception('monto inválido');

    final tickets = await listarTicketsPendientesCliente(clienteId);
    var restante = aplicarTotal;
    for (final t in tickets) {
      if (restante <= 0) break;
      final aplicar = min(restante, t.saldoPendiente);
      t.saldoPendiente -= aplicar;
      if (t.saldoPendiente <= 0.0001) {
        t.saldoPendiente = 0;
        t.estado = TicketEstado.pagada;
      }
      restante -= aplicar;
    }

    final efectivamenteAplicado = aplicarTotal - restante;
    final nuevoSaldoFavor = (saldoFavorActual - efectivamenteAplicado).clamp(0.0, double.infinity).toDouble();
    _creditosFavorCliente[clienteId] = nuevoSaldoFavor;
  }

  Future<List<OperacionComercialLogMock>> listarOperacionesComercialesRecientes({
    int? ticketId,
    String? tipo,
    int limit = 10,
  }) async {
    Iterable<OperacionComercialLogMock> filtradas = _operacionesComercialesLog;
    if (ticketId != null) {
      filtradas = filtradas.where((o) => o.ticketId == ticketId);
    }
    if (tipo != null && tipo.isNotEmpty && tipo != 'Todas') {
      filtradas = filtradas.where((o) => o.tipo == tipo);
    }
    return filtradas.take(limit).toList();
  }
}

enum TicketEstado { pendiente, suspendida, pagada, fiada, anulada }

enum MetodoPago { efectivo, tarjetaCredito, transferencia, cuentaCorriente }

class PagoLineaMock {
  PagoLineaMock({
    required this.metodoPago,
    required this.monto,
  });

  final MetodoPago metodoPago;
  final double monto;
}

class ClienteMock {
  ClienteMock({
    required this.clienteId,
    required this.personaId,
    required this.nombreCompleto,
    required this.documento,
    required this.limiteCredito,
    this.activo = true,
  });

  final int clienteId;
  final int personaId;
  final String nombreCompleto;
  final String documento;
  final double limiteCredito;
  final bool activo;
}

class ClienteDeudaSummary {
  ClienteDeudaSummary({
    required this.clienteId,
    required this.personaId,
    required this.clienteNombre,
    required this.documento,
    required this.ticketsPendientes,
    required this.deudaTotal,
    required this.saldoFavor,
    required this.limiteCredito,
    required this.disponible,
    required this.vencimientoHoy,
  });

  final int clienteId;
  final int personaId;
  final String clienteNombre;
  final String documento;
  final int ticketsPendientes;
  final double deudaTotal;
  final double saldoFavor;
  final double limiteCredito;
  final double disponible;
  final int vencimientoHoy;
}

class TicketItemMock {
  TicketItemMock({
    required this.productoId,
    required this.nombre,
    required this.cantidad,
    required this.precioUnitario,
    required this.subtotal,
  });

  final int productoId;
  final String nombre;
  final double cantidad;
  final double precioUnitario;
  final double subtotal;
}

class TicketMock {
  TicketMock({
    required this.ticketId,
    required this.clienteId,
    required this.clienteNombre,
    required this.documento,
    required this.estado,
    required this.fecha,
    required this.items,
    required this.total,
    required this.saldoPendiente,
    this.vendedorNombre = '',
    this.cajeroNombre = '',
  });

  final int ticketId;
  final int clienteId;
  final String clienteNombre;
  final String documento;
  TicketEstado estado;
  final DateTime fecha;
  final List<TicketItemMock> items;
  double total;
  double saldoPendiente;
  /// Nombre del vendedor que originó el ticket (mock / integración futura).
  final String vendedorNombre;
  /// Cajero asignado o caja de cobro (mock / integración futura).
  final String cajeroNombre;
}

class OperacionComercialLogMock {
  OperacionComercialLogMock({
    required this.operacionId,
    required this.tipo,
    required this.ticketId,
    required this.clienteNombre,
    required this.importe,
    required this.reintegroMetodo,
    required this.motivo,
    required this.detalle,
    required this.fecha,
  });

  final String operacionId;
  final String tipo;
  final int ticketId;
  final String clienteNombre;
  final double importe;
  final String reintegroMetodo;
  final String motivo;
  final String detalle;
  final DateTime fecha;
}


