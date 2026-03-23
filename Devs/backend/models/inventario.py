"""Entidades del dominio de inventario."""
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base


class UbicacionStock(str, Enum):
    GONDOLA = "GONDOLA"
    DEPOSITO = "DEPOSITO"


class TipoMovimiento(str, Enum):
    VENTA = "VENTA"
    COMPRA = "COMPRA"
    TRANSFERENCIA = "TRANSFERENCIA"
    DEVOLUCION = "DEVOLUCION"
    AJUSTE = "AJUSTE"
    MERMA = "MERMA"
    CONSUMO_INTERNO = "CONSUMO_INTERNO"
    REVERSION = "REVERSION"


class Stock(Base):
    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False)
    ubicacion: Mapped[str] = mapped_column(String(32), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)


class Lote(Base):
    """
    Lote de producto con fecha de vencimiento (gestión de lotes para dashboard 'productos próximos a vencer').
    """
    __tablename__ = "lote"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    ubicacion: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    referencia: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
