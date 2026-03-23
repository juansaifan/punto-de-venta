# Submódulo --- Ventas

## Módulo 2 --- Punto de Venta

Versión 1 --- Documentación funcional

------------------------------------------------------------------------

# 1. Objetivo del submódulo

El submódulo **Ventas** es la interfaz principal del sistema POS
utilizada por los vendedores para registrar operaciones de venta.

Permite:

-   escanear productos
-   construir el carrito de venta
-   calcular totales automáticamente
-   generar tickets de venta
-   enviar ventas a Caja para cobro
-   finalizar ventas directamente cuando el modo TEU está activado

Este submódulo está optimizado para **velocidad de operación y uso con
lector de código de barras**.

------------------------------------------------------------------------

# 2. Modos de operación

El submódulo Ventas posee dos modos operativos:

    Modo TEU OFF (Vendedor + Caja)
    Modo TEU ON (Todo en Uno)

Estos modos permiten adaptar el sistema a distintos tamaños de comercio.

------------------------------------------------------------------------

# 3. Modo TEU OFF --- Vendedor + Caja

Este modo se utiliza cuando el proceso de venta está dividido entre:

-   vendedor
-   cajero

Flujo:

    vendedor registra venta
    ↓
    sistema genera ticket
    ↓
    cliente pasa a caja
    ↓
    cajero cobra venta

El módulo Ventas en este modo **no registra pagos**.

------------------------------------------------------------------------

# 4. Modo TEU ON --- Todo en Uno

Este modo permite que una sola persona realice todo el proceso de venta.

Flujo:

    registrar venta
    ↓
    seleccionar método de pago
    ↓
    confirmar pago
    ↓
    imprimir ticket

En este modo se reutiliza **la lógica de pagos del submódulo Caja**.

------------------------------------------------------------------------

# 5. Estructura de la pantalla principal

La pantalla POS se divide en tres áreas principales.

    Ventas / POS
    │
    ├─ Buscador de productos
    ├─ Área de productos / categorías
    └─ Carrito de venta

------------------------------------------------------------------------

# 6. Buscador de productos

Ubicado en la parte superior central.

Campo:

    Buscar producto por nombre o código de barras

Características:

-   búsqueda dinámica
-   compatible con lector de código de barras

Si el producto no existe se puede crear uno nuevo.

------------------------------------------------------------------------

# 7. Área de categorías y productos

Debajo del buscador se muestran **categorías de productos**.

Al seleccionar una categoría:

    categoría
    ↓
    subcategoría
    ↓
    producto

Al seleccionar un producto:

    producto agregado al carrito

------------------------------------------------------------------------

# 8. Carrito de venta

Ubicado en el panel derecho de la pantalla.

Contiene:

| Producto \| Cantidad \| Precio \| Subtotal \|

Funciones:

-   modificar cantidad
-   eliminar producto
-   aplicar descuento

------------------------------------------------------------------------

# 9. Información del cliente

El panel del carrito incluye un selector de cliente.

Campo:

    Cliente
    [ Consumidor Final ]

Permite:

-   buscar cliente por nombre o DNI
-   crear cliente nuevo

------------------------------------------------------------------------

# 10. Lista de precios

El sistema permite seleccionar la lista de precios aplicada.

Ejemplo:

    Precio general
    Precio promocional
    Lista mayorista

El sistema marca automáticamente la lista activa.

------------------------------------------------------------------------

# 11. Totales de venta

El sistema calcula automáticamente:

-   subtotal
-   descuentos
-   impuestos
-   total final

------------------------------------------------------------------------

# 12. Ventas en suspenso

El sistema permite mantener múltiples ventas abiertas.

Barra inferior:

    Venta principal | Pendiente 1 | Pendiente 2 | +

Esto permite atender múltiples clientes simultáneamente.

------------------------------------------------------------------------

# 13. Estados de la venta

Una venta puede tener los siguientes estados:

-   pendiente
-   pagada
-   suspendida
-   fiada
-   cancelada

------------------------------------------------------------------------

# 14. Generación de ticket

En modo **TEU OFF**:

    venta registrada
    ↓
    ticket generado
    ↓
    cliente pasa a caja

El ticket incluye:

-   número de operación
-   código de barras
-   detalle de productos
-   total

------------------------------------------------------------------------

# 15. Métodos de pago (Modo TEU ON)

Cuando el modo TEU está activo aparece un selector adicional:

    Método de pago

Opciones:

-   efectivo
-   tarjeta crédito
-   tarjeta débito
-   transferencia
-   pago combinado
-   cuenta corriente

Al confirmar el pago se ejecuta el flujo de pagos del módulo Caja.

------------------------------------------------------------------------

# 16. Integración con otros módulos

El submódulo Ventas interactúa con:

Inventario

    descuento de stock al finalizar la venta

Personas

    asociación de cliente a la venta

Caja

    envío de tickets para cobro

Finanzas

    registro de ingresos

------------------------------------------------------------------------

# 17. Flujo general del módulo

    buscar producto
    ↓
    agregar al carrito
    ↓
    seleccionar cliente
    ↓
    verificar total
    ↓
    generar ticket o cobrar (según modo TEU)

------------------------------------------------------------------------

# Estado del submódulo

Con esta documentación queda definido el submódulo **Ventas** dentro del
**Módulo 2 --- Punto de Venta**.
