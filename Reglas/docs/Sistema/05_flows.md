# 05 — Flujos Principales del Sistema

## 1. Flujo de Venta — Modo TEU_ON (cobro inmediato en mostrador)

**Descripción:** El vendedor crea la venta y cobra en el mismo acto. No pasa por caja.

```
Cliente llega al mostrador
        │
        ▼
POST /api/ventas
  body: { items: [...], metodo_pago: "EFECTIVO", modo_venta: "TEU_ON" }
        │
        ├── svc_ventas.registrar_venta()
        │     ├── Valida items y cliente
        │     ├── Crea Venta(estado=PAGADA, metodo_pago=EFECTIVO)
        │     ├── Crea ItemVenta por cada producto
        │     ├── Recalcula totales (subtotal, descuento, total)
        │     └── Genera numero_ticket (TCK-00000001)
        │
        ├── svc_inventario.descontar_stock_por_venta()
        │     └── Por cada ítem: reduce Stock.cantidad en GONDOLA
        │         └── Registra MovimientoInventario tipo=VENTA
        │
        ├── svc_tesoreria.obtener_caja_abierta()
        │     └── Si hay caja abierta → vincula venta.caja_id
        │         └── svc_tesoreria.registrar_movimiento_caja(tipo=VENTA)
        │
        └── emit_event("VentaRegistrada", {...})
              └── Consumidores: auditoría de inventario / finanzas

Resultado: Venta con estado PAGADA + stock descontado + movimiento en caja
```

**Módulos involucrados:** `routers/ventas.py`, `services/ventas.py`, `services/inventario.py`, `services/tesoreria.py`, `events.py`

---

## 2. Flujo de Venta — Modo TEU_OFF (cola para caja)

**Descripción:** El vendedor registra el pedido; el cobro lo realiza el cajero desde la pantalla de Caja.

### Paso 1: Registro del ticket en el POS

```
POST /api/ventas
  body: { items: [...], modo_venta: "TEU_OFF" }
        │
        └── svc_ventas.registrar_venta()
              ├── Crea Venta(estado=PENDIENTE, metodo_pago=PENDIENTE)
              ├── Crea ItemVenta
              ├── Genera numero_ticket
              └── NO descuenta stock (se hace al cobrar)
```

**Nota:** En TEU_OFF el stock NO se descuenta al registrar, sino al cobrar el ticket desde caja. *No evidente en el código si hay un segundo descuento de stock en el cobro — ver `caja_tickets.py`/`cobro_ticket()`: no llama a `descontar_stock` explícitamente. Potencial inconsistencia.*

### Paso 2: Gestión del carrito (opcional)

```
POST   /api/ventas/{id}/items          # Agregar producto
PATCH  /api/ventas/{id}/items/{item_id} # Modificar cantidad/precio
DELETE /api/ventas/{id}/items/{item_id} # Eliminar producto
PATCH  /api/ventas/{id}/descuento       # Aplicar descuento

# Todos los estados válidos: Venta.estado == PENDIENTE
```

### Paso 3: Opcional — Suspender / Reanudar

```
POST /api/ventas/{id}/suspender   # PENDIENTE → SUSPENDIDA
POST /api/ventas/{id}/reanudar    # SUSPENDIDA → PENDIENTE
```

### Paso 4: Cobro desde Caja

```
GET  /api/caja/{id}/tickets-pendientes   # Lista la cola de ventas PENDIENTE
POST /api/caja/tickets/{venta_id}/cobrar
  body: {
    pagos: [
      { metodo_pago: "EFECTIVO",          importe: 1000 },
      { metodo_pago: "CUENTA_CORRIENTE",  importe:  500 }
    ]
  }
        │
        └── svc_caja_tickets.cobro_ticket()
              ├── Verifica que hay caja abierta
              ├── Verifica que la venta está PENDIENTE
              ├── Valida suma de pagos == venta.total
              ├── Si hay CUENTA_CORRIENTE:
              │     ├── Valida límite de crédito del cliente
              │     └── Registra MovimientoCuentaCorriente(tipo=VENTA)
              ├── Por cada pago no-crédito:
              │     └── svc_tesoreria.registrar_movimiento_caja(tipo=VENTA)
              ├── Crea PaymentTransaction por cada pago
              ├── emit_event("PagoRegistrado") por cada PaymentTransaction
              └── Actualiza estado de venta:
                    • Pago total en crédito → FIADA
                    • Pago en efectivo/otros → PAGADA
                    • Pagos combinados → metodo_pago = PAGO_COMBINADO
```

**Módulos involucrados:** `routers/ventas.py`, `routers/caja.py`, `services/ventas.py`, `services/caja_tickets.py`, `services/tesoreria.py`, `services/cuentas_corrientes.py`, `events.py`

---

## 3. Flujo de Caja

### Apertura de Caja

```
POST /api/caja/abrir
  body: { saldo_inicial: 5000, usuario_id: 1 }
        │
        └── svc_tesoreria.abrir_caja()
              ├── Verifica que NO haya caja abierta (una a la vez)
              ├── Crea Caja(fecha_cierre=None)
              └── emit_event("CajaAbierta")
```

### Cierre de Caja (Arqueo)

```
POST /api/caja/{id}/cerrar
  body: { saldo_final: 6200, supervisor_autorizado: false }
        │
        └── svc_tesoreria.cerrar_caja()
              ├── Lee configuración de caja (get_configuracion_caja)
              │     • obligar_arqueo: si True, saldo_final es obligatorio
              │     • permitir_cierre_con_diferencia
              │     • requerir_autorizacion_supervisor_cierre
              ├── Calcula saldo_teorico (saldo_inicial + ingresos - egresos)
              ├── Valida diferencia (saldo_final vs saldo_teorico)
              ├── Registra fecha_cierre
              └── emit_event("CajaCerrada")
```

### Movimiento Manual de Caja

```
POST /api/caja/{id}/movimientos
  body: { tipo: "GASTO", monto: 200, referencia: "Limpieza" }
        │
        └── svc_tesoreria.registrar_movimiento_caja()
              └── emit_event("MovimientoCajaRegistrado")
```

**Tipos de movimiento de caja:** `VENTA`, `DEVOLUCION`, `RETIRO`, `INGRESO`, `GASTO`

---

## 4. Flujo de Pesables

```
[Balanza / Operario]
        │
        ▼  Pesa el producto y registra
POST /api/pesables
  body: { producto_id: 5, peso: 1.250 }
        │
        └── svc_pesables.preparar_item()
              ├── Lee producto (debe tener pesable=True y plu asignado)
              ├── Calcula precio_total = peso × producto.precio_venta
              ├── Genera barcode EAN-13 (codifica PLU + precio en el barcode)
              └── Crea PesableItem(estado=pending)

        │
        ▼  Imprime etiqueta EAN-13
PATCH /api/pesables/{id}/estado
  body: { estado: "printed" }

        │
        ▼  [POS] Cajero escanea etiqueta
POST /api/ventas/{venta_id}/items/pesable-barcode
  body: { barcode: "2012501500123" }
        │
        └── svc_ventas.agregar_pesable_por_barcode()
              ├── Busca PesableItem por barcode
              ├── Verifica estado == "printed" (no "used")
              ├── Crea ItemVenta:
              │     • cantidad    = peso (1.250 kg)
              │     • precio_unitario = precio/kg
              │     • subtotal    = precio_total del barcode (NO recalcula)
              ├── Marca PesableItem.estado = "used"
              └── Recalcula totales de la venta
```

**Regla crítica:** El precio viaja codificado en el barcode EAN-13. El POS nunca recalcula el precio de un ítem pesable.

---

## 5. Flujo de Productos / Inventario

### Creación de Producto

```
POST /api/productos
  body: { sku, nombre, precio_venta, tipo_producto, pesable, plu, ... }
        │
        └── svc_productos.crear_producto()
              └── Valida unicidad de SKU y PLU (si pesable)
```

### Ingreso de Stock (por Compra o Carga Manual)

```
POST /api/inventario/ingresar
  body: { producto_id, cantidad, tipo: "COMPRA", ubicacion: "GONDOLA" }
        │
        └── svc_inventario.ingresar_stock()
              ├── Obtiene o crea registro Stock(producto_id, ubicacion)
              ├── stock.cantidad += cantidad
              └── Crea MovimientoInventario(tipo=COMPRA, cantidad=+N)
```

### Transferencia entre Ubicaciones

```
POST /api/inventario/transferir
  body: { producto_id, cantidad, origen: "DEPOSITO", destino: "GONDOLA" }
        │
        └── svc_inventario.transferir_stock()
              ├── Verifica stock suficiente en origen
              ├── Reduce Stock en origen
              ├── Incrementa Stock en destino
              └── Crea dos MovimientoInventario (salida + entrada)
```

---

## 6. Flujo de Compra a Proveedor

```
POST /api/compras
  body: {
    proveedor_id: 3,
    items: [{ producto_id: 1, cantidad: 100, costo_unitario: 50 }]
  }
        │
        └── svc_compras.registrar_compra()
              ├── Valida proveedor existe
              ├── Crea Compra(estado=CONFIRMADA)
              ├── Crea ItemCompra por cada ítem
              └── (Opcionalmente) ingresa stock automáticamente
```

---

## 7. Flujo de Devolución / Operación Comercial

```
POST /api/operaciones-comerciales
  body: {
    venta_id: 10,
    tipo: "DEVOLUCION",
    motivo: "Producto en mal estado",
    items: [{ producto_id: 2, cantidad: 1, precio_unitario: 300 }]
  }
        │
        └── svc_operaciones_comerciales.ejecutar_operacion()
              ├── Verifica que la venta existe
              ├── Crea OperacionComercial(tipo=DEVOLUCION, estado=EJECUTADA)
              ├── Crea OperacionComercialDetalle por cada ítem
              ├── Si tipo=DEVOLUCION: reingresa stock al inventario
              └── Si tipo incluye reintegro: actualiza caja o cuenta corriente
```

---

## 8. Flujo de Cuenta Corriente de Cliente

```
[Al vender a crédito]
svc_ventas / caja_tickets llama:
svc_cuentas_corrientes.registrar_movimiento_cuenta_corriente(
    tipo=VENTA, monto=total_venta
)
→ Crea o actualiza CuentaCorrienteCliente.saldo += monto

[Al cobrar deuda]
POST /api/cuentas-corrientes/{cliente_id}/pagar
  body: { monto: 500 }
→ Registra MovimientoCuentaCorriente(tipo=PAGO)
→ CuentaCorrienteCliente.saldo -= monto
```
