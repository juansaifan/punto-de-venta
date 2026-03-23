"""Entidad Usuario (vinculado a persona y opcionalmente a un rol)."""
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(128))
    persona_id: Mapped[Optional[int]] = mapped_column(ForeignKey("persona.id"), nullable=True)
    rol_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rol.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    rol: Mapped[Optional["Rol"]] = relationship("Rol")
