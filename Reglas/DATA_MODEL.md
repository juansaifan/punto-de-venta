# DATA_MODEL --- Sistema Punto de Venta

## 1. Propósito

Este documento define el **modelo de datos conceptual del sistema Punto
de Venta**.

Su objetivo es:

-   describir entidades principales
-   definir relaciones entre dominios
-   establecer reglas de consistencia
-   guiar el diseño de la base de datos
-   servir como referencia para agentes de desarrollo

El modelo de datos **no debe modificarse arbitrariamente**. Cualquier
cambio estructural debe actualizar este documento.

------------------------------------------------------------------------

# 2. Dominios del Modelo de Datos

El modelo de datos se organiza en los siguientes dominios:

Ventas\
Inventario\
Tesorería\
Finanzas\
Personas

Cada dominio es responsable de **sus propias entidades**.

------------------------------------------------------------------------

# 3. Dominio Ventas

## Entidad: Venta

Campos principales:

venta_id (PK)\
fecha\
cliente_id (FK)\
empleado_id (FK)\
total_bruto\
descuento_total\
total_final\
estado

Relaciones:

Venta 1 → N DetalleVenta\
Venta 1 → N Pago

------------------------------------------------------------------------

## Entidad: DetalleVenta

detalle_id (PK)\
venta_id (FK)\
producto_id (FK)\
cantidad\
precio_unitario\
subtotal

------------------------------------------------------------------------

## Entidad: Pago

pago_id (PK)\
venta_id (FK)\
metodo_pago\
monto\
fecha

------------------------------------------------------------------------

# 4. Dominio Inventario

## Entidad: Producto

producto_id (PK)\
sku\
codigo_barra (EAN/GTIN u otros; para Pesables puede ser EAN-13 generado)\
nombre\
descripcion\
precio_venta\
costo_actual (si aplica)\
tipo_medicion (unidad|peso)\
stock_actual\
stock_minimo\
activo

Notas:

- Para Pesables (docs `Módulo 2/4. Pesables/submodulo_pesables.md`), un producto puede ser **pesable** y tener un **PLU** (5 dígitos) para generar el EAN-13 por precio.

------------------------------------------------------------------------

## Entidad: MovimientoInventario

movimiento_id (PK)\
producto_id (FK)\
tipo_movimiento\
cantidad\
fecha\
referencia

Tipos:

entrada\
salida\
ajuste

------------------------------------------------------------------------

## Entidad: PesableItem

Representa un ítem pesable **preparado/etiquetado** listo para ser vendido mediante escaneo en POS.

Campos principales (según docs Pesables):

pesable_item_id (PK)\
producto_id (FK)\
nombre_producto (snapshot)\
plu\
peso\
precio_unitario\
precio_total\
barcode (EAN-13)\
estado (pending|printed|used)\
creado_en

Relaciones:

Producto 1 → N PesableItem

Reglas:

- El EAN-13 se genera por **precio** (no por peso) con formato `[20][PLU(5)][PRECIO(5)][CHECKSUM]`.
- En POS, al escanear el EAN-13 de pesables **no se recalcula** el precio; se muestra peso + precio y se respeta el total codificado.

------------------------------------------------------------------------

# 5. Dominio Tesorería

## Entidad: Caja

caja_id (PK)\
fecha_apertura\
fecha_cierre\
saldo_inicial\
saldo_final\
estado

------------------------------------------------------------------------

## Entidad: MovimientoCaja

movimiento_id (PK)\
caja_id (FK)\
tipo\
monto\
descripcion\
fecha

Tipos:

ingreso\
egreso

------------------------------------------------------------------------

# 6. Dominio Finanzas

## Entidad: CuentaFinanciera

cuenta_id (PK)\
nombre\
tipo\
saldo

------------------------------------------------------------------------

## Entidad: TransaccionFinanciera

transaccion_id (PK)\
cuenta_id (FK)\
tipo\
monto\
fecha\
descripcion

Tipos:

ingreso\
gasto

------------------------------------------------------------------------

# 7. Dominio Personas

## Entidad: Cliente

cliente_id (PK)\
nombre\
telefono\
email\
fecha_registro

------------------------------------------------------------------------

## Entidad: Empleado

empleado_id (PK)\
nombre\
rol\
activo

------------------------------------------------------------------------

## Entidad: Proveedor

proveedor_id (PK)\
nombre\
telefono\
email

------------------------------------------------------------------------

# 8. Reglas de Consistencia

Reglas fundamentales del sistema:

1.  Toda venta debe tener al menos un DetalleVenta.
2.  Todo DetalleVenta debe referenciar un Producto.
3.  Una venta debe registrar al menos un Pago.
4.  Cada venta genera un movimiento de inventario.
5.  Cada venta genera un movimiento de caja.
6.  Los pagos deben coincidir con el total de la venta.

------------------------------------------------------------------------

# 9. Evolución del Modelo

Si el sistema requiere nuevas entidades:

1.  deben agregarse a este documento
2.  deben respetar el dominio correspondiente
3.  deben documentar sus relaciones

------------------------------------------------------------------------

Última actualización: 2026
