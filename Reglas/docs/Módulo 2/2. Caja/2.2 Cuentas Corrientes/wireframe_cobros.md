Wireframe v1 — Pantalla Cobros (Estructura v2)

1. Objetivo del submódulo
El submódulo Cobros permite gestionar las cuentas corrientes de clientes, registrar pagos posteriores y administrar las deudas generadas por ventas fiadas.
El módulo permite:
consultar clientes con deuda
visualizar tickets pendientes
registrar pagos parciales o totales
aplicar pagos automáticamente a tickets pendientes
mantener historial de cobros
El sistema utiliza el principio contable:
FIFO (First In First Out)
Esto significa que los pagos se aplican primero al ticket más antiguo pendiente.

2. Flujo operativo general
Cliente con deuda
       ↓
Seleccionar cliente
       ↓
Visualizar tickets pendientes
       ↓
Registrar pago
       ↓
Seleccionar medio de pago
       ↓
Aplicar pago a tickets pendientes

3. Estructura del módulo
Cobros
│
├─ KPIs del módulo
├─ Lista de cuentas corrientes
│     └ Cliente expandido
│           └ Tickets pendientes
│
└ Flujo de cobro
     ├ Selección cliente
     ├ Popup medios de pago
     ├ Popup pago
     └ Confirmación

4. KPIs del módulo
En la parte superior de la pantalla se muestran indicadores rápidos que permiten al operador o al administrador visualizar el estado de las cuentas corrientes.
KPIs visibles
Clientes con deuda
Deuda total
Pagos registrados hoy
Vencimientos hoy

Ejemplo
Clientes con deuda: 14
Deuda total: $83.200
Pagos hoy: $12.400
Vencimientos hoy: $6.800

5. Ordenamiento de cuentas corrientes
La lista principal debe ordenarse automáticamente según:
1. Fecha de vencimiento más próxima
2. Monto adeudado
Esto permite que el cajero o el supervisor identifique rápidamente:
qué deudas vencen hoy
qué clientes requieren seguimiento

6. Pantalla principal — Lista de cuentas corrientes
La pantalla principal presenta una fila por cliente.
Esto evita tener múltiples tickets visibles y simplifica la operación.

Tabla principal
Columnas:
Cliente
DNI
Tickets pendientes
Deuda total
Fecha de vencimiento
Último movimiento

Ejemplo
Cliente            DNI        Tickets   Deuda total   Vencimiento   Último movimiento
Victoria Perez     32911452   3         $6.200        15/03         12/03
Juan Gomez         30111452   1         $1.800        18/03         11/03
Maria Lopez        28911234   2         $3.500        20/03         10/03

7. Expansión de cliente
Al seleccionar un cliente se despliega el detalle de sus tickets pendientes.

Estructura
Cliente: Victoria Perez
Deuda total: $6.200
Tabla de tickets:
Ticket | Fecha | Total | Pagado | Saldo | Vencimiento

Ejemplo
000124 | 10/03 | $2000 | $2000 | $0    | 10/03
000130 | 11/03 | $3000 | $1000 | $2000 | 15/03
000135 | 12/03 | $2200 | $0    | $2200 | 18/03

8. Acciones disponibles
Botones dentro del cliente expandido:
Registrar pago
Ver historial
El botón principal es:
Registrar pago

9. Flujo de registro de pago
Cuando se presiona Registrar pago, el sistema abre el flujo de cobro.
Este flujo reutiliza exactamente los mismos popups que el submódulo Caja.

Popup — Medios de pago
Opciones disponibles:
Efectivo
Tarjeta crédito
Tarjeta débito
Transferencia
Pago combinado

Popup — Pago
Los formularios de pago son idénticos a los utilizados en Caja.
Incluyen:
Valor del pago
Banco / cuenta
Vendedor
Cobrador / Cajero
Observaciones

10. Aplicación automática del pago
Cuando se registra un pago, el sistema aplica el importe automáticamente a los tickets pendientes.
Regla:
Ordenar tickets por fecha
Aplicar pago al ticket más antiguo
Continuar hasta agotar el monto

Ejemplo
Deuda:
Ticket A: $1000
Ticket B: $2000
Ticket C: $3000
Pago recibido:
$2500
Resultado:
Ticket A → cancelado
Ticket B → saldo $500
Ticket C → sin cambios

11. Confirmación del pago
Al finalizar el proceso:
Se registra PaymentTransaction
Se actualizan los saldos de tickets
Se actualiza la deuda del cliente

12. Modelo de datos utilizado
Los cobros utilizan la misma estructura que los pagos en caja.
Entidad:
PaymentTransaction
Estructura conceptual:
Venta
 │
 └ PaymentTransaction
       ├ metodo_pago
       ├ importe
       ├ banco
       ├ cobrador
       ├ fecha
       └ observaciones
Para los cobros de cuenta corriente se agrega:
source = cuenta_corriente

13. Layout general de la pantalla
HEADER

KPIs DEL MÓDULO

Buscar cliente

Tabla cuentas corrientes
     ↓
Cliente expandido
     ↓
Tickets pendientes

Botón Registrar pago

14. Beneficios de este diseño
Este enfoque permite:
operación rápida para el cajero
visualización clara de clientes con deuda
control de vencimientos
aplicación automática de pagos
reutilización del flujo de Caja
trazabilidad completa de pagos
