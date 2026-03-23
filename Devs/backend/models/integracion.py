"""Configuración por tipo de integración (docs Módulo 8: activar/desactivar, credenciales, logs)."""
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class IntegracionLog(Base):
    """
    Log de un intento de integración (éxito o fallo). Docs Módulo 8: "registrar fallos de integración
    sin interrumpir la operación" y "Logs de integración".
    """
    __tablename__ = "integracion_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_codigo: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    exito: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mensaje: Mapped[str] = mapped_column(String(512), nullable=False)
    detalle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)


class IntegracionConfig(Base):
    """
    Estado y configuración por tipo de integración.
    Un registro por tipo_codigo (catálogo TIPOS_INTEGRACION del servicio).
    config_json: JSON serializado (credenciales, parámetros por tipo).
    """
    __tablename__ = "integracion_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_codigo: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
