import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../widgets/primary_button.dart';
import 'producto_form.dart';

class PantallaProductos extends StatefulWidget {
  const PantallaProductos({super.key});

  @override
  State<PantallaProductos> createState() => _PantallaProductosState();
}

class _PantallaProductosState extends State<PantallaProductos> {
  final _clienteApi = ClienteApi();
  final _controlBusqueda = TextEditingController();
  final List<Map<String, dynamic>> _productos = [];
  bool _cargando = false;

  @override
  void initState() {
    super.initState();
    _cargarProductos();
  }

  @override
  void dispose() {
    _controlBusqueda.dispose();
    super.dispose();
  }

  Future<void> _cargarProductos({String? filtro}) async {
    setState(() => _cargando = true);
    try {
      final lista = await _clienteApi.listarProductos(busqueda: filtro);
      setState(() {
        _productos
          ..clear()
          ..addAll(lista);
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al cargar productos: $e')),
      );
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  void _abrirFormulario({Map<String, dynamic>? producto}) async {
    final resultado = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: ProductoForm(producto: producto, clienteApi: _clienteApi),
      ),
    );
    if (resultado == true) {
      _clienteApi.invalidarCacheProductos();
      _cargarProductos(filtro: _controlBusqueda.text);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.all(8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controlBusqueda,
                  decoration: const InputDecoration(
                    labelText: 'Buscar producto',
                    prefixIcon: Icon(Icons.search),
                  ),
                  onSubmitted: (value) => _cargarProductos(filtro: value),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 200,
                child: BotonPrimario(
                  texto: 'Nuevo producto',
                  icono: Icons.add,
                  onPressed: () => _abrirFormulario(),
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: _cargando
              ? const Center(child: CircularProgressIndicator())
              : Card(
                  margin: const EdgeInsets.all(8),
                  child: _productos.isEmpty
                      ? const Center(child: Text('No hay productos'))
                      : SingleChildScrollView(
                          child: DataTable(
                            columns: const [
                              DataColumn(label: Text('SKU')),
                              DataColumn(label: Text('Nombre')),
                              DataColumn(label: Text('Precio')),
                              DataColumn(label: Text('Activo')),
                              DataColumn(label: Text('')),
                            ],
                            rows: _productos
                                .map(
                                  (p) => DataRow(
                                    cells: [
                                      DataCell(Text(p['sku'] ?? '')),
                                      DataCell(Text(p['nombre'] ?? '')),
                                      DataCell(Text(
                                          'S/ ${(p['precio_venta'] as num?)?.toStringAsFixed(2) ?? '0.00'}')),
                                      DataCell(
                                        Icon(
                                          (p['activo'] as bool? ?? true)
                                              ? Icons.check_circle
                                              : Icons.cancel,
                                          color: (p['activo'] as bool? ?? true)
                                              ? Colors.green
                                              : Colors.red,
                                        ),
                                      ),
                                      DataCell(
                                        IconButton(
                                          icon: const Icon(Icons.edit),
                                          onPressed: () =>
                                              _abrirFormulario(producto: p),
                                        ),
                                      ),
                                    ],
                                  ),
                                )
                                .toList(),
                          ),
                        ),
                ),
        ),
      ],
    );
  }
}

