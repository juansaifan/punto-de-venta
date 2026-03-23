"""Consumidor de eventos para Inventario (alertas operativas)."""

from __future__ import annotations

from typing import Any

from backend.events import subscribe
from backend.services import auditoria_eventos as svc_auditoria


_registrado = False


def _persistir(payload: dict[str, Any], *, nombre: str, entidad_tipo: str) -> None:
    sesion = payload.get("__sesion")
    if sesion is None:
        return
    payload_a_guardar = {k: v for k, v in payload.items() if k != "__sesion"}
    svc_auditoria.registrar_evento(
        sesion,
        nombre=nombre,
        payload=payload_a_guardar,
        modulo="inventario",
        entidad_tipo=entidad_tipo,
        entidad_id=None,
    )


def _handler_stock_bajo(payload: dict[str, Any]) -> None:
    _persistir(payload, nombre="StockBajoDetectado", entidad_tipo="stock")


def _handler_lotes_proximos(payload: dict[str, Any]) -> None:
    _persistir(payload, nombre="LotesProximosAVencerDetectados", entidad_tipo="lote")


def registrar_consumidores() -> None:
    global _registrado
    if _registrado:
        return
    subscribe("StockBajoDetectado", _handler_stock_bajo)
    subscribe("LotesProximosAVencerDetectados", _handler_lotes_proximos)
    _registrado = True

