Wireframe v1 — Pantalla Ventas / POS
Modo TEU OFF (Vendedor + Caja)
Este modo corresponde al flujo donde:
Vendedor registra la venta
↓
se genera ticket
↓
Caja cobra
Es decir, no se cobra en esta pantalla.

1. Header del sistema
Barra superior común a todo el sistema POS.
Elementos:
☰ Menú principal
Ventas / POS
Estado del sistema
Sucursal activa
Usuario activo
Accesos rápidos
Ubicación visual:
☰  Ventas / POS                               Disponible   ⟳   ⧉   ?   Usuario

2. Barra de búsqueda de productos
Ubicada inmediatamente debajo del header.
Componentes:
[ 🔍 ]  Buscar producto o código de barras...
[ Nuevo producto ]
Funcionalidades:
lector de código de barras
búsqueda por nombre
búsqueda por código
autocompletado dinámico
Resultado de búsqueda:
imagen producto
nombre
precio

3. Selector de modo TEU
Ubicado en el panel derecho, al lado del título Ventas / POS.
Formato:
Ventas / POS      TEU  [ OFF ]
Tipo de control:
toggle deslizante
Estados:
TEU OFF
TEU  [ OFF ]
Significa:
modo vendedor + caja
TEU ON
TEU  [ ON ]
Significa:
modo autoservicio
venta + cobro en una sola pantalla
En este documento solo se define TEU OFF.

4. Panel de categorías
Zona principal izquierda de la pantalla.
Grid de categorías grandes.
Ejemplo visual:
Bebidas        Lácteos       Fiambres       Panadería
Snacks         Limpieza      Despensa       Carnicería
Características:
botones grandes
iconos representativos
navegación jerárquica
Flujo:
Categoría
↓
Subcategoría
↓
Productos

5. Panel de configuración de venta (lado derecho)
Columna derecha fija.

5.1 Lista de precios
Campo desplegable.
Lista de precios
[ General ▼ ]
Permite seleccionar:
General
Mayorista
Promoción
Lista especial

5.2 Tipo de comprobante
Campo desplegable.
Tipo comprobante
[ Ticket ▼ ]
Opciones posibles:
Ticket
Factura A
Factura B
Factura C
Nota de crédito

6. Cliente
Debajo del tipo de comprobante.
Estructura:
Cliente
[ Consumidor final ▼ ]
Valor por defecto:
Consumidor final
Al desplegar permite:
buscar cliente por nombre
buscar cliente por DNI
Si el cliente no existe aparece la opción:
+ Nuevo cliente
Flujo:
Nuevo cliente
↓
abre módulo Personas
↓
crear cliente

7. Lista de productos agregados
Debajo de cliente.
Cada producto agregado muestra:
Nombre producto
Código interno
Precio unitario
Cantidad
Ejemplo:
Fideos Spaghetti Verizzia 500 g      $3.630
ALM-02-0001

[-] 1 [+]
Funciones:
aumentar cantidad
disminuir cantidad

8. Resumen de venta
Panel inferior del carrito.
Estructura:
Subtotal     $3.000
IVA (21%)      $630

TOTAL        $3.630
Esto permite visualizar:
base imponible
impuestos
total final

9. Acciones de venta
Ubicadas debajo del panel de categorías.
Botones:
Cancelar venta
Aplicar descuento
Funciones:
Cancelar venta
elimina todos los productos
Aplicar descuento
descuento porcentual
descuento monto fijo
cupón promocional

10. Botón principal
Ubicado en la parte inferior del panel derecho.
VENDER
Acción:
VENDER
↓
generar ticket
↓
enviar ticket a CAJA
No se procesa pago aquí.

11. Ventas en suspenso
Barra inferior horizontal.
Estructura:
Venta principal     Victoria     +
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

12. Flujo operativo completo (TEU OFF)
seleccionar categoría
↓
agregar productos
↓
seleccionar cliente
↓
aplicar descuentos (opcional)
↓
VENDER
↓
generar ticket
↓
ticket enviado a caja
↓
cajero cobra

13. Diferencia con modo TEU ON
Modo TEU OFF:
venta
↓
ticket
↓
caja cobra
Modo TEU ON:
venta
↓
selección método pago
↓
pago inmediato
↓
impresión ticket
La diferencia visual principal es:
aparece selector de método de pago
junto al campo Cliente.

Estado del Wireframe POS
Con este documento queda definido completamente:
Pantalla principal POS
Modo TEU OFF
