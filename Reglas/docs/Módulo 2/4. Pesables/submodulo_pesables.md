# Submódulo — Pesables
## Módulo 2 — Punto de Venta
## Versión Técnica Extendida (Modo Manual + Etiquetado Estandarizado)

---

## 1. Objetivo del submódulo

El submódulo **Pesables** tiene como objetivo gestionar productos cuyo precio depende de su peso o de un valor definido al momento de la preparación.

Permite:

- calcular precio en base a peso o ingreso manual de precio  
- generar etiquetas con código de barras estándar (EAN-13)  
- integrar el producto directamente con el flujo de ventas  

Ejemplos de productos:

fiambres
carnicería
verdulería
panadería
productos a granel

El resultado es un producto etiquetado listo para ser vendido en el POS.

---

## 2. Alcance del submódulo

El submódulo se encarga de:

- seleccionar productos pesables
- calcular precio o peso (bidireccional)
- generar código de barras EAN-13
- generar etiquetas imprimibles
- gestionar múltiples productos en lote
- registrar productos preparados

---

## 3. Flujo operativo general (modo manual)

seleccionar producto  
↓  
ingresar peso o precio  
↓  
cálculo automático  
↓  
agregar a lista de pesables  
↓  
(repetir N veces)  
↓  
generar etiquetas (batch)  
↓  
imprimir etiquetas  
↓  
cliente pasa por caja  
↓  
escaneo en POS  

---

## 4. Lógica de cálculo (bidireccional)

### Entrada por peso

precio_total = peso * precio_unitario

### Entrada por precio

peso = precio / precio_unitario

---

## 5. Generación de código de barras (EAN-13)

Formato:

[20][PLU(5)][PRECIO(5)][CHECKSUM]

Ejemplo:

20 10001 03000 X

- 20 → prefijo pesables  
- 10001 → PLU producto  
- 03000 → precio en centavos  
- X → checksum  

---

## 6. Etiquetas

Cada etiqueta debe incluir:

- Nombre del producto  
- Peso  
- Precio  
- Código de barras EAN-13  

Ejemplo:

Producto: Pan  
Peso: 1.500 kg  
Precio: $3.000  

[código de barras]  
201000103000X  

---

## 7. Impresión en lote

El sistema debe permitir:

- acumular múltiples productos pesables  
- generar todos los códigos de barras  
- enviar una única orden de impresión  

Botón principal:

[ Generar etiquetas e imprimir ]

---

## 8. Ticket de venta (POS)

Cada ítem pesable debe reflejar:

Pan 1.500kg x $2000/kg → $3000

Regla:

- mostrar peso + precio en ticket  
- no recalcular precio  

---

## 9. Modelo de datos

### Producto

{
  "id": "string",
  "nombre": "string",
  "precio_unitario": "number",
  "pesable": true,
  "plu": "number"
}

### PesableItem

{
  "id": "string",
  "producto_id": "string",
  "nombre_producto": "string",
  "plu": "number",
  "peso": "number",
  "precio_unitario": "number",
  "precio_total": "number",
  "barcode": "string",
  "estado": "pending|printed|used"
}

---

## 10. Estados

- pending → cargado  
- printed → etiqueta generada  
- used → vendido  

---

## 11. Integración con otros módulos

Inventario

- obtiene productos pesables  

Ventas

- escaneo de productos  
- carrito  
- ticket  

Configuración

- formato de etiquetas  
- impresoras  

---

## 12. Riesgos técnicos

1. Reutilización de etiquetas  
→ controlar estado "used"

2. Cambios de precio  
→ el precio viaja en el código

3. Redondeo  
→ centralizar en servicio único

---

## 13. Decisiones clave

- usar EAN-13 estándar  
- codificar por precio (no peso)  
- impresión en lote  
- POS no recalcula  

---

## 14. Estado del submódulo

Estado actual:

pendiente de implementación técnica  

---

## 15. Siguientes pasos

- implementar calculadora bidireccional  
- crear servicio de barcode  
- implementar lista de pesables  
- diseñar layout de etiquetas  
- integrar impresión batch  
- adaptar POS para mostrar peso en ticket  
