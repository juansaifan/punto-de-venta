# 09 — Problemas Conocidos y Deuda Técnica

## Problemas Funcionales

### 1. Stock no se descuenta en cobro TEU_OFF
**Severidad:** Alta  
**Ubicación:** `services/caja_tickets.py` → `cobro_ticket()`

En el flujo TEU_OFF, el stock se descuenta en el momento de registrar la venta (`routers/ventas.py` llama `svc_inventario.descontar_stock_por_venta()` al crear la venta). Sin embargo, en `cobro_ticket()` no hay segunda llamada de descuento de stock.

Esto puede ser intencional (el stock se reserva al crear el ticket), pero no está documentado explícitamente en el código, y genera el riesgo de que tickets cancelados no restauren el stock. Verificar si `cancelar_venta()` revierte el movimiento de inventario (no evidente en el código analizado).

---

### 2. `Compra.proveedor_id` referencia `persona` directamente (no `proveedor`)
**Severidad:** Media  
**Ubicación:** `backend/models/compra.py`

```python
proveedor_id: Mapped[int] = mapped_column(ForeignKey("persona.id"), nullable=False)
```

La FK apunta a `persona.id` en lugar de `proveedor.id`. Esto permite crear una compra con cualquier persona (cliente, empleado, contacto) como proveedor, sin validar que esa persona tenga rol de proveedor. El servicio de compras debería validar esta condición explícitamente.

---

### 3. Reconciliación de pasarelas por monto, no por referencia
**Severidad:** Media  
**Ubicación:** `services/integraciones.py` → `reconciliar_pagos_pasarela()`

```python
venta_match = sesion.scalars(
    select(Venta).where(Venta.total == monto).limit(1)
).first()
```

La reconciliación busca ventas solo por monto total, sin usar la referencia externa de la pasarela. Dos ventas del mismo importe en el mismo período producirán falsos positivos.

---

### 4. Historial de backups se pierde al reiniciar
**Severidad:** Baja  
**Ubicación:** `services/integraciones.py`

```python
_ultimo_backup: dict[str, Any] = { ... }  # Variable de módulo
```

El estado de backups se almacena en memoria. Al reiniciar el proceso, se pierde el historial. Solo los logs en `integracion_log` persisten (pero sin el historial detallado de registros).

---

### 5. CORS completamente abierto
**Severidad:** Media (solo en contexto producción)  
**Ubicación:** `backend/api/app.py`

```python
CORSMiddleware(allow_origins=["*"], ...)
```

Adecuado para desarrollo. En producción debe restringirse a los orígenes del frontend Flutter/web.

---

### 6. `load_dotenv()` no invocado explícitamente
**Severidad:** Baja  
**Ubicación:** `backend/config/settings.py`

`python-dotenv` está en `requirements.txt` pero `load_dotenv()` no se llama en `settings.py`. Las variables de entorno deben configurarse externamente (sistema operativo / IDE). Un archivo `.env` no sería cargado automáticamente.

---

### 7. `@app.on_event("startup")` está deprecado en FastAPI
**Severidad:** Baja  
**Ubicación:** `backend/api/app.py`

```python
@app.on_event("startup")
def startup():
    ...
```

FastAPI deprecó `on_event` en favor de `lifespan`. No es un error, pero generará warnings en versiones futuras de FastAPI.

---

### 8. Impuesto (`impuesto`) siempre en 0
**Severidad:** Media (funcional)  
**Ubicación:** `backend/models/venta.py`, `services/ventas.py`

El campo `impuesto` existe en el modelo pero siempre se inicializa en `Decimal("0")`. No hay lógica de cálculo de IVA u otro impuesto. Esto afecta la facturación electrónica cuando se implemente.

---

### 9. Subcategoría con FK a `categoria_producto` no validada en servicio
**Severidad:** Baja  
**Ubicación:** `backend/models/producto.py`

```python
subcategoria_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categoria_producto.id"), nullable=True)
```

El campo `subcategoria_id` es independiente de `categoria_id`. No hay validación de que la subcategoría sea hija de la categoría asignada.

---

## Deuda Técnica

### 10. Frontend Flutter sin gestor de estado formal
**Severidad:** Media (escalabilidad)

Las pantallas implementadas usan `StatefulWidget` sin un patrón de gestión de estado (Provider, Riverpod, Bloc). A medida que crezcan las pantallas y la lógica compartida, esto dificultará el mantenimiento.

---

### 11. Frontend web HTML/JS sin implementar
**Severidad:** Baja  
Las carpetas `frontend/components/` y `frontend/ui/` están vacías. El `mock_dashboard_api.js` sugiere trabajo experimental. Este frontend puede ser abandonado o requiere decisión formal sobre su rol en el proyecto.

---

### 12. Carpeta `Devs/scripts/` vacía
**Severidad:** Baja  
No hay scripts para seeding inicial de datos, migración o mantenimiento. Cualquier setup de datos debe hacerse manualmente via API o tests.

---

### 13. Sin migraciones de base de datos (Alembic)
**Severidad:** Alta (producción)  
El sistema usa `Base.metadata.create_all()` para crear tablas. En producción, cambios en el esquema (nuevas columnas, nuevas tablas) requieren Alembic o un mecanismo de migración equivalente. Sin esto, actualizar el sistema en producción es riesgoso.

---

### 14. Usuario y Rol sin implementación visible en servicios
**Severidad:** Media  
Los modelos `usuario.py` y `rol.py` existen, y `venta.usuario_id` / `caja.usuario_id` referencian `usuario`. Sin embargo, no hay un sistema de autenticación ni autorización implementado en los endpoints. Cualquier cliente puede llamar cualquier endpoint sin credenciales.

---

### 15. `detalle_pagos` en `Venta` es JSON serializado como String
**Severidad:** Baja (diseño)  
```python
detalle_pagos: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
```
El detalle de pagos combinados se almacena como JSON en un campo String de 512 chars. Si hay muchos pagos combinados, podría truncarse. Sería más robusto usar `Text` o confiar exclusivamente en `PaymentTransaction`.

---

## Inconsistencias

### 16. Nombres mixtos en funciones (español/inglés)
El código usa nombres en español (`registrar_venta`, `obtener_caja_abierta`) pero los modelos de pago usan inglés (`PaymentTransaction`, `payment_transaction`). No es un error funcional, pero rompe la consistencia del codebase.

### 17. `Empleado.documento` duplica `Persona.documento`
```python
class Empleado(Base):
    documento: Mapped[Optional[str]] = ...  # Ya existe en Persona
```
El campo `documento` está en `Persona` y también en `Empleado`, lo que puede generar datos inconsistentes.
