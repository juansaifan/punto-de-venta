# MODULE_STATUS.md — Estado de Módulos

Este documento controla el progreso real de cada módulo.

---

# Estados

PLANNED
El módulo aún no comenzó.

IN_PROGRESS
El módulo está en desarrollo.

STABLE
El módulo funciona correctamente pero puede recibir mejoras.

LOCK_CANDIDATE
El módulo parece terminado y requiere auditoría.

LOCKED
El módulo está finalizado.
---

# Reglas de transición

PLANNED → IN_PROGRESS  
Cuando comienza el desarrollo.

IN_PROGRESS → STABLE  
Cuando el módulo tiene funcionalidad básica completa (aunque falten mejoras).

STABLE → LOCK_CANDIDATE  
Cuando parece terminado y solo requiere auditoría final.

LOCK_CANDIDATE → LOCKED  
Después de auditoría satisfactoria.

---

# Estado real de los módulos (auditoría arquitecto marzo 2026)

La siguiente tabla refleja el criterio actual de auditoría, **no** un arrastre de estados anteriores.

## 1. Estado por módulo (criterio: modulo completo, con frontend en Flutter)

La backend / modelo / tests del modulo estan desarrollados y testeados. El estado a continuacion refleja la madurez del modulo **para continuar desarrollo en Devs**, considerando:
- Backend y modelo reales (en `Devs/backend`)
- Tests existentes (en `Devs/tests`)
- Frontend Flutter objetivo (en `Devs/frontend_flutter`), que actualmente opera con repositorios *mock/offline* y aún falta cablear a endpoints HTTP reales.

| Módulo         | Estado      | Criterio principal |
|----------------|-------------|---------------------|
| Dashboard      | IN_PROGRESS| Backend + endpoints de Dashboard listos; existe UI Flutter con auto-refresh y panel lateral en `frontend_flutter`, pero consumiendo mocks/offline (falta HTTP real). |
| Punto de Venta | IN_PROGRESS| Backend muy avanzado (TEU_ON/TEU_OFF, suspenso, operaciones comerciales y submódulo Pesables); existe UI Flutter (ventas + caja) en `frontend_flutter` con lógica mock (falta wiring a `/api/...`). |
| Tesorería      | IN_PROGRESS| Backend listo (caja + cuentas corrientes); existe UI Flutter parcial (modo caja/CC) con mocks/offline; faltan subpantallas de tesorería según docs. |
| Finanzas       | PLANNED     | Backend listo (análisis + exportaciones); no hay pantallas Flutter de Finanzas en `frontend_flutter`. |
| Inventario     | IN_PROGRESS| Backend listo (stock, lotes, movimientos, alertas); existe UI Flutter parcial (inventario + CRUD productos) con mocks/offline; falta UI avanzada (lotes/movimientos/conteos/transferencias). |
| Personas       | PLANNED     | Backend listo (clientes/proveedores/empleados/usuarios/roles); no hay pantallas Flutter de Personas en `frontend_flutter`. |
| Reportes       | PLANNED     | Backend listo (reportes + exportación CSV); no hay pantallas Flutter de Reportes en `frontend_flutter`. |
| Integraciones  | PLANNED     | Backend listo (catálogo/estado/config/logs + flujo alternativo sin impresora); no hay pantallas Flutter de Integraciones en `frontend_flutter`. |
| Configuración  | PLANNED     | Backend listo (config, usuarios/roles/permisos y medios de pago); no hay pantallas Flutter de Configuración en `frontend_flutter`. |

## 2. Nivel de avance por módulo (aproximado)

Los porcentajes combinan backend, modelo de datos, tests e integracion entre modulos. En Devs ya existe base Flutter (`frontend_flutter`) pero en modo offline/mocks; la columna Frontend refleja el grado de madurez Flutter y su cableado real al backend.

| Módulo         | Backend | Frontend (Flutter) | Modelo de datos | Tests | Nivel total aprox. |
|----------------|---------|--------------------|-----------------|-------|--------------------|
| Dashboard      | ~97 %   | ~70 %              | ~70 %           | ~90 % | ~82 %              |
| Punto de Venta | ~94 %   | ~75 %              | ~85 %           | ~92 % | ~86 %              |
| Tesorería      | ~92 %   | ~55 %              | ~82 %           | ~90 % | ~80 %              |
| Finanzas       | ~93 %   | ~0 %               | ~80 %           | ~88 % | ~65 %              |
| Inventario     | ~90 %   | ~60 %              | ~88 %           | ~88 % | ~81 %              |
| Personas       | ~92 %   | ~0 %               | ~85 %           | ~90 % | ~67 %              |
| Reportes       | ~94 %   | ~0 %               | ~85 %           | ~90 % | ~67 %              |
| Integraciones  | ~90 %   | ~0 %               | ~80 %           | ~88 % | ~64 %              |
| Configuración  | ~95 %   | ~0 %               | ~90 %           | ~92 % | ~69 %              |

Estos valores son estimaciones de auditoría y sirven solo como guía de madurez relativa entre módulos.

## 3. Tareas de frontend (Flutter) - Migracion desde `pos-market`

1. Consolidar el frontend Flutter objetivo en `D:\Proyectos\Punto de Venta\Devs\frontend_flutter` (Flutter/Dart + UI Material + `package:http`).
2. Reemplazar los repositorios *mock/offline* por un `ClienteApi` HTTP real (reutilizando el enfoque de `pos-market/pos_frontend/lib/core/api/api_client.dart`).
3. Prioridad Modulo 1 (Dashboard): cablear `dashboard_screen.dart` a `GET /api/dashboard/*` y validar refresh (60–120s) y render de:
   - `indicadores`, `indicadores-comparativos`, `ventas-por-hora`
   - `productos-stock-bajo`, `productos-proximos-vencer`
   - `alertas-operativas` y `panel-lateral`
4. Prioridad Modulo 2 (Punto de Venta): cablear `ventas_screen.dart` + flujo de caja/suspenso para operar contra:
   - `POST /api/ventas` (modo_venta TEU_ON/TEU_OFF)
   - `GET /api/caja/tickets/pendientes` y `POST /api/caja/tickets/{venta_id}/cobrar`
   - `POST /api/ventas/{venta_id}/suspender` y `POST /api/ventas/{venta_id}/reanudar`
5. Luego integrar Modulo 5 (Inventario) y avanzar Modulo 3 (Tesorería) completando pantallas faltantes según docs.
6. Finalmente agregar pantallas Flutter para Módulos 6–9 (Personas, Reportes, Integraciones, Configuración) consumiendo endpoints existentes.

## 4. Pesables (Módulo 2 / submódulo)

Fuente funcional/técnica: `Reglas/docs/Módulo 2/4. Pesables/submodulo_pesables.md`.

Estado:

- **Backend:** implementado en gran parte (entidad `PesableItem`, servicio de cálculo y EAN-13, endpoints `/api/pesables/*`, tests dedicados).
- **Frontend:** pendiente (la UI Flutter actual no implementa preparación/etiquetado batch ni consumo real de `/api/pesables/*`).

Brecha concreta (para destrabar cierre end-to-end sin ambigüedad):

- **Integración POS↔Pesables**: hoy existe backend pesables, pero falta cablear POS/caja para usar `barcode` EAN-13 de pesables en flujo real de venta.
- **Frontend Flutter**: crear pantallas/flujo de preparación, impresión batch y cambio de estados (`pending|printed|used`) consumiendo `/api/pesables/*`.
- **Contrato de escaneo**: asegurar en ventas que al escanear pesables se respete “precio codificado en etiqueta” (sin recalcular en POS).
