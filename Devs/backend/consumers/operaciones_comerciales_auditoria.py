"""Consumidor de eventos para auditoría de Operaciones Comerciales."""

from __future__ import annotations

from typing import Any

from backend.events import subscribe
from backend.services import auditoria_eventos as svc_auditoria

_registrado = False


def _handler_operacion_comercial_registrada(payload: dict[str, Any]) -> None:
    sesion = payload.get("__sesion")
    if sesion is None:
        return

    payload_a_guardar = {k: v for k, v in payload.items() if k != "__sesion"}
    svc_auditoria.registrar_evento(
        sesion,
        nombre="OperacionComercialRegistrada",
        payload=payload_a_guardar,
        modulo="ventas",
        entidad_tipo="operacion_comercial",
        entidad_id=payload_a_guardar.get("operacion_id"),
    )


def registrar_consumidores() -> None:
    global _registrado
    if _registrado:
        return
    subscribe("OperacionComercialRegistrada", _handler_operacion_comercial_registrada)
    _registrado = True

