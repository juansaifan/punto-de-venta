# DOMINIOS --- Sistema Punto de Venta

## 1. Propósito

Este documento define los **dominios del negocio (bounded contexts)**
del sistema Punto de Venta.

Sirve para:

-   estructurar la arquitectura del sistema
-   separar responsabilidades
-   facilitar mantenimiento
-   permitir desarrollo modular
-   ayudar a agentes de IA a comprender el sistema

Cada dominio representa **un área del negocio con sus propias reglas,
entidades y operaciones**.

------------------------------------------------------------------------

# 2. Lista de Dominios

El sistema se divide en los siguientes dominios:

1.  Ventas (Punto de Venta)
2.  Inventario
3.  Tesorería
4.  Finanzas
5.  Personas
6.  Reportes
7.  Configuración
8.  Integraciones
9.  Observabilidad (Dashboard)

------------------------------------------------------------------------

# 3. Dominio: Ventas

Responsable de registrar operaciones comerciales.

Entidades:

-   Venta
-   DetalleVenta
-   Pago

Responsabilidades:

-   registrar ventas
-   calcular totales
-   aplicar descuentos
-   registrar pagos
-   generar comprobantes

Eventos emitidos:

VentaRegistrada\
PagoRegistrado

Dependencias:

Inventario\
Tesorería\
Personas

------------------------------------------------------------------------

# 4. Dominio: Inventario

Gestiona productos y stock.

Entidades:

Producto\
MovimientoInventario

Responsabilidades:

-   catálogo de productos
-   control de stock
-   movimientos de inventario
-   alertas de stock

Eventos emitidos:

StockBajoDetectado\
LotesProximosAVencerDetectados

------------------------------------------------------------------------

# 5. Dominio: Tesorería

Controla el flujo real de dinero.

Entidades:

Caja\
MovimientoCaja

Responsabilidades:

-   apertura de caja
-   cierre de caja
-   ingresos
-   egresos
-   arqueo de caja

Eventos emitidos:

CajaAbierta\
CajaCerrada\
MovimientoCajaRegistrado

------------------------------------------------------------------------

# 6. Dominio: Finanzas

Gestiona la estructura financiera del negocio.

Entidades:

CuentaFinanciera\
TransaccionFinanciera

Responsabilidades:

-   cuentas por pagar
-   cuentas por cobrar
-   control de gastos
-   control de ingresos

Eventos emitidos:

IngresoRegistrado\
GastoRegistrado

------------------------------------------------------------------------

# 7. Dominio: Personas

Gestiona entidades humanas.

Entidades:

Cliente\
Empleado\
Proveedor

Responsabilidades:

-   registro de clientes
-   historial de compras
-   gestión de empleados

Eventos emitidos:

No definidos como eventos de bus in-process en la implementación actual.

------------------------------------------------------------------------

# 8. Dominio: Reportes

Produce información analítica.

Responsabilidades:

-   agregación de datos
-   generación de reportes
-   análisis de ventas
-   análisis financiero

Este dominio **consume eventos de otros dominios**.

------------------------------------------------------------------------

# 9. Dominio: Configuración

Define parámetros globales del sistema.

Responsabilidades:

-   usuarios
-   roles
-   permisos
-   impuestos
-   parámetros del negocio

Eventos emitidos:

No definidos como eventos de bus in-process en la implementación actual.

------------------------------------------------------------------------

# 10. Dominio: Integraciones

Conecta el sistema con sistemas externos.

Responsabilidades:

-   APIs externas
-   facturación electrónica
-   pasarelas de pago
-   exportaciones de datos

Eventos consumidos:

VentaRegistrada\
PagoRegistrado

------------------------------------------------------------------------

# 11. Dominio: Observabilidad (Dashboard)

Provee visibilidad operativa.

Responsabilidades:

-   métricas del negocio
-   indicadores clave
-   monitoreo

Este dominio **solo consume datos**, no genera operaciones.

------------------------------------------------------------------------

Última actualización: 2026
