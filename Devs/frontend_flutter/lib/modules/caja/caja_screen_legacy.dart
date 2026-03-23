import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/api/api_client.dart';

enum CajaModo { venta, cuentaCorriente }
enum CajaFiltroVenta { pendientes, suspendidos }

class _PagoLineaDraft {
  _PagoLineaDraft({required this.metodoPago, required this.monto});

  MetodoPago metodoPago;
  double monto;
}

class _OperacionLogPreset {
  _OperacionLogPreset({
    required this.nombre,
    required this.filtroOperacion,
    required this.rango,
    required this.desde,
    required this.hasta,
    required this.orden,
    required this.busqueda,
  });

  final String nombre;
  final String filtroOperacion;
  final String rango;
  final DateTime? desde;
  final DateTime? hasta;
  final String orden;
  final String busqueda;
}

class _ExportCsvPreset {
  _ExportCsvPreset({
    required this.nombre,
    required this.destino,
    required this.rutaPersonalizada,
    required this.nombreArchivoBase,
  });

  final String nombre;
  final String destino;
  final String rutaPersonalizada;
  final String nombreArchivoBase;
}

class _ExportCsvHistoryItem {
  _ExportCsvHistoryItem({
    required this.fecha,
    required this.path,
    required this.destino,
    required this.rutaPersonalizada,
    required this.nombreArchivoBase,
    required this.filas,
  });

  final DateTime fecha;
  final String path;
  final String destino;
  final String rutaPersonalizada;
  final String nombreArchivoBase;
  final int filas;
}

class _ImportStrategyHistoryItem {
  _ImportStrategyHistoryItem({
    required this.fecha,
    required this.origen,
    required this.modo,
    required this.politicaOperacion,
    required this.politicaExportacion,
  });

  final DateTime fecha;
  final String origen;
  final String modo;
  final String politicaOperacion;
  final String politicaExportacion;
}

class PantallaCajaLegacy extends StatefulWidget {
  const PantallaCajaLegacy({super.key});

  @override
  State<PantallaCajaLegacy> createState() => _PantallaCajaLegacyState();
}

class _PantallaCajaLegacyState extends State<PantallaCajaLegacy> {
  final _api = ClienteApi();

  CajaModo _modo = CajaModo.venta;
  CajaFiltroVenta _filtroVenta = CajaFiltroVenta.pendientes;

  bool _cargando = false;
  String? _error;

  // Modo ventas
  final _controlTicketId = TextEditingController();
  final _controlBusquedaOperacionLog = TextEditingController();
  List<TicketMock> _ticketsPendientes = [];
  List<TicketMock> _ticketsSuspendidos = [];
  TicketMock? _ticketSeleccionado;
  String _filtroOperacionLog = 'Todas';
  String _rangoOperacionLog = 'Todo';
  DateTime? _desdeOperacionLog;
  DateTime? _hastaOperacionLog;
  String _ordenOperacionLog = 'Más reciente';
  String _busquedaOperacionLog = '';
  int _limiteOperacionLog = 5;
  final List<_OperacionLogPreset> _presetsOperacionLog = [];
  String? _presetOperacionLogSeleccionado;
  final List<_OperacionLogPreset> _presetsOperacionLogDialog = [];
  String? _presetOperacionLogDialogSeleccionado;
  String _destinoExportCsv = 'Temporal';
  String _rutaPersonalizadaExportCsv = '';
  String _nombreArchivoBaseExportCsv = 'pos_bitacora';
  final List<_ExportCsvPreset> _presetsExportCsv = [];
  String? _presetExportCsvSeleccionado;
  final List<_ExportCsvHistoryItem> _historialExportCsv = [];
  static const _kExportConfigKey = 'caja.export.csv.config.v1';
  static const _kExportPresetsKey = 'caja.export.csv.presets.v1';
  static const _kExportHistoryKey = 'caja.export.csv.history.v1';
  static const _kOperacionPresetsMainKey = 'caja.operacion.presets.main.v1';
  static const _kOperacionPresetsDialogKey = 'caja.operacion.presets.dialog.v1';
  static const _kImportPrefsKey = 'caja.import.prefs.v1';
  String _preferenciaModoImportacion = 'replace';
  String _preferenciaPoliticaOperacion = 'importado';
  String _preferenciaPoliticaExportacion = 'importado';
  bool _usarSiempreEstrategiaImportacion = true;
  DateTime? _ultimaActualizacionConfigImport;
  String _origenUltimaActualizacionConfigImport = 'local';
  final List<_ImportStrategyHistoryItem> _historialEstrategiaImport = [];

  Future<void> _cargarPreferenciasExportCsv() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final configRaw = prefs.getString(_kExportConfigKey);
      final presetsRaw = prefs.getString(_kExportPresetsKey);
      final historyRaw = prefs.getString(_kExportHistoryKey);

      String destino = _destinoExportCsv;
      String ruta = _rutaPersonalizadaExportCsv;
      String nombreBase = _nombreArchivoBaseExportCsv;
      String? presetSeleccionado = _presetExportCsvSeleccionado;
      final presets = <_ExportCsvPreset>[];
      final history = <_ExportCsvHistoryItem>[];

      if (configRaw != null && configRaw.isNotEmpty) {
        final map = jsonDecode(configRaw) as Map<String, dynamic>;
        destino = (map['destino'] as String?) ?? destino;
        ruta = (map['ruta'] as String?) ?? ruta;
        nombreBase = (map['nombre_base'] as String?) ?? nombreBase;
        presetSeleccionado = map['preset_seleccionado'] as String?;
      }

      if (presetsRaw != null && presetsRaw.isNotEmpty) {
        final list = jsonDecode(presetsRaw) as List<dynamic>;
        for (final item in list) {
          final map = item as Map<String, dynamic>;
          presets.add(
            _ExportCsvPreset(
              nombre: (map['nombre'] as String?) ?? '',
              destino: (map['destino'] as String?) ?? 'Temporal',
              rutaPersonalizada: (map['ruta'] as String?) ?? '',
              nombreArchivoBase: (map['nombre_base'] as String?) ?? 'pos_bitacora',
            ),
          );
        }
      }

      if (historyRaw != null && historyRaw.isNotEmpty) {
        final list = jsonDecode(historyRaw) as List<dynamic>;
        for (final item in list) {
          final map = item as Map<String, dynamic>;
          final fechaRaw = map['fecha'] as String?;
          final fecha = fechaRaw == null ? null : DateTime.tryParse(fechaRaw);
          if (fecha == null) continue;
          history.add(
            _ExportCsvHistoryItem(
              fecha: fecha,
              path: (map['path'] as String?) ?? '',
              destino: (map['destino'] as String?) ?? 'Temporal',
              rutaPersonalizada: (map['ruta'] as String?) ?? '',
              nombreArchivoBase: (map['nombre_base'] as String?) ?? 'pos_bitacora',
              filas: (map['filas'] as num?)?.toInt() ?? 0,
            ),
          );
        }
      }

      if (!mounted) return;
      setState(() {
        _destinoExportCsv = destino;
        _rutaPersonalizadaExportCsv = ruta;
        _nombreArchivoBaseExportCsv = nombreBase;
        _presetExportCsvSeleccionado = presetSeleccionado;
        _presetsExportCsv
          ..clear()
          ..addAll(presets.where((p) => p.nombre.trim().isNotEmpty));
        _historialExportCsv
          ..clear()
          ..addAll(history.take(10));
      });
    } catch (_) {
      // Si falla lectura local, continuar con valores por defecto.
    }
  }

  Future<void> _guardarPreferenciasExportCsv() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final config = <String, dynamic>{
        'destino': _destinoExportCsv,
        'ruta': _rutaPersonalizadaExportCsv,
        'nombre_base': _nombreArchivoBaseExportCsv,
        'preset_seleccionado': _presetExportCsvSeleccionado,
      };
      final presets = _presetsExportCsv
          .map(
            (p) => <String, dynamic>{
              'nombre': p.nombre,
              'destino': p.destino,
              'ruta': p.rutaPersonalizada,
              'nombre_base': p.nombreArchivoBase,
            },
          )
          .toList();
      final history = _historialExportCsv
          .take(10)
          .map(
            (h) => <String, dynamic>{
              'fecha': h.fecha.toIso8601String(),
              'path': h.path,
              'destino': h.destino,
              'ruta': h.rutaPersonalizada,
              'nombre_base': h.nombreArchivoBase,
              'filas': h.filas,
            },
          )
          .toList();
      await prefs.setString(_kExportConfigKey, jsonEncode(config));
      await prefs.setString(_kExportPresetsKey, jsonEncode(presets));
      await prefs.setString(_kExportHistoryKey, jsonEncode(history));
    } catch (_) {
      // Fallo de persistencia local no bloquea flujo de UI.
    }
  }

  Future<void> _cargarPreferenciasPresetsOperacion() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final mainRaw = prefs.getString(_kOperacionPresetsMainKey);
      final dialogRaw = prefs.getString(_kOperacionPresetsDialogKey);
      final main = <_OperacionLogPreset>[];
      final dialog = <_OperacionLogPreset>[];

      List<_OperacionLogPreset> parseList(String raw) {
        final list = jsonDecode(raw) as List<dynamic>;
        return list.map((item) {
          final map = item as Map<String, dynamic>;
          final desdeRaw = map['desde'] as String?;
          final hastaRaw = map['hasta'] as String?;
          return _OperacionLogPreset(
            nombre: (map['nombre'] as String?) ?? '',
            filtroOperacion: (map['filtro'] as String?) ?? 'Todas',
            rango: (map['rango'] as String?) ?? 'Todo',
            desde: desdeRaw == null ? null : DateTime.tryParse(desdeRaw),
            hasta: hastaRaw == null ? null : DateTime.tryParse(hastaRaw),
            orden: (map['orden'] as String?) ?? 'Más reciente',
            busqueda: (map['busqueda'] as String?) ?? '',
          );
        }).toList();
      }

      if (mainRaw != null && mainRaw.isNotEmpty) {
        main.addAll(parseList(mainRaw));
      }
      if (dialogRaw != null && dialogRaw.isNotEmpty) {
        dialog.addAll(parseList(dialogRaw));
      }

      if (!mounted) return;
      setState(() {
        _presetsOperacionLog
          ..clear()
          ..addAll(main.where((p) => p.nombre.trim().isNotEmpty));
        _presetsOperacionLogDialog
          ..clear()
          ..addAll(dialog.where((p) => p.nombre.trim().isNotEmpty));
      });
    } catch (_) {
      // Si falla lectura local, continuar con memoria en runtime.
    }
  }

  Future<void> _guardarPreferenciasPresetsOperacion() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      List<Map<String, dynamic>> encodeList(List<_OperacionLogPreset> list) {
        return list
            .map(
              (p) => <String, dynamic>{
                'nombre': p.nombre,
                'filtro': p.filtroOperacion,
                'rango': p.rango,
                'desde': p.desde?.toIso8601String(),
                'hasta': p.hasta?.toIso8601String(),
                'orden': p.orden,
                'busqueda': p.busqueda,
              },
            )
            .toList();
      }

      await prefs.setString(_kOperacionPresetsMainKey, jsonEncode(encodeList(_presetsOperacionLog)));
      await prefs.setString(_kOperacionPresetsDialogKey, jsonEncode(encodeList(_presetsOperacionLogDialog)));
    } catch (_) {
      // Fallo de persistencia local no bloquea flujo de UI.
    }
  }

  Future<void> _cargarPreferenciasImportacion() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_kImportPrefsKey);
      if (raw == null || raw.isEmpty) return;
      final map = jsonDecode(raw) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _preferenciaModoImportacion = (map['modo'] as String?) ?? _preferenciaModoImportacion;
        _preferenciaPoliticaOperacion =
            (map['politica_operacion'] as String?) ?? _preferenciaPoliticaOperacion;
        _preferenciaPoliticaExportacion =
            (map['politica_exportacion'] as String?) ?? _preferenciaPoliticaExportacion;
        _usarSiempreEstrategiaImportacion =
            (map['auto_guardar_estrategia'] as bool?) ?? _usarSiempreEstrategiaImportacion;
        final updatedAtRaw = map['updated_at'] as String?;
        _ultimaActualizacionConfigImport =
            updatedAtRaw == null ? null : DateTime.tryParse(updatedAtRaw);
        _origenUltimaActualizacionConfigImport =
            (map['updated_origin'] as String?) ?? _origenUltimaActualizacionConfigImport;
        _historialEstrategiaImport.clear();
        final rawHistory = map['history'];
        if (rawHistory is List<dynamic>) {
          for (final entry in rawHistory) {
            final h = entry as Map<String, dynamic>;
            final fechaRaw = h['fecha'] as String?;
            final fecha = fechaRaw == null ? null : DateTime.tryParse(fechaRaw);
            if (fecha == null) continue;
            _historialEstrategiaImport.add(
              _ImportStrategyHistoryItem(
                fecha: fecha,
                origen: (h['origen'] as String?) ?? 'local',
                modo: (h['modo'] as String?) ?? 'replace',
                politicaOperacion: (h['politica_operacion'] as String?) ?? 'importado',
                politicaExportacion: (h['politica_exportacion'] as String?) ?? 'importado',
              ),
            );
          }
        }
      });
    } catch (_) {
      // Ignorar fallos y mantener defaults.
    }
  }

  Future<void> _guardarPreferenciasImportacion() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final payload = <String, dynamic>{
        'modo': _preferenciaModoImportacion,
        'politica_operacion': _preferenciaPoliticaOperacion,
        'politica_exportacion': _preferenciaPoliticaExportacion,
        'auto_guardar_estrategia': _usarSiempreEstrategiaImportacion,
        'updated_at': _ultimaActualizacionConfigImport?.toIso8601String(),
        'updated_origin': _origenUltimaActualizacionConfigImport,
        'history': _historialEstrategiaImport
            .take(8)
            .map(
              (h) => <String, dynamic>{
                'fecha': h.fecha.toIso8601String(),
                'origen': h.origen,
                'modo': h.modo,
                'politica_operacion': h.politicaOperacion,
                'politica_exportacion': h.politicaExportacion,
              },
            )
            .toList(),
      };
      await prefs.setString(_kImportPrefsKey, jsonEncode(payload));
    } catch (_) {
      // Persistencia no bloqueante.
    }
  }

  String _formatearFechaHora(DateTime? value) {
    if (value == null) return 'Sin registro';
    final y = value.year.toString().padLeft(4, '0');
    final m = value.month.toString().padLeft(2, '0');
    final d = value.day.toString().padLeft(2, '0');
    final hh = value.hour.toString().padLeft(2, '0');
    final mm = value.minute.toString().padLeft(2, '0');
    final ss = value.second.toString().padLeft(2, '0');
    return '$y-$m-$d $hh:$mm:$ss';
  }

  String _labelOrigenConfigImport(String origin) {
    switch (origin) {
      case 'json_import':
        return 'Importación JSON';
      case 'restore_defaults':
        return 'Restaurar defaults';
      default:
        return 'Configuración local';
    }
  }

  String _labelEstrategiaImport(
    String modo,
    String politicaOperacion,
    String politicaExportacion,
  ) {
    if (modo == 'replace') return 'Reemplazar';
    if (modo == 'merge_new') return 'Merge solo nuevos';
    final op = politicaOperacion == 'importado' ? 'JSON' : 'Local';
    final exp = politicaExportacion == 'importado' ? 'JSON' : 'Local';
    return 'Merge (Op: $op, Exp: $exp)';
  }

  void _registrarCambioEstrategia({
    required String origen,
    required String modo,
    required String politicaOperacion,
    required String politicaExportacion,
  }) {
    _historialEstrategiaImport.insert(
      0,
      _ImportStrategyHistoryItem(
        fecha: DateTime.now(),
        origen: origen,
        modo: modo,
        politicaOperacion: politicaOperacion,
        politicaExportacion: politicaExportacion,
      ),
    );
    if (_historialEstrategiaImport.length > 8) {
      _historialEstrategiaImport.removeRange(8, _historialEstrategiaImport.length);
    }
  }

  String _crearBackupPresetsJson() {
    final payload = <String, dynamic>{
      'version': 1,
      'created_at': DateTime.now().toIso8601String(),
      'operacion_presets_main': _presetsOperacionLog
          .map(
            (p) => <String, dynamic>{
              'nombre': p.nombre,
              'filtro': p.filtroOperacion,
              'rango': p.rango,
              'desde': p.desde?.toIso8601String(),
              'hasta': p.hasta?.toIso8601String(),
              'orden': p.orden,
              'busqueda': p.busqueda,
            },
          )
          .toList(),
      'operacion_presets_dialog': _presetsOperacionLogDialog
          .map(
            (p) => <String, dynamic>{
              'nombre': p.nombre,
              'filtro': p.filtroOperacion,
              'rango': p.rango,
              'desde': p.desde?.toIso8601String(),
              'hasta': p.hasta?.toIso8601String(),
              'orden': p.orden,
              'busqueda': p.busqueda,
            },
          )
          .toList(),
      'export': <String, dynamic>{
        'destino': _destinoExportCsv,
        'ruta': _rutaPersonalizadaExportCsv,
        'nombre_base': _nombreArchivoBaseExportCsv,
        'preset_seleccionado': _presetExportCsvSeleccionado,
      },
      'export_presets': _presetsExportCsv
          .map(
            (p) => <String, dynamic>{
              'nombre': p.nombre,
              'destino': p.destino,
              'ruta': p.rutaPersonalizada,
              'nombre_base': p.nombreArchivoBase,
            },
          )
          .toList(),
    };
    return const JsonEncoder.withIndent('  ').convert(payload);
  }

  List<_OperacionLogPreset> _parseOperacionPresetsList(dynamic raw) {
    final list = raw is List<dynamic> ? raw : const <dynamic>[];
    return list
        .map((item) {
          final map = item as Map<String, dynamic>;
          final nombre = (map['nombre'] as String?) ?? '';
          if (nombre.trim().isEmpty) return null;
          final desdeRaw = map['desde'] as String?;
          final hastaRaw = map['hasta'] as String?;
          return _OperacionLogPreset(
            nombre: nombre,
            filtroOperacion: (map['filtro'] as String?) ?? 'Todas',
            rango: (map['rango'] as String?) ?? 'Todo',
            desde: desdeRaw == null ? null : DateTime.tryParse(desdeRaw),
            hasta: hastaRaw == null ? null : DateTime.tryParse(hastaRaw),
            orden: (map['orden'] as String?) ?? 'Más reciente',
            busqueda: (map['busqueda'] as String?) ?? '',
          );
        })
        .whereType<_OperacionLogPreset>()
        .toList();
  }

  _OperacionLogPreset _crearPresetOperacionLog(String nombre) {
    return _OperacionLogPreset(
      nombre: nombre,
      filtroOperacion: _filtroOperacionLog,
      rango: _rangoOperacionLog,
      desde: _desdeOperacionLog,
      hasta: _hastaOperacionLog,
      orden: _ordenOperacionLog,
      busqueda: _busquedaOperacionLog,
    );
  }

  void _aplicarPresetOperacionLog(_OperacionLogPreset preset) {
    setState(() {
      _filtroOperacionLog = preset.filtroOperacion;
      _rangoOperacionLog = preset.rango;
      _desdeOperacionLog = preset.desde;
      _hastaOperacionLog = preset.hasta;
      _ordenOperacionLog = preset.orden;
      _busquedaOperacionLog = preset.busqueda;
      _limiteOperacionLog = 5;
      _presetOperacionLogSeleccionado = preset.nombre;
    });
    _controlBusquedaOperacionLog.text = preset.busqueda;
  }

  Future<void> _guardarPresetOperacionLogActual() async {
    final nombreCtrl = TextEditingController(text: _presetOperacionLogSeleccionado ?? '');
    final nombre = await showDialog<String>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Guardar preset de filtros'),
          content: TextField(
            controller: nombreCtrl,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: 'Nombre de vista',
              hintText: 'Ej: Auditoría diaria',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(nombreCtrl.text.trim()),
              child: const Text('Guardar'),
            ),
          ],
        );
      },
    );
    nombreCtrl.dispose();

    if (!mounted || nombre == null) return;
    if (nombre.length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('El nombre del preset debe tener al menos 3 caracteres.')),
      );
      return;
    }

    final nuevo = _crearPresetOperacionLog(nombre);
    setState(() {
      final idx = _presetsOperacionLog.indexWhere((p) => p.nombre.toLowerCase() == nombre.toLowerCase());
      if (idx >= 0) {
        _presetsOperacionLog[idx] = nuevo;
      } else {
        _presetsOperacionLog.add(nuevo);
      }
      _presetOperacionLogSeleccionado = nombre;
    });
    await _guardarPreferenciasPresetsOperacion();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Preset "$nombre" guardado.')),
    );
  }

  Future<void> _eliminarPresetOperacionLogSeleccionado() async {
    final nombre = _presetOperacionLogSeleccionado;
    if (nombre == null) return;
    setState(() {
      _presetsOperacionLog.removeWhere((p) => p.nombre == nombre);
      _presetOperacionLogSeleccionado = null;
    });
    await _guardarPreferenciasPresetsOperacion();
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('Preset "$nombre" eliminado.')));
  }

  String _csvEscape(String input) {
    final normalized = input.replaceAll('\r', ' ').replaceAll('\n', ' ');
    if (normalized.contains(',') || normalized.contains('"')) {
      return '"${normalized.replaceAll('"', '""')}"';
    }
    return normalized;
  }

  String _construirBitacoraCsv({
    required List<OperacionComercialLogMock> operaciones,
  }) {
    final header = [
      'operacion_id',
      'fecha',
      'tipo',
      'importe',
      'reintegro_metodo',
      'motivo',
      'detalle',
      'ticket_id',
      'cliente',
    ].join(',');

    final rows = operaciones
        .map(
          (o) => [
            _csvEscape(o.operacionId),
            _csvEscape(o.fecha.toIso8601String()),
            _csvEscape(o.tipo),
            o.importe.toStringAsFixed(2),
            _csvEscape(o.reintegroMetodo),
            _csvEscape(o.motivo),
            _csvEscape(o.detalle),
            o.ticketId.toString(),
            _csvEscape(o.clienteNombre),
          ].join(','),
        )
        .join('\n');

    return '$header\n$rows';
  }

  Future<void> _copiarBitacoraCsv({
    required List<OperacionComercialLogMock> operaciones,
  }) async {
    if (operaciones.isEmpty) return;
    final csv = _construirBitacoraCsv(operaciones: operaciones);
    await Clipboard.setData(ClipboardData(text: csv));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('CSV copiado al portapapeles (${operaciones.length} filas).')),
    );
  }

  Future<void> _guardarBitacoraCsvLocal({
    required List<OperacionComercialLogMock> operaciones,
  }) async {
    if (operaciones.isEmpty) return;
    String destinoSeleccionado = _destinoExportCsv;
    final rutaCtrl = TextEditingController(text: _rutaPersonalizadaExportCsv);
    final nombreArchivoCtrl = TextEditingController(text: _nombreArchivoBaseExportCsv);
    String? presetSeleccionado = _presetExportCsvSeleccionado;
    final confirmar = await showDialog<bool>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            Future<void> guardarPresetExportacion() async {
              final nombreCtrl = TextEditingController(text: presetSeleccionado ?? '');
              final nombrePreset = await showDialog<String>(
                context: context,
                builder: (context) {
                  return AlertDialog(
                    title: const Text('Guardar preset de exportación'),
                    content: TextField(
                      controller: nombreCtrl,
                      autofocus: true,
                      decoration: const InputDecoration(
                        labelText: 'Nombre del preset',
                        hintText: 'Ej: Auditoría escritorio',
                      ),
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Cancelar'),
                      ),
                      FilledButton(
                        onPressed: () => Navigator.of(context).pop(nombreCtrl.text.trim()),
                        child: const Text('Guardar'),
                      ),
                    ],
                  );
                },
              );
              nombreCtrl.dispose();

              if (nombrePreset == null || nombrePreset.isEmpty) return;
              if (nombrePreset.length < 3) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('El nombre del preset debe tener al menos 3 caracteres.')),
                );
                return;
              }

              final nuevo = _ExportCsvPreset(
                nombre: nombrePreset,
                destino: destinoSeleccionado,
                rutaPersonalizada: rutaCtrl.text.trim(),
                nombreArchivoBase: nombreArchivoCtrl.text.trim(),
              );

              setStateDialog(() {
                final idx = _presetsExportCsv.indexWhere(
                  (p) => p.nombre.toLowerCase() == nombrePreset.toLowerCase(),
                );
                if (idx >= 0) {
                  _presetsExportCsv[idx] = nuevo;
                } else {
                  _presetsExportCsv.add(nuevo);
                }
                presetSeleccionado = nombrePreset;
              });
              await _guardarPreferenciasExportCsv();
            }

            Future<void> importarBackupDesdeJson() async {
              final jsonCtrl = TextEditingController();
              final raw = await showDialog<String>(
                context: context,
                builder: (context) {
                  return AlertDialog(
                    title: const Text('Importar configuración JSON'),
                    content: SizedBox(
                      width: 560,
                      child: TextField(
                        controller: jsonCtrl,
                        maxLines: 12,
                        decoration: const InputDecoration(
                          labelText: 'Pega el JSON de respaldo',
                          alignLabelWithHint: true,
                        ),
                      ),
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Cancelar'),
                      ),
                      FilledButton(
                        onPressed: () => Navigator.of(context).pop(jsonCtrl.text.trim()),
                        child: const Text('Importar'),
                      ),
                    ],
                  );
                },
              );
              jsonCtrl.dispose();
              if (raw == null || raw.isEmpty) return;

              try {
                final map = jsonDecode(raw) as Map<String, dynamic>;
                final importMain = _parseOperacionPresetsList(map['operacion_presets_main']);
                final importDialog = _parseOperacionPresetsList(map['operacion_presets_dialog']);
                final exportConfig = (map['export'] as Map<String, dynamic>?) ?? <String, dynamic>{};
                final exportPresetsRaw = map['export_presets'];
                final exportPresetsList = exportPresetsRaw is List<dynamic> ? exportPresetsRaw : const <dynamic>[];
                final importExportPresets = exportPresetsList
                    .map((item) {
                      final p = item as Map<String, dynamic>;
                      final nombre = (p['nombre'] as String?) ?? '';
                      if (nombre.trim().isEmpty) return null;
                      return _ExportCsvPreset(
                        nombre: nombre,
                        destino: (p['destino'] as String?) ?? 'Temporal',
                        rutaPersonalizada: (p['ruta'] as String?) ?? '',
                        nombreArchivoBase: (p['nombre_base'] as String?) ?? 'pos_bitacora',
                      );
                    })
                    .whereType<_ExportCsvPreset>()
                    .toList();

                final nuevoDestino = (exportConfig['destino'] as String?) ?? destinoSeleccionado;
                final nuevaRuta = (exportConfig['ruta'] as String?) ?? rutaCtrl.text.trim();
                final nuevoNombreBase =
                    (exportConfig['nombre_base'] as String?) ?? nombreArchivoCtrl.text.trim();
                final nuevoPresetSeleccionado = exportConfig['preset_seleccionado'] as String?;
                String modoImportacion = _preferenciaModoImportacion;
                String politicaConflictoMergeOperacion = _preferenciaPoliticaOperacion;
                String politicaConflictoMergeExport = _preferenciaPoliticaExportacion;
                bool usarSiempreEstrategia = _usarSiempreEstrategiaImportacion;
                if (!const {'replace', 'merge', 'merge_new'}.contains(modoImportacion)) {
                  modoImportacion = 'replace';
                }
                if (!const {'importado', 'local'}.contains(politicaConflictoMergeOperacion)) {
                  politicaConflictoMergeOperacion = 'importado';
                }
                if (!const {'importado', 'local'}.contains(politicaConflictoMergeExport)) {
                  politicaConflictoMergeExport = 'importado';
                }

                String resumenNombres(List<String> items) {
                  if (items.isEmpty) return '—';
                  final sorted = [...items]..sort();
                  const max = 4;
                  if (sorted.length <= max) return sorted.join(', ');
                  return '${sorted.take(max).join(', ')} (+${sorted.length - max})';
                }

                Map<String, _OperacionLogPreset> indexOperacion(List<_OperacionLogPreset> list) {
                  return {for (final p in list) p.nombre.toLowerCase(): p};
                }

                String firmaOperacion(_OperacionLogPreset p) {
                  return [
                    p.filtroOperacion,
                    p.rango,
                    p.desde?.toIso8601String() ?? '',
                    p.hasta?.toIso8601String() ?? '',
                    p.orden,
                    p.busqueda,
                  ].join('|');
                }

                Map<String, _ExportCsvPreset> indexExport(List<_ExportCsvPreset> list) {
                  return {for (final p in list) p.nombre.toLowerCase(): p};
                }

                String firmaExport(_ExportCsvPreset p) {
                  return [p.destino, p.rutaPersonalizada, p.nombreArchivoBase].join('|');
                }

                final mainActual = indexOperacion(_presetsOperacionLog);
                final mainImport = indexOperacion(importMain);
                final dialogActual = indexOperacion(_presetsOperacionLogDialog);
                final dialogImport = indexOperacion(importDialog);
                final exportActual = indexExport(_presetsExportCsv);
                final exportImport = indexExport(importExportPresets);

                List<String> nuevos(
                  Iterable<String> actuales,
                  Iterable<String> incoming,
                ) {
                  final s = actuales.toSet();
                  return incoming.where((k) => !s.contains(k)).toList();
                }

                List<String> eliminados(
                  Iterable<String> actuales,
                  Iterable<String> incoming,
                ) {
                  final s = incoming.toSet();
                  return actuales.where((k) => !s.contains(k)).toList();
                }

                List<String> actualizadosOperacion(
                  Map<String, _OperacionLogPreset> actual,
                  Map<String, _OperacionLogPreset> incoming,
                ) {
                  final out = <String>[];
                  for (final k in incoming.keys) {
                    if (!actual.containsKey(k)) continue;
                    if (firmaOperacion(actual[k]!) != firmaOperacion(incoming[k]!)) out.add(k);
                  }
                  return out;
                }

                List<String> actualizadosExport(
                  Map<String, _ExportCsvPreset> actual,
                  Map<String, _ExportCsvPreset> incoming,
                ) {
                  final out = <String>[];
                  for (final k in incoming.keys) {
                    if (!actual.containsKey(k)) continue;
                    if (firmaExport(actual[k]!) != firmaExport(incoming[k]!)) out.add(k);
                  }
                  return out;
                }

                final mainNuevos = nuevos(mainActual.keys, mainImport.keys);
                final mainEliminados = eliminados(mainActual.keys, mainImport.keys);
                final mainActualizados = actualizadosOperacion(mainActual, mainImport);
                final dialogNuevos = nuevos(dialogActual.keys, dialogImport.keys);
                final dialogEliminados = eliminados(dialogActual.keys, dialogImport.keys);
                final dialogActualizados = actualizadosOperacion(dialogActual, dialogImport);
                final exportNuevos = nuevos(exportActual.keys, exportImport.keys);
                final exportEliminados = eliminados(exportActual.keys, exportImport.keys);
                final exportActualizados = actualizadosExport(exportActual, exportImport);

                List<_OperacionLogPreset> mergeOperacion(
                  List<_OperacionLogPreset> actual,
                  List<_OperacionLogPreset> incoming,
                  {required bool updateExisting}
                ) {
                  final map = <String, _OperacionLogPreset>{for (final p in actual) p.nombre.toLowerCase(): p};
                  for (final p in incoming) {
                    final key = p.nombre.toLowerCase();
                    if (!map.containsKey(key)) {
                      map[key] = p;
                    } else if (updateExisting) {
                      map[key] = p;
                    }
                  }
                  return map.values.toList();
                }

                List<_ExportCsvPreset> mergeExport(
                  List<_ExportCsvPreset> actual,
                  List<_ExportCsvPreset> incoming,
                  {required bool updateExisting}
                ) {
                  final map = <String, _ExportCsvPreset>{for (final p in actual) p.nombre.toLowerCase(): p};
                  for (final p in incoming) {
                    final key = p.nombre.toLowerCase();
                    if (!map.containsKey(key)) {
                      map[key] = p;
                    } else if (updateExisting) {
                      map[key] = p;
                    }
                  }
                  return map.values.toList();
                }

                final mergedMainImportado =
                    mergeOperacion(_presetsOperacionLog, importMain, updateExisting: true);
                final mergedMainMantenerLocal =
                    mergeOperacion(_presetsOperacionLog, importMain, updateExisting: false);
                final mergedDialogImportado = mergeOperacion(
                  _presetsOperacionLogDialog,
                  importDialog,
                  updateExisting: true,
                );
                final mergedDialogMantenerLocal = mergeOperacion(
                  _presetsOperacionLogDialog,
                  importDialog,
                  updateExisting: false,
                );
                final mergedExportImportado = mergeExport(
                  _presetsExportCsv,
                  importExportPresets,
                  updateExisting: true,
                );
                final mergedExportMantenerLocal = mergeExport(
                  _presetsExportCsv,
                  importExportPresets,
                  updateExisting: false,
                );

                final reemplazoConfirmado = await showDialog<bool>(
                  context: context,
                  builder: (context) {
                    return StatefulBuilder(
                      builder: (context, setStatePreview) {
                        final configCambia = nuevoDestino != _destinoExportCsv ||
                            nuevaRuta != _rutaPersonalizadaExportCsv ||
                            nuevoNombreBase != _nombreArchivoBaseExportCsv ||
                            nuevoPresetSeleccionado != _presetExportCsvSeleccionado;
                        final esReplace = modoImportacion == 'replace';
                        final esMerge = modoImportacion == 'merge';
                        final esMergeSoloNuevos = modoImportacion == 'merge_new';
                        final mergeImportadoOperacion =
                            esMerge && politicaConflictoMergeOperacion == 'importado';
                        final mergeImportadoExport = esMerge && politicaConflictoMergeExport == 'importado';
                        final mainAfterList = esReplace
                            ? importMain
                            : mergeImportadoOperacion
                                ? mergedMainImportado
                                : mergedMainMantenerLocal;
                        final dialogAfterList = esReplace
                            ? importDialog
                            : mergeImportadoOperacion
                                ? mergedDialogImportado
                                : mergedDialogMantenerLocal;
                        final exportAfterList = esReplace
                            ? importExportPresets
                            : mergeImportadoExport
                                ? mergedExportImportado
                                : mergedExportMantenerLocal;
                        final mainAfter = mainAfterList.length;
                        final dialogAfter = dialogAfterList.length;
                        final exportAfter = exportAfterList.length;
                        final mainDelCount = esReplace ? mainEliminados.length : 0;
                        final dialogDelCount = esReplace ? dialogEliminados.length : 0;
                        final exportDelCount = esReplace ? exportEliminados.length : 0;
                        final mainActCount =
                            (esReplace || mergeImportadoOperacion) ? mainActualizados.length : 0;
                        final dialogActCount =
                            (esReplace || mergeImportadoOperacion) ? dialogActualizados.length : 0;
                        final exportActCount =
                            (esReplace || mergeImportadoExport) ? exportActualizados.length : 0;
                        final actionLabel = esReplace
                            ? 'Reemplazar'
                            : esMergeSoloNuevos
                                ? 'Aplicar solo nuevos'
                                : 'Aplicar merge';
                        final estrategiaPersistida = _labelEstrategiaImport(
                          _preferenciaModoImportacion,
                          _preferenciaPoliticaOperacion,
                          _preferenciaPoliticaExportacion,
                        );
                        final estrategiaActualPreview = _labelEstrategiaImport(
                          modoImportacion,
                          politicaConflictoMergeOperacion,
                          politicaConflictoMergeExport,
                        );
                        final estrategiaDifiere = estrategiaPersistida != estrategiaActualPreview;

                        return AlertDialog(
                          title: const Text('Vista previa de importación'),
                          content: SingleChildScrollView(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Wrap(
                                  spacing: 8,
                                  children: [
                                    ChoiceChip(
                                      label: const Text('Reemplazar'),
                                      selected: modoImportacion == 'replace',
                                      onSelected: (_) => setStatePreview(() => modoImportacion = 'replace'),
                                    ),
                                    ChoiceChip(
                                      label: const Text('Merge (sin eliminar)'),
                                      selected: modoImportacion == 'merge',
                                      onSelected: (_) => setStatePreview(() => modoImportacion = 'merge'),
                                    ),
                                    ChoiceChip(
                                      label: const Text('Merge (solo nuevos)'),
                                      selected: modoImportacion == 'merge_new',
                                      onSelected: (_) => setStatePreview(() => modoImportacion = 'merge_new'),
                                    ),
                                  ],
                                ),
                                if (esMerge) ...[
                                  const SizedBox(height: 8),
                                  const Text(
                                    'Política de conflicto - Operaciones',
                                    style: TextStyle(fontWeight: FontWeight.w700),
                                  ),
                                  Wrap(
                                    spacing: 8,
                                    children: [
                                      ChoiceChip(
                                        label: const Text('Conflicto: importar'),
                                        selected: politicaConflictoMergeOperacion == 'importado',
                                        onSelected: (_) =>
                                            setStatePreview(() => politicaConflictoMergeOperacion = 'importado'),
                                      ),
                                      ChoiceChip(
                                        label: const Text('Conflicto: mantener local'),
                                        selected: politicaConflictoMergeOperacion == 'local',
                                        onSelected: (_) =>
                                            setStatePreview(() => politicaConflictoMergeOperacion = 'local'),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  const Text(
                                    'Política de conflicto - Exportación',
                                    style: TextStyle(fontWeight: FontWeight.w700),
                                  ),
                                  Wrap(
                                    spacing: 8,
                                    children: [
                                      ChoiceChip(
                                        label: const Text('Conflicto: importar'),
                                        selected: politicaConflictoMergeExport == 'importado',
                                        onSelected: (_) =>
                                            setStatePreview(() => politicaConflictoMergeExport = 'importado'),
                                      ),
                                      ChoiceChip(
                                        label: const Text('Conflicto: mantener local'),
                                        selected: politicaConflictoMergeExport == 'local',
                                        onSelected: (_) =>
                                            setStatePreview(() => politicaConflictoMergeExport = 'local'),
                                      ),
                                    ],
                                  ),
                                ],
                                const SizedBox(height: 10),
                                Text(
                                  'Presets operación (panel): ${_presetsOperacionLog.length} -> $mainAfter',
                                ),
                                Text(
                                  'Presets operación (diálogo): ${_presetsOperacionLogDialog.length} -> $dialogAfter',
                                ),
                                Text(
                                  'Presets exportación: ${_presetsExportCsv.length} -> $exportAfter',
                                ),
                                const SizedBox(height: 8),
                                const Text(
                                  'Diff presets operación (panel)',
                                  style: TextStyle(fontWeight: FontWeight.w700),
                                ),
                                Text('Nuevos (${mainNuevos.length}): ${resumenNombres(mainNuevos)}'),
                                Text(
                                  'Actualizados ($mainActCount): ${resumenNombres(mainActCount == 0 ? const <String>[] : mainActualizados)}',
                                ),
                                Text(
                                  'Eliminados ($mainDelCount): ${resumenNombres(esReplace ? mainEliminados : const <String>[])}',
                                ),
                                const SizedBox(height: 8),
                                const Text(
                                  'Diff presets operación (diálogo)',
                                  style: TextStyle(fontWeight: FontWeight.w700),
                                ),
                                Text('Nuevos (${dialogNuevos.length}): ${resumenNombres(dialogNuevos)}'),
                                Text(
                                  'Actualizados ($dialogActCount): ${resumenNombres(dialogActCount == 0 ? const <String>[] : dialogActualizados)}',
                                ),
                                Text(
                                  'Eliminados ($dialogDelCount): ${resumenNombres(esReplace ? dialogEliminados : const <String>[])}',
                                ),
                                const SizedBox(height: 8),
                                const Text(
                                  'Diff presets exportación',
                                  style: TextStyle(fontWeight: FontWeight.w700),
                                ),
                                Text('Nuevos (${exportNuevos.length}): ${resumenNombres(exportNuevos)}'),
                                Text(
                                  'Actualizados ($exportActCount): ${resumenNombres(exportActCount == 0 ? const <String>[] : exportActualizados)}',
                                ),
                                Text(
                                  'Eliminados ($exportDelCount): ${resumenNombres(esReplace ? exportEliminados : const <String>[])}',
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  configCambia
                                      ? 'Configuración de exportación: se actualizará.'
                                      : 'Configuración de exportación: sin cambios.',
                                  style: const TextStyle(fontWeight: FontWeight.w600),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  esReplace
                                      ? 'Reemplazar elimina presets locales no presentes en el JSON.'
                                      : esMergeSoloNuevos
                                          ? 'Merge solo nuevos agrega presets que no existen y no modifica existentes.'
                                          : 'Merge aplica política por dominio (Operaciones/Exportación).',
                                ),
                                const SizedBox(height: 8),
                                Card(
                                  color: _usarSiempreEstrategiaImportacion
                                      ? Colors.green.shade50
                                      : Colors.orange.shade50,
                                  child: Padding(
                                    padding: const EdgeInsets.all(8),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.stretch,
                                      children: [
                                        Text(
                                          _usarSiempreEstrategiaImportacion
                                              ? 'Estrategia persistente activa'
                                              : 'Estrategia persistente desactivada',
                                          style: const TextStyle(fontWeight: FontWeight.w700),
                                        ),
                                        const SizedBox(height: 4),
                                        Text('Guardada: $estrategiaPersistida'),
                                        Text(
                                          'Última actualización: ${_formatearFechaHora(_ultimaActualizacionConfigImport)}',
                                        ),
                                        Text(
                                          'Origen: ${_labelOrigenConfigImport(_origenUltimaActualizacionConfigImport)}',
                                        ),
                                        if (_historialEstrategiaImport.isNotEmpty) ...[
                                          const SizedBox(height: 6),
                                          const Text(
                                            'Historial reciente',
                                            style: TextStyle(fontWeight: FontWeight.w700),
                                          ),
                                          const SizedBox(height: 2),
                                          ..._historialEstrategiaImport.take(3).map(
                                                (h) => Text(
                                                  '- ${_formatearFechaHora(h.fecha)} · ${_labelOrigenConfigImport(h.origen)} · ${_labelEstrategiaImport(h.modo, h.politicaOperacion, h.politicaExportacion)}',
                                                  style: const TextStyle(fontSize: 12),
                                                ),
                                              ),
                                          const SizedBox(height: 4),
                                          Align(
                                            alignment: Alignment.centerRight,
                                            child: TextButton.icon(
                                              onPressed: () async {
                                                await showDialog<void>(
                                                  context: context,
                                                  builder: (context) {
                                                    final textoHistorial = _historialEstrategiaImport
                                                        .map(
                                                          (h) =>
                                                              '${_formatearFechaHora(h.fecha)} | ${_labelOrigenConfigImport(h.origen)} | ${_labelEstrategiaImport(h.modo, h.politicaOperacion, h.politicaExportacion)}',
                                                        )
                                                        .join('\n');
                                                    return AlertDialog(
                                                      title: const Text('Historial completo de estrategia'),
                                                      content: SizedBox(
                                                        width: 620,
                                                        child: _historialEstrategiaImport.isEmpty
                                                            ? const Text('Sin historial.')
                                                            : ListView.separated(
                                                                shrinkWrap: true,
                                                                itemCount: _historialEstrategiaImport.length,
                                                                separatorBuilder: (_, __) =>
                                                                    const Divider(height: 1),
                                                                itemBuilder: (context, index) {
                                                                  final h = _historialEstrategiaImport[index];
                                                                  return ListTile(
                                                                    dense: true,
                                                                    title: Text(
                                                                      _labelEstrategiaImport(
                                                                        h.modo,
                                                                        h.politicaOperacion,
                                                                        h.politicaExportacion,
                                                                      ),
                                                                    ),
                                                                    subtitle: Text(
                                                                      '${_formatearFechaHora(h.fecha)} · ${_labelOrigenConfigImport(h.origen)}',
                                                                    ),
                                                                  );
                                                                },
                                                              ),
                                                      ),
                                                      actions: [
                                                        TextButton.icon(
                                                          onPressed: _historialEstrategiaImport.isEmpty
                                                              ? null
                                                              : () async {
                                                                  await Clipboard.setData(
                                                                    ClipboardData(text: textoHistorial),
                                                                  );
                                                                  if (!mounted) return;
                                                                  ScaffoldMessenger.of(context).showSnackBar(
                                                                    const SnackBar(
                                                                      content: Text('Historial copiado.'),
                                                                    ),
                                                                  );
                                                                },
                                                          icon: const Icon(Icons.copy_all_outlined),
                                                          label: const Text('Copiar historial'),
                                                        ),
                                                        FilledButton(
                                                          onPressed: () => Navigator.of(context).pop(),
                                                          child: const Text('Cerrar'),
                                                        ),
                                                      ],
                                                    );
                                                  },
                                                );
                                              },
                                              icon: const Icon(Icons.history_outlined),
                                              label: const Text('Ver historial completo'),
                                            ),
                                          ),
                                        ],
                                        if (estrategiaDifiere) ...[
                                          const SizedBox(height: 2),
                                          Text('Actual en esta preview: $estrategiaActualPreview'),
                                        ],
                                      ],
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 8),
                                SwitchListTile(
                                  dense: true,
                                  contentPadding: EdgeInsets.zero,
                                  value: usarSiempreEstrategia,
                                  onChanged: (v) => setStatePreview(() => usarSiempreEstrategia = v),
                                  title: const Text('Usar siempre esta estrategia'),
                                  subtitle: const Text(
                                    'Si se desactiva, la selección aplica solo a esta importación.',
                                  ),
                                ),
                              ],
                            ),
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.of(context).pop(false),
                              child: const Text('Cancelar'),
                            ),
                            FilledButton(
                              onPressed: () => Navigator.of(context).pop(true),
                              child: Text(actionLabel),
                            ),
                          ],
                        );
                      },
                    );
                  },
                );
                if (reemplazoConfirmado != true) return;

                final esReplace = modoImportacion == 'replace';
                final esMergeSoloNuevos = modoImportacion == 'merge_new';
                final mergeImportadoOperacion =
                    modoImportacion == 'merge' && politicaConflictoMergeOperacion == 'importado';
                final mergeImportadoExport =
                    modoImportacion == 'merge' && politicaConflictoMergeExport == 'importado';
                final finalMain = esReplace
                    ? importMain
                    : mergeImportadoOperacion
                        ? mergedMainImportado
                        : mergedMainMantenerLocal;
                final finalDialog = esReplace
                    ? importDialog
                    : mergeImportadoOperacion
                        ? mergedDialogImportado
                        : mergedDialogMantenerLocal;
                final finalExportPresets = esReplace
                    ? importExportPresets
                    : mergeImportadoExport
                        ? mergedExportImportado
                        : mergedExportMantenerLocal;

                if (!mounted) return;
                setState(() {
                  _presetsOperacionLog
                    ..clear()
                    ..addAll(finalMain);
                  _presetsOperacionLogDialog
                    ..clear()
                    ..addAll(finalDialog);
                  _presetsExportCsv
                    ..clear()
                    ..addAll(finalExportPresets);
                  _destinoExportCsv = nuevoDestino;
                  _rutaPersonalizadaExportCsv = nuevaRuta;
                  _nombreArchivoBaseExportCsv = nuevoNombreBase;
                  _presetExportCsvSeleccionado = nuevoPresetSeleccionado;
                  _usarSiempreEstrategiaImportacion = usarSiempreEstrategia;
                  _ultimaActualizacionConfigImport = DateTime.now();
                  _origenUltimaActualizacionConfigImport = 'json_import';
                  _registrarCambioEstrategia(
                    origen: 'json_import',
                    modo: modoImportacion,
                    politicaOperacion: politicaConflictoMergeOperacion,
                    politicaExportacion: politicaConflictoMergeExport,
                  );
                  if (usarSiempreEstrategia) {
                    _preferenciaModoImportacion = modoImportacion;
                    _preferenciaPoliticaOperacion = politicaConflictoMergeOperacion;
                    _preferenciaPoliticaExportacion = politicaConflictoMergeExport;
                  }
                });

                setStateDialog(() {
                  destinoSeleccionado = _destinoExportCsv;
                  rutaCtrl.text = _rutaPersonalizadaExportCsv;
                  nombreArchivoCtrl.text = _nombreArchivoBaseExportCsv;
                  presetSeleccionado = _presetExportCsvSeleccionado;
                });

                await _guardarPreferenciasPresetsOperacion();
                await _guardarPreferenciasExportCsv();
                await _guardarPreferenciasImportacion();

                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      esReplace
                          ? 'Configuración importada (reemplazo).'
                          : esMergeSoloNuevos
                              ? 'Configuración importada (merge solo nuevos).'
                              : 'Configuración importada (merge: operaciones='
                                  '${mergeImportadoOperacion ? 'JSON' : 'local'}, exportación='
                                  '${mergeImportadoExport ? 'JSON' : 'local'}).',
                    ),
                  ),
                );
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('JSON inválido: $e')),
                );
              }
            }

            return AlertDialog(
              title: const Text('Guardar CSV'),
              content: SizedBox(
                width: 560,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              value: presetSeleccionado,
                              decoration: const InputDecoration(labelText: 'Preset de exportación'),
                              hint: const Text('Seleccionar preset'),
                              items: _presetsExportCsv
                                  .map((p) => DropdownMenuItem(value: p.nombre, child: Text(p.nombre)))
                                  .toList(),
                              onChanged: (v) {
                                if (v == null) return;
                                final preset = _presetsExportCsv.firstWhere((p) => p.nombre == v);
                                setStateDialog(() {
                                  presetSeleccionado = v;
                                  destinoSeleccionado = preset.destino;
                                  rutaCtrl.text = preset.rutaPersonalizada;
                                  nombreArchivoCtrl.text = preset.nombreArchivoBase;
                                });
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          FilledButton.tonalIcon(
                            onPressed: guardarPresetExportacion,
                            icon: const Icon(Icons.save_outlined),
                            label: const Text('Guardar preset'),
                          ),
                          const SizedBox(width: 8),
                          FilledButton.tonalIcon(
                            onPressed: presetSeleccionado == null
                                ? null
                                : () async {
                                    final nombre = presetSeleccionado!;
                                    setStateDialog(() {
                                      _presetsExportCsv.removeWhere((p) => p.nombre == nombre);
                                      presetSeleccionado = null;
                                    });
                                    await _guardarPreferenciasExportCsv();
                                  },
                            icon: const Icon(Icons.delete_outline),
                            label: const Text('Eliminar'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: nombreArchivoCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Nombre base del archivo',
                          hintText: 'Ej: bitacora_caja',
                        ),
                      ),
                      const SizedBox(height: 10),
                      const Text('Selecciona destino de exportación:'),
                      const SizedBox(height: 8),
                      RadioListTile<String>(
                        value: 'Temporal',
                        groupValue: destinoSeleccionado,
                        onChanged: (v) {
                          if (v == null) return;
                          setStateDialog(() => destinoSeleccionado = v);
                        },
                        title: const Text('Temporal del sistema (recomendado)'),
                      ),
                      RadioListTile<String>(
                        value: 'Escritorio',
                        groupValue: destinoSeleccionado,
                        onChanged: (v) {
                          if (v == null) return;
                          setStateDialog(() => destinoSeleccionado = v);
                        },
                        title: const Text('Escritorio'),
                      ),
                      RadioListTile<String>(
                        value: 'Descargas',
                        groupValue: destinoSeleccionado,
                        onChanged: (v) {
                          if (v == null) return;
                          setStateDialog(() => destinoSeleccionado = v);
                        },
                        title: const Text('Descargas'),
                      ),
                      RadioListTile<String>(
                        value: 'Personalizado',
                        groupValue: destinoSeleccionado,
                        onChanged: (v) {
                          if (v == null) return;
                          setStateDialog(() => destinoSeleccionado = v);
                        },
                        title: const Text('Carpeta personalizada'),
                      ),
                      if (destinoSeleccionado == 'Personalizado')
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: TextField(
                            controller: rutaCtrl,
                            decoration: const InputDecoration(
                              labelText: 'Ruta de carpeta',
                              hintText: r'Ej: C:\Temp',
                            ),
                          ),
                        ),
                      const SizedBox(height: 10),
                      if (_historialExportCsv.isNotEmpty)
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            const Text(
                              'Exportaciones recientes',
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                            const SizedBox(height: 6),
                            SizedBox(
                              height: 150,
                              child: ListView.separated(
                                itemCount: _historialExportCsv.length,
                                separatorBuilder: (_, __) => const Divider(height: 1),
                                itemBuilder: (context, index) {
                                  final h = _historialExportCsv[index];
                                  final stamp = h.fecha.toString().substring(0, 16);
                                  return ListTile(
                                    dense: true,
                                    title: Text('${h.nombreArchivoBase} · ${h.filas} filas'),
                                    subtitle: Text('$stamp · ${h.destino}\n${h.path}'),
                                    isThreeLine: true,
                                    trailing: Wrap(
                                      spacing: 8,
                                      children: [
                                        IconButton(
                                          tooltip: 'Copiar ruta',
                                          onPressed: () async {
                                            await Clipboard.setData(ClipboardData(text: h.path));
                                            if (!mounted) return;
                                            ScaffoldMessenger.of(context).showSnackBar(
                                              const SnackBar(content: Text('Ruta copiada.')),
                                            );
                                          },
                                          icon: const Icon(Icons.copy_all_outlined),
                                        ),
                                        IconButton(
                                          tooltip: 'Reutilizar configuración',
                                          onPressed: () {
                                            setStateDialog(() {
                                              destinoSeleccionado = h.destino;
                                              rutaCtrl.text = h.rutaPersonalizada;
                                              nombreArchivoCtrl.text = h.nombreArchivoBase;
                                            });
                                          },
                                          icon: const Icon(Icons.replay_outlined),
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                            ),
                          ],
                        ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        alignment: WrapAlignment.end,
                        children: [
                          FilledButton.tonalIcon(
                            onPressed: () async {
                              final backup = _crearBackupPresetsJson();
                              await Clipboard.setData(ClipboardData(text: backup));
                              if (!mounted) return;
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Backup JSON copiado al portapapeles.')),
                              );
                            },
                            icon: const Icon(Icons.copy_all_outlined),
                            label: const Text('Copiar backup JSON'),
                          ),
                          FilledButton.tonalIcon(
                            onPressed: importarBackupDesdeJson,
                            icon: const Icon(Icons.upload_file_outlined),
                            label: const Text('Importar JSON'),
                          ),
                          FilledButton.tonalIcon(
                            onPressed: () async {
                              final ok = await showDialog<bool>(
                                context: context,
                                builder: (context) => AlertDialog(
                                  title: const Text('Restaurar valores por defecto'),
                                  content: const Text(
                                    'Se eliminarán presets, historial y configuración de exportación actual. ¿Continuar?',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () => Navigator.of(context).pop(false),
                                      child: const Text('Cancelar'),
                                    ),
                                    FilledButton(
                                      onPressed: () => Navigator.of(context).pop(true),
                                      child: const Text('Restaurar'),
                                    ),
                                  ],
                                ),
                              );
                              if (ok != true) return;

                              if (!mounted) return;
                              setState(() {
                                _presetsOperacionLog.clear();
                                _presetsOperacionLogDialog.clear();
                                _presetOperacionLogSeleccionado = null;
                                _presetOperacionLogDialogSeleccionado = null;
                                _busquedaOperacionLog = '';
                                _presetsExportCsv.clear();
                                _historialExportCsv.clear();
                                _destinoExportCsv = 'Temporal';
                                _rutaPersonalizadaExportCsv = '';
                                _nombreArchivoBaseExportCsv = 'pos_bitacora';
                                _presetExportCsvSeleccionado = null;
                                _preferenciaModoImportacion = 'replace';
                                _preferenciaPoliticaOperacion = 'importado';
                                _preferenciaPoliticaExportacion = 'importado';
                                _usarSiempreEstrategiaImportacion = true;
                                _ultimaActualizacionConfigImport = DateTime.now();
                                _origenUltimaActualizacionConfigImport = 'restore_defaults';
                                _registrarCambioEstrategia(
                                  origen: 'restore_defaults',
                                  modo: _preferenciaModoImportacion,
                                  politicaOperacion: _preferenciaPoliticaOperacion,
                                  politicaExportacion: _preferenciaPoliticaExportacion,
                                );
                              });
                              setStateDialog(() {
                                destinoSeleccionado = _destinoExportCsv;
                                rutaCtrl.text = _rutaPersonalizadaExportCsv;
                                nombreArchivoCtrl.text = _nombreArchivoBaseExportCsv;
                                presetSeleccionado = _presetExportCsvSeleccionado;
                              });
                              _controlBusquedaOperacionLog.clear();
                              await _guardarPreferenciasPresetsOperacion();
                              await _guardarPreferenciasExportCsv();
                              await _guardarPreferenciasImportacion();
                              if (!mounted) return;
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Valores por defecto restaurados.')),
                              );
                            },
                            icon: const Icon(Icons.settings_backup_restore_outlined),
                            label: const Text('Restaurar defaults'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(false),
                  child: const Text('Cancelar'),
                ),
                FilledButton(
                  onPressed: () => Navigator.of(context).pop(true),
                  child: const Text('Guardar'),
                ),
              ],
            );
          },
        );
      },
    );
    if (confirmar != true) {
      rutaCtrl.dispose();
      nombreArchivoCtrl.dispose();
      return;
    }

    final rutaPersonalizadaSeleccionada = rutaCtrl.text.trim();
    final nombreArchivoBaseSeleccionado = nombreArchivoCtrl.text.trim();
    setState(() {
      _destinoExportCsv = destinoSeleccionado;
      _rutaPersonalizadaExportCsv = rutaPersonalizadaSeleccionada;
      _nombreArchivoBaseExportCsv = nombreArchivoBaseSeleccionado;
      _presetExportCsvSeleccionado = presetSeleccionado;
    });
    await _guardarPreferenciasExportCsv();

    Directory destino;
    final userProfile = Platform.environment['USERPROFILE'] ?? '';
    switch (destinoSeleccionado) {
      case 'Escritorio':
        destino = userProfile.isNotEmpty
            ? Directory('$userProfile\\Desktop')
            : Directory.systemTemp;
        break;
      case 'Descargas':
        destino = userProfile.isNotEmpty
            ? Directory('$userProfile\\Downloads')
            : Directory.systemTemp;
        break;
      case 'Personalizado':
        final customPath = rutaPersonalizadaSeleccionada;
        if (customPath.isEmpty) {
          rutaCtrl.dispose();
          nombreArchivoCtrl.dispose();
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Debes indicar una carpeta personalizada válida.')),
          );
          return;
        }
        destino = Directory(customPath);
        break;
      default:
        destino = Directory.systemTemp;
    }

    final nombreArchivoBaseLimpio = _nombreArchivoBaseExportCsv
        .trim()
        .replaceAll(RegExp(r'[^a-zA-Z0-9_-]'), '_')
        .replaceAll(RegExp(r'_+'), '_');
    if (nombreArchivoBaseLimpio.isEmpty) {
      rutaCtrl.dispose();
      nombreArchivoCtrl.dispose();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nombre de archivo inválido. Usa letras, números, guion o guion bajo.')),
      );
      return;
    }

    rutaCtrl.dispose();
    nombreArchivoCtrl.dispose();

    try {
      if (!await destino.exists()) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('La carpeta no existe: ${destino.path}')),
        );
        return;
      }
      final csv = _construirBitacoraCsv(operaciones: operaciones);
      final now = DateTime.now();
      final stamp =
          '${now.year.toString().padLeft(4, '0')}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}_${now.hour.toString().padLeft(2, '0')}${now.minute.toString().padLeft(2, '0')}${now.second.toString().padLeft(2, '0')}';
      final path = '${destino.path}\\${nombreArchivoBaseLimpio}_$stamp.csv';
      final file = File(path);
      await file.writeAsString(csv);
      setState(() {
        _historialExportCsv.insert(
          0,
          _ExportCsvHistoryItem(
            fecha: now,
            path: path,
            destino: destinoSeleccionado,
            rutaPersonalizada: rutaPersonalizadaSeleccionada,
            nombreArchivoBase: nombreArchivoBaseLimpio,
            filas: operaciones.length,
          ),
        );
        if (_historialExportCsv.length > 10) {
          _historialExportCsv.removeRange(10, _historialExportCsv.length);
        }
      });
      await _guardarPreferenciasExportCsv();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('CSV guardado en: $path'),
          action: SnackBarAction(
            label: 'Copiar ruta',
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: path));
            },
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo guardar CSV local: $e')),
      );
    }
  }

  // Modo cuenta corriente
  List<ClienteDeudaSummary> _clientesDeuda = [];
  int? _clienteIdSeleccionado;
  List<TicketMock> _ticketsCliente = [];

  @override
  void initState() {
    super.initState();
    _controlBusquedaOperacionLog.text = _busquedaOperacionLog;
    _cargarPreferenciasPresetsOperacion();
    _cargarPreferenciasExportCsv();
    _cargarPreferenciasImportacion();
    _cargar();
  }

  @override
  void dispose() {
    _controlTicketId.dispose();
    _controlBusquedaOperacionLog.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      if (_modo == CajaModo.venta) {
        _ticketsPendientes = await _api.listarTicketsPendientesVenta();
        _ticketsSuspendidos = await _api.listarTicketsSuspendidosVenta();
        _ticketSeleccionado = null;
      } else {
        _clientesDeuda = await _api.listarClientesConDeuda();
        _clienteIdSeleccionado = _clientesDeuda.isNotEmpty ? _clientesDeuda.first.clienteId : null;
        if (_clienteIdSeleccionado != null) {
          _ticketsCliente = await _api.listarTicketsPendientesCliente(_clienteIdSeleccionado!);
        } else {
          _ticketsCliente = [];
        }
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  double get _totalPendienteVentas =>
      _ticketsPendientes.fold<double>(0, (acc, t) => acc + t.saldoPendiente);

  double get _totalSuspendidaVentas =>
      _ticketsSuspendidos.fold<double>(0, (acc, t) => acc + t.saldoPendiente);

  double get _deudaTotalCliente => _ticketsCliente.fold<double>(0, (acc, t) => acc + t.saldoPendiente);

  String _estadoLabel(TicketEstado e) {
    switch (e) {
      case TicketEstado.pendiente:
        return 'Pendiente';
      case TicketEstado.suspendida:
        return 'Suspendida';
      case TicketEstado.pagada:
        return 'Pagada';
      case TicketEstado.fiada:
        return 'Fiada';
      case TicketEstado.anulada:
        return 'Anulada';
    }
  }

  Future<void> _abrirPopupPagoTicket(TicketMock ticket) async {
    await showDialog<void>(
      context: context,
      builder: (context) {
        final total = ticket.saldoPendiente;

        final lineas = <_PagoLineaDraft>[
          _PagoLineaDraft(metodoPago: MetodoPago.efectivo, monto: total),
        ];

        return StatefulBuilder(
          builder: (context, setStateDialog) {
            final inmediato = lineas
                .where((l) => l.metodoPago != MetodoPago.cuentaCorriente)
                .fold<double>(0.0, (acc, l) => acc + l.monto);
            final saldoFiada = (total - inmediato).clamp(0.0, total);
            final cuentaCorrienteMonto = lineas
                .where((l) => l.metodoPago == MetodoPago.cuentaCorriente)
                .fold<double>(0.0, (acc, l) => acc + l.monto);

            return AlertDialog(
              title: Text('Pagar ticket #${ticket.ticketId}'),
              content: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Total pendiente: S/ ${total.toStringAsFixed(2)}'),
                    const SizedBox(height: 10),
                    const SizedBox(height: 10),
                    Text(
                      'Pagos combinados: la suma de métodos excepto `Cuenta corriente` se considera pago inmediato. Si no cubre el total, el remanente pasa a `FIADA`. Si ingresas `Cuenta corriente`, su monto debe coincidir con el saldo a `FIADA`.',
                      style: const TextStyle(color: Colors.black54, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 12),
                    ...List.generate(lineas.length, (i) {
                      final l = lineas[i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 10),
                        child: Padding(
                          padding: const EdgeInsets.all(10),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: DropdownButtonFormField<MetodoPago>(
                                      value: l.metodoPago,
                                      decoration: const InputDecoration(labelText: 'Método de pago'),
                                      items: const [
                                        DropdownMenuItem(value: MetodoPago.efectivo, child: Text('Efectivo')),
                                        DropdownMenuItem(value: MetodoPago.tarjetaCredito, child: Text('Tarjeta crédito')),
                                        DropdownMenuItem(value: MetodoPago.transferencia, child: Text('Transferencia')),
                                        DropdownMenuItem(value: MetodoPago.cuentaCorriente, child: Text('Cuenta corriente')),
                                      ],
                                      onChanged: (v) {
                                        if (v == null) return;
                                        setStateDialog(() => l.metodoPago = v);
                                      },
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  IconButton(
                                    tooltip: 'Quitar línea',
                                    onPressed: lineas.length <= 1 ? null : () => setStateDialog(() => lineas.removeAt(i)),
                                    icon: const Icon(Icons.delete_outline),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              TextFormField(
                                initialValue: l.monto.toStringAsFixed(2),
                                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                decoration: InputDecoration(
                                  labelText: 'Monto',
                                  prefixText: 'S/ ',
                                ),
                                onChanged: (v) {
                                  final parsed = double.tryParse(v.replaceAll(',', '.'));
                                  if (parsed == null) return;
                                  setStateDialog(() => l.monto = parsed);
                                },
                              ),
                              if (l.metodoPago == MetodoPago.cuentaCorriente)
                                const Padding(
                                  padding: EdgeInsets.only(top: 6),
                                  child: Text(
                                    '`Cuenta corriente` no cuenta como pago inmediato en este mock.',
                                    style: TextStyle(color: Colors.black54, fontWeight: FontWeight.w600),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      );
                    }),
                    FilledButton.tonalIcon(
                      onPressed: () {
                        setStateDialog(() => lineas.add(_PagoLineaDraft(metodoPago: MetodoPago.tarjetaCredito, monto: 0)));
                      },
                      icon: const Icon(Icons.add),
                      label: const Text('Agregar método'),
                    ),
                    const SizedBox(height: 12),
                    Text('Pago inmediato: S/ ${inmediato.toStringAsFixed(2)}'),
                    Text('Saldo a `FIADA`: S/ ${saldoFiada.toStringAsFixed(2)}'),
                    if (cuentaCorrienteMonto > 0.0001) Text('Cuenta corriente ingresada: S/ ${cuentaCorrienteMonto.toStringAsFixed(2)}'),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancelar'),
                ),
                ElevatedButton.icon(
                  onPressed: () async {
                    try {
                      final pagos = lineas
                          .where((l) => l.monto > 0.0001)
                          .map((l) => PagoLineaMock(metodoPago: l.metodoPago, monto: l.monto))
                          .toList();

                      if (pagos.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Debe ingresar al menos un monto > 0.')),
                        );
                        return;
                      }

                      final inmediatoLocal = pagos
                          .where((p) => p.metodoPago != MetodoPago.cuentaCorriente)
                          .fold<double>(0.0, (acc, p) => acc + p.monto);

                      final cuentaCorrienteLocal = pagos
                          .where((p) => p.metodoPago == MetodoPago.cuentaCorriente)
                          .fold<double>(0.0, (acc, p) => acc + p.monto);

                      if (inmediatoLocal - total > 0.0001) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('La suma del pago inmediato excede el total.')),
                        );
                        return;
                      }

                      final saldoFiadaLocal = (total - inmediatoLocal).clamp(0.0, total);
                      if (cuentaCorrienteLocal > 0.0001 &&
                          (saldoFiadaLocal - cuentaCorrienteLocal).abs() > 0.0001) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Cuenta corriente debe coincidir con el saldo a FIADA. Saldo: ${saldoFiadaLocal.toStringAsFixed(2)}',
                            ),
                          ),
                        );
                        return;
                      }

                      await _api.pagarTicketVentaCombinado(
                        ticketId: ticket.ticketId,
                        pagos: pagos,
                      );

                      if (!mounted) return;
                      Navigator.of(context).pop();

                      final pagoParcial = inmediatoLocal < total;
                      if (pagoParcial) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Pago parcial registrado. Saldo a FIADA: S/ ${saldoFiadaLocal.toStringAsFixed(2)}',
                            ),
                          ),
                        );
                      }
                      await _cargar();
                    } catch (e) {
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Error al pagar: $e')),
                      );
                    }
                  },
                  icon: const Icon(Icons.check),
                  label: const Text('Confirmar'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _abrirPopupPagoCuentaCorriente() async {
    final clienteId = _clienteIdSeleccionado;
    if (clienteId == null) return;
    final deuda = _deudaTotalCliente;
    double monto = deuda;
    MetodoPago metodo = MetodoPago.efectivo;

    await showDialog<void>(
      context: context,
      builder: (context) {
        final _montoCtrl = TextEditingController(text: deuda.toStringAsFixed(2));
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: Text('Registrar pago (cliente #$clienteId)'),
              content: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Deuda total pendiente: S/ ${deuda.toStringAsFixed(2)}'),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<MetodoPago>(
                      value: metodo,
                      decoration: const InputDecoration(
                        labelText: 'Método de pago',
                      ),
                      items: const [
                        DropdownMenuItem(value: MetodoPago.efectivo, child: Text('Efectivo')),
                        DropdownMenuItem(value: MetodoPago.tarjetaCredito, child: Text('Tarjeta crédito')),
                        DropdownMenuItem(value: MetodoPago.transferencia, child: Text('Transferencia')),
                      ],
                      onChanged: (v) {
                        if (v == null) return;
                        setStateDialog(() => metodo = v);
                      },
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      controller: _montoCtrl,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Monto a pagar',
                        prefixText: 'S/ ',
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancelar'),
                ),
                ElevatedButton.icon(
                  onPressed: () async {
                    final raw = _montoCtrl.text.replaceAll(',', '.');
                    monto = double.tryParse(raw) ?? 0;
                    if (monto <= 0) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Monto inválido.')),
                      );
                      return;
                    }
                    if (monto > deuda) {
                      // Aceptamos pago parcial pero no exceder el monto pendiente.
                      monto = deuda;
                    }
                    try {
                      await _api.aplicarPagoCuentaCorriente(
                        clienteId: clienteId,
                        metodoPago: metodo,
                        monto: monto,
                      );
                      if (!mounted) return;
                      Navigator.of(context).pop();
                      await _cargar();
                    } catch (e) {
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Error al registrar pago: $e')),
                      );
                    }
                  },
                  icon: const Icon(Icons.check),
                  label: const Text('Confirmar'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Widget _buildModoVenta() {
    final isDesktop = MediaQuery.of(context).size.width >= 1100;
    final list = _filtroVenta == CajaFiltroVenta.pendientes ? _ticketsPendientes : _ticketsSuspendidos;
    return isDesktop
        ? Row(
            children: [
              Expanded(
                flex: 3,
                child: Card(
                  margin: const EdgeInsets.all(12),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                'Cobros por venta',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                              ),
                            ),
                            const SizedBox(width: 12),
                            FilledButton.tonal(
                              onPressed: _cargando ? null : _cargar,
                              child: const Text('Actualizar'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        ToggleButtons(
                          isSelected: [
                            _filtroVenta == CajaFiltroVenta.pendientes,
                            _filtroVenta == CajaFiltroVenta.suspendidos,
                          ],
                          onPressed: (index) {
                            setState(() {
                              _filtroVenta = index == 0 ? CajaFiltroVenta.pendientes : CajaFiltroVenta.suspendidos;
                              _ticketSeleccionado = null;
                            });
                          },
                          children: const [
                            Padding(
                              padding: EdgeInsets.symmetric(horizontal: 16),
                              child: Text('Pendientes'),
                            ),
                            Padding(
                              padding: EdgeInsets.symmetric(horizontal: 16),
                              child: Text('Suspendidos'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 12,
                          children: [
                            Chip(label: Text('Tickets: ${list.length}')),
                            Chip(
                              label: Text(
                                _filtroVenta == CajaFiltroVenta.pendientes
                                    ? 'Pendiente: S/ ${_totalPendienteVentas.toStringAsFixed(2)}'
                                    : 'Suspendida: S/ ${_totalSuspendidaVentas.toStringAsFixed(2)}',
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _controlTicketId,
                                keyboardType: const TextInputType.numberWithOptions(decimal: false),
                                decoration: const InputDecoration(
                                  labelText: 'Escanear / ingresar ticket ID',
                                  prefixIcon: Icon(Icons.qr_code_scanner),
                                ),
                                onSubmitted: (v) async {
                                  final id = int.tryParse(v.trim());
                                  if (id == null) return;
                                  final ticket = await _api.obtenerTicket(id);
                                  if (ticket == null) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text('Ticket no encontrado')),
                                    );
                                    return;
                                  }
                                  setState(() {
                                    _ticketSeleccionado = ticket;
                                  });
                                },
                              ),
                            ),
                            const SizedBox(width: 10),
                            IconButton(
                              onPressed: () async {
                                final id = int.tryParse(_controlTicketId.text.trim());
                                if (id == null) return;
                                final ticket = await _api.obtenerTicket(id);
                                if (ticket == null) return;
                                setState(() => _ticketSeleccionado = ticket);
                              },
                              icon: const Icon(Icons.search),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Expanded(
                          child: ListView.separated(
                            itemCount: list.length,
                            separatorBuilder: (_, __) => const Divider(height: 1),
                            itemBuilder: (context, index) {
                              final t = list[index];
                              final selected = _ticketSeleccionado?.ticketId == t.ticketId;
                              return ListTile(
                                selected: selected,
                                title: Text('Ticket #${t.ticketId}'),
                                subtitle: Text('${t.clienteNombre} · ${t.documento}'),
                                trailing: Text('S/ ${t.saldoPendiente.toStringAsFixed(2)}'),
                                onTap: () {
                                  setState(() {
                                    _ticketSeleccionado = t;
                                    _filtroOperacionLog = 'Todas';
                                    _rangoOperacionLog = 'Todo';
                                    _desdeOperacionLog = null;
                                    _hastaOperacionLog = null;
                                    _ordenOperacionLog = 'Más reciente';
                                    _busquedaOperacionLog = '';
                                    _limiteOperacionLog = 5;
                                    _presetOperacionLogSeleccionado = null;
                                  });
                                  _controlBusquedaOperacionLog.clear();
                                },
                              );
                            },
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: _buildDetalleTicketVenta(),
              ),
            ],
          )
        : Column(
            children: [
              Card(
                margin: const EdgeInsets.all(12),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Cobros por venta',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 8),
                      ToggleButtons(
                        isSelected: [
                          _filtroVenta == CajaFiltroVenta.pendientes,
                          _filtroVenta == CajaFiltroVenta.suspendidos,
                        ],
                        onPressed: (index) {
                          setState(() {
                            _filtroVenta = index == 0 ? CajaFiltroVenta.pendientes : CajaFiltroVenta.suspendidos;
                            _ticketSeleccionado = null;
                          });
                        },
                        children: const [
                          Padding(
                            padding: EdgeInsets.symmetric(horizontal: 16),
                            child: Text('Pendientes'),
                          ),
                          Padding(
                            padding: EdgeInsets.symmetric(horizontal: 16),
                            child: Text('Suspendidos'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 12,
                        children: [
                          Chip(label: Text('Tickets: ${list.length}')),
                          Chip(
                            label: Text(
                              _filtroVenta == CajaFiltroVenta.pendientes
                                  ? 'Pendiente: S/ ${_totalPendienteVentas.toStringAsFixed(2)}'
                                  : 'Suspendida: S/ ${_totalSuspendidaVentas.toStringAsFixed(2)}',
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _controlTicketId,
                        keyboardType: const TextInputType.numberWithOptions(decimal: false),
                        decoration: const InputDecoration(
                          labelText: 'Escanear / ingresar ticket ID',
                          prefixIcon: Icon(Icons.qr_code_scanner),
                        ),
                        onSubmitted: (v) async {
                          final id = int.tryParse(v.trim());
                          if (id == null) return;
                          final ticket = await _api.obtenerTicket(id);
                          if (ticket == null) return;
                          setState(() {
                            _ticketSeleccionado = ticket;
                          });
                        },
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        height: 280,
                        child: ListView.separated(
                          itemCount: list.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final t = list[index];
                            final selected = _ticketSeleccionado?.ticketId == t.ticketId;
                            return ListTile(
                              selected: selected,
                              title: Text('Ticket #${t.ticketId}'),
                              subtitle: Text('${t.clienteNombre} · ${t.documento}'),
                              trailing: Text('S/ ${t.saldoPendiente.toStringAsFixed(2)}'),
                              onTap: () {
                                setState(() {
                                  _ticketSeleccionado = t;
                                  _filtroOperacionLog = 'Todas';
                                  _rangoOperacionLog = 'Todo';
                                  _desdeOperacionLog = null;
                                  _hastaOperacionLog = null;
                                  _ordenOperacionLog = 'Más reciente';
                                  _busquedaOperacionLog = '';
                                  _limiteOperacionLog = 5;
                                  _presetOperacionLogSeleccionado = null;
                                });
                                _controlBusquedaOperacionLog.clear();
                              },
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Expanded(child: _buildDetalleTicketVenta()),
            ],
          );
  }

  Widget _buildDetalleTicketVenta() {
    final t = _ticketSeleccionado;
    return Card(
      margin: const EdgeInsets.all(12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: t == null
            ? Center(
                child: Text(
                  'Seleccione un ticket para ver detalle.',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Detalle ticket #${t.ticketId}',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                        ),
                      ),
                      Chip(label: Text(_estadoLabel(t.estado))),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text('${t.clienteNombre} · ${t.documento}'),
                  const SizedBox(height: 8),
                  Text('Fecha: ${t.fecha.toString().substring(0, 16)}'),
                  const SizedBox(height: 12),
                  Expanded(
                    child: SingleChildScrollView(
                      child: DataTable(
                        columns: const [
                          DataColumn(label: Text('Producto')),
                          DataColumn(label: Text('Cant.')),
                          DataColumn(label: Text('Precio')),
                          DataColumn(label: Text('Subtotal')),
                        ],
                        rows: t.items
                            .map(
                              (it) => DataRow(
                                cells: [
                                  DataCell(Text(it.nombre)),
                                  DataCell(Text(it.cantidad.toStringAsFixed(0))),
                                  DataCell(Text('S/ ${it.precioUnitario.toStringAsFixed(2)}')),
                                  DataCell(Text('S/ ${it.subtotal.toStringAsFixed(2)}')),
                                ],
                              ),
                            )
                            .toList(),
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'TOTAL: S/ ${t.saldoPendiente.toStringAsFixed(2)}',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 12,
                    runSpacing: 8,
                    children: [
                      if (t.estado == TicketEstado.pendiente)
                        FilledButton.icon(
                          onPressed: () async {
                            await _abrirPopupPagoTicket(t);
                          },
                          icon: const Icon(Icons.payment),
                          label: const Text('Pagar'),
                        ),
                      if (t.estado == TicketEstado.pendiente)
                        FilledButton.tonalIcon(
                          onPressed: () async {
                            await _suspenderTicket(t);
                          },
                          icon: const Icon(Icons.pause_circle_outline),
                          label: const Text('Suspender'),
                        ),
                      if (t.estado == TicketEstado.suspendida)
                        FilledButton.tonalIcon(
                          onPressed: () async {
                            await _reanudarTicket(t);
                          },
                          icon: const Icon(Icons.play_circle_outline),
                          label: const Text('Reanudar'),
                        ),
                      if (t.estado == TicketEstado.fiada)
                        FilledButton.tonalIcon(
                          onPressed: () async {
                            await _abrirPopupNotaCredito(t);
                          },
                          icon: const Icon(Icons.money_off_csred),
                          label: const Text('Nota de crédito'),
                        ),
                      if (t.estado == TicketEstado.fiada)
                        FilledButton.tonalIcon(
                          onPressed: () async {
                            setState(() => _modo = CajaModo.cuentaCorriente);
                            await _cargar();
                          },
                          icon: const Icon(Icons.account_balance_wallet_outlined),
                          label: const Text('Cobrar deuda'),
                        ),
                      if (t.estado != TicketEstado.anulada)
                        FilledButton.tonalIcon(
                          onPressed: () async {
                            await _anularTicketOperacion(t);
                          },
                          icon: const Icon(Icons.delete_forever),
                          label: const Text('Anular'),
                        ),
                      if (t.estado != TicketEstado.anulada)
                        FilledButton.tonalIcon(
                          onPressed: () async {
                            await _abrirOperacionesComercialesDialog(ticketIdPrefill: t.ticketId);
                          },
                          icon: const Icon(Icons.search),
                          label: const Text('Operaciones'),
                        ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final tipo in const [
                        'Todas',
                        'Devolución',
                        'Cambio',
                        'Nota de crédito',
                        'Nota de débito',
                        'Anulación',
                      ])
                        ChoiceChip(
                          label: Text(tipo),
                          selected: _filtroOperacionLog == tipo,
                          onSelected: (_) => setState(() {
                            _filtroOperacionLog = tipo;
                            _limiteOperacionLog = 5;
                          }),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final rango in const ['Todo', 'Hoy', '7 días', '30 días'])
                        ChoiceChip(
                          label: Text(rango),
                          selected: _rangoOperacionLog == rango,
                          onSelected: (_) => setState(() {
                            _rangoOperacionLog = rango;
                            _limiteOperacionLog = 5;
                          }),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.tonalIcon(
                          onPressed: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: _desdeOperacionLog ?? DateTime.now(),
                              firstDate: DateTime(2020),
                              lastDate: DateTime.now().add(const Duration(days: 365)),
                            );
                            if (picked == null) return;
                            setState(() {
                              _desdeOperacionLog = DateTime(picked.year, picked.month, picked.day);
                              _limiteOperacionLog = 5;
                            });
                          },
                          icon: const Icon(Icons.date_range),
                          label: Text(
                            _desdeOperacionLog == null
                                ? 'Desde'
                                : 'Desde: ${_desdeOperacionLog!.toString().substring(0, 10)}',
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: FilledButton.tonalIcon(
                          onPressed: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: _hastaOperacionLog ?? DateTime.now(),
                              firstDate: DateTime(2020),
                              lastDate: DateTime.now().add(const Duration(days: 365)),
                            );
                            if (picked == null) return;
                            setState(() {
                              _hastaOperacionLog = DateTime(picked.year, picked.month, picked.day, 23, 59, 59);
                              _limiteOperacionLog = 5;
                            });
                          },
                          icon: const Icon(Icons.event),
                          label: Text(
                            _hastaOperacionLog == null
                                ? 'Hasta'
                                : 'Hasta: ${_hastaOperacionLog!.toString().substring(0, 10)}',
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _ordenOperacionLog,
                          decoration: const InputDecoration(labelText: 'Orden'),
                          items: const [
                            DropdownMenuItem(value: 'Más reciente', child: Text('Más reciente')),
                            DropdownMenuItem(value: 'Más antiguo', child: Text('Más antiguo')),
                            DropdownMenuItem(value: 'Importe (mayor)', child: Text('Importe (mayor)')),
                            DropdownMenuItem(value: 'Importe (menor)', child: Text('Importe (menor)')),
                          ],
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => _ordenOperacionLog = v);
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.tonal(
                        onPressed: () {
                          setState(() {
                            _desdeOperacionLog = null;
                            _hastaOperacionLog = null;
                            _limiteOperacionLog = 5;
                          });
                        },
                        child: const Text('Limpiar fechas'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _controlBusquedaOperacionLog,
                    decoration: const InputDecoration(
                      labelText: 'Buscar en operaciones del ticket',
                      prefixIcon: Icon(Icons.search),
                    ),
                    onChanged: (v) => setState(() {
                      _busquedaOperacionLog = v.trim().toLowerCase();
                      _limiteOperacionLog = 5;
                    }),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _presetOperacionLogSeleccionado,
                          decoration: const InputDecoration(labelText: 'Vista guardada'),
                          hint: const Text('Seleccionar preset'),
                          items: _presetsOperacionLog
                              .map((p) => DropdownMenuItem(value: p.nombre, child: Text(p.nombre)))
                              .toList(),
                          onChanged: (v) {
                            if (v == null) return;
                            final preset = _presetsOperacionLog.firstWhere((p) => p.nombre == v);
                            _aplicarPresetOperacionLog(preset);
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.tonalIcon(
                        onPressed: _guardarPresetOperacionLogActual,
                        icon: const Icon(Icons.save_outlined),
                        label: const Text('Guardar vista'),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.tonalIcon(
                        onPressed: _presetOperacionLogSeleccionado == null
                            ? null
                            : _eliminarPresetOperacionLogSeleccionado,
                        icon: const Icon(Icons.delete_outline),
                        label: const Text('Eliminar'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  FutureBuilder<List<OperacionComercialLogMock>>(
                    future: _api.listarOperacionesComercialesRecientes(
                      ticketId: t.ticketId,
                      tipo: _filtroOperacionLog,
                      limit: 50,
                    ),
                    builder: (context, snap) {
                      if (!snap.hasData || snap.data!.isEmpty) {
                        return const SizedBox.shrink();
                      }
                      final now = DateTime.now();
                      bool dentroRango(OperacionComercialLogMock o) {
                        final diff = now.difference(o.fecha);
                        switch (_rangoOperacionLog) {
                          case 'Hoy':
                            return o.fecha.year == now.year &&
                                o.fecha.month == now.month &&
                                o.fecha.day == now.day;
                          case '7 días':
                            return diff.inDays < 7;
                          case '30 días':
                            return diff.inDays < 30;
                          default:
                            return true;
                        }
                      }
                      bool dentroRangoCustom(OperacionComercialLogMock o) {
                        if (_desdeOperacionLog != null && o.fecha.isBefore(_desdeOperacionLog!)) return false;
                        if (_hastaOperacionLog != null && o.fecha.isAfter(_hastaOperacionLog!)) return false;
                        return true;
                      }
                      final opsRaw = snap.data!;
                      final opsRango = opsRaw.where(dentroRango).where(dentroRangoCustom).toList();
                      final opsFiltradas = _busquedaOperacionLog.isEmpty
                          ? opsRango
                          : opsRango.where((o) {
                              final q = _busquedaOperacionLog;
                              return o.tipo.toLowerCase().contains(q) ||
                                  o.motivo.toLowerCase().contains(q) ||
                                  o.detalle.toLowerCase().contains(q) ||
                                  o.reintegroMetodo.toLowerCase().contains(q);
                            }).toList();
                      opsFiltradas.sort((a, b) {
                        switch (_ordenOperacionLog) {
                          case 'Más antiguo':
                            return a.fecha.compareTo(b.fecha);
                          case 'Importe (mayor)':
                            return b.importe.compareTo(a.importe);
                          case 'Importe (menor)':
                            return a.importe.compareTo(b.importe);
                          default:
                            return b.fecha.compareTo(a.fecha);
                        }
                      });
                      final ops = opsFiltradas.take(_limiteOperacionLog).toList();
                      return Card(
                        color: Colors.blueGrey.shade50,
                        child: Padding(
                          padding: const EdgeInsets.all(10),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              const Text(
                                'Operaciones recientes (ticket)',
                                style: TextStyle(fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: 6),
                              Wrap(
                                spacing: 8,
                                children: [
                                  Chip(label: Text('Coincidencias: ${opsFiltradas.length}')),
                                  Chip(label: Text('Mostrando: ${ops.length}')),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Align(
                                alignment: Alignment.centerRight,
                                child: Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: [
                                    FilledButton.tonalIcon(
                                      onPressed: opsFiltradas.isEmpty
                                          ? null
                                          : () async {
                                              await _guardarBitacoraCsvLocal(operaciones: opsFiltradas);
                                            },
                                      icon: const Icon(Icons.download_outlined),
                                      label: const Text('Guardar CSV'),
                                    ),
                                    FilledButton.tonalIcon(
                                      onPressed: opsFiltradas.isEmpty
                                          ? null
                                          : () async {
                                              await _copiarBitacoraCsv(operaciones: opsFiltradas);
                                            },
                                      icon: const Icon(Icons.file_copy_outlined),
                                      label: const Text('Copiar CSV'),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 6),
                              if (ops.isEmpty)
                                const Text(
                                  'Sin resultados para los filtros aplicados.',
                                  style: TextStyle(fontWeight: FontWeight.w600),
                                ),
                              ...ops.map(
                                (o) => Card(
                                  margin: const EdgeInsets.symmetric(vertical: 3),
                                  child: ExpansionTile(
                                    dense: true,
                                    tilePadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
                                    title: Text('${o.tipo} · S/ ${o.importe.toStringAsFixed(2)}'),
                                    subtitle: Text(
                                      '${o.reintegroMetodo} · ${o.motivo} · ${o.fecha.toString().substring(0, 16)}',
                                    ),
                                    children: [
                                      Padding(
                                        padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.stretch,
                                          children: [
                                            Text('Detalle: ${o.detalle}'),
                                            const SizedBox(height: 4),
                                            Text('Operación ID: ${o.operacionId}'),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              if (opsFiltradas.length > ops.length)
                                Align(
                                  alignment: Alignment.centerRight,
                                  child: TextButton.icon(
                                    onPressed: () {
                                      setState(() {
                                        _limiteOperacionLog = (_limiteOperacionLog + 5).clamp(5, 100);
                                      });
                                    },
                                    icon: const Icon(Icons.expand_more),
                                    label: const Text('Ver más'),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
      ),
    );
  }

  Widget _buildModoCuentaCorriente() {
    final isDesktop = MediaQuery.of(context).size.width >= 1100;
    return isDesktop
        ? Row(
            children: [
              Expanded(
                flex: 3,
                child: Card(
                  margin: const EdgeInsets.all(12),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                'Cobros de cuenta corriente',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                              ),
                            ),
                            const SizedBox(width: 12),
                            FilledButton.tonal(
                              onPressed: _cargando ? null : _cargar,
                              child: const Text('Actualizar'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 12,
                          children: [
                            Chip(label: Text('Clientes: ${_clientesDeuda.length}')),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Expanded(
                          child: ListView.separated(
                            itemCount: _clientesDeuda.length,
                            separatorBuilder: (_, __) => const Divider(height: 1),
                            itemBuilder: (context, index) {
                              final c = _clientesDeuda[index];
                              final selected = _clienteIdSeleccionado == c.clienteId;
                              return ListTile(
                                selected: selected,
                                title: Text(c.clienteNombre),
                                subtitle: Text('DNI: ${c.documento} · Tickets: ${c.ticketsPendientes}'),
                                trailing: Text('S/ ${c.deudaTotal.toStringAsFixed(2)}'),
                                onTap: () async {
                                  setState(() => _clienteIdSeleccionado = c.clienteId);
                                  _ticketsCliente = await _api.listarTicketsPendientesCliente(c.clienteId);
                                  setState(() {});
                                },
                              );
                            },
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: _buildDetalleCuentaCorriente(),
              ),
            ],
          )
        : Column(
            children: [
              Card(
                margin: const EdgeInsets.all(12),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Cobros de cuenta corriente',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 260,
                        child: ListView.separated(
                          itemCount: _clientesDeuda.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final c = _clientesDeuda[index];
                            final selected = _clienteIdSeleccionado == c.clienteId;
                            return ListTile(
                              selected: selected,
                              title: Text(c.clienteNombre),
                              subtitle: Text('DNI: ${c.documento}'),
                              trailing: Text('S/ ${c.deudaTotal.toStringAsFixed(2)}'),
                              onTap: () async {
                                setState(() => _clienteIdSeleccionado = c.clienteId);
                                _ticketsCliente = await _api.listarTicketsPendientesCliente(c.clienteId);
                                setState(() {});
                              },
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Expanded(child: _buildDetalleCuentaCorriente()),
            ],
          );
  }

  Widget _buildDetalleCuentaCorriente() {
    final clienteId = _clienteIdSeleccionado;
    ClienteDeudaSummary? selectedSummary;
    if (clienteId != null) {
      for (final c in _clientesDeuda) {
        if (c.clienteId == clienteId) {
          selectedSummary = c;
          break;
        }
      }
    }

    return Card(
      margin: const EdgeInsets.all(12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: clienteId == null
            ? Center(
                child: Text(
                  'Seleccioná un cliente con deuda.',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Cliente: ${selectedSummary?.clienteNombre ?? '—'}',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                        ),
                      ),
                      Chip(
                        label: Text(
                          'Disponible: S/ ${(selectedSummary?.disponible ?? 0).toStringAsFixed(2)}',
                        ),
                      ),
                      const SizedBox(width: 8),
                      Chip(
                        label: Text(
                          'Saldo a favor: S/ ${(selectedSummary?.saldoFavor ?? 0).toStringAsFixed(2)}',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'FIFO: aplica pagos al ticket más antiguo.',
                    style: const TextStyle(color: Colors.black54),
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: _ticketsCliente.isEmpty
                        ? const Center(child: Text('Sin tickets pendientes para este cliente.'))
                        : SingleChildScrollView(
                            child: DataTable(
                              columns: const [
                                DataColumn(label: Text('Ticket')),
                                DataColumn(label: Text('Fecha')),
                                DataColumn(label: Text('Total')),
                                DataColumn(label: Text('Saldo')),
                              ],
                              rows: _ticketsCliente
                                  .map(
                                    (t) => DataRow(
                                      cells: [
                                        DataCell(Text('#${t.ticketId}')),
                                        DataCell(Text(t.fecha.toString().substring(0, 10))),
                                        DataCell(Text('S/ ${t.total.toStringAsFixed(2)}')),
                                        DataCell(Text('S/ ${t.saldoPendiente.toStringAsFixed(2)}')),
                                      ],
                                    ),
                                  )
                                  .toList(),
                            ),
                          ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Deuda total: S/ ${_deudaTotalCliente.toStringAsFixed(2)}',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    onPressed: _ticketsCliente.isEmpty ? null : _abrirPopupPagoCuentaCorriente,
                    icon: const Icon(Icons.attach_money),
                    label: const Text('Registrar pago'),
                  ),
                  const SizedBox(height: 8),
                  FilledButton.tonalIcon(
                    onPressed: (_ticketsCliente.isEmpty || (selectedSummary?.saldoFavor ?? 0) <= 0.0001)
                        ? null
                        : () => _aplicarSaldoFavorCliente(clienteId),
                    icon: const Icon(Icons.account_balance_wallet),
                    label: const Text('Aplicar saldo a favor'),
                  ),
                ],
              ),
      ),
    );
  }

  Future<void> _suspenderTicket(TicketMock ticket) async {
    await _api.suspenderTicketVenta(ticketId: ticket.ticketId);
    if (!mounted) return;
    await _cargar();
  }

  Future<void> _reanudarTicket(TicketMock ticket) async {
    await _api.reanudarTicketVenta(ticketId: ticket.ticketId);
    if (!mounted) return;
    await _cargar();
  }

  Future<void> _aplicarSaldoFavorCliente(int clienteId) async {
    try {
      await _api.aplicarCreditoFavorCuentaCorriente(clienteId: clienteId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Saldo a favor aplicado a deuda (FIFO).')),
      );
      await _cargar();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al aplicar saldo a favor: $e')),
      );
    }
  }

  Future<void> _anularTicketOperacion(TicketMock ticket) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Anular operación'),
        content: Text('¿Seguro que deseas anular el ticket #${ticket.ticketId}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton.icon(
            onPressed: () => Navigator.of(context).pop(true),
            icon: const Icon(Icons.delete_forever),
            label: const Text('Anular'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await _api.anularTicketOperacion(ticketId: ticket.ticketId);
    if (!mounted) return;
    await _cargar();
  }

  Future<void> _abrirPopupNotaCredito(TicketMock ticket) async {
    final saldo = ticket.saldoPendiente;
    final textCtrl = TextEditingController(text: saldo.toStringAsFixed(2));

    await showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text('Nota de crédito (ticket #${ticket.ticketId})'),
          content: TextFormField(
            controller: textCtrl,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Importe de crédito',
              prefixText: 'S/ ',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancelar'),
            ),
            ElevatedButton.icon(
              onPressed: () async {
                final raw = textCtrl.text.replaceAll(',', '.');
                final importe = double.tryParse(raw) ?? 0;
                if (importe <= 0) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Importe inválido.')),
                  );
                  return;
                }
                Navigator.of(context).pop();
                await _api.registrarNotaCreditoCuentaCorriente(
                  ticketId: ticket.ticketId,
                  importe: importe,
                );
                if (!mounted) return;
                await _cargar();
              },
              icon: const Icon(Icons.payment),
              label: const Text('Confirmar'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _abrirOperacionesComercialesDialog({int? ticketIdPrefill}) async {
    final controlador = TextEditingController(
      text: ticketIdPrefill != null ? ticketIdPrefill.toString() : '',
    );
    final controlBusquedaDialog = TextEditingController();
    String filtroOperacionDialog = 'Todas';
    String rangoOperacionDialog = 'Todo';
    DateTime? desdeOperacionDialog;
    DateTime? hastaOperacionDialog;
    String ordenOperacionDialog = 'Más reciente';
    String busquedaOperacionDialog = '';
    int limiteOperacionDialog = 5;
    bool cargando = false;
    String? error;
    TicketMock? seleccionado;
    List<TicketMock> resultados = [];

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            Future<void> buscar() async {
              setStateDialog(() {
                cargando = true;
                error = null;
              });
              try {
                final busqueda = controlador.text;
                final list = await _api.listarTicketsOperaciones(busqueda: busqueda);
                setStateDialog(() {
                  resultados = list;
                  seleccionado = list.isNotEmpty ? list.first : null;
                  filtroOperacionDialog = 'Todas';
                  rangoOperacionDialog = 'Todo';
                  desdeOperacionDialog = null;
                  hastaOperacionDialog = null;
                  ordenOperacionDialog = 'Más reciente';
                  busquedaOperacionDialog = '';
                  limiteOperacionDialog = 5;
                  _presetOperacionLogDialogSeleccionado = null;
                  controlBusquedaDialog.clear();
                  cargando = false;
                });
              } catch (e) {
                setStateDialog(() {
                  error = e.toString();
                  cargando = false;
                });
              }
            }

            WidgetsBinding.instance.addPostFrameCallback((_) async {
              // Carga inicial si se prefiltra por ticket.
              if (ticketIdPrefill != null && resultados.isEmpty) {
                await buscar();
              }
            });

            return AlertDialog(
              title: const Text('Operaciones comerciales'),
              content: SizedBox(
                width: 900,
                height: 520,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextField(
                      controller: controlador,
                      decoration: const InputDecoration(
                        labelText: 'Buscar por ticket, cliente o producto',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onSubmitted: (_) => buscar(),
                    ),
                    const SizedBox(height: 10),
                    if (error != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Text(
                          error!,
                          style: TextStyle(color: Colors.red.shade900),
                        ),
                      ),
                    Row(
                      children: [
                        Expanded(
                          child: FilledButton.tonal(
                            onPressed: cargando ? null : buscar,
                            child: const Text('Buscar'),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: FilledButton(
                            onPressed: () => Navigator.of(context).pop(),
                            child: const Text('Cerrar'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: cargando
                          ? const Center(child: CircularProgressIndicator())
                          : resultados.isEmpty
                              ? const Center(child: Text('Sin resultados.'))
                              : ListView.separated(
                                  itemCount: resultados.length,
                                  separatorBuilder: (_, __) => const Divider(height: 1),
                                  itemBuilder: (context, index) {
                                    final t = resultados[index];
                                    final selected = seleccionado?.ticketId == t.ticketId;
                                    return ListTile(
                                      selected: selected,
                                      title: Text('Ticket #${t.ticketId}'),
                                      subtitle: Text('${t.clienteNombre} · ${t.documento}'),
                                      trailing: Text('S/ ${t.saldoPendiente.toStringAsFixed(2)}'),
                                      onTap: () => setStateDialog(() {
                                        seleccionado = t;
                                        filtroOperacionDialog = 'Todas';
                                        rangoOperacionDialog = 'Todo';
                                        desdeOperacionDialog = null;
                                        hastaOperacionDialog = null;
                                        ordenOperacionDialog = 'Más reciente';
                                        busquedaOperacionDialog = '';
                                        limiteOperacionDialog = 5;
                                        _presetOperacionLogDialogSeleccionado = null;
                                        controlBusquedaDialog.clear();
                                      }),
                                    );
                                  },
                                ),
                    ),
                    const SizedBox(height: 10),
                    if (seleccionado != null)
                      FutureBuilder<List<OperacionComercialLogMock>>(
                        future: _api.listarOperacionesComercialesRecientes(
                          ticketId: seleccionado!.ticketId,
                          limit: 3,
                        ),
                        builder: (context, snapOps) {
                          if (!snapOps.hasData || snapOps.data!.isEmpty) {
                            return const SizedBox.shrink();
                          }
                          final ops = snapOps.data!;
                          return Card(
                            color: Colors.blueGrey.shade50,
                            margin: const EdgeInsets.only(bottom: 8),
                            child: Padding(
                              padding: const EdgeInsets.all(8),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  const Text(
                                    'Últimas operaciones del ticket',
                                    style: TextStyle(fontWeight: FontWeight.w800),
                                  ),
                                  const SizedBox(height: 4),
                                  ...ops.map(
                                    (o) => Text(
                                      '- ${o.tipo}: S/ ${o.importe.toStringAsFixed(2)} · ${o.motivo}',
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    if (seleccionado != null) const SizedBox(height: 8),
                    if (seleccionado != null)
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final tipo in const [
                            'Todas',
                            'Devolución',
                            'Cambio',
                            'Nota de crédito',
                            'Nota de débito',
                            'Anulación',
                          ])
                            ChoiceChip(
                              label: Text(tipo),
                              selected: filtroOperacionDialog == tipo,
                              onSelected: (_) => setStateDialog(() {
                                filtroOperacionDialog = tipo;
                                limiteOperacionDialog = 5;
                              }),
                            ),
                        ],
                      ),
                    if (seleccionado != null) const SizedBox(height: 8),
                    if (seleccionado != null)
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final rango in const ['Todo', 'Hoy', '7 días', '30 días'])
                            ChoiceChip(
                              label: Text(rango),
                              selected: rangoOperacionDialog == rango,
                              onSelected: (_) => setStateDialog(() {
                                rangoOperacionDialog = rango;
                                limiteOperacionDialog = 5;
                              }),
                            ),
                        ],
                      ),
                    if (seleccionado != null) const SizedBox(height: 8),
                    if (seleccionado != null)
                      Row(
                        children: [
                          Expanded(
                            child: FilledButton.tonalIcon(
                              onPressed: () async {
                                final picked = await showDatePicker(
                                  context: context,
                                  initialDate: desdeOperacionDialog ?? DateTime.now(),
                                  firstDate: DateTime(2020),
                                  lastDate: DateTime.now().add(const Duration(days: 365)),
                                );
                                if (picked == null) return;
                                setStateDialog(() {
                                  desdeOperacionDialog = DateTime(picked.year, picked.month, picked.day);
                                  limiteOperacionDialog = 5;
                                });
                              },
                              icon: const Icon(Icons.date_range),
                              label: Text(
                                desdeOperacionDialog == null
                                    ? 'Desde'
                                    : 'Desde: ${desdeOperacionDialog!.toString().substring(0, 10)}',
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: FilledButton.tonalIcon(
                              onPressed: () async {
                                final picked = await showDatePicker(
                                  context: context,
                                  initialDate: hastaOperacionDialog ?? DateTime.now(),
                                  firstDate: DateTime(2020),
                                  lastDate: DateTime.now().add(const Duration(days: 365)),
                                );
                                if (picked == null) return;
                                setStateDialog(() {
                                  hastaOperacionDialog = DateTime(
                                    picked.year,
                                    picked.month,
                                    picked.day,
                                    23,
                                    59,
                                    59,
                                  );
                                  limiteOperacionDialog = 5;
                                });
                              },
                              icon: const Icon(Icons.event),
                              label: Text(
                                hastaOperacionDialog == null
                                    ? 'Hasta'
                                    : 'Hasta: ${hastaOperacionDialog!.toString().substring(0, 10)}',
                              ),
                            ),
                          ),
                        ],
                      ),
                    if (seleccionado != null) const SizedBox(height: 8),
                    if (seleccionado != null)
                      Row(
                        children: [
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              value: ordenOperacionDialog,
                              decoration: const InputDecoration(labelText: 'Orden'),
                              items: const [
                                DropdownMenuItem(value: 'Más reciente', child: Text('Más reciente')),
                                DropdownMenuItem(value: 'Más antiguo', child: Text('Más antiguo')),
                                DropdownMenuItem(value: 'Importe (mayor)', child: Text('Importe (mayor)')),
                                DropdownMenuItem(value: 'Importe (menor)', child: Text('Importe (menor)')),
                              ],
                              onChanged: (v) {
                                if (v == null) return;
                                setStateDialog(() => ordenOperacionDialog = v);
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          FilledButton.tonal(
                            onPressed: () => setStateDialog(() {
                              desdeOperacionDialog = null;
                              hastaOperacionDialog = null;
                              limiteOperacionDialog = 5;
                            }),
                            child: const Text('Limpiar fechas'),
                          ),
                        ],
                      ),
                    if (seleccionado != null) const SizedBox(height: 8),
                    if (seleccionado != null)
                      TextField(
                        controller: controlBusquedaDialog,
                        decoration: const InputDecoration(
                          labelText: 'Buscar en operaciones del ticket',
                          prefixIcon: Icon(Icons.search),
                        ),
                        onChanged: (v) => setStateDialog(() {
                          busquedaOperacionDialog = v.trim().toLowerCase();
                          limiteOperacionDialog = 5;
                        }),
                      ),
                    if (seleccionado != null) const SizedBox(height: 8),
                    if (seleccionado != null)
                      Row(
                        children: [
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              value: _presetOperacionLogDialogSeleccionado,
                              decoration: const InputDecoration(labelText: 'Vista guardada'),
                              hint: const Text('Seleccionar preset'),
                              items: _presetsOperacionLogDialog
                                  .map((p) => DropdownMenuItem(value: p.nombre, child: Text(p.nombre)))
                                  .toList(),
                              onChanged: (v) {
                                if (v == null) return;
                                final preset = _presetsOperacionLogDialog.firstWhere((p) => p.nombre == v);
                                setStateDialog(() {
                                  filtroOperacionDialog = preset.filtroOperacion;
                                  rangoOperacionDialog = preset.rango;
                                  desdeOperacionDialog = preset.desde;
                                  hastaOperacionDialog = preset.hasta;
                                  ordenOperacionDialog = preset.orden;
                                  busquedaOperacionDialog = preset.busqueda;
                                  limiteOperacionDialog = 5;
                                  _presetOperacionLogDialogSeleccionado = preset.nombre;
                                });
                                controlBusquedaDialog.text = preset.busqueda;
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          FilledButton.tonalIcon(
                            onPressed: () async {
                              final nombreCtrl = TextEditingController(
                                text: _presetOperacionLogDialogSeleccionado ?? '',
                              );
                              final nombre = await showDialog<String>(
                                context: context,
                                builder: (context) {
                                  return AlertDialog(
                                    title: const Text('Guardar preset de filtros'),
                                    content: TextField(
                                      controller: nombreCtrl,
                                      autofocus: true,
                                      decoration: const InputDecoration(
                                        labelText: 'Nombre de vista',
                                        hintText: 'Ej: Operaciones semanales',
                                      ),
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.of(context).pop(),
                                        child: const Text('Cancelar'),
                                      ),
                                      FilledButton(
                                        onPressed: () => Navigator.of(context).pop(nombreCtrl.text.trim()),
                                        child: const Text('Guardar'),
                                      ),
                                    ],
                                  );
                                },
                              );
                              nombreCtrl.dispose();

                              if (nombre == null || nombre.isEmpty) return;
                              if (nombre.length < 3) {
                                if (!mounted) return;
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('El nombre del preset debe tener al menos 3 caracteres.'),
                                  ),
                                );
                                return;
                              }

                              final nuevo = _OperacionLogPreset(
                                nombre: nombre,
                                filtroOperacion: filtroOperacionDialog,
                                rango: rangoOperacionDialog,
                                desde: desdeOperacionDialog,
                                hasta: hastaOperacionDialog,
                                orden: ordenOperacionDialog,
                                busqueda: busquedaOperacionDialog,
                              );

                              setStateDialog(() {
                                final idx = _presetsOperacionLogDialog.indexWhere(
                                  (p) => p.nombre.toLowerCase() == nombre.toLowerCase(),
                                );
                                if (idx >= 0) {
                                  _presetsOperacionLogDialog[idx] = nuevo;
                                } else {
                                  _presetsOperacionLogDialog.add(nuevo);
                                }
                                _presetOperacionLogDialogSeleccionado = nombre;
                              });
                              await _guardarPreferenciasPresetsOperacion();

                              if (!mounted) return;
                              ScaffoldMessenger.of(
                                context,
                              ).showSnackBar(SnackBar(content: Text('Preset "$nombre" guardado.')));
                            },
                            icon: const Icon(Icons.save_outlined),
                            label: const Text('Guardar vista'),
                          ),
                          const SizedBox(width: 8),
                          FilledButton.tonalIcon(
                            onPressed: _presetOperacionLogDialogSeleccionado == null
                                ? null
                                : () async {
                                    final nombre = _presetOperacionLogDialogSeleccionado!;
                                    setStateDialog(() {
                                      _presetsOperacionLogDialog.removeWhere((p) => p.nombre == nombre);
                                      _presetOperacionLogDialogSeleccionado = null;
                                    });
                                    await _guardarPreferenciasPresetsOperacion();
                                    ScaffoldMessenger.of(
                                      context,
                                    ).showSnackBar(SnackBar(content: Text('Preset "$nombre" eliminado.')));
                                  },
                            icon: const Icon(Icons.delete_outline),
                            label: const Text('Eliminar'),
                          ),
                        ],
                      ),
                    if (seleccionado != null) const SizedBox(height: 8),
                    if (seleccionado != null)
                      SizedBox(
                        height: 210,
                        child: FutureBuilder<List<OperacionComercialLogMock>>(
                          future: _api.listarOperacionesComercialesRecientes(
                            ticketId: seleccionado!.ticketId,
                            tipo: filtroOperacionDialog,
                            limit: 50,
                          ),
                          builder: (context, snap) {
                            if (!snap.hasData || snap.data!.isEmpty) {
                              return const SizedBox.shrink();
                            }
                            final now = DateTime.now();
                            bool dentroRango(OperacionComercialLogMock o) {
                              final diff = now.difference(o.fecha);
                              switch (rangoOperacionDialog) {
                                case 'Hoy':
                                  return o.fecha.year == now.year &&
                                      o.fecha.month == now.month &&
                                      o.fecha.day == now.day;
                                case '7 días':
                                  return diff.inDays < 7;
                                case '30 días':
                                  return diff.inDays < 30;
                                default:
                                  return true;
                              }
                            }

                            bool dentroRangoCustom(OperacionComercialLogMock o) {
                              if (desdeOperacionDialog != null && o.fecha.isBefore(desdeOperacionDialog!)) {
                                return false;
                              }
                              if (hastaOperacionDialog != null && o.fecha.isAfter(hastaOperacionDialog!)) {
                                return false;
                              }
                              return true;
                            }

                            final opsRaw = snap.data!;
                            final opsRango = opsRaw.where(dentroRango).where(dentroRangoCustom).toList();
                            final opsFiltradas = busquedaOperacionDialog.isEmpty
                                ? opsRango
                                : opsRango.where((o) {
                                    final q = busquedaOperacionDialog;
                                    return o.tipo.toLowerCase().contains(q) ||
                                        o.motivo.toLowerCase().contains(q) ||
                                        o.detalle.toLowerCase().contains(q) ||
                                        o.reintegroMetodo.toLowerCase().contains(q);
                                  }).toList();

                            opsFiltradas.sort((a, b) {
                              switch (ordenOperacionDialog) {
                                case 'Más antiguo':
                                  return a.fecha.compareTo(b.fecha);
                                case 'Importe (mayor)':
                                  return b.importe.compareTo(a.importe);
                                case 'Importe (menor)':
                                  return a.importe.compareTo(b.importe);
                                default:
                                  return b.fecha.compareTo(a.fecha);
                              }
                            });

                            final ops = opsFiltradas.take(limiteOperacionDialog).toList();
                            return Card(
                              color: Colors.blueGrey.shade50,
                              child: Padding(
                                padding: const EdgeInsets.all(10),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.stretch,
                                  children: [
                                    const Text(
                                      'Bitácora filtrada (ticket)',
                                      style: TextStyle(fontWeight: FontWeight.w800),
                                    ),
                                    const SizedBox(height: 6),
                                    Wrap(
                                      spacing: 8,
                                      children: [
                                        Chip(label: Text('Coincidencias: ${opsFiltradas.length}')),
                                        Chip(label: Text('Mostrando: ${ops.length}')),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Align(
                                      alignment: Alignment.centerRight,
                                      child: Wrap(
                                        spacing: 8,
                                        runSpacing: 8,
                                        children: [
                                          FilledButton.tonalIcon(
                                            onPressed: opsFiltradas.isEmpty
                                                ? null
                                                : () async {
                                                    await _guardarBitacoraCsvLocal(
                                                      operaciones: opsFiltradas,
                                                    );
                                                  },
                                            icon: const Icon(Icons.download_outlined),
                                            label: const Text('Guardar CSV'),
                                          ),
                                          FilledButton.tonalIcon(
                                            onPressed: opsFiltradas.isEmpty
                                                ? null
                                                : () async {
                                                    await _copiarBitacoraCsv(operaciones: opsFiltradas);
                                                  },
                                            icon: const Icon(Icons.file_copy_outlined),
                                            label: const Text('Copiar CSV'),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(height: 6),
                                    if (ops.isEmpty)
                                      const Text(
                                        'Sin resultados para los filtros aplicados.',
                                        style: TextStyle(fontWeight: FontWeight.w600),
                                      ),
                                    if (ops.isNotEmpty)
                                      Expanded(
                                        child: ListView(
                                          children: [
                                            ...ops.map(
                                              (o) => Card(
                                                margin: const EdgeInsets.symmetric(vertical: 3),
                                                child: ExpansionTile(
                                                  dense: true,
                                                  tilePadding: const EdgeInsets.symmetric(
                                                    horizontal: 10,
                                                    vertical: 2,
                                                  ),
                                                  title: Text('${o.tipo} · S/ ${o.importe.toStringAsFixed(2)}'),
                                                  subtitle: Text(
                                                    '${o.reintegroMetodo} · ${o.motivo} · ${o.fecha.toString().substring(0, 16)}',
                                                  ),
                                                  children: [
                                                    Padding(
                                                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                                                      child: Column(
                                                        crossAxisAlignment: CrossAxisAlignment.stretch,
                                                        children: [
                                                          Text('Detalle: ${o.detalle}'),
                                                          const SizedBox(height: 4),
                                                          Text('Operación ID: ${o.operacionId}'),
                                                        ],
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            ),
                                            if (opsFiltradas.length > ops.length)
                                              Align(
                                                alignment: Alignment.centerRight,
                                                child: TextButton.icon(
                                                  onPressed: () {
                                                    setStateDialog(() {
                                                      limiteOperacionDialog = (limiteOperacionDialog + 5)
                                                          .clamp(5, 100);
                                                    });
                                                  },
                                                  icon: const Icon(Icons.expand_more),
                                                  label: const Text('Ver más'),
                                                ),
                                              ),
                                          ],
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                    if (seleccionado != null)
                      Wrap(
                        spacing: 12,
                        runSpacing: 8,
                        children: [
                          FilledButton.tonal(
                            onPressed: seleccionado!.estado == TicketEstado.anulada
                                ? null
                                : () async {
                                    await _abrirPopupDevolucion(seleccionado!);
                                    await buscar();
                                  },
                            child: const Text('Devolución'),
                          ),
                          FilledButton.tonal(
                            onPressed: seleccionado!.estado == TicketEstado.anulada
                                ? null
                                : () async {
                                    await _abrirPopupCambio(seleccionado!);
                                    await buscar();
                                  },
                            child: const Text('Cambio'),
                          ),
                          FilledButton.tonal(
                            onPressed: seleccionado!.estado == TicketEstado.anulada
                                ? null
                                : () async {
                                    await _anularTicketOperacion(seleccionado!);
                                    // Refresca lista luego de operar.
                                    await buscar();
                                  },
                            child: const Text('Anular'),
                          ),
                          FilledButton.tonal(
                            onPressed: seleccionado!.estado == TicketEstado.anulada
                                ? null
                                : () async {
                                    await _abrirPopupNotaDebito(seleccionado!);
                                    await buscar();
                                  },
                            child: const Text('Nota de débito'),
                          ),
                          FilledButton.tonal(
                            onPressed: seleccionado!.estado == TicketEstado.fiada
                                ? () async {
                                    await _abrirPopupNotaCredito(seleccionado!);
                                    await buscar();
                                  }
                                : null,
                            child: const Text('Nota de crédito'),
                          ),
                        ],
                      ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    controlador.dispose();
    controlBusquedaDialog.dispose();
  }

  Future<void> _abrirPopupDevolucion(TicketMock ticket) async {
    final Map<int, double> cantidadesSeleccionadas = <int, double>{};
    String reintegroMetodo = 'efectivo';
    final motivoCtrl = TextEditingController();
    String labelReintegro(String metodo) {
      switch (metodo) {
        case 'efectivo':
          return 'Efectivo';
        case 'medio_pago_original':
          return 'Medio de pago original';
        case 'credito_cc':
          return 'Crédito en cuenta corriente';
        default:
          return metodo;
      }
    }

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            final mapItems = {for (final it in ticket.items) it.productoId: it};
            final importeSeleccionado = cantidadesSeleccionadas.entries.fold<double>(0.0, (acc, e) {
              final item = mapItems[e.key];
              if (item == null) return acc;
              return acc + (item.precioUnitario * e.value);
            });
            final saldoActual = ticket.saldoPendiente;
            final compensaDeuda = reintegroMetodo == 'credito_cc' && ticket.estado == TicketEstado.fiada
                ? importeSeleccionado.clamp(0.0, saldoActual)
                : 0.0;
            final saldoFavorGenerado = reintegroMetodo == 'credito_cc'
                ? (ticket.estado == TicketEstado.pagada
                    ? importeSeleccionado
                    : ticket.estado == TicketEstado.fiada
                        ? (importeSeleccionado - compensaDeuda).clamp(0.0, double.infinity)
                        : 0.0)
                : 0.0;
            final creditoRequiereCliente = reintegroMetodo == 'credito_cc' && ticket.clienteId == 0;
            final motivoValido = motivoCtrl.text.trim().length >= 3;
            final selectedLines = cantidadesSeleccionadas.entries
                .where((e) => e.value > 0.0001)
                .map((e) {
                  final item = mapItems[e.key]!;
                  final cantidad = e.value;
                  final subtotal = item.precioUnitario * cantidad;
                  return {
                    'nombre': item.nombre,
                    'cantidad': cantidad,
                    'precio': item.precioUnitario,
                    'subtotal': subtotal,
                  };
                })
                .toList();

            return AlertDialog(
              title: Text('Devolución (ticket #${ticket.ticketId})'),
              content: SizedBox(
                width: 520,
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      DropdownButtonFormField<String>(
                        value: reintegroMetodo,
                        decoration: const InputDecoration(labelText: 'Reintegro'),
                        items: const [
                          DropdownMenuItem(value: 'efectivo', child: Text('Efectivo')),
                          DropdownMenuItem(value: 'medio_pago_original', child: Text('Medio de pago original')),
                          DropdownMenuItem(value: 'credito_cc', child: Text('Crédito en cuenta corriente')),
                        ],
                        onChanged: (v) {
                          if (v == null) return;
                          reintegroMetodo = v;
                          setStateDialog(() {});
                        },
                      ),
                      const SizedBox(height: 10),
                      TextFormField(
                        controller: motivoCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Motivo de devolución',
                          hintText: 'Ej.: producto defectuoso',
                        ),
                        onChanged: (_) => setStateDialog(() {}),
                      ),
                      const SizedBox(height: 4),
                      if (!motivoValido && motivoCtrl.text.isNotEmpty)
                        const Text(
                          'El motivo debe tener al menos 3 caracteres.',
                          style: TextStyle(color: Colors.red, fontWeight: FontWeight.w700),
                        ),
                      const SizedBox(height: 12),
                      Text(
                        'Seleccioná productos y cantidad',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
                      ),
                      const SizedBox(height: 8),
                      ...ticket.items.map((it) {
                        final selected = cantidadesSeleccionadas.containsKey(it.productoId);
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            CheckboxListTile(
                              value: selected,
                              title: Text(it.nombre),
                              subtitle: Text('En ticket: ${it.cantidad.toStringAsFixed(0)}'),
                              controlAffinity: ListTileControlAffinity.leading,
                              onChanged: (v) {
                                setStateDialog(() {
                                  if (v == true) {
                                    cantidadesSeleccionadas[it.productoId] = it.cantidad;
                                  } else {
                                    cantidadesSeleccionadas.remove(it.productoId);
                                  }
                                });
                              },
                            ),
                            if (selected)
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16),
                                child: TextFormField(
                                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                  decoration: InputDecoration(
                                    labelText: 'Cantidad a devolver (máx. ${it.cantidad.toStringAsFixed(0)})',
                                  ),
                                  initialValue: (cantidadesSeleccionadas[it.productoId] ?? it.cantidad).toStringAsFixed(0),
                                  onChanged: (v) {
                                    final parsed = double.tryParse(v.replaceAll(',', '.'));
                                    if (parsed == null) return;
                                    final max = it.cantidad;
                                    final normalized = parsed.clamp(0.0, max);
                                    setStateDialog(() {
                                      cantidadesSeleccionadas[it.productoId] = normalized;
                                    });
                                    if (parsed - max > 0.0001) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(
                                          content: Text('Cantidad ajustada al máximo disponible del ticket: ${max.toStringAsFixed(0)}'),
                                        ),
                                      );
                                    }
                                  },
                                ),
                              ),
                          ],
                        );
                      }).toList(),
                      if (selectedLines.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        const Text(
                          'Productos seleccionados',
                          style: TextStyle(fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 6),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(8),
                            child: Column(
                              children: selectedLines
                                  .map(
                                    (line) => ListTile(
                                      dense: true,
                                      title: Text(line['nombre'] as String),
                                      subtitle: Text(
                                        'Cant: ${(line['cantidad'] as double).toStringAsFixed(2)} × S/ ${(line['precio'] as double).toStringAsFixed(2)}',
                                      ),
                                      trailing: Text('S/ ${(line['subtotal'] as double).toStringAsFixed(2)}'),
                                    ),
                                  )
                                  .toList(),
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 12),
                      Card(
                        color: Colors.blueGrey.shade50,
                        child: Padding(
                          padding: const EdgeInsets.all(10),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              const Text(
                                'Impacto de la devolución (preview)',
                                style: TextStyle(fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: 6),
                              Text('Importe seleccionado: S/ ${importeSeleccionado.toStringAsFixed(2)}'),
                              if (reintegroMetodo == 'credito_cc')
                                Text(
                                  ticket.estado == TicketEstado.fiada
                                      ? 'Compensa deuda FIADA: S/ ${compensaDeuda.toStringAsFixed(2)}'
                                      : 'Compensa deuda FIADA: S/ 0.00',
                                ),
                              if (reintegroMetodo == 'credito_cc')
                                Text('Saldo a favor generado: S/ ${saldoFavorGenerado.toStringAsFixed(2)}'),
                              if (reintegroMetodo == 'efectivo')
                                const Text('Reintegro en efectivo (mock: sin persistencia de movimiento de caja).'),
                              if (reintegroMetodo == 'medio_pago_original')
                                const Text('Reintegro por medio original (mock: ajuste de ticket sin pasarela real).'),
                              if (creditoRequiereCliente)
                                const Padding(
                                  padding: EdgeInsets.only(top: 6),
                                  child: Text(
                                    'Crédito en cuenta corriente requiere cliente asociado (no Consumidor final).',
                                    style: TextStyle(color: Colors.red, fontWeight: FontWeight.w700),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancelar'),
                ),
                ElevatedButton.icon(
                  onPressed: (cantidadesSeleccionadas.values.every((v) => v <= 0.0001) ||
                          creditoRequiereCliente ||
                          !motivoValido)
                      ? null
                      : () async {
                          try {
                            final validEntries = cantidadesSeleccionadas.entries
                                .where((e) => e.value > 0.0001)
                                .toList();

                            if (validEntries.isEmpty) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Debe seleccionar al menos una cantidad válida.')),
                              );
                              return;
                            }

                            final ok = await showDialog<bool>(
                              context: context,
                              builder: (context) => AlertDialog(
                                title: const Text('Confirmar operación'),
                                content: SizedBox(
                                  width: 460,
                                  child: SingleChildScrollView(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.stretch,
                                      children: [
                                        Text('Tipo: Devolución'),
                                        Text('Ticket: #${ticket.ticketId}'),
                                        Text('Reintegro: ${labelReintegro(reintegroMetodo)}'),
                                        Text('Ítems: ${selectedLines.length}'),
                                        Text('Importe: S/ ${importeSeleccionado.toStringAsFixed(2)}'),
                                        Text('Motivo: ${motivoCtrl.text.trim()}'),
                                        if (reintegroMetodo == 'credito_cc')
                                          Text('Compensa deuda: S/ ${compensaDeuda.toStringAsFixed(2)}'),
                                        if (reintegroMetodo == 'credito_cc')
                                          Text('Saldo a favor: S/ ${saldoFavorGenerado.toStringAsFixed(2)}'),
                                      ],
                                    ),
                                  ),
                                ),
                                actions: [
                                  TextButton(
                                    onPressed: () => Navigator.of(context).pop(false),
                                    child: const Text('Cancelar'),
                                  ),
                                  ElevatedButton.icon(
                                    onPressed: () => Navigator.of(context).pop(true),
                                    icon: const Icon(Icons.check),
                                    label: const Text('Confirmar'),
                                  ),
                                ],
                              ),
                            );
                            if (ok != true) return;

                            for (final entry in validEntries) {
                              await _api.registrarDevolucionOperacion(
                                ticketId: ticket.ticketId,
                                productoId: entry.key,
                                cantidad: entry.value,
                                reintegroMetodo: reintegroMetodo,
                                motivo: motivoCtrl.text.trim(),
                              );
                            }
                            if (!mounted) return;
                            Navigator.of(context).pop();
                          } catch (e) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Error devolución: $e')),
                            );
                          }
                        },
                  icon: const Icon(Icons.undo),
                  label: const Text('Confirmar devolución'),
                ),
              ],
            );
          },
        );
      },
    );
    motivoCtrl.dispose();
  }

  Future<void> _abrirPopupCambio(TicketMock ticket) async {
    int? productoDevuelto = ticket.items.isNotEmpty ? ticket.items.first.productoId : null;
    double cantidadDevuelta = 1;
    String codigoNuevo = '';
    int? productoNuevoId;
    String? nombreNuevo;
    double precioNuevo = 0;
    double cantidadNueva = 1;
    final List<Map<String, dynamic>> lineasCambios = [];

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: Text('Cambio (ticket #${ticket.ticketId})'),
              content: SizedBox(
                width: 680,
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      DropdownButtonFormField<int>(
                        value: productoDevuelto,
                        decoration: const InputDecoration(labelText: 'Producto a devolver'),
                        items: ticket.items
                            .map(
                              (it) => DropdownMenuItem(
                                value: it.productoId,
                                child: Text('${it.nombre} (x${it.cantidad.toStringAsFixed(0)})'),
                              ),
                            )
                            .toList(),
                        onChanged: (v) {
                          productoDevuelto = v;
                          setStateDialog(() {});
                        },
                      ),
                      const SizedBox(height: 10),
                      TextFormField(
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(labelText: 'Cantidad a devolver'),
                        initialValue: cantidadDevuelta.toStringAsFixed(0),
                        onChanged: (v) {
                          cantidadDevuelta = double.tryParse(v.replaceAll(',', '.')) ?? 1;
                        },
                      ),
                      const SizedBox(height: 6),
                      Builder(builder: (context) {
                        if (productoDevuelto == null) {
                          return const SizedBox.shrink();
                        }
                        if (ticket.items.isEmpty) {
                          return const SizedBox.shrink();
                        }
                        final itemEnTicket = ticket.items.firstWhere((it) => it.productoId == productoDevuelto);
                        final yaAsignado = lineasCambios
                            .where((l) => l['productoDevueltoId'] == productoDevuelto)
                            .fold<double>(0.0, (acc, l) => acc + ((l['cantidadDevuelta'] as double?) ?? 0));
                        final disponible = (itemEnTicket.cantidad - yaAsignado).clamp(0.0, double.infinity);
                        return Text(
                          'Disponible para este producto en el ticket: ${(disponible).toStringAsFixed(2).replaceAll('.', ',')} unidades',
                          style: const TextStyle(color: Colors.black54, fontWeight: FontWeight.w600),
                        );
                      }),
                      const SizedBox(height: 14),
                      TextField(
                        decoration: const InputDecoration(
                          labelText: 'SKU / Código de barras del producto nuevo',
                          prefixIcon: Icon(Icons.search),
                        ),
                        onChanged: (v) => codigoNuevo = v,
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: FilledButton.tonal(
                              onPressed: () async {
                                final result = await _api.buscarProductoPorCodigo(codigoNuevo);
                                if (result == null) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Producto nuevo no encontrado')),
                                  );
                                  return;
                                }
                                setStateDialog(() {
                                  productoNuevoId = result['id'] as int?;
                                  nombreNuevo = result['nombre'] as String?;
                                  precioNuevo = (result['precio_venta'] as num?)?.toDouble() ?? 0;
                                });
                              },
                              child: const Text('Buscar producto'),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      if (productoNuevoId != null)
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(10),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Nuevo: ${nombreNuevo ?? '-'} (#$productoNuevoId)'),
                                Text('Precio unitario: S/ ${precioNuevo.toStringAsFixed(2)}'),
                              ],
                            ),
                          ),
                        ),
                      const SizedBox(height: 10),
                      if (productoNuevoId != null)
                        TextFormField(
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: const InputDecoration(labelText: 'Cantidad nueva'),
                          initialValue: cantidadNueva.toStringAsFixed(0),
                          onChanged: (v) {
                            cantidadNueva = double.tryParse(v.replaceAll(',', '.')) ?? 1;
                          },
                        ),
                      const SizedBox(height: 12),
                      FilledButton.tonal(
                        onPressed: (productoDevuelto == null || productoNuevoId == null)
                            ? null
                            : () async {
                                final nombreDevuelto = ticket.items
                                    .firstWhere((it) => it.productoId == productoDevuelto)
                                    .nombre;

                                final itemEnTicket = ticket.items.firstWhere((it) => it.productoId == productoDevuelto);
                                final yaAsignado = lineasCambios
                                    .where((l) => l['productoDevueltoId'] == productoDevuelto)
                                    .fold<double>(0.0, (acc, l) => acc + ((l['cantidadDevuelta'] as double?) ?? 0));
                                final disponible = (itemEnTicket.cantidad - yaAsignado).clamp(0.0, double.infinity);

                                // Prevalidar stock del producto NUEVO antes de agregar la línea.
                                // El mock descuenta stock solo al confirmar, pero si se excede puede fallar a mitad.
                                final plannedNuevo = lineasCambios
                                    .where((l) => l['productoNuevoId'] == productoNuevoId)
                                    .fold<double>(0.0, (acc, l) => acc + ((l['cantidadNueva'] as double?) ?? 0));
                                final stockNuevoDisponible =
                                    await _api.obtenerStockDisponibleProducto(productoNuevoId!);
                                final disponibleNuevo = (stockNuevoDisponible - plannedNuevo).clamp(0.0, double.infinity);

                                if (cantidadDevuelta <= 0.0001) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('La cantidad a devolver debe ser mayor a 0.')),
                                  );
                                  return;
                                }
                                if (cantidadDevuelta - disponible > 0.0001) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        'La suma de cantidades para "${nombreDevuelto}" excede la cantidad disponible en el ticket. Disponible: ${disponible.toStringAsFixed(2)}',
                                      ),
                                    ),
                                  );
                                  return;
                                }

                                if (cantidadNueva <= 0.0001) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('La cantidad nueva debe ser mayor a 0.')),
                                  );
                                  return;
                                }
                                if (cantidadNueva - disponibleNuevo > 0.0001) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        'Stock insuficiente para el producto nuevo. Disponible: ${disponibleNuevo.toStringAsFixed(2)} unidades',
                                      ),
                                    ),
                                  );
                                  return;
                                }

                                setStateDialog(() {
                                  lineasCambios.add({
                                    'productoDevueltoId': productoDevuelto!,
                                    'nombreDevuelto': nombreDevuelto,
                                    'cantidadDevuelta': cantidadDevuelta,
                                    'productoNuevoId': productoNuevoId!,
                                    'nombreNuevo': nombreNuevo ?? 'Producto',
                                    'cantidadNueva': cantidadNueva,
                                  });
                                });
                              },
                        child: const Text('Agregar cambio'),
                      ),
                      if (lineasCambios.isNotEmpty)
                        const SizedBox(height: 10),
                      if (lineasCambios.isNotEmpty)
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(10),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: List.generate(lineasCambios.length, (i) {
                                final l = lineasCambios[i];
                                return ListTile(
                                  title: Text('${l['nombreDevuelto']} -> ${l['nombreNuevo']}'),
                                  subtitle: Text(
                                    'Devuelto: ${(l['cantidadDevuelta'] as double).toStringAsFixed(0)} · Nuevo: ${(l['cantidadNueva'] as double).toStringAsFixed(0)}',
                                  ),
                                  trailing: IconButton(
                                    tooltip: 'Quitar',
                                    onPressed: () {
                                      setStateDialog(() {
                                        lineasCambios.removeAt(i);
                                      });
                                    },
                                    icon: const Icon(Icons.delete_outline),
                                  ),
                                );
                              }),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancelar'),
                ),
                ElevatedButton.icon(
                  onPressed: lineasCambios.isEmpty
                      ? null
                      : () async {
                          try {
                            for (final l in lineasCambios) {
                              await _api.registrarCambioOperacion(
                                ticketId: ticket.ticketId,
                                productoDevueltoId: l['productoDevueltoId'] as int,
                                cantidadDevuelta: l['cantidadDevuelta'] as double,
                                productoNuevoId: l['productoNuevoId'] as int,
                                cantidadNueva: l['cantidadNueva'] as double,
                              );
                            }
                            if (!mounted) return;
                            Navigator.of(context).pop();
                          } catch (e) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Error cambio: $e')),
                            );
                          }
                        },
                  icon: const Icon(Icons.swap_horiz),
                  label: const Text('Confirmar cambio'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _abrirPopupNotaDebito(TicketMock ticket) async {
    final textCtrl = TextEditingController();

    await showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text('Nota de débito (ticket #${ticket.ticketId})'),
          content: TextFormField(
            controller: textCtrl,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Importe de débito',
              prefixText: 'S/ ',
            ),
            onChanged: (v) {
              // El valor real se parsea en el botón Confirmar.
            },
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancelar'),
            ),
            ElevatedButton.icon(
              onPressed: () async {
                final raw = textCtrl.text.replaceAll(',', '.');
                final monto = double.tryParse(raw) ?? 0;
                if (monto <= 0) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Importe inválido.')),
                  );
                  return;
                }
                try {
                  await _api.registrarNotaDebitoOperacion(
                    ticketId: ticket.ticketId,
                    importe: monto,
                  );
                  if (!mounted) return;
                  Navigator.of(context).pop();
                } catch (e) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Error nota débito: $e')),
                  );
                }
              },
              icon: const Icon(Icons.add_circle_outline),
              label: const Text('Confirmar'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: ToggleButtons(
              isSelected: [_modo == CajaModo.venta, _modo == CajaModo.cuentaCorriente],
              onPressed: (index) async {
                setState(() {
                  _modo = index == 0 ? CajaModo.venta : CajaModo.cuentaCorriente;
                });
                await _cargar();
              },
              children: const [
                Padding(padding: EdgeInsets.symmetric(horizontal: 16), child: Text('Modo Venta')),
                Padding(padding: EdgeInsets.symmetric(horizontal: 16), child: Text('Modo Cuenta')),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(12),
              child: Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    _error!,
                    style: TextStyle(color: Colors.red.shade900),
                  ),
                ),
              ),
            ),
          if (_cargando)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else if (_modo == CajaModo.venta)
            Expanded(child: _buildModoVenta())
          else
            Expanded(child: _buildModoCuentaCorriente()),
        ],
      ),
    );
  }
}

