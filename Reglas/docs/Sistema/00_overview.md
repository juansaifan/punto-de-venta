# 00 — Visión General del Sistema

## Descripción General

**Punto de Venta (POS)** es un sistema de gestión comercial orientado a comercios minoristas. Permite registrar y cobrar ventas, gestionar inventario, manejar caja, cuentas corrientes de clientes, compras a proveedores, finanzas y reportes operativos.

El nombre del negocio configurado por defecto en el código es **"La Casona"** (visible en el app Flutter).

---

## Objetivo del Producto

Proveer una plataforma de punto de venta que cubra el ciclo completo de operaciones de un negocio minorista:

- Venta directa al mostrador (TEU_ON) y diferida a caja (TEU_OFF)
- Gestión de inventario con ubicaciones (góndola / depósito)
- Pesables con generación de etiquetas EAN-13
- Cuentas corrientes de clientes (crédito)
- Tesorería, finanzas y cuentas financieras
- Compras a proveedores
- Reportes y dashboard operativo
- Integraciones externas (facturación electrónica, pasarelas, mensajería, hardware)

---

## Alcance Funcional Actual

| Módulo | Estado backend | Estado frontend Flutter |
|---|---|---|
| Dashboard | Implementado | Pantalla implementada |
| Ventas (POS) | Implementado | Pantalla implementada |
| Caja (Tesorería) | Implementado | Pantalla implementada |
| Pesables | Implementado | Pantalla implementada |
| Inventario | Implementado | Pantalla implementada |
| Operaciones Comerciales | Implementado | Placeholder |
| Personas (clientes, proveedores, empleados) | Implementado | Placeholder |
| Finanzas | Implementado | Placeholder |
| Compras | Implementado | Placeholder |
| Reportes | Implementado | Placeholder |
| Configuración | Implementado | Placeholder |
| Integraciones | Implementado | Placeholder |
| Cuentas Corrientes | Implementado | No presente |
| Auditoría de Eventos | Implementado | No presente |
| Solicitudes de Compra | Implementado | No presente |

---

## Stack Tecnológico Identificado

### Backend
| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ (CPython 3.13 en uso) |
| Framework web | FastAPI |
| ORM | SQLAlchemy 2.x (Mapped columns) |
| Base de datos | SQLite (default, configurable vía env) |
| Servidor ASGI | Uvicorn |
| Testing | pytest 9.x |
| HTTP cliente (tests) | httpx |
| Config | python-dotenv |

### Frontend
| Componente | Tecnología |
|---|---|
| Framework principal | Flutter / Dart (SDK ≥3.3.0) |
| HTTP client | package:http ^1.2.0 |
| Persistencia local | shared_preferences ^2.5.3 |
| Target actual | Windows desktop |
| Frontend web (legacy/incompleto) | HTML/JS + CSS (carpeta `frontend/`) |

---

## Principales Módulos

1. **Ventas** — Registro de ventas en modos TEU_ON (cobro inmediato) y TEU_OFF (cola para caja)
2. **Caja / Tesorería** — Apertura, cierre, movimientos, arqueo y cobro de tickets pendientes
3. **Productos** — ABM de productos con soporte de pesables (EAN-13 y PLU)
4. **Inventario** — Stock por ubicación, movimientos, lotes, vencimientos, rotación
5. **Pesables** — Flujo completo: preparar ítem pesable → generar EAN-13 → escaneo en POS
6. **Personas** — Clientes, proveedores, empleados y contactos
7. **Cuentas Corrientes** — Saldo de deuda y pagos de clientes
8. **Compras** — Órdenes de compra a proveedores con impacto en inventario
9. **Operaciones Comerciales** — Devoluciones, cambios, notas de crédito/débito, anulaciones
10. **Finanzas** — Cuentas financieras y transacciones (caja física, banco, billetera virtual)
11. **Reportes** — Informes operativos de ventas, inventario y finanzas
12. **Integraciones** — Facturación electrónica, pasarelas de pago, hardware POS, mensajería, backup, API externa
13. **Configuración** — Empresa, sucursales, medios de pago, permisos, parámetros de sistema
14. **Auditoría de Eventos** — Bus de eventos in-process con persistencia de log
15. **Dashboard** — KPIs y métricas en tiempo real
