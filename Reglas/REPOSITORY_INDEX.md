# Índice del repositorio – Sistema Punto de Venta

Documento de referencia: estructura del proyecto, módulos, stack tecnológico y estado del desarrollo. Mantenido por el agente según AGENT_RULES.md.

---

## 1. Directorios principales

| Ruta | Descripción |
|------|-------------|
| `D:\Proyectos\Punto de Venta\Reglas` | Documentación y reglas: PROYECTO.md, AGENT_RULES.md, ROADMAP.md, docs/, logs/ |
| `D:\Proyectos\Punto de Venta\Devs` | Código del proyecto: backend, frontend, scripts, docs, logs |

El agente **no escribe código** en Reglas. Todo el código vive en Devs.

---

## 2. Reglas (Reglas/)

| Archivo | Propósito |
|---------|-----------|
| **PROYECTO.md** | Definición del sistema, objetivos, alcance, arquitectura, convenciones. Incluye **Stack Tecnológico Detectado**. |
| **AGENT_RULES.md** | Reglas operativas del agente (no modificar). |
| **ROADMAP.md** | Fases de desarrollo (Fase 0 a 10). |
| **REPOSITORY_INDEX.md** | Este índice. |
| **docs/** | Documentación por módulo (Dashboard, Punto de Venta, Tesorería, Inventario, etc.). |
| **logs/** | Memoria del agente (dev_log.md). |

---

## 3. Código (Devs/)

### 3.1 Estructura esperada (PROYECTO.md)

```
Devs/
├── backend/
│   ├── api/           # Endpoints REST (FastAPI)
│   │   ├── routers/   # Routers por recurso (productos, ...)
│   │   └── schemas/   # DTOs Pydantic (producto, ...)
│   ├── services/      # Lógica de negocio por dominio (productos, ...)
│   ├── models/        # Entidades de dominio
│   └── database/      # Persistencia (base, sesión, BD)
├── frontend/
│   ├── ui/
│   └── components/
├── tests/             # Pruebas (conftest, test_productos, ...)
├── scripts/
├── docs/
├── logs/
├── requirements.txt
└── README.md
```

### 3.2 Stack tecnológico

| Aspecto | Tecnología |
|---------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x |
| Base de datos | SQLite (por defecto) |
| Frontend | Flutter / Dart (objetivo vigente; existe base funcional en `Devs/frontend_flutter`) |
| Pruebas | pytest (pendiente de instalación en el entorno actual del agente) |

### 3.3 Estado actual del desarrollo

| Componente | Estado |
|------------|--------|
| **Backend – estructura** | Creada: config, database, models, api, services |
| **Backend – modelos** | Persona, Usuario (con rol_id), Rol, Permiso (rol_permiso N:M), Producto (incluye `pesable` y `plu`), **PesableItem**, CategoriaProducto, Venta (**cliente_id** FK Persona), ItemVenta, Caja, MovimientoCaja, Stock, **Lote** (fecha_vencimiento), MovimientoInventario, CuentaFinanciera, TransaccionFinanciera, MedioPago, Empresa, Sucursal, **ParametroSistema** (clave/valor_json), **IntegracionConfig**, **IntegracionLog**, **EventoSistemaLog** (auditoría de eventos), **SolicitudCompra/ItemSolicitudCompra** (abastecimiento automático) |
| **Backend – API** | Raíz `/`, `/health`; **productos**; **personas** (CRUD de personas y roles + vínculo **Persona ↔ Usuario**); **ventas** (TEU_OFF/TEU_ON, tickets, `suspender`/`reanudar`, búsqueda/filtros, carrito y descuento); **pesables** (`/api/pesables/*`: cálculo, preparación, batch, etiquetas, estados, habilitación PLU); **inventario** (ingresar, stock por producto (con `ubicacion`), movimientos con filtros, **categorías** GET/POST/PATCH, **productos/{id}/lotes** POST, **alertas** GET, **reposicion/ejecutar** POST, **solicitudes-compra** GET/GET{id} + **convertir-a-compra** POST); **caja** (abrir/cerrar/movimientos + `/api/caja/tickets/pendientes` y `/api/caja/tickets/{venta_id}/cobrar` para TEU_OFF); **operaciones-comerciales** (devoluciones, notas de crédito/débito, cambios, anulaciones y crédito en cuenta corriente); **tesorería/cuentas-corrientes** (resumen, movimientos, aging, deudores y estadísticas); **auditoria/eventos**; **reportes**; **dashboard**; **finanzas**; **configuracion**; **integraciones** |
| **Backend – servicios** | **productos**; **personas**; **ventas** (TEU_OFF/TEU_ON + suspenso); **caja_tickets** (tickets en cola y cobro desde caja); **operaciones_comerciales** (devolución, nota de crédito/débito, cambio de producto, crédito en cuenta corriente y anulación de venta pendiente); **inventario**; **alertas_inventario**; **reposicion_automatica**; **solicitudes_compra**; **tesorería** (caja, **cuentas_corrientes** de clientes); **auditoria_eventos** (persistencia/listado); **reportes**; **dashboard**; **finanzas**; **configuracion**; **integraciones**; **events**; **consumers** (handlers de eventos) |
| **Frontend** | `Devs/frontend_flutter/` es la base activa (Flutter/Dart) con avance offline/mocks en Dashboard, Ventas, Caja e Inventario. `Devs/frontend/` queda como prototipo web legado temporal. |
| **Scripts** | Carpeta creada; vacía |
| **Tests** | test_productos, test_personas, test_ventas, test_inventario, test_caja, test_reportes, test_dashboard, test_finanzas, test_configuracion, test_integraciones, test_auditoria_eventos, test_pos_tickets, test_operaciones_comerciales, test_operaciones_comerciales_avanzadas, test_ventas_suspenso, test_pesables, test_cuentas_corrientes, test_compras; **585 casos de prueba declarados** |

### 3.4 Módulos detectados (docs/)

- Módulo 1: Dashboard  
- Módulo 2: Punto de Venta (Ventas, Caja, Operaciones comerciales, Pesables)  
- Módulo 3: Tesorería  
- Módulo 4: Finanzas  
- Módulo 5: Inventario  
- Módulo 6: Personas  
- Módulo 7: Reportes  
- Módulo 8: Integraciones  
- Módulo 9: Configuración  

---

## 4. Proyecto de referencia analizado

Se analizó el proyecto **pos-market** (La Casona – Market POS) para:

- Detectar stack (Python, FastAPI, SQLAlchemy, Flutter, SQLite).
- Identificar código reutilizable: modelos, capa de persistencia, servicios, API.
- Migrar y adaptar a la estructura backend (config, database, models, api, services) en Devs.

El código migrado fue **limpiado y reorganizado** bajo el paquete `backend` (imports `backend.*`).

---

## 5. Próximo paso de desarrollo

Según ROADMAP.md (Fase 1 – Núcleo Operativo):

- **Hecho en Iteración 1:** CRUD de productos (API + servicio + tests).
- **Hecho en Iteración 2:** CRUD de personas (API + servicio + tests), dominio Personas.
- **Hecho en Iteración 3:** API y servicio de ventas (registrar venta con ítems, descuento, método de pago; obtener por id; listar).
- **Hecho en Iteración 4:** Descuento de inventario al registrar venta: servicio inventario (descontar_stock_por_venta, ingresar_stock, obtener_cantidad_stock), API inventario (ingresar, GET stock), integración en flujo de ventas.
- **Hecho en Iteración 5:** Tesorería (Fase 2): apertura y cierre de caja.
- **Hecho en Iteración 6:** Movimientos de caja: registrar_movimiento_caja (INGRESO, GASTO, etc.), listar_movimientos_caja; API POST/GET /api/caja/{id}/movimientos.
- **Hecho en Iteración 7:** Vincular venta a caja abierta: al registrar venta, si hay caja abierta se asigna venta.caja_id; VentaResponse incluye caja_id.
- **Hecho en Iteración 8:** Evento VentaRegistrada: bus in-process; se emite al registrar venta.
- **Ejecución autónoma extendida:** Movimiento de caja automático por venta (tipo VENTA) y desarrollo de módulos analiticos y de configuracion (backend + modelo + tests). El siguiente hito de producto es completar la migracion del frontend hacia Flutter, comenzando por Dashboard (Modulo 1), sobre el backend existente.

Detalle de cada iteración en **logs/dev_log.md**.

---

## 6. Estado Frontend (Flutter)

- En `Devs/frontend_flutter/` existe el proyecto principal de frontend objetivo (Flutter/Dart).
- `Módulo 1 (Dashboard)` y partes de `Módulo 2/3/5` están funcionales en modo offline/mocks.
- La deuda principal es de integración: reemplazar `ClienteApi` mock por cliente HTTP real contra `/api/*`.
- El submódulo Pesables aún no tiene UI Flutter end-to-end (preparación, etiquetas, uso por escaneo).

## 7. Estado Frontend (prototipo web)

- `Devs/frontend/` contiene un prototipo web HTML/JS temporal (legado) para referencia; la ejecución objetivo ahora es Flutter.
