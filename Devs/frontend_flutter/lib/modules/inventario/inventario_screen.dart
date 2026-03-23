import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';

class PantallaInventario extends StatefulWidget {
  const PantallaInventario({super.key});

  @override
  State<PantallaInventario> createState() => _PantallaInventarioState();
}

class _PantallaInventarioState extends State<PantallaInventario> {
  final _clienteApi = ClienteApi();
  final _controlProductoId = TextEditingController();
  final _controlAjusteCantidad = TextEditingController();
  String _ubicacionAjuste = 'GONDOLA';

  Map<String, dynamic>? _stockGondola;
  Map<String, dynamic>? _stockDeposito;
  bool _cargando = false;
  bool _ajustando = false;

  @override
  void dispose() {
    _controlProductoId.dispose();
    _controlAjusteCantidad.dispose();
    super.dispose();
  }

  Future<void> _ajustarStock() async {
    final id = int.tryParse(_controlProductoId.text.trim());
    final cantidad = double.tryParse(_controlAjusteCantidad.text.replaceAll(',', '.'));
    if (id == null || cantidad == null || cantidad == 0) return;
    setState(() => _ajustando = true);
    try {
      await _clienteApi.ajustarStock(
        productoId: id,
        cantidad: cantidad,
        ubicacion: _ubicacionAjuste,
        referencia: 'Ajuste desde POS',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ajuste registrado')),
      );
      _controlAjusteCantidad.clear();
      _cargarStock();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      if (mounted) setState(() => _ajustando = false);
    }
  }

  Future<void> _cargarStock() async {
    final id = int.tryParse(_controlProductoId.text.trim());
    if (id == null) return;
    setState(() => _cargando = true);
    try {
      final gondola = await _clienteApi.consultarStock(id, ubicacion: 'GONDOLA');
      final deposito = await _clienteApi.consultarStock(id, ubicacion: 'DEPOSITO');
      setState(() {
        _stockGondola = gondola;
        _stockDeposito = deposito;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al obtener stock: $e')),
      );
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Inventario',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              SizedBox(
                width: 200,
                child: TextField(
                  controller: _controlProductoId,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'ID de producto',
                  ),
                  onSubmitted: (_) => _cargarStock(),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: _cargarStock,
                icon: const Icon(Icons.search),
                label: const Text('Ver stock'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          if (_cargando) const LinearProgressIndicator(),
          const SizedBox(height: 16),
          if (_stockGondola != null || _stockDeposito != null) ...[
            Row(
              children: [
                Expanded(
                  child: _tarjetaStock('GÓNDOLA', _stockGondola),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _tarjetaStock('DEPÓSITO', _stockDeposito),
                ),
              ],
            ),
            const SizedBox(height: 24),
            const Text(
              'Ajustar stock',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                DropdownButton<String>(
                  value: _ubicacionAjuste,
                  items: const [
                    DropdownMenuItem(value: 'GONDOLA', child: Text('GÓNDOLA')),
                    DropdownMenuItem(value: 'DEPOSITO', child: Text('DEPÓSITO')),
                  ],
                  onChanged: (v) => setState(() => _ubicacionAjuste = v ?? 'GONDOLA'),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 120,
                  child: TextField(
                    controller: _controlAjusteCantidad,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'Cantidad (+/-)',
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: _ajustando ? null : _ajustarStock,
                  icon: const Icon(Icons.edit),
                  label: const Text('Ajustar'),
                ),
              ],
            ),
          ] else
            const Text('Ingrese un ID de producto para ver el stock.'),
        ],
      ),
    );
  }

  Widget _tarjetaStock(String ubicacion, Map<String, dynamic>? data) {
    final cantidad = (data?['cantidad'] as num?)?.toDouble() ?? 0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              ubicacion,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Cantidad: $cantidad',
              style: const TextStyle(fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}

