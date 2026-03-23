# 08 — Flujo de Desarrollo

## Prerequisitos

- Python 3.11+ (se usa CPython 3.13 según `__pycache__`)
- Flutter SDK ≥ 3.3.0 (para frontend)
- Git (no hay `.git` en el directorio raíz del workspace)

---

## Cómo Correr el Backend

Desde la carpeta `Devs/`:

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Iniciar el servidor de desarrollo
uvicorn backend.api.app:app --reload --port 8000
```

**Documentación interactiva:** http://localhost:8000/docs (Swagger UI)  
**Health check:** http://localhost:8000/health → `{ "estado": "ok" }`  
**Raíz:** http://localhost:8000/ → `{ "mensaje": "Sistema Punto de Venta API", "docs": "/docs" }`

La base de datos SQLite se crea automáticamente en `Devs/data/pos.db` si no existe.

---

## Cómo Correr los Tests (Backend)

Desde la carpeta `Devs/`:

```bash
pytest
# O con output detallado:
pytest -v
# O un test específico:
pytest tests/test_ventas.py -v
```

### Suite de Tests Disponibles

| Archivo | Cobertura |
|---|---|
| `test_ventas.py` | Flujo completo de ventas TEU_ON y TEU_OFF |
| `test_ventas_suspenso.py` | Suspensión y reanudación de ventas |
| `test_caja.py` | Apertura, cierre, movimientos y arqueo de caja |
| `test_anulacion_ejecutada.py` | Operaciones comerciales (anulación) |
| `test_auditoria_eventos.py` | Bus de eventos y log de auditoría |
| `test_compras.py` | Registro de compras a proveedores |
| `test_configuracion.py` | Parámetros de sistema y configuración |
| `test_cuentas_corrientes.py` | Saldo, movimientos y límite de crédito |
| `test_dashboard.py` | KPIs del dashboard |
| `test_finanzas.py` | Cuentas financieras y transacciones |
| `test_integraciones.py` | Configuración y logs de integración |
| `test_inventario.py` | Stock, lotes, movimientos y conteo |
| `test_operaciones_comerciales.py` | Devoluciones, notas de crédito/débito |
| `test_operaciones_comerciales_avanzadas.py` | Casos avanzados de operaciones |
| `test_personas.py` | ABM de personas y roles |
| `test_pesables.py` | Flujo completo de pesables (EAN-13) |
| `test_pos_tickets.py` | Flujo TEU_OFF + cobro de tickets |
| `test_productos.py` | ABM de productos y categorías |
| `test_reportes.py` | Reportes operativos |

### `conftest.py`
Define fixtures compartidas entre tests. Incluye sesión de BD en memoria (SQLite en memoria para tests aislados) y configuración base del sistema.

---

## Cómo Correr el Frontend Flutter

```bash
# Desde frontend_flutter/
flutter pub get
flutter run -d windows
```

Para compilar release:
```bash
flutter build windows
```

El ejecutable queda en `build/windows/x64/runner/Release/`.

---

## Estructura de Carpetas del Proyecto

```
Punto de Venta/
├── Devs/                          # Código fuente
│   ├── backend/                   # API Python/FastAPI
│   ├── frontend/                  # Frontend web (experimental, incompleto)
│   ├── frontend_flutter/          # Frontend Flutter (principal)
│   ├── data/
│   │   └── pos.db                 # Base de datos SQLite
│   ├── docs/                      # Documentación técnica (vacío)
│   ├── logs/
│   │   └── dev_log.md             # Log de desarrollo manual
│   ├── scripts/                   # Scripts utilitarios (vacío)
│   ├── tests/                     # Suite de tests pytest
│   ├── requirements.txt           # Dependencias Python
│   └── README.md
└── Reglas/                        # Documentación de reglas y decisiones
    ├── ARQUITECTURA.md
    ├── DATA_MODEL.md
    ├── DOMINIOS.md
    ├── EVENTOS.md
    ├── MODULE_STATUS.md
    ├── PROYECTO.md
    ├── REPOSITORY_INDEX.md
    ├── ROADMAP.md
    ├── DEVELOPMENT_STRATEGY.md
    ├── AUDITORIA_ESTADO_SISTEMA.md
    ├── docs/                      # Documentación funcional por módulo
    │   ├── Módulo 1/              # Dashboard
    │   ├── Módulo 2/              # POS (Ventas, Caja, Ops Comerciales, Pesables)
    │   ├── Módulo 3/              # Tesorería
    │   ├── Módulo 4/              # Finanzas
    │   ├── Módulo 5/              # Inventario
    │   ├── Módulo 6/              # Personas
    │   ├── Módulo 7/              # Reportes
    │   ├── Módulo 8/              # Integraciones
    │   └── Módulo 9/              # Configuración
    └── logs/
        ├── dev_log.md
        ├── system_state.md
        └── system_state_vigente.md
```

---

## Scripts Disponibles

La carpeta `Devs/scripts/` existe pero está vacía (solo `.gitkeep`). **No hay scripts utilitarios implementados.**

---

## Modo Debug

Activar logging SQL:

```bash
# Windows PowerShell
$env:POS_DEBUG="1"; uvicorn backend.api.app:app --reload --port 8000

# Linux/Mac
POS_DEBUG=1 uvicorn backend.api.app:app --reload --port 8000
```

---

## Base de Datos de Desarrollo vs Tests

| Contexto | BD usada |
|---|---|
| Desarrollo (uvicorn) | `Devs/data/pos.db` (SQLite archivo) |
| Tests (pytest) | SQLite en memoria (`:memory:`) — definido en `conftest.py` |

Los tests son completamente aislados; no afectan la BD de desarrollo.

---

## Build / Deploy

No hay scripts de deploy ni configuración de contenedores (sin `Dockerfile`, sin `docker-compose.yml`). El sistema está diseñado para ejecución local (Windows desktop + API Python local).

Para producción, los pasos serían:
1. Configurar `POS_DATABASE_URL` hacia PostgreSQL u otro motor
2. Ejecutar `uvicorn` como servicio del sistema o proceso supervisado
3. Compilar Flutter en release para Windows
4. Configurar `POS_STORE_NAME`, `POS_CURRENCY` según el negocio
5. Crear registro `Empresa` en BD con datos del negocio
