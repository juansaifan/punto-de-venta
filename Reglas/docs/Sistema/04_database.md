# 04 — Base de Datos

## Motor y Configuración

- **Motor:** SQLite (por defecto) — configurable vía `POS_DATABASE_URL`
- **Ruta por defecto:** `Devs/data/pos.db`
- **ORM:** SQLAlchemy 2.x con `DeclarativeBase`
- **WAL mode activado:** `PRAGMA journal_mode=WAL`
- **Foreign keys activadas:** `PRAGMA foreign_keys=ON`
- **Creación de tablas:** automática en startup mediante `Base.metadata.create_all()`

---

## Tablas y Modelos

### Dominio: Ventas

#### `venta`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `numero_ticket` | String(32) | único, nullable, índice (`TCK-00000001`) |
| `subtotal` | Numeric(12,2) | suma de ítems |
| `descuento` | Numeric(12,2) | descuento global |
| `impuesto` | Numeric(12,2) | por ahora siempre 0 |
| `total` | Numeric(12,2) | subtotal - descuento + impuesto |
| `metodo_pago` | String(32) | EFECTIVO, CUENTA_CORRIENTE, PAGO_COMBINADO, PENDIENTE |
| `detalle_pagos` | String(512) | JSON serializado con detalle de pagos combinados |
| `usuario_id` | FK → usuario.id | nullable |
| `caja_id` | FK → caja.id | nullable |
| `cliente_id` | FK → persona.id | nullable |
| `estado` | String(32) | índice — ver `EstadoVenta` |
| `creado_en` | DateTime | UTC |

**Estados (`EstadoVenta`):** `PENDIENTE`, `PAGADA`, `SUSPENDIDA`, `FIADA`, `CANCELADA`

#### `item_venta`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `venta_id` | FK → venta.id | cascade delete |
| `producto_id` | FK → producto.id | |
| `nombre_producto` | String(256) | desnormalizado (snapshot al momento de venta) |
| `cantidad` | Numeric(12,3) | permite decimales (pesables) |
| `precio_unitario` | Numeric(12,2) | |
| `subtotal` | Numeric(12,2) | cantidad × precio_unitario |

---

### Dominio: Pagos

#### `payment_transaction`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `venta_id` | FK → venta.id | índice |
| `caja_id` | FK → caja.id | nullable, índice |
| `metodo_pago` | String(32) | EFECTIVO, TARJETA, CUENTA_CORRIENTE, etc. |
| `importe` | Numeric(12,2) | |
| `medio_pago` | String(64) | nullable (banco/entidad para auditoría) |
| `cobrador` | String(128) | nullable |
| `observaciones` | Text | nullable |
| `fecha` | DateTime | índice |

---

### Dominio: Caja

#### `caja`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `fecha_apertura` | DateTime | UTC |
| `fecha_cierre` | DateTime | nullable — si null = caja abierta |
| `saldo_inicial` | Numeric(12,2) | |
| `saldo_final` | Numeric(12,2) | nullable — registrado al arqueo |
| `usuario_id` | FK → usuario.id | nullable |

#### `movimiento_caja`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `caja_id` | FK → caja.id | |
| `tipo` | String(32) | VENTA, DEVOLUCION, RETIRO, INGRESO, GASTO |
| `monto` | Numeric(12,2) | siempre positivo |
| `medio_pago` | String(32) | default EFECTIVO |
| `fecha` | DateTime | UTC |
| `referencia` | String(256) | nullable |

---

### Dominio: Productos

#### `producto`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `sku` | String(64) | único, índice |
| `codigo_barra` | String(32) | nullable, índice |
| `nombre` | String(256) | |
| `descripcion` | Text | nullable |
| `categoria_id` | FK → categoria_producto.id | nullable |
| `subcategoria_id` | FK → categoria_producto.id | nullable |
| `tipo_producto` | String(32) | `inventariable` / `no_inventariable` |
| `tipo_medicion` | String(16) | `unidad` / `peso` |
| `precio_venta` | Numeric(12,2) | |
| `costo_actual` | Numeric(12,2) | |
| `stock_minimo` | Numeric(14,3) | umbral de alerta |
| `punto_reorden` | Numeric(14,3) | dispara solicitud automática de compra |
| `categoria_fiscal` | String(32) | nullable |
| `proveedor` | String(128) | nullable (texto libre, no FK) |
| `pesable` | Boolean | True = precio depende del peso |
| `plu` | Integer | nullable, único — código PLU (5 dígitos, solo pesables) |
| `activo` | Boolean | soft delete |
| `creado_en` | DateTime | UTC |
| `actualizado_en` | DateTime | UTC, onupdate |

#### `categoria_producto`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `codigo` | String(32) | único, índice |
| `nombre` | String(128) | |
| `descripcion` | String(256) | nullable |
| `categoria_padre_id` | FK → categoria_producto.id | nullable — árbol de categorías |

---

### Dominio: Inventario

#### `stock`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `producto_id` | FK → producto.id | |
| `ubicacion` | String(32) | GONDOLA / DEPOSITO |
| `cantidad` | Numeric(14,3) | puede ser negativo en edge cases |

#### `lote`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `producto_id` | FK → producto.id | |
| `cantidad` | Numeric(14,3) | |
| `fecha_vencimiento` | Date | |

#### `movimiento_inventario`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `producto_id` | FK → producto.id | |
| `tipo` | String(32) | VENTA, COMPRA, TRANSFERENCIA, DEVOLUCION, AJUSTE, MERMA, CONSUMO_INTERNO, REVERSION |
| `cantidad` | Numeric(14,3) | con signo (negativo = salida) |
| `ubicacion` | String(32) | nullable |
| `fecha` | DateTime | UTC |
| `referencia` | String(256) | nullable |

---

### Dominio: Personas

#### `persona`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `nombre` | String(128) | |
| `apellido` | String(128) | |
| `documento` | String(32) | nullable |
| `telefono` | String(32) | nullable |
| `activo` | Boolean | |

#### `cliente`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `persona_id` | FK → persona.id | cascade delete |
| `segmento` | String(64) | nullable |
| `condicion_pago` | String(64) | nullable |
| `limite_credito` | Numeric(14,2) | nullable |
| `estado` | String(32) | ACTIVO, etc. |
| `fecha_alta` | DateTime | |
| `observaciones` | Text | nullable |

#### `proveedor`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `persona_id` | FK → persona.id | |
| `cuit` | String(32) | nullable |
| `condiciones_comerciales` | String(128) | nullable |
| `condiciones_pago` | String(128) | nullable |
| `lista_precios` | String(128) | nullable |
| `estado` | String(32) | |
| `frecuencia_entrega` | String(64) | nullable |
| `minimo_compra` | Numeric(14,2) | nullable |
| `tiempo_estimado_entrega` | String(64) | nullable |
| `observaciones` | Text | nullable |

#### `empleado`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `persona_id` | FK → persona.id | |
| `documento` | String(32) | nullable |
| `cargo` | String(64) | nullable |
| `fecha_ingreso` | DateTime | |
| `estado` | String(32) | |

#### `contacto`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `persona_id` | FK → persona.id | |
| `nombre` | String(128) | |
| `cargo` | String(64) | nullable |
| `telefono` | String(32) | nullable |
| `email` | String(128) | nullable |
| `observaciones` | Text | nullable |

---

### Dominio: Cuentas Corrientes

#### `cuenta_corriente_cliente`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `cliente_id` | FK → cliente.id | único (1:1 con cliente) |
| `saldo` | Numeric(14,2) | saldo de deuda actual |
| `actualizado_en` | DateTime | |

#### `movimiento_cuenta_corriente`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `cuenta_id` | FK → cuenta_corriente_cliente.id | |
| `tipo` | String(16) | VENTA / PAGO / AJUSTE |
| `monto` | Numeric(14,2) | |
| `descripcion` | Text | nullable |
| `fecha` | DateTime | |

---

### Dominio: Compras

#### `compra`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `proveedor_id` | FK → persona.id | (no FK a proveedor, sino a persona directamente) |
| `fecha` | DateTime | UTC |
| `total` | Numeric(12,2) | |
| `estado` | String(32) | CONFIRMADA, etc. |

#### `item_compra`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `compra_id` | FK → compra.id | cascade delete |
| `producto_id` | FK → producto.id | |
| `nombre_producto` | String(256) | snapshot |
| `cantidad` | Numeric(12,3) | |
| `costo_unitario` | Numeric(12,2) | |
| `subtotal` | Numeric(12,2) | |

---

### Dominio: Finanzas

#### `cuenta_financiera`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `nombre` | String(128) | |
| `tipo` | String(32) | caja_fisica, cuenta_bancaria, billetera_virtual, fondo_operativo, fondo_cambio, GENERAL |
| `saldo` | Numeric(14,2) | |
| `estado` | String(16) | activa |
| `observaciones` | Text | nullable |

#### `transaccion_financiera`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `cuenta_id` | FK → cuenta_financiera.id | |
| `tipo` | String(32) | |
| `monto` | Numeric(12,2) | |
| `fecha` | DateTime | |
| `descripcion` | Text | nullable |
| `conciliada` | Boolean | default False |
| `fecha_conciliacion` | DateTime | nullable |

---

### Dominio: Operaciones Comerciales

#### `operacion_comercial`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `venta_id` | FK → venta.id | índice |
| `cliente_id` | FK → persona.id | nullable, índice |
| `tipo` | Enum | DEVOLUCION, CAMBIO_PRODUCTO, NOTA_CREDITO, NOTA_DEBITO, CREDITO_CUENTA_CORRIENTE, ANULACION |
| `estado` | Enum | EJECUTADA / CANCELADA |
| `motivo` | String(256) | nullable |
| `importe_total` | Numeric(12,2) | |
| `detalle_json` | Text | nullable |
| `creado_en` | DateTime | índice |

#### `operacion_comercial_detalle`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `operacion_id` | FK → operacion_comercial.id | |
| `item_venta_id` | FK → item_venta.id | nullable |
| `producto_id` | FK → producto.id | |
| `nombre_producto` | String(256) | snapshot |
| `cantidad` | Numeric(12,3) | |
| `precio_unitario` | Numeric(12,2) | |
| `subtotal` | Numeric(12,2) | |

---

### Dominio: Pesables

#### `pesable_item`
| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `producto_id` | FK → producto.id | índice |
| `nombre_producto` | String(256) | snapshot |
| `plu` | Integer | PLU del producto (5 dígitos max) |
| `peso` | Numeric(10,3) | en kg |
| `precio_unitario` | Numeric(12,2) | precio por kg |
| `precio_total` | Numeric(12,2) | peso × precio_unitario |
| `barcode` | String(13) | EAN-13, índice |
| `estado` | String(16) | pending / printed / used |
| `creado_en` | DateTime | nullable |

---

### Dominio: Configuración

#### `empresa` (singleton id=1)
CUIT, razón social, condición fiscal, dirección, email, logo.

#### `sucursal`
Nombre, dirección, teléfono, activo.

#### `medio_pago`
`codigo` (único), nombre, activo, comisión, días de acreditación.

#### `parametro_sistema`
`clave` (único), `valor_json` (Text — JSON serializado por sección de configuración).

#### `permiso`
`codigo` (único), nombre, descripción.

#### `rol_permiso` (tabla asociativa N:M)
`rol_id` + `permiso_id`

---

### Dominio: Integraciones

#### `integracion_config`
`tipo_codigo` (único), `activo`, `config_json` (credenciales JSON).

#### `integracion_log`
`tipo_codigo`, `exito`, `mensaje`, `detalle`, `created_at`.

---

### Dominio: Auditoría

#### `evento_sistema_log`
`nombre`, `modulo`, `entidad_tipo`, `entidad_id`, `payload_json`, `fecha`.

---

## Relaciones Clave

```
persona (1) ──< (N) cliente
persona (1) ──< (N) proveedor
persona (1) ──< (N) empleado
persona (1) ──< (N) contacto

cliente (1) ──── (1) cuenta_corriente_cliente
cuenta_corriente_cliente (1) ──< (N) movimiento_cuenta_corriente

venta (1) ──< (N) item_venta
venta (1) ──< (N) payment_transaction
venta (1) ──< (N) operacion_comercial

caja (1) ──< (N) movimiento_caja
caja (1) ──< (N) venta (vía venta.caja_id)

producto (1) ──< (N) stock (por ubicacion)
producto (1) ──< (N) lote
producto (1) ──< (N) movimiento_inventario
producto (1) ──< (N) pesable_item

categoria_producto (1) ──< (N) producto
categoria_producto (1) ──< (N) categoria_producto (subcategorías, self-referencia)

compra (1) ──< (N) item_compra
cuenta_financiera (1) ──< (N) transaccion_financiera
```

---

## Suposiciones / No Evidente en el Código

- La tabla `rol` existe (referenciada en `rol_permiso` y en `models/rol.py`) pero su estructura detallada no fue analizada.
- La tabla `usuario` existe (referenciada en `venta.usuario_id` y `caja.usuario_id`) pero su estructura detallada no fue analizada.
- `solicitud_compra` existe como modelo pero su estructura completa no fue revisada en este análisis.
- La referencia `compra.proveedor_id → persona.id` (no → proveedor.id) parece ser una decisión de diseño para evitar la jerarquía cliente-persona; puede ser intencional.
