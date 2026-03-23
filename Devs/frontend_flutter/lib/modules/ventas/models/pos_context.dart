class POS {
  const POS({
    required this.id,
    required this.nombre,
    required this.activo,
  });

  final String id;
  final String nombre;
  final bool activo;

  POS copyWith({
    String? id,
    String? nombre,
    bool? activo,
  }) {
    return POS(
      id: id ?? this.id,
      nombre: nombre ?? this.nombre,
      activo: activo ?? this.activo,
    );
  }
}

class POSSession {
  const POSSession({
    required this.posId,
    required this.vendedorId,
  });

  final String posId;
  final String vendedorId;
}
