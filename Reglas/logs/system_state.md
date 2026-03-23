# system_state.md — Punto de Venta

**Última actualización:** 2026-03-18 (Iteración 23 — Módulo 3 Tesorería + Módulo 5 Inventario)
**Origen:** Auditoría basada en `Devs/backend` + `Devs/tests`.

---
## Progreso global (aprox.)

- **Proyecto total:** ~98%
- **Backend total:** ~98%
- **Modelo de datos:** ~97%
- **Tests:** ~100% (624 pasando)
- **Frontend total:** NO APLICABLE (gestionado por otro agente)

---
## Estado por módulo (aprox.)

| Módulo | Estado | Backend | Modelo | Tests | Nivel backend aprox. |
|--------|---------|---------|--------|--------|----------------------|
| 1 Dashboard | STABLE | ~99% | ~75% | ~99% | ~99% |
| 2 Punto de Venta | STABLE | ~100% | ~85% | ~100% | ~100% |
| 3 Tesorería | STABLE | ~98% | ~80% | ~98% | ~98% |
| 4 Finanzas | COMPLETE | ~100% | ~80% | ~100% | ~100% |
| 5 Inventario | STABLE | ~97% | ~90% | ~97% | ~97% |
| 6 Personas | STABLE | ~99% | ~82% | ~99% | ~99% |
| 7 Reportes | STABLE | ~99% | ~82% | ~99% | ~99% |
| 8 Integraciones | STABLE | ~92% | ~72% | ~92% | ~92% |
| 9 Configuración | STABLE | ~99% | ~88% | ~99% | ~99% |

---
## Funcionalidades implementadas (iteración actual — Iteración 23)

### Módulo 3 — Tesorería / Finanzas (CuentaFinanciera completo)

**Modelo `CuentaFinanciera` actualizado:**
- Nuevos campos: `estado` (activa/inactiva), `observaciones`

**Servicio `finanzas.py` (nuevas funciones):**
- `actualizar_cuenta` — PATCH parcial de nombre, tipo, estado, observaciones
- `transferir_entre_cuentas` — crea GASTO en origen + INGRESO en destino; valida saldo, estado activa

**Nuevos endpoints:**
- `POST /api/finanzas/cuentas/transferir` — Transferencia entre cuentas (§8 Tesorería)
- `PATCH /api/finanzas/cuentas/{id}` — Actualización parcial de cuenta
- `GET /api/finanzas/cuentas?estado=` — Filtro por estado activa/inactiva

**Schemas actualizados:**
- `CuentaFinancieraResponse` incluye `estado` y `observaciones`
- Nuevos Pydantic models: `CrearCuentaRequest`, `ActualizarCuentaRequest`, `TransferirEntreCuentasRequest/Response`

### Módulo 5 — Inventario (Categorías completo + Importación masiva)

**Servicio `inventario.py` (nuevas funciones):**
- `eliminar_categoria` — elimina con validación (rechaza si tiene productos o subcategorías)
- `importar_productos` — bulk create/update por SKU con contadores y errores parciales

**Nuevos endpoints:**
- `DELETE /api/inventario/categorias/{id}` — Eliminar categoría (204/400/404)
- `POST /api/inventario/productos/importar` — Importación masiva JSON (§9 Módulo 5)

**Fix de deuda técnica:**
- `ProductoCreate` ahora acepta `categoria_id` y `subcategoria_id`
- `crear_producto` servicio persiste `categoria_id` y `subcategoria_id`
- `PATCH /productos/{id}` y `crear_producto` alineados

### Módulo 2 — Pesables (iteración anterior — Iteración 22)

- Fix bug: `precio_unitario` en `ItemVenta` pesable ahora es precio/kg (no precio_total)
- `GET /pesables/productos` — lista productos habilitados como pesables
- `DELETE /pesables/items/{id}` — cancelar ítem en estado pending
- `GET /productos?pesable=true|false` — filtro por pesable en listado de productos

---
## Brechas y pendientes

**Módulo 3 (Tesorería) — pendiente menor:**
- No existe una entidad explícita de "transferencia" (las transferencias se registran como 2 transacciones relacionadas por descripción).

**Módulo 5 (Inventario) — pendiente menor:**
- Unidades logísticas (pack/caja/bulto) — no implementadas (feature avanzado, no crítico)
- Históricos de precios/costos como entidad separada — no implementada

**Módulo 8 (Integraciones) — ~92% backend:**
- Mensajería (WhatsApp/Email/SMS) — flujo básico existe pero no hay integración real con proveedor externo
- E-commerce sync — no implementado (avanzado, depende de integración externa)

---
## Total de tests

**624 tests pasando** (py -m pytest — 2026-03-18)

Tests nuevos en esta iteración (+27):
- `test_finanzas.py`: +17 (CuentaFinanciera estado/obs, actualizar_cuenta, transferir entre cuentas)
- `test_inventario.py`: +10 (eliminar_categoria, importar_productos)

---
## Próximo paso sugerido

Auditar **Módulo 8 (Integraciones ~92%)** para identificar brechas concretas en:
- Configuración de dispositivos hardware (impresoras, balanzas)
- Estadísticas y alertas de integración
- Mensajería digital (flujo de comprobante digital completo)

Alternativamente, auditar **Módulo 1 (Dashboard ~99%)** para cerrar el 1% restante.
