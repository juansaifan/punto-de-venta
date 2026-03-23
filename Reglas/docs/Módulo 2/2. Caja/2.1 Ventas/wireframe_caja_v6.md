Wireframe v1 — Pantalla Caja
Estructura v6

1. Header del sistema
Barra superior común al sistema POS.
Elementos:
☰ Menú principal
Caja
Estado del sistema
Sucursal activa
Usuario activo
Accesos rápidos
Ejemplo:
Caja | Disponible | Sucursal Principal | Usuario

2. Estado inicial — Esperando ticket
Pantalla base del cajero.
Área de escaneo:
[ Escanear código de ticket o ingresar número ]
Entrada permitida:
lector de código de barras
ingreso manual
Cuando se escanea:
el sistema carga automáticamente la venta

3. Panel de cola de tickets
Debajo del escáner aparece la cola de ventas pendientes de cobro.

3.1 Resumen de cola
Indicador superior.
Tickets en espera: 5
Monto total pendiente: $82.300
Objetivo:
visibilidad de cola
control de flujo de caja

3.2 Lista de tickets
Tabla principal.
Ticket | Cliente | DNI | Hora | Total
Ejemplo:
000124 | Victoria Perez | 32911452 | 18:03 | $3.630
000125 | Consumidor Final | - | 18:04 | $2.200
000126 | Juan Gomez | 30111452 | 18:05 | $8.400
000127 | Maria Rodriguez | 27911252 | 18:06 | $9.700
000128 | Luis Alvarez | 22543936 | 18:09 | $58.370
Acciones disponibles:
click → seleccionar ticket
doble click → abrir ticket
La fila seleccionada queda resaltada.

4. Acción principal — Botón PAGAR
Se agrega el botón Pagar también en la pantalla principal.
Ubicación:
parte inferior derecha del panel de tickets
Botón:
Pagar
Estados del botón:

5. Estado 2 — Ticket cargado
Cuando:
escaneo de ticket
o
click en ticket
Se muestra el detalle de la venta.

5.1 Información del ticket
Encabezado:
Ticket Nº
Fecha
Vendedor
Cliente
Ejemplo:
Ticket 000124
Cliente: Victoria Perez
DNI: 32911452
Vendedor: Juan

5.2 Lista de productos
Tabla:
Producto
Cantidad
Precio
Subtotal

5.3 Resumen de venta
Panel inferior.
Subtotal
Impuestos
Descuentos
TOTAL
Ejemplo:
TOTAL
$3.630

5.4 Acciones del ticket
Botones:
Cancelar
Pagar
Acción Pagar:
abre selector de método de pago

6. Popup — Selección de método de pago
Al presionar Pagar se abre el selector.
Encabezado:
Pagar factura
TOTAL $3.630
Métodos disponibles:
Principales:
Efectivo
Tarjeta crédito
Transferencia
Otros:
Tarjeta débito
Pago combinado
Cuenta corriente
Otros métodos

7. Popup — Pago en efectivo
Encabezado:
TOTAL $3.630
Por cobrar: $3.630
Luego de ingresar dinero:
Cambio: $370
Campo:
Valor del pago en efectivo
El sistema calcula automáticamente:
Cambio = monto recibido - total

Opciones rápidas
Botones:
$3.630
$3.700
$4.000

Campos adicionales
Vendedor
Cobrador / Cajero
Observaciones
Ejemplo:
Vendedor: Juan
Cobrador: Maria

Acciones
Cancelar
Continuar
Al continuar:
se registra el pago
se finaliza la venta
se imprime comprobante

8. Popup — Pagos electrónicos
Utilizado para:
Tarjeta crédito
Tarjeta débito
Transferencia
Campos:
Valor del pago
Banco
Características:
valor autocompletado con total
editable

Campos adicionales
Vendedor
Cobrador / Cajero
Observaciones

Objetivo del campo Banco
Permitir registrar a qué cuenta ingresó el dinero.
Ejemplo:
Cuenta bancaria
MercadoPago
POSNET
Caja virtual
Esto permite:
conciliación bancaria
reportes financieros
control de ingresos

9. Popup — Pago combinado
Permite dividir el pago en múltiples métodos.
Encabezado:
TOTAL $3.630
Total recibido $0
Por cobrar $3.630
Valores actualizados dinámicamente.

Tabla de métodos
Estructura:
Método de pago | Valor del pago | Banco
Ejemplo:
Efectivo | 0 | Efectivo POS
Débito   | 0 | Caja general

Agregar método
Botón:
+ Agregar método
Permite agregar nuevos métodos de pago.

Cálculo automático
El sistema actualiza:
Total recibido
Total restante
Ejemplo:
Efectivo 2000
Débito   1630
Resultado:
Total recibido $3630
Por cobrar $0

Campos adicionales
Debajo de la tabla:
Vendedor
Cobrador / Cajero

Acciones
Cancelar
Continuar

10. Popup — Cuenta corriente
Para registrar ventas fiadas.
Campos:
Cliente
Saldo actual
Límite de crédito
Vendedor
Cobrador / Cajero
Acción:
Registrar deuda
Resultado:
venta registrada como FIADA
actualización de cuenta corriente

11. Confirmación final
Una vez completado el pago:
venta finalizada
ticket eliminado de cola
comprobante impreso

Flujo operativo completo
escanear ticket
o
seleccionar ticket
↓
verificar venta
↓
Pagar
↓
seleccionar método
↓
confirmar pago
↓
imprimir comprobante

Modelo de pagos — PaymentTransaction
Cada venta puede contener uno o múltiples pagos.
Estructura conceptual:
Operacion Comercial
      │
      └── Venta
              │
              └── PaymentTransaction
                      ├ Pago 1
                      ├ Pago 2
                      └ Pago N
Cada PaymentTransaction registra:
metodo_pago
importe
banco / cuenta
cobrador
fecha
observaciones
Esto permite manejar correctamente:
pagos combinados
auditoría de caja
conciliación bancaria
devoluciones

Estado del módulo Caja
Con esta versión queda definido:
flujo completo de cobro
manejo de múltiples métodos de pago
pagos combinados
cuentas corrientes
trazabilidad de vendedor y cajero
conciliación financiera
coherencia UI con módulo Cobros
El módulo Caja puede considerarse cerrado funcionalmente.
