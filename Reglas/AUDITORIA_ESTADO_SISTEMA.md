# Informe de Auditoría — Estado del Sistema Punto de Venta

**Tipo:** Auditoría de arquitectura y nivel de desarrollo  
**Alcance:** Backend, frontend, modelo de datos, tests e integración entre módulos  
**Fuentes:** Documentación en `Reglas/`, código en `Devs/`, documentación funcional en `Reglas/docs/`  
**Fecha de referencia:** Marzo 2026  

---

## Estado general del sistema

El sistema es **principalmente backend**: API REST operativa, modelo de datos implementado, servicios de dominio por módulo y 94 tests pasando. El frontend está sin desarrollar (solo estructura de carpetas). La integración entre módulos se realiza vía llamadas directas entre servicios y un bus de eventos in-process (solo **VentaRegistrada** con handlers para inventario y tesorería).

**Porcentaje total aproximado del proyecto:** **42–48 %**

- **Backend:** ~65 % (núcleo operativo y analítica básica hecha; Configuración e Integraciones mínimos).
- **Frontend:** 0 % (carpetas `ui/` y `components/` vacías).
- **Base de datos / modelo:** ~75 % (entidades core alineadas con DATA_MODEL; faltan cliente en venta, roles Cliente/Empleado/Proveedor explícitos).
- **Tests:** ~45 % (94 tests; buena cobertura en ventas, caja, productos, personas, reportes, finanzas, configuración; mínima en dashboard e integraciones).
- **Integración entre módulos:** ~50 % (flujo venta → inventario y caja; evento VentaRegistrada; resto de eventos de EVENTOS.md no implementados).

---

## Auditoría por módulo

### Módulo 1 — Dashboard

**Nivel de desarrollo total:** 35 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 70  | Un endpoint: GET `/api/dashboard/indicadores`. Servicio `indicadores_hoy`: ventas del día, ticket promedio, caja abierta, saldo teórico, productos con stock bajo, valor inventario. |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | 100 | No tiene entidades propias; consume Venta, Caja, Stock, Producto. |
| Tests          | 25  | 1 test que valida estructura JSON del indicador. |

**Funcionalidades implementadas**

- Indicadores del día: cantidad de ventas, total ventas, ticket promedio, caja abierta, saldo caja teórico, productos con stock bajo, valor inventario.

**Funcionalidades faltantes (según docs)**

- KPIs con comparación vs período anterior y variación porcentual.
- Gráfico de ventas del día por hora (barras + línea).
- Alertas operativas: productos próximos a vencer, productos con stock bajo en tabla detallada.
- Panel lateral con tarjetas de estado.

**Problemas detectados**

- Un solo test; sin tests de borde (sin ventas, sin caja, etc.).
- Documentación del Dashboard más rica que lo implementado (gráficos, tendencias, rankings).

---

### Módulo 2 — Punto de Venta (Ventas)

**Nivel de desarrollo total:** 78 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 85  | POST venta (ítems, descuento, método de pago), GET por id, GET listado. Integración con caja abierta, inventario (descuento) y movimiento de caja automático. Emisión de evento VentaRegistrada. |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | 80  | Venta, ItemVenta. Falta `cliente_id` (DATA_MODEL y docs exigen cliente en venta). |
| Tests          | 75  | 13 tests (registro, ítems, descuento, validaciones, integración caja/inventario). |

**Funcionalidades implementadas**

- Registrar venta con ítems, descuento y método de pago.
- Asignación a caja abierta si existe.
- Descuento de stock por venta.
- Movimiento de caja automático (tipo VENTA).
- Emisión de evento VentaRegistrada.
- Consulta por ID y listado de ventas.

**Funcionalidades faltantes**

- Asociar venta a **cliente** (no existe `cliente_id` en modelo).
- Comprobantes / tickets (impresión o generación).
- Múltiples métodos de pago en una misma venta (modelo tiene un solo `metodo_pago` y `detalle_pagos` texto).
- Submódulos documentados: Caja (parcialmente en Tesorería), Operaciones comerciales, Pesables (no implementados en este módulo).

**Problemas detectados**

- Inconsistencia con DATA_MODEL: venta sin `cliente_id` ni `empleado_id` (se usa `usuario_id`).
- Documentación funcional (wireframes POS, operaciones comerciales) sin reflejo en backend.

---

### Módulo 3 — Tesorería

**Nivel de desarrollo total:** 82 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 90  | Apertura/cierre de caja, GET caja abierta, listado cajas, movimientos (POST/GET), resumen caja. Integración: venta registra movimiento tipo VENTA. |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | 95  | Caja, MovimientoCaja; tipos INGRESO, EGRESO, VENTA. |
| Tests          | 80  | 15 tests (abrir, cerrar, movimientos, resumen, integración con ventas). |

**Funcionalidades implementadas**

- Apertura y cierre de caja.
- Obtener caja abierta, por ID y listado.
- Registrar movimientos (ingreso, egreso, venta) y listar por caja.
- Resumen de caja (saldo teórico, total ingresos/egresos/ventas).

**Funcionalidades faltantes**

- Arqueo de caja formal (conteo físico vs teórico y diferencias).
- Eventos CajaAbierta, CajaCerrada, MovimientoCajaRegistrado (no emitidos explícitamente; lógica sí existe).
- Cuentas corrientes y cobros (documentación Módulo 2 – Caja).

**Problemas detectados**

- Ninguno crítico. Módulo sólido para el flujo actual.

---

### Módulo 4 — Finanzas

**Nivel de desarrollo total:** 55 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 65  | CRUD cuentas, registrar transacción (ingreso/gasto), listar transacciones, resumen cuenta, evolución de saldo. |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | 90  | CuentaFinanciera, TransaccionFinanciera. |
| Tests          | 60  | 16 tests (cuentas, transacciones, resumen, evolución saldo, validaciones). |

**Funcionalidades implementadas**

- Listar y crear cuentas financieras.
- Obtener cuenta por ID.
- Registrar transacciones (ingreso/gasto) y actualización de saldo.
- Listar transacciones con filtros.
- Resumen de cuenta y evolución de saldo en rango de fechas.

**Funcionalidades faltantes (según docs y ROADMAP)**

- Cuentas por pagar / por cobrar como flujos diferenciados.
- Conciliaciones.
- Vinculación automática con ventas/tesorería (eventos IngresoRegistrado, GastoRegistrado no implementados).
- Análisis de flujo de caja, rentabilidad y liquidez (documentación funcional).

**Problemas detectados**

- Módulo usable pero aún no integrado por eventos con Ventas/Tesorería.
- Documentación del módulo más amplia (balances, indicadores) que lo implementado.

---

### Módulo 5 — Inventario

**Nivel de desarrollo total:** 58 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 60  | Ingreso de stock (POST), GET stock por producto. Servicio de productos (CRUD) en módulo Productos; descuento por venta en servicio inventario. |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | 85  | Producto, CategoriaProducto, Stock, MovimientoInventario. Tipos de movimiento definidos en modelo. |
| Tests          | 35  | 3 tests (ingreso stock, GET stock, integración con venta). |

**Funcionalidades implementadas**

- Ingreso de stock por producto (y ubicación).
- Consulta de stock por producto.
- Descuento automático de stock al registrar venta.
- Modelo con movimientos (VENTA, COMPRA, AJUSTE, etc.) y Stock por ubicación.

**Funcionalidades faltantes (según docs y ROADMAP)**

- API de movimientos de inventario (listar, ajustes manuales).
- Alertas de stock mínimo (solo usado en Dashboard como conteo).
- Historial de movimientos por producto.
- Categorías: modelo existe; no hay API CRUD de categorías.
- Control de proveedores, vencimientos, rotación (doc. funcional).
- Múltiples sucursales/depósitos (modelo permite ubicación; no hay ABM de ubicaciones).

**Problemas detectados**

- Pocos tests para el peso del módulo en el flujo de ventas.
- Documentación de inventario muy superior a lo implementado (cargas, históricos, reposiciones).

---

### Módulo 6 — Personas

**Nivel de desarrollo total:** 52 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 70  | CRUD genérico de Persona (listar, obtener, crear, PATCH). Sin distinción Cliente/Empleado/Proveedor en API. |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | 50  | Una sola entidad Persona (nombre, apellido, documento, teléfono, activo). DATA_MODEL y docs exigen Cliente, Empleado, Proveedor. |
| Tests          | 70  | 7 tests de API de personas. |

**Funcionalidades implementadas**

- Listar, obtener por ID, crear y actualizar Persona.
- Uso de usuario_id en Venta (no de “empleado” como rol de persona).

**Funcionalidades faltantes**

- Entidades o roles diferenciados: Cliente, Empleado, Proveedor (documentación y DATA_MODEL).
- Contactos asociados a personas.
- Historial de compras por cliente.
- Vinculación venta–cliente (cliente_id en Venta).
- Usuarios del sistema y roles están en Configuración, no en Personas (coherente con estructura actual).

**Problemas detectados**

- **Inconsistencia importante:** documentación y DATA_MODEL definen tres entidades (Cliente, Empleado, Proveedor); el código tiene una sola tabla Persona sin roles. Esto bloquea ventas con cliente y reportes por cliente.

---

### Módulo 7 — Reportes

**Nivel de desarrollo total:** 62 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 70  | Ventas por día, por producto, por empleado, evolución diaria, resumen rango, inventario valorizado. Validación de rango de fechas. |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | 100 | Solo consumo de datos de otros módulos. |
| Tests          | 75  | 14 tests (todos los endpoints y validación fecha_desde/fecha_hasta). |

**Funcionalidades implementadas**

- Ventas por día (cantidad, total, ticket promedio).
- Ventas por producto en rango (cantidad vendida, total).
- Ventas por empleado (usuario_id) en rango.
- Evolución diaria de ventas en rango.
- Resumen de ventas en rango (cantidad, total, ticket promedio).
- Inventario valorizado (por producto y total).
- Validación fecha_desde ≤ fecha_hasta en todos los reportes con rango.

**Funcionalidades faltantes (según docs)**

- Sección Análisis: tendencias por semana/mes, análisis por franja horaria, rankings (más vendidos, margen, merma, clientes rentables, proveedores).
- Reportes por Caja, Clientes, Proveedores.
- Margen por producto (requiere costo en producto).
- Exportación (PDF/Excel) no definida en código.

**Problemas detectados**

- ventas_por_empleado devuelve empleado_nombre: null (no se resuelve nombre desde Usuario/Persona).
- Documentación de Reportes muy amplia (gráficos, rankings, comparativas) frente a lo implementado.

---

### Módulo 8 — Configuración

**Nivel de desarrollo total:** 40 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 45  | Usuarios: listar, obtener por ID, crear, PATCH activo. Roles: listar, obtener por ID, crear. Sin permisos granulares ni parámetros de negocio. |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | 70  | Usuario, Rol. Relación usuario–rol existe en modelo. |
| Tests          | 75  | 14 tests (CRUD usuarios/roles, 404, PATCH activo). |

**Funcionalidades implementadas**

- CRUD básico de usuarios (sin PATCH completo de todos los campos).
- CRUD de roles (listar, obtener, crear).
- Activación/desactivación de usuario (PATCH activo).

**Funcionalidades faltantes (según docs)**

- Submódulos: Empresa (datos del negocio, CUIT, dirección, logo), Sucursales, Facturación, Medios de pago, Caja, Inventario, POS, Integraciones, Sistema.
- Permisos por rol y auditoría de acciones.
- Parámetros de negocio (impuestos, comportamientos POS).

**Problemas detectados**

- Configuración documentada es mucho más que usuarios y roles; el resto no está implementado.
- No hay endpoint para “parámetros globales” ni para asignación explícita de rol a usuario en API (puede existir en modelo).

---

### Módulo 9 — Integraciones

**Nivel de desarrollo total:** 8 %

| Aspecto        | %   | Comentario |
|----------------|-----|------------|
| Backend        | 10  | Un endpoint: GET `/api/integraciones/estado` (placeholder: facturación electrónica y pasarelas en false). |
| Frontend       | 0   | Sin desarrollo. |
| Base de datos  | N/A | Sin entidades propias. |
| Tests          | 15  | 1 test que comprueba estructura del JSON de estado. |

**Funcionalidades implementadas**

- Respuesta de estado de integraciones (facturación_electronica, pasarelas_pago) como “no configurado”.

**Funcionalidades faltantes (según docs)**

- Integraciones fiscales (AFIP/ARCA, factura electrónica).
- Hardware POS (impresoras, lectores).
- Pasarelas de pago reales.
- Mensajería, tienda/e-commerce, integración contable, API externa, backups, logs de integración.

**Problemas detectados**

- Módulo es solo un placeholder; no hay integraciones reales ni eventos consumidos (p. ej. VentaRegistrada para facturación).

---

## Ranking de módulos más avanzados

1. **Tesorería** — ~82 %: Flujo completo de caja, movimientos, resumen e integración con ventas.
2. **Punto de Venta (Ventas)** — ~78 %: Registro de ventas, ítems, descuento, caja, inventario y evento.
3. **Reportes** — ~62 %: Varios reportes de ventas e inventario y validaciones.
4. **Inventario** — ~58 %: Stock y movimientos por venta; falta API de movimientos y categorías.
5. **Finanzas** — ~55 %: Cuentas y transacciones con resumen y evolución de saldo.
6. **Personas** — ~52 %: CRUD de Persona; falta modelo Cliente/Empleado/Proveedor.
7. **Configuración** — ~40 %: Usuarios y roles básicos.
8. **Dashboard** — ~35 %: Un indicador agregado; sin gráficos ni alertas.
9. **Integraciones** — ~8 %: Solo endpoint de estado placeholder.

---

## Módulos más incompletos

1. **Integraciones** — Casi todo por hacer (fiscales, hardware, pagos, mensajería, etc.).
2. **Dashboard** — Falta la mayor parte de la documentación (gráficos, KPIs comparativos, alertas).
3. **Configuración** — Solo usuarios y roles; faltan empresa, sucursales, facturación, medios de pago, etc.
4. **Personas** — Modelo unificado Persona sin roles; faltan Cliente/Empleado/Proveedor y venta–cliente.
5. **Inventario** — Faltan API de movimientos, categorías, alertas y flujos avanzados.

---

## Deuda técnica detectada

1. **Modelo de datos vs documentación**
   - **Venta:** DATA_MODEL y DOMINIOS indican `cliente_id` y `empleado_id`; en código solo `usuario_id` y `caja_id`. No se puede asociar venta a cliente.
   - **Personas:** DATA_MODEL y docs definen Cliente, Empleado, Proveedor; código tiene una sola entidad Persona sin roles ni tipos.

2. **Eventos (EVENTOS.md)**
   - Solo se implementa **VentaRegistrada** (y handlers para inventario y caja).
   - No se emiten: PagoRegistrado, CajaAbierta, CajaCerrada, MovimientoCajaRegistrado, ProductoCreado, StockActualizado, InventarioAjustado, IngresoRegistrado, GastoRegistrado, ClienteCreado, EmpleadoCreado, UsuarioCreado, RolActualizado.
   - El bus es in-process y no está documentado qué handlers están registrados al arranque.

3. **FastAPI**
   - Uso de `@app.on_event("startup")` (deprecado); se recomienda migrar a lifespan.

4. **Frontend**
   - Estructura vacía; no hay ninguna pantalla ni integración con la API.

5. **Reportes**
   - ventas_por_empleado no devuelve nombre del empleado (empleado_nombre: null).
   - No hay reportes por cliente (depende de cliente_id en Venta).

6. **Configuración**
   - No hay API para parámetros de empresa, sucursales, medios de pago ni impuestos.

7. **Tests**
   - Dashboard e Integraciones con un test cada uno.
   - Inventario con solo 3 tests para un módulo crítico.
   - No hay tests de integración end-to-end (flujo completo venta → inventario → caja → evento).

8. **Documentación**
   - REPOSITORY_INDEX.md indica 53 tests; en realidad hay 94 (desactualizado).
   - MODULE_STATUS.md indica estados (LOCKED, LOCK_CANDIDATE, IN_PROGRESS) que no coinciden con esta auditoría porcentual (por ejemplo, Integraciones en IN_PROGRESS pero nivel ~8 %).

---

## Recomendaciones de desarrollo

**Prioridad 1 – Alinear modelo y núcleo**

- Añadir **cliente_id** (opcional) a Venta y, si se mantiene modelo unificado, definir cómo se relaciona Persona como cliente (p. ej. tipo o rol). Esto habilita reportes por cliente y cumplimiento con DATA_MODEL.
- Decidir modelo de Personas: ya sea entidades Cliente/Empleado/Proveedor o roles/tipos sobre Persona, y documentarlo en DATA_MODEL y DOMINIOS.
- Completar **Reportes**: resolver nombre en ventas_por_empleado (join con Usuario/Persona) y, con cliente_id, reporte de ventas por cliente.

**Prioridad 2 – Estabilidad y calidad**

- Aumentar tests en **Inventario** (movimientos, categorías cuando existan API) y en **Dashboard** (casos sin datos, sin caja).
- Migrar startup de FastAPI a **lifespan** para eliminar deprecación.
- Registrar en documentación los **handlers de eventos** (qué escucha VentaRegistrada y dónde).

**Prioridad 3 – Cerrar brechas funcionales**

- **Configuración:** al menos datos de Empresa y Medios de pago si el negocio lo requiere para comprobantes.
- **Dashboard:** segundo paso: ventas por hora (para gráfico) y listado de productos con stock bajo; después comparativas y alertas de vencimiento si el modelo de productos lo soporta.
- **Inventario:** API de movimientos (listar por producto/rango) y de categorías (CRUD), y alertas de stock mínimo explícitas.

**Prioridad 4 – Integraciones y frontend**

- **Integraciones:** mantener placeholder hasta definir primera integración real (p. ej. facturación electrónica o impresora); entonces exponer configuración y consumo de eventos.
- **Frontend:** iniciar por pantallas que consuman la API ya establecida: listado de productos, registro de venta, caja abierta/cierre, indicadores del dashboard.

**Orden sugerido para maximizar avance**

1. Modelo: cliente en venta + aclaración Personas (Cliente/Empleado/Proveedor o roles).
2. Reportes: nombre en ventas por empleado y reporte por cliente cuando exista cliente_id.
3. Tests: Inventario y Dashboard.
4. Configuración: empresa y medios de pago (mínimo viable).
5. Dashboard: ventas por hora y lista de productos con stock bajo.
6. Inventario: API movimientos y categorías.
7. Frontend: pantallas mínimas de POS y caja.
8. Integraciones: cuando se defina la primera integración real.

---

*Informe generado a partir de la documentación en `Reglas/`, código en `Devs/` y documentación funcional en `Reglas/docs/` (Módulos 1–9).*
