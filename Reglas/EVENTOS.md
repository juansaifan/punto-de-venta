# EVENTOS --- Sistema Punto de Venta

## 1. Propósito

Este documento define los **eventos del sistema**.

Los eventos permiten:

-   comunicación entre módulos
-   automatización
-   auditoría
-   integraciones externas

Un evento representa **algo importante que ocurrió en el sistema**.

------------------------------------------------------------------------

# 2. Eventos de Ventas

VentaRegistrada

Se dispara cuando se confirma/registra una venta.

Datos típicos (según implementación actual):

-   venta_id
-   fecha (ISO string)
-   total
-   caja_id (puede ser null si no hay caja)

------------------------------------------------------------------------

PagoRegistrado

Se dispara cuando se registra un pago.

Datos:

-   pago_id
-   venta_id
-   metodo_pago
-   monto

-------------------------------------------------------------------------

OperacionComercialRegistrada

Se dispara cuando se ejecuta una operación comercial posterior (devolución, cambio, notas de crédito/débito, anulaciones, etc.).

Datos típicos (según implementación actual):

-   operacion_id
-   venta_id
-   cliente_id (puede ser null)
-   tipo
-   estado
-   motivo
-   importe_total

------------------------------------------------------------------------

# 3. Eventos de Inventario

StockBajoDetectado

Se dispara cuando el sistema detecta productos con stock por debajo del mínimo (alertas operativas).

Datos típicos:

-   ubicacion
-   total
-   items (top N, con datos de stock)

-------------------------------------------------------------------------

LotesProximosAVencerDetectados

Se dispara cuando el sistema detecta lotes próximos a vencerse (alertas operativas).

Datos típicos:

-   dias_vencimiento
-   total
-   items (top N, con datos de lote)

-------------------------------------------------------------------------

# 4. Eventos de Tesorería

CajaAbierta

Se dispara al iniciar una caja.

------------------------------------------------------------------------

CajaCerrada

Se dispara al cerrar la caja.

------------------------------------------------------------------------

MovimientoCajaRegistrado

Se dispara cuando hay un ingreso o egreso.

------------------------------------------------------------------------

Datos:

- movimiento_id
- caja_id
- tipo
- monto
- medio_pago
- referencia (opcional)
- fecha (ISO string)

MovimientoCuentaCorrienteRegistrado

Se dispara cuando se registra un movimiento en la cuenta corriente de un cliente (Tesorería/Cuentas Corrientes).

Datos:

- movimiento_id
- cuenta_id
- cliente_id
- tipo (VENTA | PAGO | AJUSTE)
- monto
- descripcion (opcional)
- fecha (ISO string)
- saldo_despues

Notas:

- Es un evento **in-process** (bus interno). Para auditoría/observabilidad se consume y persiste en `evento_sistema_log`.

# 5. Eventos de Finanzas

IngresoRegistrado

Se dispara al registrar ingresos financieros.

------------------------------------------------------------------------

GastoRegistrado

Se dispara al registrar gastos.

------------------------------------------------------------------------

# 6. Uso de Eventos

Los eventos permiten:

-   sincronizar módulos
-   generar reportes
-   activar automatizaciones
-   enviar información a sistemas externos

Ejemplo:

VentaRegistrada → actualizar inventario\
VentaRegistrada → registrar ingreso en caja\
VentaRegistrada → alimentar reportes

------------------------------------------------------------------------

Última actualización: 2026-03-19
