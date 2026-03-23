# 06 — Integraciones

## Visión General

El módulo de Integraciones (`backend/services/integraciones.py`) gestiona todas las conexiones del POS con sistemas externos. No implementa comunicación real con servicios externos; provee la infraestructura para configurarlos, activarlos y registrar su actividad.

**Router:** `backend/api/routers/integraciones.py`  
**Modelos:** `IntegracionConfig`, `IntegracionLog` (`backend/models/integracion.py`)

---

## Catálogo de Tipos de Integración

```python
TIPOS_INTEGRACION = [
    "facturacion_electronica",  # AFIP/ARCA
    "pasarelas_pago",           # MercadoPago, Getnet, etc.
    "hardware_pos",             # Impresoras, lectores, balanzas
    "mensajeria",               # WhatsApp, email, SMS
    "tienda_ecommerce",         # Sincronización con tiendas online
    "integracion_contable",     # Exportación a sistemas contables
    "api_externa",              # Exposición de API para terceros
    "backups_sincronizacion",   # Copias automáticas y sincronización
]
```

Cada tipo tiene: `codigo`, `nombre`, `descripcion`.

---

## Dispositivos de Hardware POS

```python
DISPOSITIVOS_POS = [
    "impresora",     # Tickets, facturas, comprobantes, etiquetas
    "lector_barras", # Captura de códigos en ventas e inventario
    "balanza",       # Pesaje automático, etiquetas, transferencia de peso
]
```

La disponibilidad de un dispositivo se determina por el estado de `IntegracionConfig.tipo_codigo == "hardware_pos"`:
- Si `hardware_pos` está activo → todos los dispositivos se consideran disponibles (salvo config explícita en `config_json`)

---

## Modelo de Datos de Integraciones

### `IntegracionConfig`
| Campo | Descripción |
|---|---|
| `tipo_codigo` | Identificador único del tipo (del catálogo) |
| `activo` | Si la integración está habilitada |
| `config_json` | JSON con credenciales o parámetros específicos del tipo |

### `IntegracionLog`
| Campo | Descripción |
|---|---|
| `tipo_codigo` | Tipo de integración |
| `exito` | Boolean — resultado de la operación |
| `mensaje` | Descripción (máx 512 chars) |
| `detalle` | Texto adicional (Text, nullable) |
| `created_at` | Timestamp UTC |

---

## Funcionalidades Implementadas

### Gestión de Estado

| Función | Descripción |
|---|---|
| `listar_tipos_integracion()` | Lista el catálogo con nombre y descripción |
| `obtener_estado_integraciones(sesion)` | Estado de cada tipo desde BD (activo/desactivado) |
| `configurar_activo(sesion, tipo, activo)` | Activa o desactiva un tipo |
| `obtener_config(sesion, tipo)` | Lee config JSON de un tipo |
| `guardar_config(sesion, tipo, config)` | Guarda config JSON |
| `probar_conexion(sesion, tipo)` | Prueba simulada (verifica si hay config_json) |
| `resumen_integraciones(sesion)` | Health global: activos, configurados, último log |

### Logs

| Función | Descripción |
|---|---|
| `registrar_log(sesion, tipo, exito, mensaje, detalle)` | Persiste un log |
| `listar_logs(sesion, tipo?, limite)` | Lista logs más recientes primero |
| `estadisticas_logs(sesion, tipo?)` | Tasa de éxito/fallo por tipo |

### Hardware POS

| Función | Descripción |
|---|---|
| `listar_dispositivos_pos()` | Catálogo de dispositivos |
| `obtener_estado_dispositivo(sesion, codigo)` | Disponibilidad de un dispositivo específico |

### Flujo Alternativo Sin Impresora

Cuando no hay impresora disponible durante el cobro:
1. Solicitar DNI del cliente
2. Buscar cliente existente (o crear nuevo)
3. Solicitar email
4. Enviar comprobante digital (log simulado)

Función: `ejecutar_flujo_alternativo_sin_impresora(sesion, venta_id, documento_cliente, email, ...)`

### Mensajería / Comprobante Digital

| Función | Descripción |
|---|---|
| `enviar_comprobante_digital(sesion, venta_id, email, tipo_comprobante)` | Simula envío de comprobante. Registra log de mensajería. Si mensajería no está activa, registra como `[SIM]`. |

### Integración Contable

| Función | Descripción |
|---|---|
| `exportacion_contable(sesion, fecha_desde, fecha_hasta)` | Exporta ventas y movimientos de caja para sistemas contables (Alegra, Contabilium, etc.) |

Formato de respuesta:
```json
{
  "periodo": { "desde": "...", "hasta": "..." },
  "ventas": [...],
  "resumen_ventas": { "cantidad": N, "total_facturado": N },
  "movimientos_caja": [...],
  "resumen_caja": { "total_ingresos": N, "total_egresos": N, "resultado_neto": N },
  "exportado_en": "..."
}
```

### API Externa

| Función | Descripción |
|---|---|
| `resumen_api_externa(sesion)` | Expone KPIs de inventario, ventas del día y versión del sistema para terceros |
| `datos_producto_externo(sesion, producto_id)` | Datos de un producto (SKU, precio, stock, pesable) para e-commerce |

### Backups

| Función | Descripción |
|---|---|
| `obtener_estado_backup()` | Estado del último backup (en memoria, no persistido) |
| `ejecutar_backup(sesion, frecuencia)` | Backup simulado. Frecuencias: manual, hourly, daily, weekly |

El historial de backups se mantiene en una variable de módulo (`_ultimo_backup`). **Se pierde al reiniciar el proceso.**

### Facturación Electrónica

| Función | Descripción |
|---|---|
| `datos_fiscales_venta(sesion, venta_id)` | Estructura los datos de una venta para emisión de comprobante fiscal (AFIP/ARCA). Incluye ítems, totales, emisor (CUIT, punto_venta) y tipo de comprobante |

Las credenciales fiscales se leen de `ParametroSistema` clave `integraciones`.

### Pasarelas de Pago — Reconciliación

| Función | Descripción |
|---|---|
| `reconciliar_pagos_pasarela(sesion, tipo_pasarela, pagos_externos)` | Compara pagos externos (MercadoPago, Getnet, PosNet, Stripe) contra ventas del sistema por monto. Genera informe de conciliados vs sin coincidencia. |

**Limitación:** La reconciliación actual compara únicamente por monto (`venta.total == pago.monto`), no por referencia. Esto puede producir falsos positivos.

---

## Manejo de Errores

- Todos los logs de integración se persisten incluso ante fallos, para no interrumpir la operación.
- Si `tipo_codigo` no es válido (no está en el catálogo), las funciones retornan `None` en lugar de lanzar excepción.
- Los handlers de eventos (consumers) capturan excepciones sin relanzarlas (`events.py` usa try/except por handler).

---

## Estado de Implementación

| Integración | Estado |
|---|---|
| Facturación electrónica | Estructura definida + datos fiscales. Sin conexión real a AFIP/ARCA. |
| Pasarelas de pago | Reconciliación simulada. Sin webhook ni conexión real. |
| Hardware POS | Catálogo y estado de disponibilidad. Sin driver real. |
| Mensajería | Simulada (log de envío, sin SMTP ni WhatsApp real). |
| Tienda/E-commerce | Catálogo definido. Sin sincronización real. |
| Integración contable | Exportación de datos implementada. Sin conector a sistemas externos. |
| API externa | Endpoints de resumen y producto implementados. |
| Backups | Simulado en memoria. Sin escritura real a disco o nube. |
