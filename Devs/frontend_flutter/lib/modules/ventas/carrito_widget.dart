import 'package:flutter/material.dart';

class ItemCarrito {
  ItemCarrito({
    required this.idProducto,
    required this.nombre,
    required this.precioUnitario,
    this.cantidad = 1,
  });

  final int idProducto;
  final String nombre;
  final double precioUnitario;
  int cantidad;

  double get subtotal => precioUnitario * cantidad;
}

typedef CambiarCantidadCallback = void Function(ItemCarrito item, int nuevaCantidad);
typedef EliminarItemCallback = void Function(ItemCarrito item);

class CarritoWidget extends StatelessWidget {
  const CarritoWidget({
    super.key,
    required this.items,
    required this.onCambiarCantidad,
    required this.onEliminar,
  });

  final List<ItemCarrito> items;
  final CambiarCantidadCallback onCambiarCantidad;
  final EliminarItemCallback onEliminar;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const Center(
        child: Text(
          'El carrito está vacío',
          style: TextStyle(fontSize: 18),
        ),
      );
    }

    return ListView.separated(
      itemCount: items.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final item = items[index];
        return ListTile(
          title: Text(
            item.nombre,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
          ),
          subtitle: Text(
            'S/ ${item.precioUnitario.toStringAsFixed(2)}',
          ),
          trailing: SizedBox(
            width: 220,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                IconButton(
                  icon: const Icon(Icons.remove_circle_outline),
                  iconSize: 28,
                  onPressed: () {
                    final nueva = item.cantidad - 1;
                    if (nueva >= 1) {
                      onCambiarCantidad(item, nueva);
                    }
                  },
                ),
                Text(
                  '${item.cantidad}',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                IconButton(
                  icon: const Icon(Icons.add_circle_outline),
                  iconSize: 28,
                  onPressed: () {
                    final nueva = item.cantidad + 1;
                    onCambiarCantidad(item, nueva);
                  },
                ),
                const SizedBox(width: 16),
                Text(
                  'S/ ${item.subtotal.toStringAsFixed(2)}',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () => onEliminar(item),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

