"""Servicios para solicitudes de compra (abastecimiento)."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.producto import Producto
from backend.models.solicitud_compra import ItemSolicitudCompra, SolicitudCompra


def crear_solicitud_compra(
    sesion: Session,
    *,
    items: list[dict],
    referencia: Optional[str] = None,
) -> SolicitudCompra:
    if not items:
        raise ValueError("La solicitud debe tener al menos un ítem")

    sol = SolicitudCompra(referencia=referencia)
    sesion.add(sol)
    sesion.flush()

    for it in items:
        producto_id = int(it["producto_id"])
        cantidad = Decimal(str(it["cantidad"]))
        motivo = it.get("motivo")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        prod = sesion.get(Producto, producto_id)
        if prod is None:
            raise ValueError(f"Producto {producto_id} no encontrado")
        sesion.add(
            ItemSolicitudCompra(
                solicitud_id=sol.id,
                producto_id=producto_id,
                cantidad=cantidad,
                motivo=(str(motivo)[:128] if motivo else None),
            )
        )

    sesion.flush()
    sesion.refresh(sol)
    return sol


def listar_solicitudes(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[SolicitudCompra]:
    stmt = (
        select(SolicitudCompra)
        .order_by(SolicitudCompra.creada_en.desc(), SolicitudCompra.id.desc())
        .limit(limite)
        .offset(offset)
    )
    return sesion.scalars(stmt).all()


def obtener_solicitud(
    sesion: Session,
    solicitud_id: int,
) -> Optional[SolicitudCompra]:
    return sesion.get(SolicitudCompra, solicitud_id)


def listar_items_solicitud(
    sesion: Session,
    solicitud_id: int,
) -> Sequence[ItemSolicitudCompra]:
    stmt = (
        select(ItemSolicitudCompra)
        .where(ItemSolicitudCompra.solicitud_id == solicitud_id)
        .order_by(ItemSolicitudCompra.id.asc())
    )
    return sesion.scalars(stmt).all()


def marcar_solicitud_estado(
    sesion: Session,
    *,
    solicitud_id: int,
    estado: str,
) -> SolicitudCompra:
    sol = sesion.get(SolicitudCompra, solicitud_id)
    if sol is None:
        raise ValueError("Solicitud no encontrada")
    estado_norm = (estado or "").strip().upper()
    if estado_norm not in {"PENDIENTE", "ATENDIDA", "CANCELADA"}:
        raise ValueError("Estado inválido")
    sol.estado = estado_norm
    sesion.add(sol)
    sesion.flush()
    sesion.refresh(sol)
    return sol

