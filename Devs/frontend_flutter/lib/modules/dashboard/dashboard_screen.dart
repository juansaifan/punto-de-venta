import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

class PantallaDashboard extends StatefulWidget {
  const PantallaDashboard({super.key});

  @override
  State<PantallaDashboard> createState() => _PantallaDashboardState();
}

class _PantallaDashboardState extends State<PantallaDashboard> {
  bool _cargando = true;
  bool _vacio = false;
  String? _error;
  int _tick = 0;

  static const int _diasVencimiento = 30;
  static const int _refreshSegundos = 90;

  DashboardOfflineResponse? _data;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _cargar(iniciarTimer: true);
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _cargar({bool iniciarTimer = false}) async {
    setState(() {
      _cargando = true;
      _error = null;
      _vacio = false;
    });
    try {
      final repo = MockDashboardRepository();
      final resp = await repo.obtenerDashboard(diasVencimiento: _diasVencimiento, tick: ++_tick);
      setState(() {
        _data = resp;
        _vacio = resp == null;
        _cargando = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _cargando = false;
      });
    } finally {
      if (iniciarTimer) {
        _timer?.cancel();
        _timer = Timer.periodic(const Duration(seconds: _refreshSegundos), (_) {
          _cargar();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Dashboard',
                  style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.tonal(
                onPressed: _cargando ? null : () => _cargar(),
                child: Text(_cargando ? 'Actualizando…' : 'Refrescar'),
              ),
              const SizedBox(width: 8),
              Text(
                'Auto: ${_refreshSegundos}s',
                style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.7)),
              ),
            ],
          ),
          const SizedBox(height: 12),

          if (_error != null)
            Expanded(
              child: Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Error al cargar Dashboard',
                        style: TextStyle(color: Colors.red.shade700, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _error!,
                        style: TextStyle(color: Colors.red.shade900),
                      ),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        onPressed: _cargando ? null : () => _cargar(),
                        icon: const Icon(Icons.refresh),
                        label: const Text('Reintentar'),
                      ),
                    ],
                  ),
                ),
              ),
            )
          else if (_cargando)
            const Expanded(
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_vacio || _data == null)
            Expanded(
              child: Card(
                child: Center(
                  child: Text(
                    'Sin datos disponibles',
                    style: theme.textTheme.titleMedium,
                  ),
                ),
              ),
            )
          else
            Expanded(
              child: _ConstruirContenido(data: _data!, diasVencimiento: _diasVencimiento),
            ),
        ],
      ),
    );
  }
}

class _ConstruirContenido extends StatelessWidget {
  const _ConstruirContenido({required this.data, required this.diasVencimiento});

  final DashboardOfflineResponse data;
  final int diasVencimiento;

  @override
  Widget build(BuildContext context) {
    final isDesktop = MediaQuery.of(context).size.width >= 1000;

    final central = ListView(
      padding: EdgeInsets.zero,
      children: [
        _KpiGridComparativo(data: data),
        const SizedBox(height: 12),
        _VentasPorHoraCard(rows: data.ventasPorHora),
        const SizedBox(height: 12),
        _AlertasOperativasCard(
          stockBajo: data.alertas.stockBajo,
          proximosVencer: data.alertas.proximosVencer,
          diasVencimiento: diasVencimiento,
        ),
      ],
    );

    final lateral = ListView(
      padding: EdgeInsets.zero,
      children: [
        _SaludNegocioCard(data: data),
        const SizedBox(height: 12),
        _PromedioVentasDiariasCard(data: data),
        const SizedBox(height: 12),
        _PromedioDiaSemanaCard(data: data),
        const SizedBox(height: 12),
        _PronosticoHoyCard(data: data),
        const SizedBox(height: 12),
        _PuntoEquilibrioCard(data: data),
        const SizedBox(height: 12),
        _GananciaActualCard(data: data),
        const SizedBox(height: 12),
        _ObjetivosGananciaCard(data: data),
        const SizedBox(height: 12),
        _MargenPromedioCard(data: data),
      ],
    );

    if (isDesktop) {
      return Row(
        children: [
          Expanded(flex: 8, child: central),
          const SizedBox(width: 14),
          Expanded(flex: 3, child: lateral),
        ],
      );
    }

    return Column(
      children: [
        Expanded(child: central),
        const SizedBox(height: 12),
        SizedBox(height: 520, child: lateral),
      ],
    );
  }
}

class _KpiGridComparativo extends StatelessWidget {
  const _KpiGridComparativo({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final items = data.comparativos;
    return Card(
      elevation: 0.5,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'KPIs principales',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 10),
            LayoutBuilder(
              builder: (context, c) {
                final columns = c.maxWidth >= 720 ? 3 : 2;
                return GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: items.length,
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: columns,
                    childAspectRatio: 1.2,
                  ),
                  itemBuilder: (context, i) {
                    final r = items[i];
                    final isUp = (r.variacionPct ?? 0) >= 0;
                    return Card(
                      elevation: 0.3,
                      color: Theme.of(context).colorScheme.surfaceContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              r.kpi,
                              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                    fontWeight: FontWeight.w700,
                                  ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Text(
                                  _money(r.valor),
                                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                                ),
                                const SizedBox(width: 10),
                                Chip(
                                  backgroundColor: isUp ? Colors.green.shade50 : Colors.red.shade50,
                                  label: Text(
                                    '${r.variacionPct != null ? (isUp ? '+' : '') + r.variacionPct!.toStringAsFixed(2) : '—'}%',
                                    style: TextStyle(
                                      color: isUp ? Colors.green.shade800 : Colors.red.shade800,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Ayer: ${_money(r.valorAnterior)}',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _VentasPorHoraCard extends StatelessWidget {
  const _VentasPorHoraCard({required this.rows});
  final List<VentasHoraRow> rows;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0.5,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Ventas del día por hora',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 260,
              child: VentasPorHoraGrafico(rows: rows),
            ),
          ],
        ),
      ),
    );
  }
}

class VentasPorHoraGrafico extends StatelessWidget {
  const VentasPorHoraGrafico({super.key, required this.rows});
  final List<VentasHoraRow> rows;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, c) {
        return CustomPaint(
          painter: _VentasPorHoraPainter(rows: rows),
          size: Size(c.maxWidth, c.maxHeight),
        );
      },
    );
  }
}

class _VentasPorHoraPainter extends CustomPainter {
  _VentasPorHoraPainter({required this.rows});
  final List<VentasHoraRow> rows;

  @override
  void paint(Canvas canvas, Size size) {
    final maxCantidad = rows.map((r) => r.cantidad).fold<double>(0, max);
    final maxTotal = rows.map((r) => r.total).fold<double>(0, max);

    final paintBar = Paint()
      ..style = PaintingStyle.fill
      ..color = const Color(0xFF1E88E5).withOpacity(0.25);

    final paintBarStrong = Paint()
      ..style = PaintingStyle.fill
      ..color = const Color(0xFF1E88E5).withOpacity(0.75);

    final paintLine = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..color = const Color(0xFF43A047);

    // Padding interno para ejes.
    const padTop = 14.0;
    const padBottom = 26.0;
    const padLeft = 12.0;
    const padRight = 12.0;

    final w = size.width - padLeft - padRight;
    final h = size.height - padTop - padBottom;

    if (rows.isEmpty || w <= 0 || h <= 0) return;

    final barW = w / rows.length;
    final barInnerW = barW * 0.62;

    // Grid horizontal simple
    for (int i = 0; i <= 4; i++) {
      final y = padTop + h * (i / 4);
      final p = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = Colors.black.withOpacity(0.05);
      canvas.drawLine(Offset(padLeft, y), Offset(padLeft + w, y), p);
    }

    // Bars + line
    final points = <Offset>[];
    for (int i = 0; i < rows.length; i++) {
      final r = rows[i];

      final normCantidad = maxCantidad > 0 ? (r.cantidad / maxCantidad) : 0;
      final barH = normCantidad * h;

      final xCenter = padLeft + barW * i + barW / 2;
      final x0 = xCenter - barInnerW / 2;
      final y0 = padTop + (h - barH);

      canvas.drawRect(
        Rect.fromLTWH(x0, y0, barInnerW, barH),
        normCantidad > 0.65 ? paintBarStrong : paintBar,
      );

      // Línea para total importe
      final normTotal = maxTotal > 0 ? (r.total / maxTotal) : 0;
      final yLine = padTop + (h - normTotal * h);
      points.add(Offset(xCenter, yLine));
    }

    if (points.length >= 2) {
      final path = Path()..moveTo(points.first.dx, points.first.dy);
      for (final pt in points.skip(1)) {
        path.lineTo(pt.dx, pt.dy);
      }
      canvas.drawPath(path, paintLine);
    }

    // Etiquetas: mostrar cada 4 horas para no saturar
    final labelEvery = 4;
    final textPainter = TextPainter(
      textDirection: TextDirection.ltr,
    );
    for (int i = 0; i < rows.length; i++) {
      if (i % labelEvery != 0 && i != rows.length - 1) continue;
      final r = rows[i];
      final label = r.hora;
      textPainter.text = TextSpan(
        text: label,
        style: TextStyle(fontSize: 10, color: Colors.black.withOpacity(0.55)),
      );
      textPainter.layout();
      final x = padLeft + barW * i + barW / 2 - textPainter.width / 2;
      final y = padTop + h + 6;
      textPainter.paint(canvas, Offset(x, y));
    }
  }

  @override
  bool shouldRepaint(covariant _VentasPorHoraPainter oldDelegate) {
    return oldDelegate.rows != rows;
  }
}

class _AlertasOperativasCard extends StatelessWidget {
  const _AlertasOperativasCard({
    required this.stockBajo,
    required this.proximosVencer,
    required this.diasVencimiento,
  });

  final List<StockBajoItem> stockBajo;
  final List<ProximoVencerItem> proximosVencer;
  final int diasVencimiento;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0.5,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Alertas operativas',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 10),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: _TablaStockBajo(items: stockBajo),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _TablaProximosVencer(items: proximosVencer, diasVencimiento: diasVencimiento),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _TablaStockBajo extends StatelessWidget {
  const _TablaStockBajo({required this.items});
  final List<StockBajoItem> items;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.surfaceContainer,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Stock bajo', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            if (items.isEmpty)
              const Text('Sin alertas')
            else
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  columns: const [
                    DataColumn(label: Text('Producto')),
                    DataColumn(label: Text('SKU')),
                    DataColumn(label: Text('Cant.')),
                    DataColumn(label: Text('Mín.')),
                  ],
                  rows: items
                      .take(10)
                      .map(
                        (p) => DataRow(
                          cells: [
                            DataCell(Text(p.nombre)),
                            DataCell(Text(p.sku)),
                            DataCell(Text(p.stockActual.toStringAsFixed(0))),
                            DataCell(Text(p.stockMinimo.toStringAsFixed(0))),
                          ],
                        ),
                      )
                      .toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _TablaProximosVencer extends StatelessWidget {
  const _TablaProximosVencer({required this.items, required this.diasVencimiento});
  final List<ProximoVencerItem> items;
  final int diasVencimiento;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.surfaceContainer,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Próximos a vencer (≤ $diasVencimiento días)',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            if (items.isEmpty)
              const Text('Sin alertas')
            else
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  columns: const [
                    DataColumn(label: Text('Producto')),
                    DataColumn(label: Text('Lote')),
                    DataColumn(label: Text('Venc.')),
                    DataColumn(label: Text('Días')),
                  ],
                  rows: items
                      .take(10)
                      .map(
                        (x) => DataRow(
                          cells: [
                            DataCell(Text(x.productoNombre)),
                            DataCell(Text(x.loteCodigo)),
                            DataCell(Text(x.fechaVencimiento)),
                            DataCell(Text(x.diasRestantes.toStringAsFixed(0))),
                          ],
                        ),
                      )
                      .toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// ---------------- Lateral ----------------

class _SaludNegocioCard extends StatelessWidget {
  const _SaludNegocioCard({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final s = data.panelLateral.salud;
    final color = s.estado == 'verde'
        ? Colors.green
        : s.estado == 'amarillo'
            ? Colors.orange
            : Colors.red;

    return Card(
      elevation: 0.5,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Salud del negocio', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            Row(
              children: [
                CircleAvatar(radius: 10, backgroundColor: color),
                const SizedBox(width: 10),
                Text(
                  s.estado.toUpperCase(),
                  style: TextStyle(fontWeight: FontWeight.w900, color: color),
                ),
              ],
            ),
            const SizedBox(height: 10),
            _line('Ingresos actuales', _money(s.ingresosActuales)),
            _line('Punto equilibrio', _money(s.puntoEquilibrio)),
            _line('Objetivo diario', _money(s.objetivoDiario)),
          ],
        ),
      ),
    );
  }

  Widget _line(String l, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(l, style: const TextStyle(color: Colors.black54))),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _PromedioVentasDiariasCard extends StatelessWidget {
  const _PromedioVentasDiariasCard({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final p = data.panelLateral.promedioVentas;
    return _CardLateral(
      title: 'Promedio de ventas por día',
      children: [
        _line('Tickets promedio', p.ticketsPromedio.toStringAsFixed(0)),
        _line('Ingresos promedio', _money(p.ingresosPromedio)),
      ],
    );
  }

  Widget _line(String l, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(l, style: const TextStyle(color: Colors.black54))),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _PromedioDiaSemanaCard extends StatelessWidget {
  const _PromedioDiaSemanaCard({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final p = data.panelLateral.promedioPorDiaSemana;
    return _CardLateral(
      title: 'Promedio para este día de la semana',
      children: [
        _line('Día', p.diaSemana),
        _line('Tickets promedio', p.ticketsPromedio.toStringAsFixed(0)),
        _line('Ingresos promedio', _money(p.ingresosPromedio)),
      ],
    );
  }

  Widget _line(String l, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(l, style: const TextStyle(color: Colors.black54))),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _PronosticoHoyCard extends StatelessWidget {
  const _PronosticoHoyCard({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final p = data.panelLateral.pronostico;
    return _CardLateral(
      title: 'Pronóstico (hoy)',
      children: [
        _line('Ingresos pronosticados', _money(p.totalPronosticado)),
        _line('Cumplimiento objetivo diario', '${p.cumplimientoObjetivoDiarioPct.toStringAsFixed(0)}%'),
      ],
    );
  }

  Widget _line(String l, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(l, style: const TextStyle(color: Colors.black54))),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _PuntoEquilibrioCard extends StatelessWidget {
  const _PuntoEquilibrioCard({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final p = data.panelLateral.puntoEquilibrio;
    return _CardLateral(
      title: 'Punto de equilibrio',
      children: [
        _line('Valor', _money(p.valor)),
        _line('Cumplimiento', '${p.cumplimientoPct.toStringAsFixed(1)}%'),
      ],
    );
  }

  Widget _line(String l, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(l, style: const TextStyle(color: Colors.black54))),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _GananciaActualCard extends StatelessWidget {
  const _GananciaActualCard({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final g = data.panelLateral.gananciaActual;
    final isPos = g >= 0;
    return _CardLateral(
      title: 'Ganancia actual',
      children: [
        Row(
          children: [
            Icon(isPos ? Icons.trending_up : Icons.trending_down, color: isPos ? Colors.green : Colors.red),
            const SizedBox(width: 8),
            Text(
              _money(g),
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w900,
                color: isPos ? Colors.green.shade800 : Colors.red.shade800,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ObjetivosGananciaCard extends StatelessWidget {
  const _ObjetivosGananciaCard({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final o = data.panelLateral.objetivosGanancia;
    return _CardLateral(
      title: 'Objetivos de ganancia',
      children: [
        _line('Diario', _money(o.objetivoDiario)),
        _line('Semanal', _money(o.objetivoSemanal)),
        _line('Mensual', _money(o.objetivoMensual)),
      ],
    );
  }

  Widget _line(String l, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(l, style: const TextStyle(color: Colors.black54))),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _MargenPromedioCard extends StatelessWidget {
  const _MargenPromedioCard({required this.data});
  final DashboardOfflineResponse data;

  @override
  Widget build(BuildContext context) {
    final m = data.panelLateral.margenPromedio;
    final isUp = m.tendenciaPct >= 0;
    return _CardLateral(
      title: 'Margen promedio del día',
      children: [
        Row(
          children: [
            Icon(isUp ? Icons.arrow_upward : Icons.arrow_downward,
                color: isUp ? Colors.green.shade700 : Colors.red.shade700),
            const SizedBox(width: 8),
            Text(
              '${m.tendenciaPct >= 0 ? '+' : ''}${m.tendenciaPct.toStringAsFixed(1)}%',
              style: TextStyle(
                fontWeight: FontWeight.w900,
                color: isUp ? Colors.green.shade800 : Colors.red.shade800,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          'Margen estimado: ${_money(m.margenValor)}',
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
      ],
    );
  }
}

class _CardLateral extends StatelessWidget {
  const _CardLateral({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0.5,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 10),
            ...children,
          ],
        ),
      ),
    );
  }
}

// ---------------- Mock + Models ----------------

String _money(num v) {
  final n = v.toDouble();
  return n.toStringAsFixed(0);
}

double _round2(num v) => v.toDouble();

class DashboardOfflineResponse {
  final CajaSummary caja;
  final AlertasOperativas alertas;
  final DashboardIndicadores indicadores;
  final List<ComparativoKpi> comparativos;
  final List<VentasHoraRow> ventasPorHora;
  final PanelLateral panelLateral;

  DashboardOfflineResponse({
    required this.caja,
    required this.alertas,
    required this.indicadores,
    required this.comparativos,
    required this.ventasPorHora,
    required this.panelLateral,
  });
}

class CajaSummary {
  final bool cajaAbierta;
  final int? cajaId;
  final double saldoTeorico;

  CajaSummary({required this.cajaAbierta, required this.cajaId, required this.saldoTeorico});
}

class AlertasOperativas {
  final List<StockBajoItem> stockBajo;
  final List<ProximoVencerItem> proximosVencer;

  AlertasOperativas({required this.stockBajo, required this.proximosVencer});
}

class StockBajoItem {
  final String nombre;
  final String sku;
  final double stockActual;
  final double stockMinimo;
  StockBajoItem({required this.nombre, required this.sku, required this.stockActual, required this.stockMinimo});
}

class ProximoVencerItem {
  final String productoNombre;
  final String loteCodigo;
  final String fechaVencimiento;
  final double diasRestantes;

  ProximoVencerItem({
    required this.productoNombre,
    required this.loteCodigo,
    required this.fechaVencimiento,
    required this.diasRestantes,
  });
}

class DashboardIndicadores {
  final double ventasDia;
  final double totalVentasDia;
  final double ticketPromedio;
  final int productosStockBajo;
  final double valorInventario;
  final double saldoCajaTeorico;

  DashboardIndicadores({
    required this.ventasDia,
    required this.totalVentasDia,
    required this.ticketPromedio,
    required this.productosStockBajo,
    required this.valorInventario,
    required this.saldoCajaTeorico,
  });
}

class ComparativoKpi {
  final String kpi;
  final double valor;
  final double valorAnterior;
  final double? variacionPct;
  ComparativoKpi({required this.kpi, required this.valor, required this.valorAnterior, required this.variacionPct});
}

class VentasHoraRow {
  final String hora;
  final double cantidad;
  final double total;
  VentasHoraRow({required this.hora, required this.cantidad, required this.total});
}

class PanelLateral {
  final SaludNegocio salud;
  final PromedioVentasDiarias promedioVentas;
  final PromedioPorDiaSemana promedioPorDiaSemana;
  final PronosticoHoy pronostico;
  final PuntoEquilibrio puntoEquilibrio;
  final double gananciaActual;
  final ObjetivosGanancia objetivosGanancia;
  final MargenPromedio margenPromedio;

  PanelLateral({
    required this.salud,
    required this.promedioVentas,
    required this.promedioPorDiaSemana,
    required this.pronostico,
    required this.puntoEquilibrio,
    required this.gananciaActual,
    required this.objetivosGanancia,
    required this.margenPromedio,
  });
}

class SaludNegocio {
  final String estado; // verde / amarillo / rojo
  final double ingresosActuales;
  final double puntoEquilibrio;
  final double objetivoDiario;
  SaludNegocio({required this.estado, required this.ingresosActuales, required this.puntoEquilibrio, required this.objetivoDiario});
}

class PromedioVentasDiarias {
  final double ticketsPromedio;
  final double ingresosPromedio;
  PromedioVentasDiarias({required this.ticketsPromedio, required this.ingresosPromedio});
}

class PromedioPorDiaSemana {
  final String diaSemana;
  final double ticketsPromedio;
  final double ingresosPromedio;
  PromedioPorDiaSemana({required this.diaSemana, required this.ticketsPromedio, required this.ingresosPromedio});
}

class PronosticoHoy {
  final double totalPronosticado;
  final double cumplimientoObjetivoDiarioPct;
  PronosticoHoy({required this.totalPronosticado, required this.cumplimientoObjetivoDiarioPct});
}

class PuntoEquilibrio {
  final double valor;
  final double cumplimientoPct;
  PuntoEquilibrio({required this.valor, required this.cumplimientoPct});
}

class ObjetivosGanancia {
  final double objetivoDiario;
  final double objetivoSemanal;
  final double objetivoMensual;
  ObjetivosGanancia({required this.objetivoDiario, required this.objetivoSemanal, required this.objetivoMensual});
}

class MargenPromedio {
  final double margenValor;
  final double tendenciaPct;
  MargenPromedio({required this.margenValor, required this.tendenciaPct});
}

class MockDashboardRepository {
  // Catálogo reducido para generar alertas.
  static const _productos = [
    {'nombre': 'Fideos Spaghetti Verizzia 500g', 'sku': 'FDS-500-SPAG'},
    {'nombre': 'Salsa Tomate Tradicional', 'sku': 'SLV-TOM-200'},
    {'nombre': 'Aceite de Oliva 1L', 'sku': 'ACE-OLV-1L'},
    {'nombre': 'Yerba Mate 500g', 'sku': 'YRB-MAT-500'},
    {'nombre': 'Azúcar 1kg', 'sku': 'AZC-1KG'},
    {'nombre': 'Leche Entera 1L', 'sku': 'LCH-ENT-1L'},
    {'nombre': 'Queso Sardo 300g', 'sku': 'QSO-SAR-300'},
    {'nombre': 'Detergente Líquido 1L', 'sku': 'DTG-LIQ-1L'},
    {'nombre': 'Yogur Bebible 1L', 'sku': 'YGR-BEB-1L'},
    {'nombre': 'Agua Mineral 2L', 'sku': 'AGU-MIN-2L'},
  ];

  Future<DashboardOfflineResponse?> obtenerDashboard({
    required int diasVencimiento,
    required int tick,
  }) async {
    // Latencia simulada para UX (loading).
    await Future<void>.delayed(const Duration(milliseconds: 450));

    final rand = Random(0xDA7A ^ tick);

    final ventasPorHora = List<VentasHoraRow>.generate(24, (h) {
      final peso =
          exp(-pow((h - 12) / 3.2, 2)) + exp(-pow((h - 19) / 3.8, 2)) * 0.75 + 0.18;
      final vari = 0.85 + rand.nextDouble() * 0.35;
      final cantidad = (8 + peso * 18 * vari).round().toDouble();
      final importeProm = 2800 + rand.nextDouble() * 2600;
      final total = (cantidad * importeProm * (0.92 + rand.nextDouble() * 0.22) / 100).roundToDouble() * 100;
      return VentasHoraRow(
        hora: h.toString().padLeft(2, '0') + ':00',
        cantidad: cantidad,
        total: total,
      );
    });

    final totalVentasDia = ventasPorHora.fold<double>(0, (a, r) => a + r.total);
    final ventasDia = ventasPorHora.fold<double>(0, (a, r) => a + r.cantidad);
    final ticketPromedio = ventasDia > 0 ? totalVentasDia / ventasDia : 0.0;

    final productosStockBajoCount = 5 + rand.nextInt(8);
    final productosStockBajo = List<StockBajoItem>.generate(productosStockBajoCount, (i) {
      final p = _productos[(i + rand.nextInt(_productos.length)) % _productos.length];
      final stockMinimo = (5 + rand.nextDouble() * 30).round().toDouble();
      final stockActual = (rand.nextDouble() * (stockMinimo - 1)).roundToDouble();
      return StockBajoItem(
        nombre: p['nombre'] as String,
        sku: p['sku'] as String,
        stockActual: stockActual,
        stockMinimo: stockMinimo,
      );
    });

    final vencimientosCount = 3 + rand.nextInt(7);
    final now = DateTime.now();
    final proximosVencer = List<ProximoVencerItem>.generate(vencimientosCount, (i) {
      final p = _productos[(i + 2 + rand.nextInt(_productos.length)) % _productos.length];
      final diasRestantes = 1 + rand.nextInt(max(1, diasVencimiento));
      final fecha = DateTime(now.year, now.month, now.day).add(Duration(days: diasRestantes));
      return ProximoVencerItem(
        productoNombre: p['nombre'] as String,
        loteCodigo: 'LOTE-${(i + 1).toString().padLeft(2, '0')}-${fecha.month}${fecha.day}',
        fechaVencimiento: '${fecha.year}-${fecha.month.toString().padLeft(2, '0')}-${fecha.day.toString().padLeft(2, '0')}',
        diasRestantes: diasRestantes.toDouble(),
      );
    });

    // Parametrización base del dashboard (mock).
    const objetivoDiario = 500000.0;
    const puntoEquilibrio = 320000.0;

    final gananciaActual = totalVentasDia - puntoEquilibrio;
    final estado = gananciaActual >= 0
        ? 'verde'
        : gananciaActual > -puntoEquilibrio * 0.25
            ? 'amarillo'
            : 'rojo';

    // Pronóstico hoy
    final minutosHoy = (now.hour * 60 + now.minute).toDouble();
    final ritmo = minutosHoy > 0 ? totalVentasDia / minutosHoy : totalVentasDia;
    final minutosMax = 24 * 60;
    final pronosticado = (ritmo * minutosMax * (0.95 + rand.nextDouble() * 0.1) / 100).roundToDouble() * 100;
    final cumplimientoObjPct =
        objetivoDiario > 0 ? (pronosticado / objetivoDiario) * 100 : 0.0;

    final ahoraCumplPE =
        puntoEquilibrio > 0 ? (totalVentasDia / puntoEquilibrio) * 100 : 0.0;

    final valorInventario = (8000000 + rand.nextDouble() * 5000000).roundToDouble();

    final promedioTickets = max(10.0, ventasDia * (0.12 + rand.nextDouble() * 0.08));
    final ingresosPromedio = totalVentasDia * (0.85 + rand.nextDouble() * 0.25);

    // Promedio por día de semana (mock)
    final diaSemana = _diaSemana(now.weekday);
    final ticketsSemana = promedioTickets * (0.9 + rand.nextDouble() * 0.25);
    final ingresosSemana = ingresosPromedio * (0.85 + rand.nextDouble() * 0.3);

    // Margen
    final margenPct = 0.18 + rand.nextDouble() * 0.12;
    final margenValor = totalVentasDia * margenPct;
    final tendenciaPct = -8 + rand.nextDouble() * 16;

    final panelLateral = PanelLateral(
      salud: SaludNegocio(
        estado: estado,
        ingresosActuales: totalVentasDia,
        puntoEquilibrio: puntoEquilibrio,
        objetivoDiario: objetivoDiario,
      ),
      promedioVentas: PromedioVentasDiarias(
        ticketsPromedio: promedioTickets,
        ingresosPromedio: ingresosPromedio,
      ),
      promedioPorDiaSemana: PromedioPorDiaSemana(
        diaSemana: diaSemana,
        ticketsPromedio: ticketsSemana,
        ingresosPromedio: ingresosSemana,
      ),
      pronostico: PronosticoHoy(
        totalPronosticado: pronosticado,
        cumplimientoObjetivoDiarioPct: cumplimientoObjPct,
      ),
      puntoEquilibrio: PuntoEquilibrio(
        valor: puntoEquilibrio,
        cumplimientoPct: ahoraCumplPE,
      ),
      gananciaActual: gananciaActual,
      objetivosGanancia: ObjetivosGanancia(
        objetivoDiario: objetivoDiario,
        objetivoSemanal: objetivoDiario * 7 * (0.9 + rand.nextDouble() * 0.1),
        objetivoMensual: objetivoDiario * 30 * (0.92 + rand.nextDouble() * 0.1),
      ),
      margenPromedio: MargenPromedio(
        margenValor: margenValor,
        tendenciaPct: tendenciaPct,
      ),
    );

    // Caja summary (mock) + saldo teórico de caja.
    final cajaAbierta = rand.nextDouble() > 0.15;
    final cajaId = cajaAbierta ? 120 + rand.nextInt(20) : null;
    final saldoCajaTeorico = (totalVentasDia * (0.86 + rand.nextDouble() * 0.15) / 100).roundToDouble() * 100;

    final comparativos = _comparativosDesde(
      rand: rand,
      ventasDia: ventasDia,
      totalVentasDia: totalVentasDia,
      ticketPromedio: ticketPromedio,
      productosStockBajoCount: productosStockBajoCount,
      valorInventario: valorInventario,
      saldoTeorico: saldoCajaTeorico,
      puntoEquilibrio: puntoEquilibrio,
    );

    final indicadores = DashboardIndicadores(
      ventasDia: ventasDia,
      totalVentasDia: totalVentasDia,
      ticketPromedio: ticketPromedio,
      productosStockBajo: productosStockBajoCount,
      valorInventario: valorInventario,
      saldoCajaTeorico: saldoCajaTeorico,
    );

    return DashboardOfflineResponse(
      caja: CajaSummary(
        cajaAbierta: cajaAbierta,
        cajaId: cajaId,
        saldoTeorico: saldoCajaTeorico,
      ),
      alertas: AlertasOperativas(
        stockBajo: productosStockBajo,
        proximosVencer: proximosVencer,
      ),
      indicadores: indicadores,
      comparativos: comparativos,
      ventasPorHora: ventasPorHora,
      panelLateral: panelLateral,
    );
  }

  List<ComparativoKpi> _comparativosDesde({
    required Random rand,
    required double ventasDia,
    required double totalVentasDia,
    required double ticketPromedio,
    required int productosStockBajoCount,
    required double valorInventario,
    required double saldoTeorico,
    required double puntoEquilibrio,
  }) {
    double ayerFactor() => 0.75 + rand.nextDouble() * 0.25;

    final totalAyer = totalVentasDia * ayerFactor();
    final ventasAyer = ventasDia * ayerFactor();
    final ticketAyer = ticketPromedio * (0.82 + rand.nextDouble() * 0.25);
    final stockBajoAyer = productosStockBajoCount * (0.8 + rand.nextDouble() * 0.3);
    final valorInvAyer = valorInventario * (0.9 + rand.nextDouble() * 0.2);
    final saldoTeoricoAyer = saldoTeorico * (0.86 + rand.nextDouble() * 0.25);

    double variacion(double hoy, double ant) => ant == 0 ? 0 : ((hoy - ant) / ant) * 100;

    return [
      ComparativoKpi(
        kpi: 'Ventas del día',
        valor: ventasDia,
        valorAnterior: ventasAyer,
        variacionPct: variacion(ventasDia, ventasAyer),
      ),
      ComparativoKpi(
        kpi: 'Total vendido',
        valor: totalVentasDia,
        valorAnterior: totalAyer,
        variacionPct: variacion(totalVentasDia, totalAyer),
      ),
      ComparativoKpi(
        kpi: 'Ticket promedio',
        valor: ticketPromedio,
        valorAnterior: ticketAyer,
        variacionPct: variacion(ticketPromedio, ticketAyer),
      ),
      ComparativoKpi(
        kpi: 'Stock bajo',
        valor: productosStockBajoCount.toDouble(),
        valorAnterior: stockBajoAyer,
        variacionPct: variacion(productosStockBajoCount.toDouble(), stockBajoAyer),
      ),
      ComparativoKpi(
        kpi: 'Valor inventario',
        valor: valorInventario,
        valorAnterior: valorInvAyer,
        variacionPct: variacion(valorInventario, valorInvAyer),
      ),
      ComparativoKpi(
        kpi: 'Saldo teórico caja',
        valor: saldoTeorico,
        valorAnterior: saldoTeoricoAyer,
        variacionPct: variacion(saldoTeorico, saldoTeoricoAyer),
      ),
    ];
  }

  String _diaSemana(int weekday) {
    // 1=Lunes ... 7=Domingo
    const dias = {
      1: 'Lunes',
      2: 'Martes',
      3: 'Miércoles',
      4: 'Jueves',
      5: 'Viernes',
      6: 'Sábado',
      7: 'Domingo',
    };
    return dias[weekday] ?? 'Día';
  }
}

