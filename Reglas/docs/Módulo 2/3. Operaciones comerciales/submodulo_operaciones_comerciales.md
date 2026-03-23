# Wireframe v1 --- Submódulo Operaciones Comerciales

## Módulo 2 --- Punto de Venta

------------------------------------------------------------------------

# 1. Objetivo del wireframe

El submódulo **Operaciones Comerciales** permite gestionar acciones
posteriores a una venta ya registrada.

Entre las operaciones disponibles se encuentran:

-   devoluciones
-   cambios de productos
-   notas de crédito
-   notas de débito
-   créditos en cuenta corriente
-   anulaciones

El objetivo de las pantallas de este módulo es permitir:

    buscar operaciones
    ↓
    visualizar detalle de ticket
    ↓
    seleccionar productos
    ↓
    ejecutar operación comercial

------------------------------------------------------------------------

# 2. Estructura general de pantallas

El wireframe del módulo se compone de las siguientes pantallas:

    Operaciones Comerciales
    │
    ├─ Pantalla principal (búsqueda de operaciones)
    ├─ Detalle de ticket
    ├─ Devolución
    ├─ Cambio de producto
    ├─ Nota de crédito
    ├─ Nota de débito
    └─ Crédito en cuenta corriente

------------------------------------------------------------------------

# 3. Wireframe --- Pantalla principal

Pantalla utilizada para localizar operaciones.

### Buscador

Campo principal:

    Buscar cliente, DNI, ticket o producto

La búsqueda puede realizarse por:

-   nombre del cliente
-   DNI
-   número de ticket
-   producto vendido
-   fecha de venta

### Tabla de resultados

  Ticket   Cliente   DNI   Fecha   Hora   Total   Estado
  -------- --------- ----- ------- ------ ------- --------

Acción:

    Seleccionar ticket → abrir detalle

------------------------------------------------------------------------

# 4. Wireframe --- Detalle de ticket

Al seleccionar una operación se visualiza el detalle completo.

### Información del ticket

Campos:

-   Ticket Nº
-   Cliente
-   Vendedor
-   Fecha
-   Método de pago
-   Total

### Lista de productos

  Seleccionar   Producto   Cantidad   Precio   Subtotal
  ------------- ---------- ---------- -------- ----------

Los productos pueden seleccionarse para aplicar operaciones parciales o
totales.

### Barra de acciones

Botones disponibles:

-   Devolución
-   Cambio
-   Nota de crédito
-   Nota de débito
-   Crédito en cuenta

------------------------------------------------------------------------

# 5. Wireframe --- Pantalla de devolución

Permite devolver productos al inventario.

### Flujo

    seleccionar producto
    ↓
    indicar cantidad
    ↓
    seleccionar tipo de reintegro

### Opciones de reintegro

-   efectivo
-   medio de pago original
-   crédito a cuenta corriente

### Impacto en sistema

-   Inventario (reingreso de producto)
-   Caja (devolución de dinero)
-   Tesorería
-   Finanzas

------------------------------------------------------------------------

# 6. Wireframe --- Pantalla de cambio

Permite reemplazar productos vendidos por otros.

### Flujo

    producto devuelto
    ↓
    selección de nuevo producto
    ↓
    cálculo de diferencia

### Resultados posibles

-   cliente paga diferencia
-   comercio devuelve dinero

### Impacto

-   Inventario
-   Caja
-   Tesorería

------------------------------------------------------------------------

# 7. Wireframe --- Nota de crédito

Permite generar crédito comercial asociado a una venta.

### Campos

-   Ticket asociado
-   Cliente
-   Importe
-   Motivo

### Acción

    Generar nota de crédito

### Impacto

-   Caja
-   Tesorería
-   Finanzas

------------------------------------------------------------------------

# 8. Wireframe --- Nota de débito

Permite registrar cargos adicionales sobre una operación.

### Ejemplos

-   intereses
-   recargos
-   ajustes comerciales

### Campos

-   Ticket asociado
-   Cliente
-   Importe
-   Motivo

### Acción

    Generar nota de débito

------------------------------------------------------------------------

# 9. Wireframe --- Crédito en cuenta corriente

Permite registrar saldo a favor del cliente en su cuenta corriente.

### Campos

-   Cliente
-   Saldo actual
-   Importe del crédito
-   Motivo

### Resultado

    saldo agregado a cuenta corriente del cliente

------------------------------------------------------------------------

# 10. Flujo general del módulo

    buscar operación
    ↓
    abrir ticket
    ↓
    seleccionar productos
    ↓
    elegir operación comercial
    ↓
    confirmar operación
    ↓
    impacto en inventario / caja / finanzas

------------------------------------------------------------------------

# Estado del submódulo

Con este documento queda definida la **estructura completa de wireframes
del submódulo Operaciones Comerciales** dentro del **Módulo 2 --- Punto
de Venta**.
