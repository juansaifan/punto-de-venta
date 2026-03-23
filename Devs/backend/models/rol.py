"""Entidad Rol operativo."""
from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class Rol(Base):
    __tablename__ = "rol"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(64), unique=True)
    nombre: Mapped[str] = mapped_column(String(128))

    permisos: Mapped[List["Permiso"]] = relationship(
        "Permiso", secondary="rol_permiso", back_populates="roles"
    )
