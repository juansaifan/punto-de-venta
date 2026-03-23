Módulo 2 — Punto de Venta
Arquitectura del módulo (Versión 2)
El módulo Punto de Venta agrupa todas las funcionalidades necesarias para operar comercialmente un negocio desde el sistema POS.
Este módulo gestiona el flujo operativo del comercio en tiempo real, incluyendo la generación de ventas, la gestión de cobros y la administración de operaciones comerciales.
Incluye:
ventas
generación de tickets
gestión de caja
cobros
operaciones comerciales
gestión de productos pesables
El módulo no administra movimientos financieros globales del negocio.
 Las operaciones financieras generales se gestionan en los módulos:
Tesorería
Finanzas

Estructura del módulo
Punto de Venta
│
├── Ventas
├── Caja
├── Operaciones comerciales
└── Pesables

1. Ventas
Submódulo encargado de registrar las ventas realizadas en el comercio.
Permite generar tickets de venta y administrar el proceso comercial previo al cobro.

Funcionalidades
búsqueda de productos
selección por categorías
carrito de compra
selección de cliente
aplicación de descuentos
generación de ticket
ventas en suspenso

Modos de operación
El sistema permite dos modos de venta.
TEU OFF
TEU ON

TEU OFF — Venta tradicional
Flujo:
selección de productos
↓
generación de ticket
↓
ticket enviado a Caja
↓
Caja realiza el cobro
Este modo separa los roles de:
vendedor
cajero

TEU ON — Venta con cobro inmediato
Flujo:
selección de productos
↓
selección de cliente
↓
selección de método de pago
↓
cobro inmediato
↓
venta finalizada
Este modo unifica los roles de:
vendedor
cajero

Selección de cliente
Campo desplegable:
Cliente
[ Consumidor final ▼ ]
Permite:
buscar cliente existente
crear nuevo cliente
Si el cliente no existe se muestra:
+ Nuevo cliente
Esto redirige al módulo Personas.

Selección de método de pago
Disponible únicamente en modo TEU ON.
Campo:
Método de pago
[ Efectivo ▼ ]
Opciones:
efectivo
tarjeta crédito
tarjeta débito
transferencia
pago combinado
cuenta corriente
otros métodos

Ventas en suspenso
Permite gestionar múltiples ventas simultáneamente.
Ejemplo:
Venta principal
Cliente A
Cliente B
+
Flujo típico:
cliente llega
↓
se inicia venta
↓
cliente espera
↓
se crea nueva pestaña de venta

2. Caja
Submódulo encargado de registrar todos los cobros asociados a ventas o deudas.
Caja centraliza toda la lógica de cobro del sistema para evitar duplicación de procesos.

Modos de Caja
Caja posee dos modos de operación.
Cobros por venta
Cobros de deuda

Cobros por venta
Muestra la cola de tickets pendientes generados por el módulo Ventas.
Pantalla principal:
Ticket
Cliente
Hora
Total
Flujo:
abrir ticket
↓
seleccionar método de pago
↓
registrar pago
↓
finalizar venta

Cobros de deuda
Permite cobrar cuentas corrientes de clientes.
Pantalla principal:
lista de clientes con deuda
Al seleccionar cliente:
tickets pendientes
El sistema aplica pagos al:
ticket más antiguo

Métodos de pago
Caja soporta:
efectivo
tarjeta crédito
tarjeta débito
transferencia
pago combinado
cuenta corriente
otros métodos
Los métodos de pago se definen en:
Configuración → Medios de pago
Cada medio de pago se vincula con:
cuenta financiera

Motor de pagos
Todos los pagos utilizan el modelo:
PaymentTransaction
Cada registro incluye:
metodo_pago
importe
cuenta financiera
cobrador
fecha
observaciones
Esto permite manejar:
pagos combinados
conciliación bancaria
auditoría de caja
devoluciones

3. Operaciones comerciales
Submódulo encargado de gestionar y ejecutar todas las operaciones comerciales posteriores a la venta.
Este submódulo no solo permite consultar el historial de operaciones, sino también realizar modificaciones o correcciones comerciales sobre transacciones existentes.

Operaciones disponibles
Este módulo permite ejecutar operaciones como:
cambios de productos
devoluciones
notas de crédito
notas de débito
anulaciones
ajustes comerciales

Flujo típico de operación
Ejemplo de devolución:
buscar operación
↓
seleccionar venta
↓
ejecutar devolución
↓
generar nota de crédito o reintegro
Ejemplo de cambio de producto:
buscar operación
↓
seleccionar venta
↓
registrar producto devuelto
↓
registrar producto nuevo
↓
ajustar diferencia

Relación con otros módulos
Las operaciones realizadas en este submódulo pueden generar impactos en:
Caja
Tesorería
Finanzas
Inventario
Ejemplos:
Devolución
reintegro de dinero
↓
movimiento en Caja
↓
registro financiero
Nota de crédito
ajuste contable
↓
impacto en Finanzas
Cambio de producto
devolución de stock
↓
entrega de nuevo producto
↓
ajuste en Inventario
Este submódulo funciona como centro de control de las operaciones comerciales posteriores a la venta.

4. Pesables
Submódulo encargado de gestionar productos que requieren peso o preparación previa antes de ser vendidos.
Este módulo no representa un área específica del comercio, sino un tipo de producto.
Ejemplos:
fiambres
carnicería
verdulería
panadería
productos a granel

Funcionalidades
integración con balanza
registro de peso
generación de etiquetas
precio por kilo
preparación previa a venta
Los productos preparados pueden ser posteriormente vendidos en el POS.

Relación con otros módulos
El módulo Punto de Venta interactúa con:
Personas
Inventario
Tesorería
Finanzas
Configuración

Integración con Tesorería
Caja registra cobros mediante:
PaymentTransaction
Tesorería transforma estos registros en:
FinancialTransaction
permitiendo registrar el movimiento financiero real.

Integración con Finanzas
El módulo Finanzas utiliza la información proveniente de:
Ventas
Caja
Tesorería
Operaciones comerciales
para generar:
balances
reportes financieros
arqueos
análisis de ingresos y egresos

Arquitectura del flujo operativo
Ventas
↓
Caja
↓
PaymentTransaction
↓
Tesorería
↓
FinancialTransaction
↓
Finanzas

Estado del módulo
Con esta versión queda definida la arquitectura completa del:
Módulo Punto de Venta
incluyendo:
Ventas
Caja
Operaciones comerciales
Pesables
Este módulo representa la capa operativa del sistema comercial, encargada de registrar las ventas, cobros y operaciones comerciales del negocio.
