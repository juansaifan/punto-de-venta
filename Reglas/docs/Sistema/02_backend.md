# 02 — Backend

## Estructura de Carpetas

```
Devs/backend/
├── __init__.py
├── events.py              # Bus de eventos in-process
├── api/
│   ├── app.py             # Aplicación FastAPI, startup, routers
│   ├── deps.py            # Dependencias FastAPI (get_db)
│   ├── routers/           # Endpoints REST por dominio
│   │   ├── auditoria_eventos.py
│   │   ├── caja.py
│   │   ├── compras.py
│   │   ├── configuracion.py
│   │   ├── cuentas_corrientes.py
│   │   ├── dashboard.py
│   │   ├── finanzas.py
│   │   ├── integraciones.py
│   │   ├── inventario.py
│   │   ├── operaciones_comerciales.py
│   │   ├── personas.py
│   │   ├── pesables.py
│   │   ├── productos.py
│   │   ├── reportes.py
│   │   ├── solicitudes_compra.py
│   │   └── ventas.py
│   └── schemas/           # Pydantic (request/response)
│       ├── caja.py
│       ├── cuentas_corrientes.py
│       ├── finanzas.py
│       ├── inventario.py
│       ├── operaciones_comerciales.py
│       ├── persona.py
│       ├── pesables.py
│       ├── producto.py
│       └── venta.py
├── config/
│   └── settings.py        # Configuración central
├── consumers/             # Handlers de eventos
│   ├── cuentas_corrientes_auditoria.py
│   ├── finanzas_auditoria.py
│   ├── inventario_auditoria.py
│   └── operaciones_comerciales_auditoria.py
├── database/
│   ├── base.py            # DeclarativeBase SQLAlchemy
│   └── sesion.py          # Motor, sesión, inicialización
├── models/                # Entidades SQLAlchemy
│   ├── caja.py
│   ├── compra.py
│   ├── configuracion.py
│   ├── eventos.py
│   ├── finanzas.py
│   ├── integracion.py
│   ├── inventario.py
│   ├── operaciones_comerciales.py
│   ├── pagos.py
│   ├── persona.py
│   ├── pesables.py
│   ├── producto.py
│   ├── rol.py
│   ├── solicitud_compra.py
│   ├── usuario.py
│   └── venta.py
└── services/              # Lógica de negocio
    ├── alertas_inventario.py
    ├── auditoria_eventos.py
    ├── caja_tickets.py
    ├── compras.py
    ├── configuracion.py
    ├── cuentas_corrientes.py
    ├── dashboard.py
    ├── empleados_usuarios.py
    ├── finanzas.py
    ├── integraciones.py
    ├── inventario.py
    ├── operaciones_comerciales.py
    ├── personas.py
    ├── personas_usuarios.py
    ├── pesables.py
    ├── productos.py
    ├── reportes.py
    ├── reposicion_automatica.py
    ├── solicitudes_compra.py
    ├── tesoreria.py
    └── ventas.py
```

---

## Módulos y Responsabilidades

### `ventas.py` (service)
- `registrar_venta()` — Crea venta con ítems. Soporta dos modos:
  - **TEU_ON**: cobra en el momento, estado = PAGADA
  - **TEU_OFF**: queda en cola, estado = PENDIENTE
- Valida crédito en cuenta corriente si `metodo_pago == CUENTA_CORRIENTE`
- `agregar_item_a_venta()`, `eliminar_item_de_venta()`, `actualizar_item_de_venta()` — Edición del carrito (solo en PENDIENTE)
- `aplicar_descuento_a_venta()` — Descuento global
- `suspender_venta_pendiente()`, `reanudar_venta_suspensada()` — Pausa/reanuda
- `cancelar_venta()` — Solo para PENDIENTE o SUSPENDIDA
- `agregar_pesable_por_barcode()` — Integración con pesables (EAN-13)
- `buscar_ventas()` — Búsqueda por ticket, cliente, DNI o producto

### `tesoreria.py` (service)
- `abrir_caja()` — Una única caja abierta a la vez
- `cerrar_caja()` — Con validación de arqueo configurable
- `registrar_movimiento_caja()` — VENTA, INGRESO, GASTO, RETIRO, DEVOLUCION
- `obtener_resumen_caja()` — Arqueo teórico (saldo_inicial + ingresos - egresos)
- `exportar_movimientos_caja_csv()` — Exportación CSV
- `resumen_global_cajas()` — Estadísticas históricas

### `caja_tickets.py` (service)
- `listar_tickets_pendientes()` — Cola de ventas TEU_OFF pendientes de cobro
- `cobro_ticket()` — Procesa cobro con uno o más métodos de pago (pagos combinados)
  - Valida que haya caja abierta
  - Soporta `CUENTA_CORRIENTE` (registra deuda del cliente)
  - Crea `PaymentTransaction` por cada método de pago
  - Emite evento `PagoRegistrado`

### `inventario.py` (service)
- `descontar_stock_por_venta()` — Reduce stock en GONDOLA
- `ingresar_stock()` — Entrada de stock por compra u otro motivo
- `transferir_stock()` — Mueve stock entre ubicaciones (DEPOSITO ↔ GONDOLA)
- `ajustar_stock_por_conteo()` — Reconcilia diferencias en conteo manual
- `listar_checklist_conteo_manual()` / `listar_checklist_conteo_rotativo()` — Generan planillas de conteo
- `rotacion_stock()` — Análisis de rotación por período
- `ranking_mermas()` — Productos con mayor merma
- `valorizacion_inventario()` — Valor del inventario (stock × costo)
- `productos_bajo_punto_reorden()` — Alertas de reposición
- `importar_productos()` — Carga masiva (create or update por SKU)

### `pesables.py` (service)
- `preparar_item()` — Registra ítem pesable (peso + PLU) y genera barcode EAN-13
- El barcode se codifica con precio total en el estándar EAN-13 de balanzas
- El ítem pasa por estados: `pending` → `printed` → `used`

### `personas.py` / `personas_usuarios.py` (service)
- ABM de `Persona` base con roles: `Cliente`, `Proveedor`, `Empleado`, `Contacto`
- `personas_usuarios.py` vincula `Persona` → `Usuario`

### `cuentas_corrientes.py` (service)
- `registrar_movimiento_cuenta_corriente()` — Tipos: VENTA (aumenta deuda), PAGO (reduce), AJUSTE
- Validación de límite de crédito antes de registrar deuda

### `operaciones_comerciales.py` (service)
- `ejecutar_operacion()` — Crea `OperacionComercial` con detalle de ítems
- Tipos: DEVOLUCION, CAMBIO_PRODUCTO, NOTA_CREDITO, NOTA_DEBITO, CREDITO_CUENTA_CORRIENTE, ANULACION
- Las devoluciones reintegran stock al inventario

### `integraciones.py` (service)
- Catálogo de 8 tipos de integración (ver `06_integrations.md`)
- `configurar_activo()`, `guardar_config()`, `registrar_log()`, `probar_conexion()`
- `ejecutar_flujo_alternativo_sin_impresora()` — Captura cliente y envía comprobante digital
- `exportacion_contable()` — Exporta ventas y movimientos de caja para sistemas contables
- `reconciliar_pagos_pasarela()` — Conciliación contra pasarelas externas
- `ejecutar_backup()` — Backup simulado (en memoria + log)

### `auditoria_eventos.py` (service)
- `registrar_evento()` — Persiste `EventoSistemaLog` con nombre, módulo, entidad y payload JSON

### `dashboard.py` (service)
- KPIs de ventas del día, caja activa, productos sin stock, lotes por vencer

### `reportes.py` (service)
- Reportes de ventas por período, por producto, por vendedor, etc.

### `configuracion.py` (service)
- `get_configuracion_caja()` — Lee parámetros de caja (obligar_arqueo, permitir_cierre_con_diferencia, etc.)
- `get_configuracion_integraciones()` — Lee credenciales fiscales

---

## Endpoints Principales por Router

Todos bajo el prefijo `/api`.

### `/api/ventas`
| Método | Ruta | Acción |
|---|---|---|
| POST | `/ventas` | Registrar venta (TEU_ON o TEU_OFF) |
| GET | `/ventas` | Listar ventas con filtros |
| GET | `/ventas/buscar` | Búsqueda por ticket/cliente/producto |
| GET | `/ventas/{id}` | Obtener venta |
| POST | `/ventas/{id}/cancelar` | Cancelar venta |
| POST | `/ventas/{id}/suspender` | Suspender venta |
| POST | `/ventas/{id}/reanudar` | Reanudar venta suspendida |
| POST | `/ventas/{id}/items` | Agregar ítem al carrito |
| PATCH | `/ventas/{id}/items/{item_id}` | Actualizar ítem |
| DELETE | `/ventas/{id}/items/{item_id}` | Eliminar ítem |
| PATCH | `/ventas/{id}/descuento` | Aplicar descuento global |
| POST | `/ventas/{id}/items/pesable-barcode` | Agregar pesable por EAN-13 |
| GET | `/ventas/pesable/resolver-barcode` | Preview de barcode pesable |

### `/api/caja` (Tesorería)
| Método | Ruta | Acción |
|---|---|---|
| POST | `/caja/abrir` | Abrir caja |
| POST | `/caja/{id}/cerrar` | Cerrar caja |
| GET | `/caja/abierta` | Obtener caja activa |
| GET | `/caja/{id}/resumen` | Arqueo teórico |
| POST | `/caja/{id}/movimientos` | Registrar movimiento |
| GET | `/caja/{id}/movimientos` | Listar movimientos |
| GET | `/caja/{id}/tickets-pendientes` | Cola TEU_OFF |
| POST | `/caja/tickets/{venta_id}/cobrar` | Cobrar ticket pendiente |

### `/api/productos`
| Método | Ruta | Acción |
|---|---|---|
| POST | `/productos` | Crear producto |
| GET | `/productos` | Listar productos |
| GET | `/productos/{id}` | Obtener producto |
| PUT | `/productos/{id}` | Actualizar producto |
| DELETE | `/productos/{id}` | Desactivar producto |

### `/api/inventario`
| Método | Ruta | Acción |
|---|---|---|
| GET | `/inventario/stock` | Distribución de stock |
| POST | `/inventario/ingresar` | Ingresar stock |
| POST | `/inventario/transferir` | Transferir entre ubicaciones |
| POST | `/inventario/ajustar` | Ajuste por conteo |
| GET | `/inventario/movimientos` | Historial de movimientos |
| GET | `/inventario/valorizacion` | Valorización del inventario |
| GET | `/inventario/rotacion` | Análisis de rotación |

### `/api/personas`
- ABM de personas con roles (cliente, proveedor, empleado, contacto)

### `/api/finanzas`
- ABM de cuentas financieras y transacciones

### `/api/integraciones`
- Gestión de integraciones, logs, prueba de conexión, backup, exportación contable

### `/api/configuracion`
- Empresa, sucursales, medios de pago, permisos, parámetros de sistema

---

## Bus de Eventos

Implementado en `backend/events.py`. Es un diccionario en memoria de `event_name → [callbacks]`.

**Eventos emitidos:**
| Evento | Emitido por | Consumidor(es) |
|---|---|---|
| `VentaRegistrada` | `routers/ventas.py` | `inventario_auditoria`, `finanzas_auditoria` |
| `VentaCancelada` | `services/ventas.py` | `operaciones_comerciales_auditoria` |
| `VentaSuspendida` | `services/ventas.py` | — |
| `VentaReanudada` | `services/ventas.py` | — |
| `CajaAbierta` | `services/tesoreria.py` | `finanzas_auditoria` |
| `CajaCerrada` | `services/tesoreria.py` | `finanzas_auditoria` |
| `MovimientoCajaRegistrado` | `services/tesoreria.py` | `finanzas_auditoria` |
| `PagoRegistrado` | `services/caja_tickets.py` | `cuentas_corrientes_auditoria`, `finanzas_auditoria` |

**Nota:** El payload de los eventos incluye `"__sesion"` (la sesión SQLAlchemy activa), lo que permite a los consumidores persistir datos en la misma transacción.

---

## Dependencias Clave (requirements.txt)

```
SQLAlchemy>=2.0.0
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
httpx>=0.24.0
python-dotenv>=1.0.0
pytest>=7.0.0
```
