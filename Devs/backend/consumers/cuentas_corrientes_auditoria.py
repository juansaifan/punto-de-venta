"""Consumidor de eventos para Tesorería/Cuentas Corrientes.

Objetivo: persistir una bitácora operativa del evento
`MovimientoCuentaCorrienteRegistrado` para auditoría/observabilidad.
"""

from __future__ import annotations

from typing import Any

from backend.events import subscribe
from backend.services import auditoria_eventos as svc_auditoria


_registrado = False


def _handler_movimiento_cc(payload: dict[str, Any]) -> None:
    # En tests y en flujos internos, se pasa la sesión viva para que la escritura
    # quede dentro de la misma transacción.
    sesion = payload.get("__sesion")
    if sesion is None:
        # Fallback: no persistimos si no hay sesión. Mantiene el bus simple y evita
        # escribir a una BD distinta del contexto (ej. tests in-memory).
        return

    payload_a_guardar = {k: v for k, v in payload.items() if k != "__sesion"}
    svc_auditoria.registrar_evento(
        sesion,
        nombre="MovimientoCuentaCorrienteRegistrado",
        payload=payload_a_guardar,
        modulo="tesoreria",
        entidad_tipo="cuenta_corriente_cliente",
        entidad_id=payload_a_guardar.get("cliente_id"),
    )


def _handler_movimiento_caja(payload: dict[str, Any]) -> None:
    sesion = payload.get("__sesion")
    if sesion is None:
        return

    payload_a_guardar = {k: v for k, v in payload.items() if k != "__sesion"}
    svc_auditoria.registrar_evento(
        sesion,
        nombre="MovimientoCajaRegistrado",
        payload=payload_a_guardar,
        modulo="tesoreria",
        entidad_tipo="caja",
        entidad_id=payload_a_guardar.get("caja_id"),
    )


def _handler_caja_abierta(payload: dict[str, Any]) -> None:
    sesion = payload.get("__sesion")
    if sesion is None:
        return
    payload_a_guardar = {k: v for k, v in payload.items() if k != "__sesion"}
    svc_auditoria.registrar_evento(
        sesion,
        nombre="CajaAbierta",
        payload=payload_a_guardar,
        modulo="tesoreria",
        entidad_tipo="caja",
        entidad_id=payload_a_guardar.get("caja_id"),
    )


def _handler_caja_cerrada(payload: dict[str, Any]) -> None:
    sesion = payload.get("__sesion")
    if sesion is None:
        return
    payload_a_guardar = {k: v for k, v in payload.items() if k != "__sesion"}
    svc_auditoria.registrar_evento(
        sesion,
        nombre="CajaCerrada",
        payload=payload_a_guardar,
        modulo="tesoreria",
        entidad_tipo="caja",
        entidad_id=payload_a_guardar.get("caja_id"),
    )


def _handler_pago_registrado(payload: dict[str, Any]) -> None:
    """Persistir evento PagoRegistrado para auditoría."""
    sesion = payload.get("__sesion")
    if sesion is None:
        return

    payload_a_guardar = {k: v for k, v in payload.items() if k != "__sesion"}
    svc_auditoria.registrar_evento(
        sesion,
        nombre="PagoRegistrado",
        payload=payload_a_guardar,
        modulo="punto_venta",
        entidad_tipo="venta",
        entidad_id=payload_a_guardar.get("venta_id"),
    )


def registrar_consumidores() -> None:
    """Registra handlers de eventos (idempotente)."""
    global _registrado
    if _registrado:
        return
    subscribe("MovimientoCuentaCorrienteRegistrado", _handler_movimiento_cc)
    subscribe("MovimientoCajaRegistrado", _handler_movimiento_caja)
    subscribe("PagoRegistrado", _handler_pago_registrado)
    subscribe("CajaAbierta", _handler_caja_abierta)
    subscribe("CajaCerrada", _handler_caja_cerrada)
    _registrado = True

