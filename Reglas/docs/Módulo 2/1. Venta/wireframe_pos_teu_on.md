Wireframe v1 — Pantalla Ventas / POS
Modo TEU ON
Concepto del modo
Modo TEU ON significa:
venta
↓
selección método de pago
↓
pago inmediato
↓
impresión comprobante
Es decir:
Vendedor + Caja en una misma pantalla
No existe paso intermedio de Caja.

1. Header del sistema
Barra superior común a todo el sistema.
Elementos:
☰ Menú principal
Ventas / POS
Estado del sistema
Sucursal activa
Usuario activo
Accesos rápidos
Ejemplo visual:
☰  Ventas / POS                          Disponible   ⟳   ⧉   ?   Usuario

2. Barra de búsqueda de productos
Ubicada debajo del header.
Componentes:
[ 🔍 ] Buscar producto o código de barras...
[ Nuevo producto ]
Funcionalidades:
lector de código de barras
búsqueda por nombre
búsqueda por código
autocompletado
Resultado al seleccionar producto:
producto agregado al carrito

3. Selector de modo TEU
Ubicado en el panel derecho.
Formato:
Ventas / POS     TEU [ ON ]
Tipo de control:
toggle deslizante
Estados posibles:
OFF → modo vendedor + caja
ON  → modo venta + cobro
En este documento se describe ON.

4. Panel de categorías
Zona principal izquierda.
Grid de categorías.
Ejemplo:
Bebidas        Lácteos       Fiambres       Panadería
Snacks         Limpieza      Despensa       Carnicería
Características:
botones grandes
iconos representativos
navegación por categorías
Flujo:
Categoría
↓
Subcategoría
↓
Producto

5. Panel derecho — Configuración de venta
Columna derecha fija.
Contiene todos los parámetros de la venta.

5.1 Lista de precios
Campo desplegable.
Lista de precios
[ General ▼ ]
Opciones posibles:
General
Mayorista
Promoción
Lista especial

5.2 Tipo de comprobante
Campo desplegable.
Tipo comprobante
[ Ticket ▼ ]
Opciones:
Ticket
Factura A
Factura B
Factura C
Nota de crédito

6. Cliente
Campo ubicado debajo del tipo de comprobante.
Estructura:
Cliente
[ Consumidor final ▼ ]
Valor por defecto:
Consumidor final
Opciones del desplegable:
buscar cliente por nombre
buscar cliente por DNI
Si no existe:
+ Nuevo cliente
Flujo:
Nuevo cliente
↓
abre módulo Personas
↓
crear cliente

7. Método de pago (SOLO EN TEU ON)
Este campo no existe en TEU OFF.
Ubicación:
a la derecha del campo Cliente
Estructura:
Método de pago
[ Efectivo ▼ ]
Opciones del desplegable:
Efectivo
Tarjeta de crédito
Transferencia
Tarjeta débito
Combinado
Cuenta corriente
Otros métodos de pago
Objetivo:
definir el método de cobro antes de finalizar la venta
Este valor se utilizará cuando se presione VENDER.

8. Lista de productos agregados
Debajo de cliente y método de pago.
Cada producto muestra:
Nombre producto
Código interno
Precio
Cantidad
Ejemplo:
Fideos Spaghetti Verizzia 500 g     $3.630
ALM-02-0001

[-] 1 [+]
Funciones:
incrementar cantidad
decrementar cantidad

9. Resumen de venta
Panel inferior del carrito.
Estructura:
Subtotal      $3.000
IVA (21%)       $630

TOTAL         $3.630
Este panel muestra:
base imponible
impuestos
total final

10. Acciones de venta
Ubicadas debajo del panel de categorías.
Botones:
Cancelar venta
Aplicar descuento
Funciones:
Cancelar venta
elimina todos los productos
Aplicar descuento
Permite:
descuento porcentual
descuento monto fijo
cupón promocional

11. Botón principal
Ubicado en la parte inferior del panel derecho.
VENDER
En TEU ON el flujo cambia.

12. Flujo de ejecución (TEU ON)
Al presionar VENDER:
validar productos
↓
validar cliente
↓
leer método de pago seleccionado
↓
abrir popup de pago correspondiente
Ejemplo:
Efectivo
↓
popup pago efectivo
o
Tarjeta
↓
popup pago electrónico
o
Combinado
↓
popup pagos múltiples

13. Ventas en suspenso
Barra inferior horizontal.
Estructura:
Venta principal    Victoria    +
Funciones:
Venta principal
Venta actual.
Ventas adicionales
Cada venta crea una pestaña.
Botón +
Permite:
crear nueva venta
Flujo típico:
cliente A
↓
venta en proceso
↓
cliente B llega
↓
+
↓
nueva venta

14. Diferencia estructural entre modos
TEU OFF
venta
↓
generar ticket
↓
caja cobra
Interfaz:
NO tiene selector de pago

TEU ON
venta
↓
seleccionar método de pago
↓
cobro inmediato
↓
ticket impreso
Interfaz:
aparece campo
"Método de pago"

15. Modelo de pago utilizado
El POS TEU ON usa el mismo modelo definido en Caja:
PaymentTransaction
Estructura conceptual:
Operacion Comercial
     │
     └── Venta
            │
            └── PaymentTransaction
                    ├ Pago 1
                    ├ Pago 2
                    └ Pago N
Cada pago registra:
metodo_pago
importe
banco
cobrador
fecha
observaciones
Esto permite:
pagos combinados
conciliación bancaria
auditoría de caja
devoluciones
16. Reutilización del motor de pagos del módulo Caja
En Modo TEU ON el POS permite cobrar la venta inmediatamente. Sin embargo, no se implementa un sistema de pagos independiente dentro del POS.
Para evitar duplicación de lógica y mantener consistencia contable, el POS reutiliza exactamente los mismos popups y flujo de pagos definidos en el módulo Caja.

16.1 Principio de diseño
El POS no implementa lógica de pago propia.
En su lugar:
POS (TEU ON)
↓
seleccionar método de pago
↓
invocar popup de pago del módulo Caja
↓
registrar PaymentTransaction
↓
finalizar venta
Esto garantiza:
reutilización del motor de pagos
consistencia contable
mantenimiento más simple
una sola fuente de verdad para pagos

16.2 Popups reutilizados del módulo Caja
Cuando se presiona VENDER en modo TEU ON, el sistema abrirá exactamente los mismos popups definidos en Caja.
Popups disponibles:
1. Selector de método de pago
2. Pago en efectivo
3. Pago electrónico
  - tarjeta crédito
  - tarjeta débito
  - transferencia
4. Pago combinado
5. Cuenta corriente
6. Pago a cuenta
Estos popups no pertenecen al POS, sino al módulo Caja, y son invocados desde el POS.

16.3 Configuración centralizada de medios de pago
Los medios de pago no se definen dentro del POS.
Se gestionan desde un módulo de configuración del sistema.
Propuesta de ubicación:
Configuración
↓
Finanzas
↓
Medios de pago
Cada medio de pago definirá:
nombre del medio
tipo de medio
cuenta bancaria asociada
comportamiento contable
Ejemplo de configuración:

16.4 Vinculación con cuentas financieras
Cada medio de pago estará asociado a una cuenta financiera.
Esto permite:
conciliación bancaria
control de caja
reportes financieros
auditoría contable
Ejemplo:
Tarjeta crédito
↓
Banco Galicia POS
↓
Cuenta bancaria Galicia

16.5 Registro de la transacción
El POS registra los pagos utilizando el modelo:
PaymentTransaction
Estructura conceptual:
Operacion Comercial
     │
     └── Venta
            │
            └── PaymentTransaction
                    ├ Pago 1
                    ├ Pago 2
                    └ Pago N
Cada transacción guarda:
metodo_pago
importe
cuenta_financiera
cobrador
fecha
observaciones
Esto permite soportar:
pagos combinados
conciliación bancaria
control de caja
devoluciones
auditoría

16.6 Flujo final del modo TEU ON
Flujo completo del sistema:
agregar productos
↓
seleccionar cliente
↓
seleccionar método de pago
↓
presionar VENDER
↓
invocar popup de pago del módulo Caja
↓
registrar PaymentTransaction
↓
imprimir comprobante
↓
finalizar venta

Estado del módulo
Con este punto queda completamente definido:
Módulo Ventas / POS
Incluyendo:
Pantalla POS
Modo TEU OFF
Modo TEU ON
Integración con módulo Caja
Motor unificado de pagos
Por lo tanto, el módulo Ventas / POS puede considerarse cerrado funcionalmente para la versión V1 del sistema.
