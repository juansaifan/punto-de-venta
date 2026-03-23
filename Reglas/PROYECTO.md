# PROYECTO --- Sistema Punto de Venta

## 1. Propósito del Documento

Este documento define la **arquitectura conceptual completa del sistema
Punto de Venta**. Sirve como fuente de contexto para:

-   desarrolladores
-   arquitectos del sistema
-   herramientas de automatización
-   agentes de IA que trabajen sobre el repositorio

El objetivo es que cualquier sistema (humano o automatizado) pueda
comprender:

-   estructura del negocio
-   módulos del sistema
-   entidades principales
-   flujos operativos
-   dependencias entre módulos

Este documento describe **qué es el sistema y cómo está organizado**.

------------------------------------------------------------------------

# 2. Dominio del Sistema

Dominio:

Gestión Comercial + Punto de Venta + Control Operativo.

El sistema permite administrar:

-   ventas
-   clientes
-   inventario
-   caja
-   finanzas
-   métricas del negocio

------------------------------------------------------------------------

# 3. Arquitectura General

Capas:

Frontend\
Interfaz de usuario.

Backend\
Lógica de negocio.

Base de datos\
Persistencia.

Servicios internos\
Comunicación entre módulos.

Integraciones externas\
APIs externas.

------------------------------------------------------------------------

# 4. Módulos del Sistema

El sistema tiene **9 módulos principales**.

Dashboard\
Centro de métricas y monitoreo.

Punto de Venta\
Registro de ventas.

Tesorería\
Gestión de caja.

Finanzas\
Control financiero.

Inventario\
Gestión de productos y stock.

Reportes\
Análisis del negocio.

Configuración\
Parámetros del sistema.

Integraciones\
Conexión con sistemas externos.

Personas\
Clientes, empleados y proveedores.

------------------------------------------------------------------------

# 5. Entidades Principales

Producto Venta DetalleVenta Pago Cliente Empleado Proveedor
MovimientoCaja MovimientoInventario CuentaFinanciera

------------------------------------------------------------------------

# 6. Flujos Operativos

Flujo de venta:

1.  Selección de productos
2.  Cálculo de totales
3.  Registro de pago
4.  Registro de venta
5.  Descuento de inventario
6.  Movimiento de caja

------------------------------------------------------------------------

# 7. Eventos del Sistema

VentaRegistrada\
CajaAbierta\
CajaCerrada\
PagoRegistrado\
MovimientoCajaRegistrado\
MovimientoCuentaCorrienteRegistrado\
OperacionComercialRegistrada\
StockBajoDetectado\
LotesProximosAVencerDetectados\
IngresoRegistrado\
GastoRegistrado

------------------------------------------------------------------------

# 8. Escalabilidad

El sistema debe soportar:

-   múltiples sucursales
-   múltiples cajas
-   múltiples usuarios
-   integraciones externas

------------------------------------------------------------------------

# 9. Stack Tecnologico (Actual y Objetivo)

## Backend
-   Lenguaje: Python 3.11+
-   Framework: FastAPI
-   ORM: SQLAlchemy 2.x
-   Base de datos (por defecto): SQLite
-   Pruebas: pytest

## Frontend (objetivo)
-   Lenguaje/Framework: Flutter (Flutter/Dart)
-   Estilo UI: Material Design
-   Integracion con backend: llamadas HTTP (paquete `http` en el frontend Flutter original de `pos-market`)

## Regla de desarrollo del frontend
-   El frontend en `Devs/` debe desarrollarse en Flutter.
-   Cualquier UI web existente en `Devs/` se considera un prototipo temporal y no el objetivo final.

------------------------------------------------------------------------

# 10. Relación con ROADMAP.md

PROYECTO.md describe:

-   arquitectura
-   dominios
-   módulos
-   entidades

ROADMAP.md describe:

-   evolución del sistema
-   fases de desarrollo
-   funcionalidades futuras

------------------------------------------------------------------------

Última actualización: 2026
