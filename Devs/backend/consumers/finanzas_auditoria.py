"""Consumidor de eventos para Finanzas (auditoría).

Persistimos eventos in-process:
- `IngresoRegistrado`
- `GastoRegistrado`

en `evento_sistema_log` para trazabilidad y consulta vía `/api/auditoria/eventos`.
"""

from __future__ import annotations

from typing import Any

from backend.events import subscribe
from backend.services import auditoria_eventos as svc_auditoria

_registrado = False


def _persistir_finanzas(payload: dict[str, Any], *, nombre: str) -> None:
    sesion = payload.get("__sesion")
    if sesion is None:
        # Si el payload no incluye sesión viva, mantenemos el bus simple.
        return

    payload_a_guardar = {k: v for k, v in payload.items() if k != "__sesion"}
    tx_id = payload_a_guardar.get("transaccion_id")

    svc_auditoria.registrar_evento(
        sesion,
        nombre=nombre,
        payload=payload_a_guardar,
        modulo="finanzas",
        entidad_tipo="transaccion_financiera",
        entidad_id=tx_id,
    )


def _handler_ingreso(payload: dict[str, Any]) -> None:
    _persistir_finanzas(payload, nombre="IngresoRegistrado")


def _handler_gasto(payload: dict[str, Any]) -> None:
    _persistir_finanzas(payload, nombre="GastoRegistrado")


def registrar_consumidores() -> None:
    """Registra handlers de eventos (idempotente)."""
    global _registrado
    if _registrado:
        return
    subscribe("IngresoRegistrado", _handler_ingreso)
    subscribe("GastoRegistrado", _handler_gasto)
    _registrado = True

