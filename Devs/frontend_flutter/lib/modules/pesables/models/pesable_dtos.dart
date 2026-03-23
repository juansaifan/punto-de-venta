/// Contratos UI / mock para el submódulo Pesables (sin backend).
/// Ver documentación: Reglas/docs/Módulo 2/4. Pesables/submodulo_pesables.md
library;

enum EstadoPesableItem { pending, printed, used }

class ProductoPesableMock {
  const ProductoPesableMock({
    required this.id,
    required this.nombre,
    required this.precioUnitarioKg,
    required this.plu,
    this.pesable = true,
  });

  final String id;
  final String nombre;
  final double precioUnitarioKg;
  final int plu;
  final bool pesable;
}

class PesableItem {
  PesableItem({
    required this.id,
    required this.productoId,
    required this.nombreProducto,
    required this.plu,
    required this.pesoKg,
    required this.precioUnitarioKg,
    required this.precioTotal,
    required this.barcode,
    this.estado = EstadoPesableItem.pending,
  });

  final String id;
  final String productoId;
  final String nombreProducto;
  final int plu;
  final double pesoKg;
  final double precioUnitarioKg;
  final double precioTotal;
  final String barcode;
  EstadoPesableItem estado;
}

/// Genera EAN-13 según formato documentado:
/// [20][PLU(5)][PRECIO centavos(5)][CHECKSUM]
String generarEan13Pesable({
  required int plu,
  required double precioTotal,
}) {
  final centavos = (precioTotal * 100).round().clamp(0, 99999);
  final pluStr = plu.toString().padLeft(5, '0');
  final precioStr = centavos.toString().padLeft(5, '0');
  final base12 = '20$pluStr$precioStr';
  final check = _digitoControlEan13(base12);
  return '$base12$check';
}

/// Una sola etiqueta agregada para toda la lista (mock; integración real pendiente).
String generarEan13ListaPesablesMock(List<PesableItem> items) {
  if (items.isEmpty) return '—';
  final total = items.fold<double>(0, (a, i) => a + i.precioTotal);
  final pluFake =
      ((items.length * 7919) + (total * 100).round()) % 100000; // 0–99999
  return generarEan13Pesable(plu: pluFake, precioTotal: total);
}

int _digitoControlEan13(String doceDigitos) {
  assert(doceDigitos.length == 12);
  var suma = 0;
  for (var i = 0; i < 12; i++) {
    final d = int.parse(doceDigitos[i]);
    suma += (i % 2 == 0) ? d : d * 3;
  }
  return (10 - (suma % 10)) % 10;
}
