"""Entidades para solicitudes de compra (abastecimiento automático)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class SolicitudCompra(Base):
    __tablename__ = "solicitud_compra"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    estado: Mapped[str] = mapped_column(String(32), default="PENDIENTE")  # PENDIENTE / ATENDIDA / CANCELADA
    creada_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    referencia: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)


class ItemSolicitudCompra(Base):
    __tablename__ = "item_solicitud_compra"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int] = mapped_column(
        ForeignKey("solicitud_compra.id"), nullable=False
    )
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    motivo: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

