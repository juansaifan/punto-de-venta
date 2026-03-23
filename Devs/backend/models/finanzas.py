"""Entidades del dominio Finanzas (DATA_MODEL §6)."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class CuentaFinanciera(Base):
    """Cuenta financiera del negocio (caja física, banco, billetera virtual, fondo).

    Tipos admitidos (§9 Tesorería): caja_fisica, cuenta_bancaria,
    billetera_virtual, fondo_operativo, fondo_cambio, GENERAL.
    """

    __tablename__ = "cuenta_financiera"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(128))
    tipo: Mapped[str] = mapped_column(String(32), default="GENERAL")
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    estado: Mapped[str] = mapped_column(String(16), default="activa")
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class TransaccionFinanciera(Base):
    __tablename__ = "transaccion_financiera"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta_financiera.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conciliada: Mapped[bool] = mapped_column(default=False)
    fecha_conciliacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    cuenta: Mapped["CuentaFinanciera"] = relationship("CuentaFinanciera", backref="transacciones")
