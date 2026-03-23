"""Entidades de auditoría de eventos del sistema.

Persisten eventos in-process para trazabilidad operativa (Observabilidad).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class EventoSistemaLog(Base):
    __tablename__ = "evento_sistema_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(128), index=True)
    modulo: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    entidad_tipo: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    entidad_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)

    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

