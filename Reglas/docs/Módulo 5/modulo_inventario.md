Módulo 5 — Inventario (v6)
1. Objetivo
El módulo Inventario gestiona todo el ciclo de vida de la mercadería dentro del negocio.
Permite:
administrar el catálogo de productos
controlar existencias por ubicación
registrar movimientos de inventario
gestionar costos y precios
controlar vencimientos
analizar rotación
automatizar reposiciones
gestionar abastecimiento
mantener históricos completos
conocer exactamente cómo está distribuida la mercadería en el negocio
Este módulo se integra con:
Facturación → descuenta stock al vender
Dashboard → alertas operativas
Reportes → análisis comercial
Personas → gestión de proveedores

2. Estructura del módulo
Inventario
│
├─ Categorías
├─ Productos
├─ Unidades logísticas
├─ Sucursales / Depósitos / Bodegas / Góndolas
├─ Stock
├─ Precios
├─ Cargas de productos
├─ Movimientos
├─ Control de Stock
└─ Históricos

3. Submódulo — Categorías
Objetivo
Organizar el catálogo de productos mediante una estructura jerárquica.
Esto permite:
navegación del catálogo
segmentación comercial
análisis de ventas
organización del inventario

Estructura
El sistema soporta categorías y subcategorías.
Ejemplo:
Bebidas
  ├ Gaseosas
  ├ Jugos
  └ Aguas

Lácteos
  ├ Leches
  ├ Yogures
  └ Quesos

Datos registrados
nombre
categoría padre
descripción
estado

4. Submódulo — Productos
Objetivo
Gestionar el registro maestro de productos.
Define la identidad del producto sin incluir cantidades de inventario.

Datos principales
nombre
código de barras
categoría
marca
unidad de medida
tipo de producto

Variantes
Un producto puede tener múltiples variantes comerciales.
Ejemplo:
Coca Cola
  ├ 2L
  ├ 1.5L
  └ lata
Cada variante puede tener:
código de barras propio
costo propio
precio propio

Proveedores asociados
Cada producto puede registrar:
proveedor principal
proveedor alternativo

5. Submódulo — Unidades Logísticas
Objetivo
Permitir manejar distintas unidades de compra y venta.
Esto permite comprar en formatos distintos a los que se venden.

Ejemplo
Producto: Coca Cola lata

unidad compra → caja (24)
unidad venta → unidad

Tipos de unidades
unidad
pack
caja
bulto

Datos registrados
producto
unidad logística
cantidad contenida
relación con unidad base

6. Submódulo — Sucursales / Depósitos / Bodegas / Góndolas
Objetivo
Permitir modelar la estructura física del negocio para saber exactamente dónde se encuentra cada producto.

6.1 Estructura jerárquica
La relación entre las entidades es la siguiente:
Sucursal
  ├ Depósitos
  │    └ stock interno
  │
  └ Góndola
       └ stock disponible para venta
Además existe una entidad independiente:
Bodega

Reglas de relación
Sucursal
Una Sucursal representa una tienda o punto de venta.
Una sucursal puede tener:
múltiples depósitos
una góndola

Depósito
Un Depósito representa almacenamiento interno dentro de la sucursal.
Características:
pertenece a una sucursal
almacena stock de reposición
abastece a la góndola

Bodega
Una Bodega representa almacenamiento externo.
Características:
no pertenece a ninguna sucursal
funciona como depósito externo
puede abastecer múltiples sucursales

Góndola
La Góndola representa el stock disponible para venta dentro de la sucursal.
Conceptualmente se maneja como una entidad única por sucursal, aunque físicamente existan múltiples góndolas.
Esto permite simplificar el control del inventario disponible para venta.

Modelo conceptual final
Bodega (externa)

Sucursal
  ├ Depósitos
  │
  └ Góndola

Datos registrados
Para cada ubicación:
nombre
tipo de ubicación
sucursal asociada
estado

7. Submódulo — Stock
Objetivo
Gestionar las cantidades de productos disponibles en cada ubicación.

Niveles de stock
Cada producto puede definir:
stock actual
stock mínimo en góndola
stock máximo en góndola
stock mínimo en depósito
stock máximo en depósito

Transferencias automáticas
Cuando el stock en góndola llega al mínimo:
orden automática
depósito → góndola

Solicitudes automáticas de compra
Cuando el stock del depósito llega al mínimo:
generar solicitud de compra

8. Submódulo — Precios
Objetivo
Gestionar los precios de venta y reglas comerciales.

Fuentes de precio
costo + margen
precio sugerido proveedor
promociones
precio manual
listas de precios

Precio por margen
precio = costo + margen

Promociones
Se pueden crear promociones aplicadas a:
categorías
productos
listas de productos

Precio general
El precio principal del sistema.
Puede modificarse mediante:
reposiciones
edición manual
importación masiva

Listas de precios
El sistema permite múltiples listas.
Ejemplo:
precio general
precio promoción
precio mayorista
precio especial

9. Submódulo — Cargas de productos
Objetivo
Gestionar la ingesta inicial o masiva de productos.

Métodos de carga
carga manual
importación Excel
importación CSV

Datos cargados
producto
variante
código de barras
costo
precio
categoría
proveedor

Actualización mediante reposición
La reposición también puede actualizar:
costos
precios
stock

10. Submódulo — Movimientos
Objetivo
Registrar todos los cambios de inventario.

Tipos de movimientos
ingreso por compra
venta
devolución
transferencia
ajuste
merma
movimiento manual
reversión

Movimientos manuales
Permiten registrar operaciones fuera de los flujos automáticos.
Ejemplo:
reposición manual
transferencia entre depósitos
movimiento entre sucursales

Reversión de acciones
Cuando una operación fue incorrecta se puede revertir.
La reversión:
genera movimiento inverso
mantiene trazabilidad
queda registrada

11. Submódulo — Control de Stock
Objetivo
Supervisar el estado del inventario y detectar anomalías.

Control de vencimientos
Registro de lotes:
producto
lote
fecha de vencimiento
cantidad

Rotación de productos
Identifica:
productos de alta rotación
productos de baja rotación
productos sin movimiento

Conteo de inventario
Permite:
conteo manual
conteo con lector de código de barras

Tabla de distribución del inventario
Permite visualizar:
producto
ubicación
cantidad
Esto permite conocer exactamente cómo está distribuida la mercadería.

Conteo manual con checklist
El sistema puede generar:
PDF por góndola
listado de productos
campos de verificación

Conteo rotativo
Ejemplo:
lunes → bebidas
martes → lácteos
miércoles → almacén

Ranking de merma sin justificar
Permite detectar:
errores operativos
robos internos
problemas de control

12. Submódulo — Históricos
Objetivo
Registrar todos los cambios relevantes de los productos.

Históricos registrados
costos
precios
stock
modificaciones de producto
movimientos

Datos registrados
producto
tipo de cambio
valor anterior
valor nuevo
usuario
fecha
origen

Evaluación final del módulo Inventario
Con esta versión el módulo Inventario cubre completamente:
catálogo
variantes
unidades logísticas
ubicaciones físicas
stock
precios
movimientos
control
históricos
Esto corresponde a un sistema de inventario de nivel profesional para retail multisucursal.
El modelo ahora permite saber:
qué producto hay
cuánto hay
dónde está
cómo llegó ahí
quién lo modificó
