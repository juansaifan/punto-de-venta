# Submódulo --- Caja

## Módulo 2 --- Punto de Venta

Versión 1 --- Documentación funcional consolidada

------------------------------------------------------------------------

# 1. Objetivo del submódulo

El submódulo **Caja** gestiona el proceso de cobro de operaciones
comerciales generadas por el sistema.

Permite:

-   cobrar ventas generadas desde el módulo **Ventas**
-   cobrar deudas provenientes de **Cuentas Corrientes**
-   registrar pagos mediante distintos medios
-   administrar sesiones de caja
-   controlar el flujo de dinero en el punto de venta

La Caja funciona como el **centro de liquidación de operaciones
monetarias del comercio**.

------------------------------------------------------------------------

# 2. Alcance del submódulo

El submódulo Caja se encarga de:

-   cobrar tickets de venta
-   cobrar deudas de clientes
-   registrar pagos combinados
-   calcular cambios
-   registrar movimientos de caja
-   administrar sesiones de caja
-   emitir comprobantes

------------------------------------------------------------------------

# 3. Estructura del submódulo

    Caja
    │
    ├─ Pantalla principal
    ├─ Detalle de ticket
    ├─ Selección de método de pago
    ├─ Pago en efectivo
    ├─ Pago electrónico
    ├─ Pago combinado
    ├─ Cuenta corriente
    └─ Confirmación de pago

------------------------------------------------------------------------

# 4. Sesión de caja

Cada operación de caja ocurre dentro de una **sesión de caja**.

Flujo de sesión:

    apertura de caja
    ↓
    operación de cobros
    ↓
    arqueo de caja
    ↓
    cierre de caja

Datos registrados:

-   usuario
-   fecha y hora
-   monto inicial
-   saldo esperado
-   saldo contado
-   diferencias

------------------------------------------------------------------------

# 5. Pantalla principal --- Esperando ticket

La pantalla principal muestra:

### Área de escaneo

Campo:

    Escanear código de ticket o ingresar número

Permite:

-   lector de código de barras
-   ingreso manual

------------------------------------------------------------------------

### Cola de tickets pendientes

Tabla:

  Ticket   Cliente   DNI   Hora   Total
  -------- --------- ----- ------ -------

Acción:

    Seleccionar ticket → abrir detalle

------------------------------------------------------------------------

# 6. Detalle de ticket

Cuando se carga un ticket se muestra:

### Información del ticket

-   Ticket Nº
-   Fecha
-   Cliente
-   Vendedor

### Lista de productos

| Producto \| Cantidad \| Precio \| Subtotal \|

### Resumen de venta

-   Subtotal
-   Descuentos
-   Impuestos
-   TOTAL

### Acciones

    Cancelar
    Pagar

------------------------------------------------------------------------

# 7. Popup --- Selección de método de pago

Al presionar **Pagar** se abre el selector de método.

Métodos disponibles:

-   Efectivo
-   Tarjeta crédito
-   Tarjeta débito
-   Transferencia
-   Pago combinado
-   Cuenta corriente

------------------------------------------------------------------------

# 8. Popup --- Pago en efectivo

Campos:

-   Valor recibido
-   Cambio calculado automáticamente

Opciones rápidas:

-   total exacto
-   redondeos

Campos adicionales:

-   vendedor
-   cobrador / cajero
-   observaciones

Acciones:

    Cancelar
    Continuar

------------------------------------------------------------------------

# 9. Popup --- Pagos electrónicos

Utilizado para:

-   tarjeta crédito
-   tarjeta débito
-   transferencia

Campos:

-   importe
-   banco o cuenta asociada
-   vendedor
-   cobrador

------------------------------------------------------------------------

# 10. Popup --- Pago combinado

Permite dividir el pago entre múltiples métodos.

Tabla:

| Método \| Importe \| Cuenta \|

Sistema calcula:

-   total recibido
-   saldo restante

------------------------------------------------------------------------

# 11. Pago a cuenta corriente

Permite registrar una venta como deuda del cliente.

Campos:

-   cliente
-   saldo actual
-   límite de crédito
-   vendedor
-   cobrador

Resultado:

    venta registrada como deuda

------------------------------------------------------------------------

# 12. Confirmación final

Una vez confirmado el pago:

-   venta finalizada
-   ticket eliminado de cola
-   comprobante emitido

------------------------------------------------------------------------

# 13. Modelo de datos --- PaymentTransaction

Cada operación puede generar uno o múltiples pagos.

Estructura conceptual:

    Operacion Comercial
    │
    └── Venta
          │
          └── PaymentTransaction
                  ├ Pago 1
                  ├ Pago 2
                  └ Pago N

Cada registro contiene:

-   metodo_pago
-   importe
-   cuenta financiera
-   cobrador
-   fecha
-   observaciones

------------------------------------------------------------------------

# 14. Cambios estructurales para unificar Ventas y Cuentas Corrientes

Para simplificar el sistema se introduce un cambio estructural en el
submódulo Caja.

Actualmente existen dos flujos separados:

    Cobros de ventas
    Cobros de deudas

Estos flujos se unifican mediante un selector de modo.

------------------------------------------------------------------------

# 15. Selector de modo de operación

La pantalla principal de Caja incorporará un selector similar al modo
TEU.

Modos disponibles:

    Modo Venta
    Modo Cuenta Corriente

### Modo Venta

Muestra:

-   cola de tickets generados por el módulo Ventas

### Modo Cuenta Corriente

Muestra:

-   lista de clientes con deuda
-   saldo pendiente
-   vencimientos

------------------------------------------------------------------------

# 16. Pantalla de Cuentas Corrientes

Al seleccionar un cliente se muestra:

Tabla de deudas:

| Ticket \| Fecha \| Importe \| Saldo \|

Regla de pago:

    los pagos se aplican al ticket más antiguo

Acción:

    Pagar

Luego se reutiliza exactamente el mismo flujo de pagos de Caja.

------------------------------------------------------------------------

# 17. Beneficios de la unificación

Este cambio permite:

-   reutilizar lógica de pagos
-   simplificar la interfaz
-   evitar duplicación de módulos
-   centralizar control financiero

------------------------------------------------------------------------

# Estado del submódulo

Con esta versión queda definida la estructura completa del submódulo
**Caja** incluyendo la unificación con **Cuentas Corrientes**.
