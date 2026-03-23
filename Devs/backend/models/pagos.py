"""Persistencia de pagos asociados a tickets/ventas en Caja.

El POS (Modo TEU) reutiliza la lógica de Caja. Para soportar pagos combinados
y auditoría por método, se modela cada pago como un registro separado.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transaction"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    venta_id: Mapped[int] = mapped_column(
        ForeignKey("venta.id"), nullable=False, index=True
    )
    caja_id: Mapped[Optional[int]] = mapped_column(ForeignKey("caja.id"), nullable=True, index=True)

    metodo_pago: Mapped[str] = mapped_column(String(32), nullable=False)
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Campos auxiliares para auditoría (p.ej. banco/cuenta para transferencias)
    medio_pago: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cobrador: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    venta: Mapped["Venta"] = relationship(
        "Venta", back_populates="pagos"
    )

