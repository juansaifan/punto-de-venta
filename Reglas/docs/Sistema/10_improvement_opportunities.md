# 10 — Oportunidades de Mejora

## Mejoras Críticas (Alta Prioridad)

### 1. Agregar sistema de migraciones (Alembic)
**Impacto:** Permite evolucionar el esquema de BD en producción sin pérdida de datos.

```bash
pip install alembic
alembic init migrations
# Configurar env.py con la URL de BD y los modelos del proyecto
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

Una vez configurado, cada cambio de esquema genera una migración versionada y reversible.

---

### 2. Implementar autenticación y autorización
**Impacto:** Sin autenticación, cualquier cliente con acceso a la red puede ejecutar cualquier operación.

Recomendación:
- JWT con `python-jose` o `authlib` + `passlib` para hashing de contraseñas
- Integrar con el modelo `Usuario` / `Rol` / `Permiso` ya existente
- Agregar `Depends(get_current_user)` en los endpoints sensibles

El esquema de permisos (`Permiso`, `Rol`, `rol_permiso`) ya está modelado en la BD.

---

### 3. Restringir CORS en producción
**Impacto:** Seguridad básica en despliegue productivo.

```python
# Reemplazar allow_origins=["*"] por:
allow_origins=[
    "http://localhost:PORT",       # Flutter desktop en dev
    "https://app.negocio.com",     # Dominio productivo si aplica
]
```

---

## Mejoras de Arquitectura

### 4. Separar `caja_tickets.py` en servicio `cobro.py`
El servicio `caja_tickets.py` mezcla listado de tickets con lógica de cobro. Separar en:
- `svc_tickets.py` — gestión de cola de tickets
- `svc_cobro.py` — proceso de cobro y generación de `PaymentTransaction`

---

### 5. Centralizar descuento de stock en el servicio de ventas
Actualmente, el descuento de stock ocurre en `routers/ventas.py` (no en el servicio). Mover esta responsabilidad al servicio garantiza que el stock siempre se descuente, independientemente de qué router llame la función.

```python
# services/ventas.py → registrar_venta()
# Al final, llamar internamente a svc_inventario.descontar_stock_por_venta()
```

---

### 6. Agregar `lifespan` en lugar de `on_event`
Reemplazar el hook deprecado de FastAPI:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    motor = obtener_motor()
    inicializar_bd(motor)
    consumer_cc_auditoria.registrar_consumidores()
    # ...
    yield

app = FastAPI(lifespan=lifespan, ...)
```

---

### 7. Usar `Text` en lugar de `String(512)` para `detalle_pagos`
```python
# models/venta.py
detalle_pagos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

---

## Mejoras de Calidad de Código

### 8. Unificar nomenclatura (español vs inglés)
El codebase usa español consistentemente excepto en `PaymentTransaction` / `payment_transaction`. Opciones:
- Renombrar a `TransaccionPago` / `transaccion_pago`
- O migrar todo el dominio de pagos a inglés como convención de proyecto

---

### 9. Eliminar campo duplicado `Empleado.documento`
El documento ya existe en `Persona`. Eliminar el campo en `Empleado` y referenciar siempre `empleado.persona.documento`.

---

### 10. Validar rol proveedor al crear compra
En `services/compras.py` agregar:

```python
from sqlalchemy import select
from backend.models.persona import Proveedor

proveedor_rol = sesion.scalars(
    select(Proveedor).where(Proveedor.persona_id == proveedor_id)
).first()
if proveedor_rol is None:
    raise ValueError("La persona no tiene rol de proveedor")
```

---

## Mejoras de Funcionalidad

### 11. Implementar cálculo de impuestos
El campo `impuesto` en `Venta` siempre es 0. Para soporte de IVA:
- Agregar `tasa_iva` en `Producto` (o en `CategoriaProducto`)
- En `registrar_venta()`, calcular `impuesto = sum(item.subtotal * tasa_iva)`
- Exponer en los datos fiscales para facturación electrónica

---

### 12. Persistir historial de backups en BD
Reemplazar la variable de módulo `_ultimo_backup` con una tabla o con registros en `integracion_log`:

```python
# En lugar de: _ultimo_backup["registros"].append(...)
# Usar: registrar_log(sesion, "backups_sincronizacion", True, ...)
```

El log ya se registra; eliminar el historial en memoria.

---

### 13. Mejorar reconciliación de pasarelas
Agregar referencia externa en `PaymentTransaction`:
```python
referencia_externa: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
```
La reconciliación puede entonces buscar por `referencia_externa` en lugar de por monto.

---

### 14. Scripts de seeding inicial
Crear `Devs/scripts/seed_inicial.py` que cargue:
- Categorías de productos base
- Medios de pago habilitados (EFECTIVO, TARJETA_DEBITO, TARJETA_CREDITO, TRANSFERENCIA)
- Registro de empresa (singleton)
- Usuario administrador inicial

---

## Mejoras de Frontend Flutter

### 15. Adoptar gestor de estado formal
Recomendación: **Riverpod** (o Provider como alternativa más simple).

Beneficios:
- Estado compartido entre pantallas (ej. caja activa, usuario logueado)
- Invalidación y recarga de datos sin pasar callbacks entre widgets

---

### 16. Implementar pantallas placeholder
Las 7 pantallas en placeholder (`_PantallaPlaceholder`) son los siguientes módulos sin frontend:
- Operaciones Comerciales
- Tesorería
- Finanzas
- Personas
- Reportes
- Integraciones
- Configuraciones

Prioridad sugerida: **Personas** y **Operaciones Comerciales** (necesarios para flujos de venta completos).

---

### 17. Agregar manejo de errores centralizado en Flutter
Las llamadas HTTP deberían manejar errores de red, timeouts y respuestas 4xx/5xx de forma consistente, con feedback visual al usuario.

---

## Oportunidades de Modularización

### 18. Extraer lógica de generación EAN-13 a módulo dedicado
La generación del barcode EAN-13 para pesables (actualmente en `services/pesables.py`) puede extraerse a `utils/barcode.py` para facilitar testing y reutilización.

---

### 19. Crear capa de repositorio explícita
Actualmente, las queries SQLAlchemy están inline en los servicios. Para proyectos de mayor escala, separar en repositorios:
- `repositories/venta_repository.py` — queries de `Venta`
- `repositories/producto_repository.py` — queries de `Producto`
- etc.

Esto facilitaría cambiar el motor de BD sin tocar la lógica de negocio.

---

### 20. Agregar `.env.example` al repositorio
Crear un archivo de ejemplo con todas las variables de entorno:
```bash
# .env.example
POS_DATABASE_URL=sqlite:///data/pos.db
POS_STORE_NAME=Mi Negocio
POS_CURRENCY=ARS
POS_DEBUG=0
```

Y asegurarse de que `settings.py` llame `load_dotenv()` al inicio.
