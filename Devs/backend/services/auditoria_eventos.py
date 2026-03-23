"""Servicios de auditoría/bitácora de eventos del sistema."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.eventos import EventoSistemaLog


def registrar_evento(
    sesion: Session,
    *,
    nombre: str,
    payload: dict[str, Any],
    modulo: Optional[str] = None,
    entidad_tipo: Optional[str] = None,
    entidad_id: Optional[int] = None,
    fecha: Optional[datetime] = None,
) -> EventoSistemaLog:
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("Nombre de evento obligatorio")

    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    evt = EventoSistemaLog(
        nombre=nombre,
        modulo=modulo,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        payload_json=payload_json,
    )
    if fecha is not None:
        evt.fecha = fecha
    sesion.add(evt)
    sesion.flush()
    sesion.refresh(evt)
    return evt


def listar_eventos(
    sesion: Session,
    *,
    nombre: Optional[str] = None,
    modulo: Optional[str] = None,
    entidad_tipo: Optional[str] = None,
    entidad_id: Optional[int] = None,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[EventoSistemaLog]:
    stmt = select(EventoSistemaLog)

    if nombre:
        stmt = stmt.where(EventoSistemaLog.nombre == nombre)
    if modulo:
        stmt = stmt.where(EventoSistemaLog.modulo == modulo)
    if entidad_tipo:
        stmt = stmt.where(EventoSistemaLog.entidad_tipo == entidad_tipo)
    if entidad_id is not None:
        stmt = stmt.where(EventoSistemaLog.entidad_id == entidad_id)
    if desde is not None:
        stmt = stmt.where(EventoSistemaLog.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(EventoSistemaLog.fecha <= hasta)

    stmt = stmt.order_by(EventoSistemaLog.fecha.desc(), EventoSistemaLog.id.desc()).limit(limite).offset(offset)
    return sesion.scalars(stmt).all()

