# Submódulo --- Operaciones Comerciales

## Módulo 2 --- Punto de Venta

**Versión 1 --- Documentación funcional completa**

------------------------------------------------------------------------

## 1. Objetivo del submódulo

El submódulo **Operaciones Comerciales** gestiona todas las acciones
comerciales posteriores a una venta que permiten corregir, ajustar o
modificar una transacción existente.

Estas operaciones pueden afectar:

-   ventas
-   clientes
-   inventario
-   caja
-   tesorería
-   finanzas

A diferencia del módulo **Ventas**, que registra nuevas operaciones,
este submódulo administra **operaciones derivadas de ventas ya
registradas**.

------------------------------------------------------------------------

## 2. Función dentro del sistema

Operaciones Comerciales funciona como el **centro de control de
transacciones comerciales**, permitiendo revisar, modificar o ajustar
operaciones realizadas.

Permite ejecutar:

-   cambios de productos
-   devoluciones
-   notas de crédito
-   notas de débito
-   anulaciones
-   ajustes comerciales

Estas acciones pueden generar impactos en:

-   Inventario
-   Caja
-   Tesorería
-   Finanzas

------------------------------------------------------------------------

## 3. Estructura del submódulo

    Operaciones Comerciales
    │
    ├─ Pantalla principal (búsqueda)
    ├─ Detalle de operación
    ├─ Devolución
    ├─ Cambio de producto
    ├─ Nota de crédito
    ├─ Nota de débito
    └─ Confirmación de operación

------------------------------------------------------------------------

## 4. Pantalla principal --- Búsqueda de operaciones

La pantalla principal permite localizar operaciones registradas.

### Buscador principal

Campo de búsqueda:

    Buscar cliente, DNI, número de ticket o producto

La búsqueda puede realizarse por:

-   nombre del cliente
-   DNI
-   número de ticket
-   producto vendido
-   fecha de venta
-   vendedor

### Resultados

Tabla de operaciones:

  Ticket   Cliente          DNI        Fecha   Hora    Total     Estado
  -------- ---------------- ---------- ------- ------- --------- --------
  000124   Victoria Perez   32911452   12/03   18:03   \$3.630   Pagado
  000125   Juan Gomez       30111452   12/03   18:10   \$8.400   Pagado

Acción:

    click en ticket → abrir detalle

------------------------------------------------------------------------

## 5. Detalle de operación

Al seleccionar una operación se muestra el detalle completo.

### Información del ticket

-   Ticket Nº
-   Fecha
-   Cliente
-   Vendedor
-   Método de pago
-   Total

### Lista de productos

  Seleccionar   Producto               Cantidad   Precio    Subtotal
  ------------- ---------------------- ---------- --------- ----------
  ☐             Fideos Verizzia 500g   1          \$3.630   \$3.630
  ☐             Salsa tomate           2          \$1.200   \$2.400

Los productos pueden seleccionarse para operaciones **parciales o
totales**.

------------------------------------------------------------------------

## 6. Barra de operaciones

Opciones disponibles:

-   Devolución
-   Cambio
-   Nota de crédito
-   Nota de débito
-   Anular operación

Cada acción abre su subpantalla correspondiente.

------------------------------------------------------------------------

## 7. Subpantalla --- Devolución

Permite devolver productos al inventario.

### Flujo

    buscar operación
    ↓
    seleccionar producto
    ↓
    indicar cantidad
    ↓
    confirmar devolución

### Opciones de reintegro

-   efectivo
-   medio de pago original
-   crédito a cliente

### Impacto

-   Inventario (reingreso de producto)
-   Caja (devolución de dinero)
-   Tesorería (movimiento financiero)
-   Finanzas (registro contable)

------------------------------------------------------------------------

## 8. Subpantalla --- Cambio de producto

Permite reemplazar productos vendidos.

### Flujo

    seleccionar producto devuelto
    ↓
    seleccionar producto nuevo
    ↓
    calcular diferencia

### Resultado posible

-   cliente paga diferencia
-   comercio devuelve dinero

### Impacto

-   Inventario (entrada y salida de stock)
-   Caja (ajuste de dinero)
-   Tesorería (movimiento financiero)

------------------------------------------------------------------------

## 9. Subpantalla --- Nota de crédito

Permite generar crédito comercial sobre una venta.

### Casos de uso

-   error en facturación
-   devolución sin producto
-   ajuste comercial

### Flujo

    seleccionar operación
    ↓
    indicar importe
    ↓
    generar nota de crédito

### Impacto

-   Caja
-   Tesorería
-   Finanzas

------------------------------------------------------------------------

## 10. Subpantalla --- Nota de débito

Permite aplicar cargos adicionales.

### Ejemplos

-   intereses
-   recargos
-   ajustes comerciales

### Flujo

    seleccionar operación
    ↓
    indicar importe
    ↓
    confirmar nota de débito

### Impacto

-   Tesorería
-   Finanzas

------------------------------------------------------------------------

## 11. Subpantalla --- Anulación

Permite anular completamente una operación.

### Condiciones

-   permisos del usuario
-   estado del ticket
-   tiempo desde la venta

### Flujo

    buscar operación
    ↓
    seleccionar venta
    ↓
    confirmar anulación

### Impacto

-   Inventario
-   Caja
-   Tesorería
-   Finanzas

------------------------------------------------------------------------

## 12. Confirmación de operación

Antes de ejecutar una acción el sistema solicita confirmación.

Información mostrada:

-   tipo de operación
-   productos afectados
-   importe
-   usuario
-   motivo

Botones:

    Cancelar
    Confirmar operación

------------------------------------------------------------------------

## 13. Registro de auditoría

Cada operación queda registrada con:

-   usuario
-   fecha
-   hora
-   tipo de operación
-   motivo
-   referencia a operación original

Esto permite trazabilidad completa.

------------------------------------------------------------------------

## 14. Integración con otros módulos

Operaciones Comerciales interactúa con:

-   Inventario
-   Caja
-   Tesorería
-   Finanzas
-   Personas

------------------------------------------------------------------------

## 15. Flujo general del módulo

    buscar cliente o ticket
    ↓
    seleccionar operación
    ↓
    ver detalle
    ↓
    seleccionar productos
    ↓
    elegir operación comercial
    ↓
    confirmar
    ↓
    registrar impacto en sistema

------------------------------------------------------------------------

## Estado del submódulo

Con esta documentación queda definido el submódulo:

**Operaciones Comerciales**

Dentro del **Módulo 2 --- Punto de Venta**.
