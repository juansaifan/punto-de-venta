# 07 — Configuración

## Variables de Entorno

El sistema lee configuración mediante variables de entorno, con fallback a valores por defecto. Definidas en `backend/config/settings.py`.

| Variable | Default | Descripción |
|---|---|---|
| `POS_DATABASE_URL` | `sqlite:///Devs/data/pos.db` | URL de conexión SQLAlchemy. Soporta cualquier motor compatible (PostgreSQL, MySQL, etc.) |
| `POS_STORE_NAME` | `"Punto de Venta"` | Nombre del negocio. Usado en reportes y comprobantes. |
| `POS_CURRENCY` | `"PEN"` | Código de moneda. (No hay lógica de conversión implementada.) |
| `POS_DEBUG` | `"0"` | Si es `"1"`, `"true"` o `"yes"`, activa `echo=True` en SQLAlchemy (muestra SQL en consola). |

**Sin archivo `.env` presente en el repositorio.** Se usa `python-dotenv` en dependencias pero no hay evidencia de que `load_dotenv()` sea llamado explícitamente en `settings.py`. El usuario deberá configurar las variables en el entorno de ejecución.

---

## Objeto `Settings`

```python
# backend/config/settings.py
class Settings:
    project_root: Path   # Raíz del proyecto (Devs/)
    data_dir: Path       # Devs/data/
    logs_dir: Path       # Devs/logs/
    database_url: str    # URL de SQLAlchemy
    store_name: str      # Nombre del negocio
    currency: str        # Código de moneda
    debug: bool          # Modo debug
```

Acceso desde cualquier módulo: `from backend.config.settings import settings`

---

## Configuración Almacenada en Base de Datos

Además de variables de entorno, el sistema persiste configuración en la BD:

### `parametro_sistema` (tabla)

Parámetros de sistema por clave (`clave` único, `valor_json` como JSON serializado).

Claves conocidas (inferidas del código):

| Clave | Descripción |
|---|---|
| `caja` | Configuración de caja (`obligar_arqueo`, `permitir_cierre_con_diferencia`, `requerir_autorizacion_supervisor_cierre`) |
| `integraciones` | Credenciales fiscales (`cuit`, `punto_venta`, `modo_produccion`) |
| `facturacion` | Configuración de facturación (inferido, no confirmado en código) |

**Función de acceso:** `services/configuracion.py`
- `get_configuracion_caja(sesion)` → lee clave `"caja"` de `parametro_sistema`
- `get_configuracion_integraciones(sesion)` → lee clave `"integraciones"`

### `empresa` (singleton id=1)

Datos del negocio almacenados en BD (no en env vars):
- `nombre`, `razon_social`, `cuit`, `condicion_fiscal`
- `direccion`, `telefono`, `email`, `logo_url`

### `sucursal`

Sucursales del negocio con nombre, dirección y teléfono.

### `medio_pago`

Medios de pago habilitados con `codigo` (EFECTIVO, TARJETA_DEBITO, etc.), comisión y días de acreditación.

### `integracion_config`

Por cada tipo de integración: si está activa y su `config_json` (credenciales, parámetros).

---

## Configuración de Base de Datos (SQLite)

Aplicada automáticamente al crear el motor:

```python
PRAGMA foreign_keys=ON   # Integridad referencial
PRAGMA journal_mode=WAL  # Write-Ahead Logging (mejor concurrencia)
```

Para SQLite: `check_same_thread=False` (necesario para FastAPI con múltiples threads).

---

## Configuración de Caja (Detalle)

Leída desde `parametro_sistema` clave `"caja"`. Estructura esperada del JSON:

```json
{
  "obligar_arqueo": false,
  "permitir_cierre_con_diferencia": false,
  "requerir_autorizacion_supervisor_cierre": false
}
```

Si la clave no existe en BD, `get_configuracion_caja()` retorna `{}` (sin restricciones).

---

## Configuración del Servidor FastAPI

Hardcodeada en `backend/api/app.py`:

```python
app = FastAPI(
    title="Sistema Punto de Venta – API",
    version="0.1.0",
)

# CORS permisivo (desarrollo)
CORSMiddleware(
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**El CORS permisivo es adecuado solo para desarrollo.**

---

## Configuración del Frontend Flutter

Localizada en `frontend_flutter/lib/core/config/` (archivos no analizados en detalle). El `pubspec.yaml` indica:

```yaml
version: 0.1.0+1
environment:
  sdk: ">=3.3.0 <4.0.0"
```

No hay variables de entorno explícitas en Flutter; la URL del backend probablemente está hardcodeada o leída de `shared_preferences`.

---

## Flags y Settings Importantes

| Setting | Impacto |
|---|---|
| `POS_DEBUG=1` | Activa logging SQL en consola (SQLAlchemy echo). No usar en producción. |
| `obligar_arqueo=true` | El cierre de caja requiere informar `saldo_final`. |
| `permitir_cierre_con_diferencia=false` | No se puede cerrar caja si hay diferencia entre saldo teórico y real. |
| `requerir_autorizacion_supervisor_cierre=true` | Requiere `supervisor_autorizado=true` en el request de cierre. |
| `IntegracionConfig.activo=false` (mensajería) | Los comprobantes digitales se envían con prefijo `[SIM]` en el log. |
| `hardware_pos` activo | Todos los dispositivos POS se consideran disponibles. |
