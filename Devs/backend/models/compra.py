"""Entidades del dominio de Compras/Proveedores."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class Compra(Base):
    __tablename__ = "compra"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("persona.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    estado: Mapped[str] = mapped_column(String(32), default="CONFIRMADA")

    items: Mapped[List["ItemCompra"]] = relationship(
        "ItemCompra",
        back_populates="compra",
        cascade="all, delete-orphan",
    )


class ItemCompra(Base):
    __tablename__ = "item_compra"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    compra_id: Mapped[int] = mapped_column(ForeignKey("compra.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False)
    nombre_producto: Mapped[str] = mapped_column(String(256))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    compra: Mapped["Compra"] = relationship("Compra", back_populates="items")

