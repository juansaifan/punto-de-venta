# 01 — Arquitectura del Sistema

## Arquitectura General

El sistema es un **monolito modular** con separación clara de capas. No hay microservicios. La comunicación entre módulos se realiza de dos formas:

1. **Llamadas directas entre servicios** (mismo proceso Python)
2. **Bus de eventos in-process** (`backend/events.py`) para desacoplar acciones secundarias

---

## Separación Frontend / Backend

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend Flutter (Windows desktop)                          │
│  • lib/modules/ — pantallas por módulo                      │
│  • lib/core/api/ — clientes HTTP hacia backend              │
│  • lib/widgets/ — componentes reutilizables                 │
│  • lib/core/theme/ — tema visual                            │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTP REST (JSON)
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend FastAPI (Python 3.11+)                              │
│  • /api/routers/ — endpoints REST por dominio               │
│  • /api/schemas/ — validación Pydantic (request/response)   │
│  • /api/deps.py  — inyección de sesión DB                   │
│  • /services/   — lógica de negocio                         │
│  • /models/     — entidades SQLAlchemy                      │
│  • /consumers/  — handlers de eventos (auditoría)           │
│  • events.py    — bus de eventos in-process                 │
│  • /config/     — settings y variables de entorno           │
│  • /database/   — motor, sesión, inicialización             │
└───────────────────┬─────────────────────────────────────────┘
                    │ SQLAlchemy 2.x
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  SQLite (data/pos.db)                                        │
│  WAL mode activado — PRAGMA foreign_keys=ON                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Capas del Sistema (Backend)

### 1. Capa de Configuración (`backend/config/`)
- `settings.py`: Lee variables de entorno. Expone `settings` singleton con rutas, URL de BD, nombre de negocio, moneda y modo debug.

### 2. Capa de Base de Datos (`backend/database/`)
- `base.py`: `DeclarativeBase` de SQLAlchemy compartida por todos los modelos.
- `sesion.py`: Factoría de motor (`obtener_motor`), sesión (`obtener_sesion`) e inicialización de tablas (`inicializar_bd`). Activa WAL y foreign keys en SQLite.

### 3. Capa de Modelos (`backend/models/`)
- Entidades SQLAlchemy que mapean tablas de la base de datos.
- Usan la API moderna de SQLAlchemy 2.x (`Mapped`, `mapped_column`).
- No contienen lógica de negocio compleja (excepción: `Venta.recalcular_totales()`).

### 4. Capa de Servicios (`backend/services/`)
- Contiene toda la lógica de negocio.
- Reciben una `Session` de SQLAlchemy como primer parámetro.
- Son funciones puras (sin estado propio); el estado vive en la BD.
- Llaman a `emit()` del bus de eventos para notificar acciones relevantes.

### 5. Capa de API (`backend/api/`)
- **Routers** (`api/routers/`): Endpoints FastAPI. Reciben HTTP → llaman servicios → devuelven respuesta.
- **Schemas** (`api/schemas/`): Modelos Pydantic para validación de entrada y serialización de salida.
- **Deps** (`api/deps.py`): `get_db()` como dependencia FastAPI que provee la sesión de BD.

### 6. Capa de Eventos (`backend/events.py` + `backend/consumers/`)
- `events.py`: Bus pub/sub in-process. `subscribe(event, fn)` y `emit(event, payload)`.
- `consumers/`: Handlers que suscriben a eventos específicos y realizan acciones secundarias (persistir log de auditoría, actualizar cuentas corrientes, etc.).
- Los consumidores se registran en el startup de la aplicación (`app.py`).

---

## Patrones Detectados

| Patrón | Ubicación | Descripción |
|---|---|---|
| Repository / Service Layer | `services/` | Separación de acceso a datos y lógica de negocio |
| Dependency Injection | `api/deps.py` + FastAPI `Depends` | Sesión de BD inyectada en cada request |
| Observer / Event Bus | `events.py` + `consumers/` | Desacoplamiento entre dominios vía eventos |
| Singleton Settings | `config/settings.py` | Instancia única de configuración |
| Declarative ORM | `models/` + `database/base.py` | SQLAlchemy DeclarativeBase |
| Schema Validation | `api/schemas/` | Pydantic para contratos de entrada/salida |

---

## Flujo de Datos General

```
Cliente HTTP (Flutter / curl / Swagger UI)
        │
        ▼
   FastAPI Router
        │  valida con Pydantic Schema
        ▼
   Servicio (services/)
        │  opera con Session SQLAlchemy
        ▼
   Modelo / Base de Datos
        │  flush/commit
        ▼
   emit_event(...)  ──────────►  Consumer (consumers/)
                                      │
                                      ▼
                               Persistir log / actualizar saldo
```

---

## Inicialización de la Aplicación

Al iniciar con `uvicorn backend.api.app:app`:

1. Se crea el motor de BD (`obtener_motor`)
2. Se crean todas las tablas si no existen (`inicializar_bd`)
3. Se registran los consumidores de eventos:
   - `consumer_cc_auditoria.registrar_consumidores()`
   - `consumer_inventario_auditoria.registrar_consumidores()`
   - `consumer_ops_auditoria.registrar_consumidores()`
   - `consumer_finanzas_auditoria.registrar_consumidores()`
4. Se agregan los routers con prefijo `/api`
5. Se configura CORS permisivo (`allow_origins=["*"]`)
