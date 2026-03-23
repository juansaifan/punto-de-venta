# system_state_vigente.md — Punto de Venta

**Última actualización:** 2026-03-19
**Origen:** Auditoría basada en `Devs/backend` + `Devs/tests` y la UI Flutter existente en `Devs/frontend_flutter` (modo mock/offline).

---
## Progreso global (aprox.)

- **Proyecto total:** 80–85%
- **Backend total:** ~93–95%
- **Modelo de datos:** ~90%
- **Tests:** ~97%
- **Frontend total:** ~25–35% (Flutter UI parcial para Módulos 1–5, aún sin wiring HTTP real)

---
## Estado por módulo (aprox.)

| Módulo | Estado | Backend | Frontend (Flutter) | Modelo | Tests | Nivel total aprox. |
|--------|---------|---------|---------------------|--------|--------|---------------------|
| 1 Dashboard | IN_PROGRESS | ~97% | ~70% | ~70% | ~90% | ~82% |
| 2 Punto de Venta | IN_PROGRESS | ~94% | ~75% | ~85% | ~92% | ~86% |
| 3 Tesorería | IN_PROGRESS | ~92% | ~55% | ~82% | ~90% | ~80% |
| 4 Finanzas | PLANNED | ~93% | ~0% | ~80% | ~88% | ~65% |
| 5 Inventario | IN_PROGRESS | ~90% | ~60% | ~88% | ~88% | ~81% |
| 6 Personas | PLANNED | ~92% | ~0% | ~85% | ~90% | ~67% |
| 7 Reportes | PLANNED | ~94% | ~0% | ~85% | ~90% | ~67% |
| 8 Integraciones | PLANNED | ~90% | ~0% | ~80% | ~88% | ~64% |
| 9 Configuración | PLANNED | ~95% | ~0% | ~90% | ~92% | ~69% |

---
## Brechas y bloqueos principales

- Pesables (Módulo 2 / submódulo): backend implementado (entidad `PesableItem`, generación EAN-13, endpoints `/api/pesables/*`, tests dedicados), pero falta **integración end-to-end con POS/Frontend Flutter** y escaneo operativo en flujo de ventas real.
- El frontend Flutter en `frontend_flutter` está en modo `mock/offline`; falta reemplazar `ClienteApi` mock por cliente HTTP real contra `/api/...`.
- El módulo de “Pesables” depende de integración hardware/contrato técnico (balanza/impresión) y de UI Flutter; el backend ya persiste y gestiona ciclo de vida del `PesableItem`.
- `EVENTOS.md` estaba desalineado con eventos *in-process* realmente emitidos por el backend; se actualizó para evitar confusiones event-driven.

---
## Próximo paso concreto (para destrabar desarrollo en Flutter)

1. Cablear UI Flutter existente (Módulos 1 y 2, y parte de 3/5) a endpoints reales:
   - Dashboard: `GET /api/dashboard/*`
   - POS: `POST /api/ventas`, caja/tickets TEU_OFF, suspenso/reanudación
   - Caja/CC: `GET /api/caja/*` y `POST/GET /api/tesoreria/cuentas-corrientes/*`
2. Mantener mocks como “fallback” solo mientras se completa integración (sin inventar lógica adicional).

