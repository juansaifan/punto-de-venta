"""Entidades del dominio de caja."""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class TipoMovimientoCaja(str, Enum):
    VENTA = "VENTA"
    DEVOLUCION = "DEVOLUCION"
    RETIRO = "RETIRO"
    INGRESO = "INGRESO"
    GASTO = "GASTO"


class Caja(Base):
    __tablename__ = "caja"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha_apertura: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    saldo_final: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id"), nullable=True)

    movimientos: Mapped[List["MovimientoCaja"]] = relationship(
        "MovimientoCaja", back_populates="caja", order_by="MovimientoCaja.fecha"
    )

    @property
    def abierta(self) -> bool:
        return self.fecha_cierre is None


class MovimientoCaja(Base):
    __tablename__ = "movimiento_caja"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    caja_id: Mapped[int] = mapped_column(ForeignKey("caja.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    medio_pago: Mapped[str] = mapped_column(String(32), default="EFECTIVO")
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    referencia: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    caja: Mapped["Caja"] = relationship("Caja", back_populates="movimientos")
