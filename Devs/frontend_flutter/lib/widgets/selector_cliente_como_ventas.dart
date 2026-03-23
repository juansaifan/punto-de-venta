import 'package:flutter/material.dart';

import '../core/api/api_client.dart';

/// Mismo aspecto y diálogo que el selector de cliente de [PantallaVentas].
///
/// Si [permitirConsumidorFinal] es `false` (p. ej. Pesables), no se ofrece
/// “Consumidor final” y hace falta elegir un cliente con `clienteId != 0`.
class SelectorClienteComoVentas extends StatefulWidget {
  const SelectorClienteComoVentas({
    super.key,
    this.onClienteCambiado,
    this.onAbrirSelector,
    this.permitirConsumidorFinal = true,
    this.mostrarLabelEnCampo = true,
    this.placeholderSinCliente = 'Seleccionar cliente',
    this.resaltarErrorSinSeleccion = false,
  });

  /// `null` = aún sin cliente válido (solo cuando [permitirConsumidorFinal] es false).
  final ValueChanged<ClienteMock?>? onClienteCambiado;

  /// Al tocar el campo (antes del diálogo); p. ej. limpiar error de validación.
  final VoidCallback? onAbrirSelector;

  /// En `false`, no se puede elegir cliente id 0 (consumidor final).
  final bool permitirConsumidorFinal;

  /// Etiqueta “Cliente” dentro del campo; desactivar si hay leyenda fuera.
  final bool mostrarLabelEnCampo;

  /// Texto cuando aún no hay cliente elegido ([permitirConsumidorFinal] false).
  final String placeholderSinCliente;

  /// Si es true y no hay cliente, el [placeholderSinCliente] se muestra en rojo.
  final bool resaltarErrorSinSeleccion;

  @override
  State<SelectorClienteComoVentas> createState() =>
      _SelectorClienteComoVentasState();

  /// Abre el diálogo de búsqueda y selección de cliente sin necesitar una
  /// instancia del widget. Siempre exige cliente real (sin consumidor final).
  ///
  /// Retorna el [ClienteMock] elegido, o `null` si se canceló o el usuario
  /// eligió "Nuevo cliente" (se muestra snackbar en ese caso).
  static Future<ClienteMock?> mostrarDialogoSeleccion(
    BuildContext context,
  ) async {
    final clienteApi = ClienteApi();
    List<ClienteMock> clientes = const [];
    try {
      clientes = await clienteApi.listarClientes();
    } catch (_) {}
    if (!context.mounted) return null;

    String busqueda = '';
    final seleccionadoId = await showDialog<int>(
      context: context,
      builder: (dialogCtx) => StatefulBuilder(
        builder: (dialogCtx, setStateDialog) {
          final q = busqueda.trim().toLowerCase();
          final filtrados = clientes
              .where(
                (c) =>
                    c.clienteId != 0 &&
                    (q.isEmpty ||
                        c.nombreCompleto.toLowerCase().contains(q) ||
                        c.documento.toLowerCase().contains(q) ||
                        c.clienteId.toString().contains(q)),
              )
              .toList();
          return AlertDialog(
            title: const Text('Asignar cliente'),
            content: SizedBox(
              width: 520,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Debe elegir un cliente registrado.',
                    style: TextStyle(
                      fontSize: 13,
                      color: Theme.of(dialogCtx)
                          .colorScheme
                          .onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 10),
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
                    onChanged: (v) =>
                        setStateDialog(() => busqueda = v),
                  ),
                  const SizedBox(height: 10),
                  Flexible(
                    child: ListView(
                      shrinkWrap: true,
                      children: [
                        if (filtrados.isEmpty)
                          const ListTile(
                            dense: true,
                            title: Text('Sin clientes coincidentes'),
                          )
                        else
                          ...filtrados.map(
                            (c) => ListTile(
                              dense: true,
                              title: Text(c.nombreCompleto),
                              subtitle: Text(
                                c.documento.isEmpty
                                    ? 'Sin documento'
                                    : 'Doc: ${c.documento}',
                              ),
                              onTap: () =>
                                  Navigator.of(dialogCtx).pop(c.clienteId),
                            ),
                          ),
                        const Divider(height: 1),
                        ListTile(
                          dense: true,
                          leading:
                              const Icon(Icons.person_add_alt_1_outlined),
                          title: const Text('+ Nuevo cliente'),
                          onTap: () => Navigator.of(dialogCtx).pop(-1),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogCtx).pop(),
                child: const Text('Cerrar'),
              ),
            ],
          );
        },
      ),
    );

    if (!context.mounted || seleccionadoId == null) return null;
    if (seleccionadoId == -1) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Pendiente: abrir flujo de creación de nuevo cliente.',
          ),
        ),
      );
      return null;
    }
    return clientes.firstWhere(
      (c) => c.clienteId == seleccionadoId,
      orElse: () => clientes.first,
    );
  }
}

class _SelectorClienteComoVentasState extends State<SelectorClienteComoVentas> {
  static const int _sinSeleccion = -1;

  final _clienteApi = ClienteApi();
  bool _cargando = true;
  List<ClienteMock> _clientes = const [];
  int _clienteIdSeleccionado = 0;

  ClienteMock get clienteSeleccionado {
    if (!widget.permitirConsumidorFinal &&
        _clienteIdSeleccionado == _sinSeleccion) {
      return ClienteMock(
        clienteId: _sinSeleccion,
        personaId: 0,
        nombreCompleto: widget.placeholderSinCliente,
        documento: '',
        limiteCredito: 0,
      );
    }
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

  bool get _clienteValidoParaSalida {
    if (widget.permitirConsumidorFinal) return true;
    return _clienteIdSeleccionado != _sinSeleccion &&
        _clienteIdSeleccionado != 0;
  }

  @override
  void initState() {
    super.initState();
    _clienteApi.listarClientes().then((lista) {
      if (!mounted) return;
      setState(() {
        _clientes = lista;
        if (widget.permitirConsumidorFinal) {
          _clienteIdSeleccionado = lista.any((c) => c.clienteId == 0)
              ? 0
              : (lista.isNotEmpty ? lista.first.clienteId : 0);
        } else {
          // Pesables: nunca preseleccionar; el usuario debe elegir explícitamente.
          _clienteIdSeleccionado = _sinSeleccion;
        }
        _cargando = false;
      });
      _notificarPadre();
    }).catchError((_) {
      if (!mounted) return;
      setState(() {
        _cargando = false;
        if (!widget.permitirConsumidorFinal) {
          _clienteIdSeleccionado = _sinSeleccion;
        }
      });
      _notificarPadre();
    });
  }

  void _notificarPadre() {
    if (!widget.permitirConsumidorFinal) {
      widget.onClienteCambiado
          ?.call(_clienteValidoParaSalida ? clienteSeleccionado : null);
    } else {
      widget.onClienteCambiado?.call(clienteSeleccionado);
    }
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
    widget.onAbrirSelector?.call();
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
                    if (!widget.permitirConsumidorFinal) ...[
                      Text(
                        'Debe elegir un cliente registrado.',
                        style: TextStyle(
                          fontSize: 13,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 10),
                    ],
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
                          if (widget.permitirConsumidorFinal) ...[
                            ListTile(
                              dense: true,
                              leading: const Icon(Icons.person_outline),
                              title: const Text('Consumidor final'),
                              subtitle: const Text('Valor predefinido'),
                              onTap: () => Navigator.of(context).pop(0),
                            ),
                            const Divider(height: 1),
                          ],
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
          content: Text(
            'Pendiente: abrir flujo de creación de nuevo cliente.',
          ),
        ),
      );
      return;
    }
    if (!widget.permitirConsumidorFinal && seleccionado == 0) return;
    setState(() => _clienteIdSeleccionado = seleccionado);
    _notificarPadre();
  }

  @override
  Widget build(BuildContext context) {
    if (_cargando) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Center(
          child: SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      );
    }
    final sinElegir = !widget.permitirConsumidorFinal &&
        _clienteIdSeleccionado == _sinSeleccion;
    final cliente = clienteSeleccionado;
    final errorRojo = sinElegir && widget.resaltarErrorSinSeleccion;
    return InkWell(
      onTap: _abrirSelectorCliente,
      borderRadius: BorderRadius.circular(6),
      child: InputDecorator(
        decoration: InputDecoration(
          isDense: true,
          labelText: widget.mostrarLabelEnCampo ? 'Cliente' : null,
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                sinElegir
                    ? widget.placeholderSinCliente
                    : cliente.nombreCompleto,
                overflow: TextOverflow.ellipsis,
                style: sinElegir
                    ? TextStyle(
                        color: errorRojo
                            ? const Color(0xFFC62828)
                            : Theme.of(context).hintColor,
                        fontStyle: FontStyle.italic,
                        fontWeight:
                            errorRojo ? FontWeight.w600 : FontWeight.normal,
                      )
                    : null,
              ),
            ),
            Icon(
              Icons.arrow_drop_down,
              color: errorRojo ? const Color(0xFFC62828) : null,
            ),
          ],
        ),
      ),
    );
  }
}
