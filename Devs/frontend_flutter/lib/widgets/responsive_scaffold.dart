import 'package:flutter/material.dart';

class DisenoResponsivoPos extends StatefulWidget {
  const DisenoResponsivoPos({
    super.key,
    required this.indiceSeleccionado,
    required this.onCambiarIndice,
    required this.construirContenido,
  });

  final int indiceSeleccionado;
  final ValueChanged<int> onCambiarIndice;
  final WidgetBuilder construirContenido;

  @override
  State<DisenoResponsivoPos> createState() => _DisenoResponsivoPosState();
}

class _DisenoResponsivoPosState extends State<DisenoResponsivoPos> {
  bool _expandirPuntoVenta = true;

  static const _itemsPuntoVenta = <_SubItemNav>[
    _SubItemNav('Ventas', Icons.point_of_sale_outlined, 1),
    _SubItemNav('Pesables', Icons.scale_outlined, 2),
    _SubItemNav('Caja', Icons.account_balance_wallet_outlined, 3),
    _SubItemNav('Operaciones Comerciales', Icons.receipt_long_outlined, 4),
  ];

  static const _itemsModulos = <_ItemNav>[
    _ItemNav('Tesoreria', Icons.payments_outlined, 5),
    _ItemNav('Finanzas', Icons.account_balance_outlined, 6),
    _ItemNav('Inventario', Icons.inventory_2_outlined, 7),
    _ItemNav('Personas', Icons.people_outline, 8),
    _ItemNav('Reportes', Icons.assessment_outlined, 9),
    _ItemNav('Integraciones', Icons.hub_outlined, 10),
    _ItemNav('Configuraciones', Icons.settings_outlined, 11),
  ];

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final esEscritorio = constraints.maxWidth >= 900;
        if (esEscritorio) {
          return Row(
            children: [
              Material(
                color: const Color(0xFFF7F8FB),
                child: SizedBox(
                  width: 245,
                  child: Column(
                    children: [
                      const SizedBox(height: 10),
                      const _PosRailBrand(extendido: true),
                      const SizedBox(height: 8),
                      Expanded(
                        child: ListView(
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          children: [
                            _BotonModulo(
                              titulo: 'Dashboard',
                              icono: Icons.dashboard_outlined,
                              seleccionado: widget.indiceSeleccionado == 0,
                              onTap: () => widget.onCambiarIndice(0),
                            ),
                            const SizedBox(height: 2),
                            _BotonModuloExpandible(
                              titulo: 'Punto de venta',
                              icono: Icons.storefront_outlined,
                              expandido: _expandirPuntoVenta,
                              onTap: () {
                                setState(() {
                                  _expandirPuntoVenta = !_expandirPuntoVenta;
                                });
                              },
                            ),
                            if (_expandirPuntoVenta)
                              ..._itemsPuntoVenta.map(
                                (item) => _BotonSubmodulo(
                                  titulo: item.titulo,
                                  icono: item.icono,
                                  seleccionado:
                                      widget.indiceSeleccionado == item.indice,
                                  onTap: () =>
                                      widget.onCambiarIndice(item.indice),
                                ),
                              ),
                            const SizedBox(height: 2),
                            ..._itemsModulos.map(
                              (item) => Padding(
                                padding: const EdgeInsets.only(bottom: 2),
                                child: _BotonModulo(
                                  titulo: item.titulo,
                                  icono: item.icono,
                                  seleccionado:
                                      widget.indiceSeleccionado == item.indice,
                                  onTap: () =>
                                      widget.onCambiarIndice(item.indice),
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
              const VerticalDivider(width: 1),
              Expanded(
                child: Scaffold(
                  appBar: AppBar(
                    title: const Text('La Casona – POS'),
                  ),
                  body: widget.construirContenido(context),
                ),
              ),
            ],
          );
        }

        return Scaffold(
          appBar: AppBar(
            title: const Text('La Casona – POS'),
          ),
          drawer: Drawer(
            child: SafeArea(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                children: [
                  const _PosRailBrand(extendido: true),
                  const SizedBox(height: 8),
                  _BotonModulo(
                    titulo: 'Dashboard',
                    icono: Icons.dashboard_outlined,
                    seleccionado: widget.indiceSeleccionado == 0,
                    onTap: () {
                      Navigator.pop(context);
                      widget.onCambiarIndice(0);
                    },
                  ),
                  const SizedBox(height: 2),
                  _BotonModuloExpandible(
                    titulo: 'Punto de venta',
                    icono: Icons.storefront_outlined,
                    expandido: _expandirPuntoVenta,
                    onTap: () {
                      setState(
                          () => _expandirPuntoVenta = !_expandirPuntoVenta);
                    },
                  ),
                  if (_expandirPuntoVenta)
                    ..._itemsPuntoVenta.map(
                      (item) => _BotonSubmodulo(
                        titulo: item.titulo,
                        icono: item.icono,
                        seleccionado: widget.indiceSeleccionado == item.indice,
                        onTap: () {
                          Navigator.pop(context);
                          widget.onCambiarIndice(item.indice);
                        },
                      ),
                    ),
                  const SizedBox(height: 2),
                  ..._itemsModulos.map(
                    (item) => _BotonModulo(
                      titulo: item.titulo,
                      icono: item.icono,
                      seleccionado: widget.indiceSeleccionado == item.indice,
                      onTap: () {
                        Navigator.pop(context);
                        widget.onCambiarIndice(item.indice);
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
          body: widget.construirContenido(context),
        );
      },
    );
  }
}

class _ItemNav {
  const _ItemNav(this.titulo, this.icono, this.indice);

  final String titulo;
  final IconData icono;
  final int indice;
}

class _SubItemNav {
  const _SubItemNav(this.titulo, this.icono, this.indice);

  final String titulo;
  final IconData icono;
  final int indice;
}

class _BotonModulo extends StatelessWidget {
  const _BotonModulo({
    required this.titulo,
    required this.icono,
    required this.seleccionado,
    required this.onTap,
  });

  final String titulo;
  final IconData icono;
  final bool seleccionado;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          color: seleccionado ? const Color(0xFFE8EEF9) : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(icono, size: 19),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                titulo,
                style: TextStyle(
                  fontWeight: seleccionado ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BotonModuloExpandible extends StatelessWidget {
  const _BotonModuloExpandible({
    required this.titulo,
    required this.icono,
    required this.expandido,
    required this.onTap,
  });

  final String titulo;
  final IconData icono;
  final bool expandido;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(icono, size: 19),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                titulo,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
            Icon(expandido ? Icons.expand_less : Icons.expand_more),
          ],
        ),
      ),
    );
  }
}

class _BotonSubmodulo extends StatelessWidget {
  const _BotonSubmodulo({
    required this.titulo,
    required this.icono,
    required this.seleccionado,
    required this.onTap,
  });

  final String titulo;
  final IconData icono;
  final bool seleccionado;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 14, bottom: 2),
      child: _BotonModulo(
        titulo: titulo,
        icono: icono,
        seleccionado: seleccionado,
        onTap: onTap,
      ),
    );
  }
}

class _PosRailBrand extends StatelessWidget {
  const _PosRailBrand({required this.extendido});

  final bool extendido;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 50,
          height: 50,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              colors: [Color(0xFF334156), Color(0xFF1F2A3D)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: const Icon(
            Icons.storefront_rounded,
            color: Colors.white,
            size: 26,
          ),
        ),
        if (extendido) ...[
          const SizedBox(height: 8),
          const Text(
            'La Casona',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
          ),
          Text(
            'POS',
            style: TextStyle(
              fontSize: 11,
              color: Colors.blueGrey.shade700,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ],
    );
  }
}
