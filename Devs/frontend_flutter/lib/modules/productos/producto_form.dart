import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../widgets/primary_button.dart';

class ProductoForm extends StatefulWidget {
  const ProductoForm({super.key, this.producto, this.clienteApi});

  final Map<String, dynamic>? producto;
  final ClienteApi? clienteApi;

  @override
  State<ProductoForm> createState() => _ProductoFormState();
}

class _ProductoFormState extends State<ProductoForm> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _skuCtrl;
  late final TextEditingController _nombreCtrl;
  late final TextEditingController _precioCtrl;
  late final TextEditingController _codigoBarraCtrl;
  bool _guardando = false;

  @override
  void initState() {
    super.initState();
    final p = widget.producto;
    _skuCtrl = TextEditingController(text: p?['sku'] as String? ?? '');
    _nombreCtrl = TextEditingController(text: p?['nombre'] as String? ?? '');
    _precioCtrl = TextEditingController(
      text: (p?['precio_venta'] as num?)?.toStringAsFixed(2) ?? '0.00',
    );
    _codigoBarraCtrl = TextEditingController(text: p?['codigo_barra'] as String? ?? '');
  }

  @override
  void dispose() {
    _skuCtrl.dispose();
    _nombreCtrl.dispose();
    _precioCtrl.dispose();
    _codigoBarraCtrl.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!_formKey.currentState!.validate()) return;
    final precio = double.tryParse(_precioCtrl.text.replaceAll(',', '.')) ?? 0;
    final api = widget.clienteApi;
    if (api == null) {
      Navigator.of(context).pop(true);
      return;
    }

    setState(() => _guardando = true);
    try {
      if (widget.producto == null) {
        await api.crearProducto(
          sku: _skuCtrl.text.trim(),
          nombre: _nombreCtrl.text.trim(),
          precioVenta: precio,
          codigoBarra: _codigoBarraCtrl.text.trim().isEmpty ? null : _codigoBarraCtrl.text.trim(),
        );
      } else {
        final id = widget.producto!['id'] as int;
        await api.actualizarProducto(
          productoId: id,
          nombre: _nombreCtrl.text.trim(),
          precioVenta: precio,
          codigoBarra: _codigoBarraCtrl.text.trim(),
        );
      }

      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al guardar: $e')),
      );
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final esEdicion = widget.producto != null;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              esEdicion ? 'Editar producto' : 'Nuevo producto',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _skuCtrl,
              decoration: const InputDecoration(labelText: 'SKU'),
              validator: (value) => value == null || value.isEmpty ? 'Obligatorio' : null,
              readOnly: esEdicion,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _nombreCtrl,
              decoration: const InputDecoration(labelText: 'Nombre'),
              validator: (value) => value == null || value.isEmpty ? 'Obligatorio' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _codigoBarraCtrl,
              decoration: const InputDecoration(labelText: 'Código de barras'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _precioCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Precio de venta',
                prefixText: 'S/ ',
              ),
              validator: (value) {
                final v = double.tryParse((value ?? '').replaceAll(',', '.'));
                if (v == null || v < 0) return 'Precio inválido';
                return null;
              },
            ),
            const SizedBox(height: 16),
            BotonPrimario(
              texto: _guardando ? 'Guardando...' : 'Guardar',
              icono: Icons.save,
              onPressed: _guardando ? null : _guardar,
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

