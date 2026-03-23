
---

## 2026-03-19 — Iteración Módulo 7: Reportes — Brechas funcionales

**Fecha:** 2026-03-19
**Iteración:** Backend Módulo 7 (Reportes)
**Módulo trabajado:** Reportes
**Avance del módulo:** ~93% -> ~99%

**Brechas resueltas:**
- §9: endpoint ventas-por-categoria
- §7: endpoint ventas-canceladas
- §10: endpoints inventario-bajo-minimo y mermas
- §6: consolidado-diario enriquecido con ventas_fiadas, cancelaciones, clientes_activos, unidades_vendidas, productos_distintos, margen_estimado

**Archivos modificados:**
- backend/services/reportes.py: 4 nuevas funciones + consolidado enriquecido
- backend/api/routers/reportes.py: 4 nuevos endpoints + CSV actualizado
- tests/test_reportes.py: 9 nuevos tests

**Resultado:** py -m pytest => 456 passed, 2 warnings
---

## 2026-03-19 - Iteracion Modulo 4: Finanzas - Brechas funcionales

Fecha: 2026-03-19
Iteracion: Backend Modulo 4 (Finanzas)
Modulo trabajado: Finanzas
Avance del modulo: ~85% -> ~99%

Brechas resueltas:
- Sec 6: flujo-caja-agrupado por dia/semana/mes con saldo_acumulado
- Sec 10: balances-diarios y balances-anuales
- Sec 9: rentabilidad/periodo (margen bruto+neto por periodo) con CSV export
- Sec 11: indicadores-avanzados (liquidez, margen_ganancia_pct, ticket_promedio)

Archivos modificados:
- backend/services/finanzas.py: imports date_type, Any; helper _agg_transacciones_por_expr;
  funciones obtener_balances_diarios, obtener_balances_anuales, obtener_flujo_caja_agrupado,
  rentabilidad_por_periodo, obtener_indicadores_avanzados
- backend/api/routers/finanzas.py: 5 nuevos endpoints: /balances-diarios,
  /balances-anuales, /flujo-caja-agrupado, /rentabilidad/periodo, /indicadores-avanzados
- tests/test_finanzas.py: 17 nuevos tests

Tests creados:
test_balances_diarios_sin_datos, test_balances_diarios_csv_sin_datos,
test_balances_diarios_con_transacciones, test_balances_anuales_sin_datos,
test_balances_anuales_csv_sin_datos, test_balances_anuales_con_transacciones,
test_flujo_caja_agrupado_sin_datos, test_flujo_caja_agrupado_agrupacion_invalida,
test_flujo_caja_agrupado_csv_sin_datos, test_flujo_caja_agrupado_con_transacciones,
test_flujo_caja_agrupado_semana, test_rentabilidad_periodo_sin_ventas,
test_rentabilidad_periodo_csv_sin_ventas, test_rentabilidad_periodo_agrupacion_invalida,
test_rentabilidad_periodo_con_ventas, test_indicadores_avanzados_sin_datos,
test_indicadores_avanzados_con_transacciones

Resultado: py -m pytest => 473 passed, 2 warnings