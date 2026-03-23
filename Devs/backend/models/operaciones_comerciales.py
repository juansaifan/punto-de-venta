"""Modelos de persistencia para Operaciones Comerciales del POS (Módulo 2).

Este bloque cubre:
- Devolución de productos (reingreso a inventario + reintegro a caja o cuenta corriente)
- Nota de crédito (reintegro a caja o cuenta corriente)
- Anulación de ticket/venta pendiente (restaura inventario cuando corresponde)
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class TipoOperacionComercial(str, Enum):
    DEVOLUCION = "DEVOLUCION"
    CAMBIO_PRODUCTO = "CAMBIO_PRODUCTO"
    NOTA_CREDITO = "NOTA_CREDITO"
    NOTA_DEBITO = "NOTA_DEBITO"
    CREDITO_CUENTA_CORRIENTE = "CREDITO_CUENTA_CORRIENTE"
    ANULACION = "ANULACION"


class EstadoOperacionComercial(str, Enum):
    EJECUTADA = "EJECUTADA"
    CANCELADA = "CANCELADA"


class OperacionComercial(Base):
    __tablename__ = "operacion_comercial"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    venta_id: Mapped[int] = mapped_column(
        ForeignKey("venta.id"), nullable=False, index=True
    )
    cliente_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("persona.id"), nullable=True, index=True
    )

    tipo: Mapped[TipoOperacionComercial] = mapped_column(
        SAEnum(TipoOperacionComercial), nullable=False, index=True
    )
    estado: Mapped[EstadoOperacionComercial] = mapped_column(
        SAEnum(EstadoOperacionComercial),
        nullable=False,
        default=EstadoOperacionComercial.EJECUTADA,
        index=True,
    )

    motivo: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    importe_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )

    detalle_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    venta: Mapped["Venta"] = relationship("Venta")
    detalles: Mapped[list["OperacionComercialDetalle"]] = relationship(
        "OperacionComercialDetalle",
        back_populates="operacion",
        cascade="all, delete-orphan",
        order_by="OperacionComercialDetalle.id",
    )


class OperacionComercialDetalle(Base):
    __tablename__ = "operacion_comercial_detalle"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    operacion_id: Mapped[int] = mapped_column(
        ForeignKey("operacion_comercial.id"), nullable=False, index=True
    )

    # Para devoluciones: referenciar item de la venta original (opcional).
    item_venta_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("item_venta.id"), nullable=True, index=True
    )

    producto_id: Mapped[int] = mapped_column(
        ForeignKey("producto.id"), nullable=False, index=True
    )
    nombre_producto: Mapped[str] = mapped_column(String(256), nullable=False)

    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    operacion: Mapped["OperacionComercial"] = relationship(
        "OperacionComercial", back_populates="detalles"
    )

