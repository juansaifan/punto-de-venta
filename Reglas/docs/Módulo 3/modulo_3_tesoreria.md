# Módulo 3 --- Tesorería

## Documentación funcional

Versión 1

------------------------------------------------------------------------

# 1. Objetivo del módulo

El módulo **Tesorería** administra todos los movimientos financieros del
negocio que **no forman parte directa del proceso de venta**.

Mientras que el módulo **Punto de Venta** gestiona las operaciones
comerciales con clientes, el módulo Tesorería gestiona los **movimientos
financieros propios del comercio como entidad económica**.

Esto incluye:

-   ingresos de dinero al negocio
-   egresos de dinero
-   transferencias internas
-   control de efectivo
-   movimientos entre cuentas
-   administración de fondos

------------------------------------------------------------------------

# 2. Rol dentro del sistema

Tesorería representa la **gestión del dinero del negocio fuera de la
operación comercial directa**.

Ejemplos de operaciones gestionadas en este módulo:

-   retiro de dinero de caja
-   pago a proveedores
-   pago de servicios
-   compra de mercadería
-   depósitos bancarios
-   transferencias entre cuentas
-   aporte de capital
-   retiro de utilidades

------------------------------------------------------------------------

# 3. Relación con otros módulos

Tesorería interactúa con diversos módulos del sistema.

## Punto de Venta

Recibe información de:

-   movimientos de caja
-   cierres de caja
-   extracciones de dinero

## Finanzas

Envía información a:

-   balances financieros
-   análisis de flujo de fondos
-   reportes financieros

## Inventario

Puede registrar egresos relacionados con:

-   compras de mercadería
-   abastecimiento

------------------------------------------------------------------------

# 4. Estructura del módulo

    Tesorería
    │
    ├─ Movimientos
    ├─ Ingresos
    ├─ Egresos
    ├─ Transferencias
    ├─ Cuentas financieras
    └─ Historial de movimientos

------------------------------------------------------------------------

# 5. Submódulo --- Movimientos

Permite visualizar todos los movimientos financieros registrados.

Tabla principal:

| Fecha \| Tipo \| Cuenta origen \| Cuenta destino \| Importe \| Usuario
  \|

Filtros disponibles:

-   fecha
-   tipo de movimiento
-   cuenta financiera
-   usuario

------------------------------------------------------------------------

# 6. Submódulo --- Ingresos

Permite registrar dinero que ingresa al negocio.

Ejemplos:

-   aporte de socios
-   ingreso de efectivo para cambio
-   transferencia bancaria recibida
-   devolución de proveedor

Campos:

-   fecha
-   cuenta destino
-   importe
-   motivo
-   usuario
-   observaciones

------------------------------------------------------------------------

# 7. Submódulo --- Egresos

Permite registrar salidas de dinero.

Ejemplos:

-   pago a proveedor
-   compra de mercadería
-   pago de servicios
-   retiro de dinero por el dueño
-   gastos operativos

Campos:

-   fecha
-   cuenta origen
-   importe
-   motivo
-   proveedor (opcional)
-   usuario

------------------------------------------------------------------------

# 8. Submódulo --- Transferencias

Permite mover dinero entre cuentas del negocio.

Ejemplo:

    Caja principal → Cuenta bancaria

Campos:

-   cuenta origen
-   cuenta destino
-   importe
-   fecha
-   usuario

------------------------------------------------------------------------

# 9. Submódulo --- Cuentas financieras

Permite administrar las cuentas donde se encuentra el dinero del
negocio.

Tipos de cuentas posibles:

-   caja física
-   cuenta bancaria
-   billetera virtual
-   fondo operativo
-   fondo de cambio

Cada cuenta registra:

-   nombre
-   tipo
-   saldo actual
-   estado
-   observaciones

------------------------------------------------------------------------

# 10. Historial de movimientos

Tesorería mantiene un historial completo de movimientos financieros.

Cada movimiento registra:

-   tipo de operación
-   cuenta origen
-   cuenta destino
-   importe
-   usuario
-   fecha y hora
-   observaciones

Esto permite auditoría completa.

------------------------------------------------------------------------

# 11. Integración con Finanzas

Todos los movimientos registrados en Tesorería son utilizados por el
módulo **Finanzas** para:

-   cálculo de balances
-   análisis de flujo de fondos
-   reportes financieros
-   control de liquidez

------------------------------------------------------------------------

# 12. Permisos de acceso

El acceso al módulo Tesorería depende del rol del usuario.

Ejemplo:

  Rol             Acceso
  --------------- ------------------------
  Administrador   Completo
  Supervisor      Movimientos e ingresos
  Cajero          Solo consulta
  Vendedor        Sin acceso

------------------------------------------------------------------------

# 13. Flujo general del módulo

    registrar ingreso o egreso
    ↓
    asignar cuenta financiera
    ↓
    registrar movimiento
    ↓
    actualizar saldo
    ↓
    enviar información a Finanzas

------------------------------------------------------------------------

# Estado del módulo

Con esta documentación queda definido el **Módulo Tesorería** dentro de
la arquitectura del sistema.
