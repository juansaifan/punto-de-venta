"""Entidades del submódulo Pesables (Módulo 2 – Punto de Venta).

Flujo:
  preparar_item → PesableItem (estado=pending)
  generar_etiqueta  → estado=printed
  escaneo en POS → estado=used
"""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class EstadoPesableItem(str, Enum):
    PENDING = "pending"
    PRINTED = "printed"
    USED = "used"


class PesableItem(Base):
    """Ítem pesable preparado: registra el peso, precio calculado y barcode EAN-13."""

    __tablename__ = "pesable_item"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"), nullable=False, index=True)
    nombre_producto: Mapped[str] = mapped_column(String(256), nullable=False)
    plu: Mapped[int] = mapped_column(nullable=False, doc="PLU del producto (5 dígitos max)")
    peso: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, doc="Peso en kg")
    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, doc="Precio por kg"
    )
    precio_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, doc="Precio total = peso × precio_unitario"
    )
    barcode: Mapped[str] = mapped_column(
        String(13), nullable=False, index=True, doc="EAN-13 generado"
    )
    estado: Mapped[str] = mapped_column(
        String(16), nullable=False, default=EstadoPesableItem.PENDING.value
    )
    creado_en: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
