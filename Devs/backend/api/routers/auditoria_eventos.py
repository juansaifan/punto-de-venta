"""Endpoints REST para auditoría de eventos del sistema."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import auditoria_eventos as svc_auditoria


router = APIRouter(prefix="/auditoria/eventos", tags=["auditoria"])


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    return datetime.fromisoformat(v)


@router.get("")
def listar_eventos(
    db: Session = Depends(get_db),
    nombre: Optional[str] = Query(None),
    modulo: Optional[str] = Query(None),
    entidad_tipo: Optional[str] = Query(None),
    entidad_id: Optional[int] = Query(None),
    desde: Optional[str] = Query(None, description="ISO datetime (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)"),
    hasta: Optional[str] = Query(None, description="ISO datetime (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items = svc_auditoria.listar_eventos(
        db,
        nombre=nombre,
        modulo=modulo,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        desde=_parse_dt(desde),
        hasta=_parse_dt(hasta),
        limite=limite,
        offset=offset,
    )
    return [
        {
            "id": e.id,
            "nombre": e.nombre,
            "modulo": e.modulo,
            "entidad_tipo": e.entidad_tipo,
            "entidad_id": e.entidad_id,
            "fecha": e.fecha.isoformat() if e.fecha else None,
            "payload": json.loads(e.payload_json) if e.payload_json else {},
        }
        for e in items
    ]

