import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import '../../widgets/selector_cliente_como_ventas.dart';
import 'models/pesable_dtos.dart';

/// Submódulo Pesables — panel derecho: calculadora (peso ↔ precio) + lista para
/// etiquetas. Datos mock; sin backend.
class PantallaPesables extends StatefulWidget {
  const PantallaPesables({super.key});

  @override
  State<PantallaPesables> createState() => _PantallaPesablesState();
}

class _PantallaPesablesState extends State<PantallaPesables> {
  final _controlBusqueda = TextEditingController();
  final _focusBusqueda = FocusNode();
  final _pesoCtrl = TextEditingController(text: '1.000');
  final _precioTotalCtrl = TextEditingController();

  /// Evita bucles al actualizar un campo desde el otro (cálculo bidireccional).
  bool _sincronizandoCampos = false;

  ProductoPesableMock? _productoSeleccionado;

  final List<PesableItem> _items = [];
  int _pestana = 0;

  /// Modo de salida: siempre uno activo (iconos arriba del panel derecho).
  _ModoSalidaPesables _modoSalida = _ModoSalidaPesables.balanzaTicketera;

  /// Cliente elegido en modo «Enviar a caja» (mismo control que Ventas).
  ClienteMock? _clienteAsignado;

  /// Tras intentar enviar sin cliente: placeholder en rojo hasta elegir uno.
  bool _errorClienteSinSeleccionar = false;

  static final List<ProductoPesableMock> _catalogoPesables = [
    const ProductoPesableMock(
      id: 'pes-1',
      nombre: 'Jamón cocido',
      precioUnitarioKg: 8500,
      plu: 10001,
    ),
    const ProductoPesableMock(
      id: 'pes-2',
      nombre: 'Queso cremoso',
      precioUnitarioKg: 6200,
      plu: 10002,
    ),
    const ProductoPesableMock(
      id: 'pes-3',
      nombre: 'Carne picada',
      precioUnitarioKg: 4500,
      plu: 10003,
    ),
    const ProductoPesableMock(
      id: 'pes-4',
      nombre: 'Tomate perita',
      precioUnitarioKg: 1200,
      plu: 10004,
    ),
    const ProductoPesableMock(
      id: 'pes-5',
      nombre: 'Pan de mesa',
      precioUnitarioKg: 1800,
      plu: 10005,
    ),
    const ProductoPesableMock(
      id: 'pes-6',
      nombre: 'Nuez a granel',
      precioUnitarioKg: 9500,
      plu: 10006,
    ),
  ];

  static const _categorias = <_CatPes>[
    _CatPes('Fiambres', Icons.set_meal_outlined),
    _CatPes('Carniceria', Icons.kebab_dining_outlined),
    _CatPes('Verduleria', Icons.eco_outlined),
    _CatPes('Panaderia', Icons.bakery_dining_outlined),
    _CatPes('A granel', Icons.shopping_basket_outlined),
    _CatPes('Lacteos', Icons.local_drink_outlined),
    _CatPes('Otros', Icons.scale_outlined),
  ];

  @override
  void initState() {
    super.initState();
    _productoSeleccionado = _catalogoPesables.first;
    _recalcularDesdePeso();
  }

  @override
  void dispose() {
    _controlBusqueda.dispose();
    _focusBusqueda.dispose();
    _pesoCtrl.dispose();
    _precioTotalCtrl.dispose();
    super.dispose();
  }

  double get _pu => _productoSeleccionado?.precioUnitarioKg ?? 0;

  void _recalcularDesdePeso() {
    final p = double.tryParse(_pesoCtrl.text.replaceAll(',', '.')) ?? 0;
    _sincronizandoCampos = true;
    try {
      if (p <= 0 || _pu <= 0) {
        _precioTotalCtrl.text = '';
        return;
      }
      final total = p * _pu;
      _precioTotalCtrl.text = total.toStringAsFixed(2);
    } finally {
      _sincronizandoCampos = false;
    }
  }

  void _recalcularDesdePrecio() {
    final t = double.tryParse(_precioTotalCtrl.text.replaceAll(',', '.')) ?? 0;
    _sincronizandoCampos = true;
    try {
      if (t <= 0 || _pu <= 0) {
        _pesoCtrl.text = '';
        return;
      }
      final kg = t / _pu;
      _pesoCtrl.text = kg.toStringAsFixed(3);
    } finally {
      _sincronizandoCampos = false;
    }
  }

  void _agregarLinea() {
    final p = _productoSeleccionado;
    if (p == null) return;
    final peso = double.tryParse(_pesoCtrl.text.replaceAll(',', '.')) ?? 0;
    final total =
        double.tryParse(_precioTotalCtrl.text.replaceAll(',', '.')) ?? 0;
    if (peso <= 0 || total <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ingrese peso y precio válidos.')),
      );
      return;
    }
    final bc = generarEan13Pesable(plu: p.plu, precioTotal: total);
    setState(() {
      _items.add(
        PesableItem(
          id: 'pi-${DateTime.now().millisecondsSinceEpoch}',
          productoId: p.id,
          nombreProducto: p.nombre,
          plu: p.plu,
          pesoKg: peso,
          precioUnitarioKg: p.precioUnitarioKg,
          precioTotal: total,
          barcode: bc,
          estado: EstadoPesableItem.pending,
        ),
      );
    });
  }

  void _ejecutarAccionSalida() {
    switch (_modoSalida) {
      case _ModoSalidaPesables.balanzaTicketera:
        _procesarBalanzaTicketera();
        break;
      case _ModoSalidaPesables.etiquetasIndividuales:
        _imprimirEtiquetasIndividuales();
        break;
      case _ModoSalidaPesables.etiquetaUnicaLista:
        _imprimirEtiquetaListaUnica();
        break;
      case _ModoSalidaPesables.enviarCajaSinImprimir:
        _enviarACajaSinImprimir();
        break;
    }
  }

  String get _textoBotonAccionPrincipal {
    switch (_modoSalida) {
      case _ModoSalidaPesables.balanzaTicketera:
        return 'Imprimir con balanza';
      case _ModoSalidaPesables.etiquetasIndividuales:
        return 'Imprimir etiquetas';
      case _ModoSalidaPesables.etiquetaUnicaLista:
        return 'Imprimir ticket';
      case _ModoSalidaPesables.enviarCajaSinImprimir:
        return 'Enviar';
    }
  }

  /// Flujo ideal: balanza en red + ticketera (impresión automática al pesar — mock).
  void _procesarBalanzaTicketera() {
    if (_items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Sin ítems en lista. En producción la balanza en red enviará el pesaje '
            'y la ticketera imprimirá el ticket automáticamente.',
          ),
        ),
      );
      return;
    }
    setState(() {
      for (final i in _items) {
        if (i.estado == EstadoPesableItem.pending) {
          i.estado = EstadoPesableItem.printed;
        }
      }
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Balanza en red + ticketera (simulado): ${_items.length} ticket(s) '
          'impreso(s). Vinculación IP/driver pendiente de integración.',
        ),
      ),
    );
  }

  void _imprimirEtiquetasIndividuales() {
    if (_items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No hay ítems para etiquetar.')),
      );
      return;
    }
    setState(() {
      for (final i in _items) {
        if (i.estado == EstadoPesableItem.pending) {
          i.estado = EstadoPesableItem.printed;
        }
      }
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Impresión: ${_items.length} etiqueta(s) (una por producto). Integración pendiente.',
        ),
      ),
    );
  }

  void _imprimirEtiquetaListaUnica() {
    if (_items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No hay ítems. Agregue productos a la lista.'),
        ),
      );
      return;
    }
    final ean = generarEan13ListaPesablesMock(_items);
    setState(() {
      for (final i in _items) {
        if (i.estado == EstadoPesableItem.pending) {
          i.estado = EstadoPesableItem.printed;
        }
      }
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Etiqueta única (mock): $ean · ${_items.length} ítems. Caja escaneará una vez.',
        ),
      ),
    );
  }

  Future<void> _enviarACajaSinImprimir() async {
    if (_items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No hay ítems para enviar a caja.'),
        ),
      );
      return;
    }
    final idCliente = _clienteAsignado?.clienteId;
    if (idCliente == null || idCliente <= 0) {
      setState(() => _errorClienteSinSeleccionar = true);
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          icon: Icon(
            Icons.warning_amber_rounded,
            color: Colors.amber.shade800,
            size: 36,
          ),
          title: const Text('Cliente obligatorio'),
          content: const Text(
            'Debe seleccionar un cliente antes de enviar la lista a caja.',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Entendido'),
            ),
          ],
        ),
      );
      return;
    }
    final c = _clienteAsignado!;
    final cantidadItems = _items.length;
    final doc = c.documento.isEmpty ? 'sin documento' : c.documento;
    setState(_items.clear);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Lista enviada a caja (mock): ${c.nombreCompleto} · Doc: $doc · '
          '$cantidadItems ítems.',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);

    return Shortcuts(
      shortcuts: const {
        SingleActivator(LogicalKeyboardKey.f2): _IntentFocusBusqueda(),
      },
      child: Actions(
        actions: {
          _IntentFocusBusqueda: CallbackAction<_IntentFocusBusqueda>(
            onInvoke: (_) {
              _focusBusqueda.requestFocus();
              return null;
            },
          ),
        },
        child: Focus(
          autofocus: true,
          child: Container(
            color: const Color(0xFFF4F5F8),
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    border: Border.all(color: const Color(0xFFE1E3E8)),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Text(
                        'Pesables',
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
                                border:
                                    Border.all(color: const Color(0xFFE1E3E8)),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      focusNode: _focusBusqueda,
                                      controller: _controlBusqueda,
                                      decoration: const InputDecoration(
                                        hintText:
                                            'Buscar producto pesable o código...',
                                        prefixIcon: Icon(Icons.search),
                                        isDense: true,
                                      ),
                                      onSubmitted: (_) => setState(() {}),
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
                                  border: Border.all(
                                      color: const Color(0xFFE1E3E8)),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: GridView.builder(
                                  itemCount: _categorias.length,
                                  gridDelegate:
                                      const SliverGridDelegateWithFixedCrossAxisCount(
                                    crossAxisCount: 4,
                                    crossAxisSpacing: 10,
                                    mainAxisSpacing: 10,
                                    childAspectRatio: 1.7,
                                  ),
                                  itemBuilder: (context, index) {
                                    final c = _categorias[index];
                                    return InkWell(
                                      borderRadius: BorderRadius.circular(8),
                                      onTap: () => setState(() =>
                                          _controlBusqueda.text = c.nombre),
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
                                            Icon(c.icono,
                                                size: 28,
                                                color: const Color(0xFF8A8F9D)),
                                            const SizedBox(height: 8),
                                            Text(
                                              c.nombre,
                                              style: const TextStyle(
                                                fontSize: 15,
                                                fontWeight: FontWeight.w500,
                                              ),
                                            ),
                                          ],
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
                                  onPressed: () => setState(_items.clear),
                                  icon: const Icon(Icons.clear_outlined),
                                  label: const Text('Vaciar lista'),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton.icon(
                                  onPressed: () {},
                                  icon: const Icon(Icons.label_outline),
                                  label: const Text('Vista previa etiqueta'),
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
                                  _TabPes(
                                    texto: 'Lote principal',
                                    sel: _pestana == 0,
                                    onTap: () => setState(() => _pestana = 0),
                                  ),
                                  _TabPes(
                                    texto: 'Victoria',
                                    sel: _pestana == 1,
                                    onTap: () => setState(() => _pestana = 1),
                                  ),
                                  IconButton(
                                    onPressed: () {},
                                    icon: const Icon(Icons.add),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      SizedBox(
                        width: 360,
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
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: [
                                  const Expanded(
                                    child: Text(
                                      'Calculadora pesable',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 16,
                                      ),
                                    ),
                                  ),
                                  _IconoModoPesable(
                                    activo: _modoSalida ==
                                        _ModoSalidaPesables.balanzaTicketera,
                                    tooltip:
                                        'Balanza en red + ticketera: imprime el ticket al pesar (flujo ideal)',
                                    onTap: () => setState(() {
                                      _modoSalida =
                                          _ModoSalidaPesables.balanzaTicketera;
                                      _errorClienteSinSeleccionar = false;
                                    }),
                                    iconBuilder: (color) => SizedBox(
                                      width: 26,
                                      height: 22,
                                      child: Stack(
                                        clipBehavior: Clip.none,
                                        alignment: Alignment.center,
                                        children: [
                                          Icon(
                                            Icons.monitor_weight_outlined,
                                            size: 22,
                                            color: color,
                                          ),
                                          Positioned(
                                            right: -4,
                                            bottom: -2,
                                            child: Icon(
                                              Icons.print_rounded,
                                              size: 11,
                                              color: color,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  _IconoModoPesable(
                                    activo: _modoSalida ==
                                        _ModoSalidaPesables
                                            .etiquetasIndividuales,
                                    tooltip:
                                        'Etiquetas individuales (una por producto)',
                                    onTap: () => setState(() {
                                      _modoSalida = _ModoSalidaPesables
                                          .etiquetasIndividuales;
                                      _errorClienteSinSeleccionar = false;
                                    }),
                                    iconBuilder: (color) => Icon(
                                      Icons.view_week_rounded,
                                      size: 22,
                                      color: color,
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  _IconoModoPesable(
                                    activo: _modoSalida ==
                                        _ModoSalidaPesables.etiquetaUnicaLista,
                                    tooltip:
                                        'Una sola etiqueta con toda la lista',
                                    onTap: () => setState(() {
                                      _modoSalida = _ModoSalidaPesables
                                          .etiquetaUnicaLista;
                                      _errorClienteSinSeleccionar = false;
                                    }),
                                    iconBuilder: (color) => Icon(
                                      Icons.qr_code_2_outlined,
                                      size: 22,
                                      color: color,
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  _IconoModoPesable(
                                    activo: _modoSalida ==
                                        _ModoSalidaPesables
                                            .enviarCajaSinImprimir,
                                    tooltip:
                                        'Enviar a caja sin imprimir (asignar a cliente)',
                                    onTap: () => setState(() {
                                      _modoSalida = _ModoSalidaPesables
                                          .enviarCajaSinImprimir;
                                      _errorClienteSinSeleccionar = false;
                                    }),
                                    iconBuilder: (color) => Icon(
                                      Icons.badge_outlined,
                                      size: 22,
                                      color: color,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              if (_modoSalida ==
                                  _ModoSalidaPesables
                                      .enviarCajaSinImprimir) ...[
                                const Text(
                                  'Cliente',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 13,
                                    color: Color(0xFF5D6778),
                                  ),
                                ),
                                const SizedBox(height: 4),
                                SelectorClienteComoVentas(
                                  permitirConsumidorFinal: false,
                                  mostrarLabelEnCampo: false,
                                  placeholderSinCliente: 'Seleccionar cliente',
                                  resaltarErrorSinSeleccion:
                                      _errorClienteSinSeleccionar,
                                  onClienteCambiado: (cliente) => setState(
                                    () {
                                      _clienteAsignado = cliente;
                                      if (cliente != null &&
                                          cliente.clienteId > 0) {
                                        _errorClienteSinSeleccionar = false;
                                      }
                                    },
                                  ),
                                ),
                                const SizedBox(height: 10),
                              ],
                              const Text('Producto'),
                              DropdownButtonFormField<ProductoPesableMock>(
                                isExpanded: true,
                                value: _productoSeleccionado,
                                decoration:
                                    const InputDecoration(isDense: true),
                                items: _filtrarCatalogo()
                                    .map(
                                      (e) => DropdownMenuItem(
                                        value: e,
                                        child: Text(
                                          '${e.nombre} — S/ ${e.precioUnitarioKg.toStringAsFixed(0)}/kg',
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (v) {
                                  if (v == null) return;
                                  setState(() {
                                    _productoSeleccionado = v;
                                    _recalcularDesdePeso();
                                  });
                                },
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'PLU: ${_productoSeleccionado?.plu ?? '—'} · Precio/kg: S/ ${_pu.toStringAsFixed(2)}',
                                style: const TextStyle(
                                    fontSize: 12, color: Color(0xFF6A7282)),
                              ),
                              const SizedBox(height: 10),
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: _pesoCtrl,
                                      decoration: const InputDecoration(
                                        labelText: 'Peso (kg)',
                                        isDense: true,
                                      ),
                                      keyboardType:
                                          const TextInputType.numberWithOptions(
                                              decimal: true),
                                      onChanged: (_) {
                                        if (_sincronizandoCampos) return;
                                        setState(_recalcularDesdePeso);
                                      },
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: TextField(
                                      controller: _precioTotalCtrl,
                                      decoration: const InputDecoration(
                                        labelText: 'Precio total',
                                        isDense: true,
                                      ),
                                      keyboardType:
                                          const TextInputType.numberWithOptions(
                                              decimal: true),
                                      onChanged: (_) {
                                        if (_sincronizandoCampos) return;
                                        setState(_recalcularDesdePrecio);
                                      },
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'EAN-13 (preview): ${_productoSeleccionado == null ? '—' : generarEan13Pesable(plu: _productoSeleccionado!.plu, precioTotal: double.tryParse(_precioTotalCtrl.text.replaceAll(',', '.')) ?? 0)}',
                                style: const TextStyle(
                                    fontSize: 11, fontFamily: 'monospace'),
                              ),
                              const SizedBox(height: 10),
                              FilledButton.icon(
                                onPressed: _agregarLinea,
                                icon: const Icon(Icons.add),
                                label: const Text('Agregar a la lista'),
                              ),
                              const SizedBox(height: 10),
                              const Divider(),
                              const Text(
                                'Lista de pesables',
                                style: TextStyle(fontWeight: FontWeight.w700),
                              ),
                              const SizedBox(height: 6),
                              Expanded(
                                child: _items.isEmpty
                                    ? const Center(
                                        child: Text(
                                          'Sin ítems. Agregue desde la calculadora.',
                                          style: TextStyle(
                                              color: Color(0xFF6E7380)),
                                        ),
                                      )
                                    : ListView.separated(
                                        itemCount: _items.length,
                                        separatorBuilder: (_, __) =>
                                            const Divider(height: 1),
                                        itemBuilder: (context, i) {
                                          final it = _items[i];
                                          return ListTile(
                                            dense: true,
                                            title: Text(it.nombreProducto),
                                            subtitle: Text(
                                              '${it.pesoKg.toStringAsFixed(3)} kg × S/ ${it.precioUnitarioKg.toStringAsFixed(0)}/kg → S/ ${it.precioTotal.toStringAsFixed(2)}',
                                            ),
                                            trailing: Text(
                                              it.estado.name,
                                              style:
                                                  const TextStyle(fontSize: 11),
                                            ),
                                          );
                                        },
                                      ),
                              ),
                              const SizedBox(height: 8),
                              FilledButton(
                                onPressed: _ejecutarAccionSalida,
                                style: FilledButton.styleFrom(
                                  backgroundColor: const Color(0xFF3D4F63),
                                ),
                                child: Text(_textoBotonAccionPrincipal),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<ProductoPesableMock> _filtrarCatalogo() {
    final q = _controlBusqueda.text.trim().toLowerCase();
    if (q.isEmpty) return _catalogoPesables;
    final filtrados = _catalogoPesables
        .where((e) =>
            e.nombre.toLowerCase().contains(q) ||
            e.id.toLowerCase().contains(q) ||
            e.plu.toString().contains(q))
        .toList();
    return filtrados.isEmpty ? _catalogoPesables : filtrados;
  }
}

/// Cómo se procesa la lista al confirmar (un modo activo a la vez).
enum _ModoSalidaPesables {
  /// Balanza en red + ticketera (impresión automática al pesar).
  balanzaTicketera,
  etiquetasIndividuales,
  etiquetaUnicaLista,
  enviarCajaSinImprimir,
}

class _IconoModoPesable extends StatelessWidget {
  const _IconoModoPesable({
    required this.activo,
    required this.tooltip,
    required this.onTap,
    required this.iconBuilder,
  });

  final bool activo;
  final String tooltip;
  final VoidCallback onTap;
  final Widget Function(Color color) iconBuilder;

  static const _verdeFondo = Color(0xFFE8F5E9);
  static const _verdeIcono = Color(0xFF2E7D32);
  static const _grisFondo = Color(0xFFECEFF3);
  static const _grisIcono = Color(0xFF6B7280);

  @override
  Widget build(BuildContext context) {
    final colorIcono = activo ? _verdeIcono : _grisIcono;
    return Tooltip(
      message: tooltip,
      child: Material(
        color: activo ? _verdeFondo : _grisFondo,
        borderRadius: BorderRadius.circular(8),
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        shadowColor: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          splashFactory: NoSplash.splashFactory,
          splashColor: Colors.transparent,
          highlightColor: Colors.transparent,
          hoverColor: Colors.transparent,
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: iconBuilder(colorIcono),
          ),
        ),
      ),
    );
  }
}

class _CatPes {
  const _CatPes(this.nombre, this.icono);
  final String nombre;
  final IconData icono;
}

class _TabPes extends StatelessWidget {
  const _TabPes({
    required this.texto,
    required this.sel,
    required this.onTap,
  });

  final String texto;
  final bool sel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: sel ? const Color(0xFFF4F6FA) : Colors.transparent,
          border: const Border(
            right: BorderSide(color: Color(0xFFE1E3E8)),
          ),
        ),
        alignment: Alignment.center,
        child: Text(
          texto,
          style: TextStyle(
            fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ),
    );
  }
}

class _IntentFocusBusqueda extends Intent {
  const _IntentFocusBusqueda();
}
