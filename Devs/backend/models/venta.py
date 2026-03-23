"""Entidades del dominio de ventas."""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class EstadoVenta(str, Enum):
    PENDIENTE = "PENDIENTE"
    PAGADA = "PAGADA"
    SUSPENDIDA = "SUSPENDIDA"
    FIADA = "FIADA"
    CANCELADA = "CANCELADA"


class Venta(Base):
    __tablename__ = "venta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_ticket: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    impuesto: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    metodo_pago: Mapped[str] = mapped_column(String(32), default="EFECTIVO")
    detalle_pagos: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    caja_id: Mapped[Optional[int]] = mapped_column(ForeignKey("caja.id"), nullable=True)
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("persona.id"), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(32),
        default=EstadoVenta.PENDIENTE.value,
        index=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    items: Mapped[List["ItemVenta"]] = relationship(
        "ItemVenta", back_populates="venta", cascade="all, delete-orphan"
    )

    pagos: Mapped[List["PaymentTransaction"]] = relationship(
        "PaymentTransaction",
        back_populates="venta",
        cascade="all, delete-orphan",
    )

    def recalcular_totales(self) -> None:
        self.subtotal = sum(i.subtotal for i in self.items)
        self.total = self.subtotal - self.descuento + self.impuesto


class ItemVenta(Base):
    __tablename__ = "item_venta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("venta.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False)
    nombre_producto: Mapped[str] = mapped_column(String(256))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    venta: Mapped["Venta"] = relationship("Venta", back_populates="items")
