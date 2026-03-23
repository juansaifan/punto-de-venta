"""Entidades del dominio Configuración (medios de pago, empresa, permisos; docs Módulo 9 §3, §6, §11)."""
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Numeric, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

# Tabla asociativa N:M entre Rol y Permiso (ROADMAP Fase 7: permisos)
rol_permiso = Table(
    "rol_permiso",
    Base.metadata,
    Column("rol_id", ForeignKey("rol.id"), primary_key=True),
    Column("permiso_id", ForeignKey("permiso.id"), primary_key=True),
)


# ID único usado para el registro singleton de datos de empresa
EMPRESA_ID = 1


class Empresa(Base):
    """
    Datos del negocio (singleton, id=EMPRESA_ID). Usado en comprobantes, reportes, integraciones fiscales.
    docs Módulo 9 §3.
    """
    __tablename__ = "empresa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    razon_social: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    cuit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    condicion_fiscal: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Sucursal(Base):
    """
    Sucursal del negocio (docs Módulo 9 §4). Se vincula con Inventario (ubicaciones/depósitos).
    """
    __tablename__ = "sucursal"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(128), nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)


class Permiso(Base):
    """
    Permiso operativo (niveles de acceso; docs Módulo 9 §11 Seguridad).
    codigo: identificador único (ej. ventas.crear, reportes.ver).
    """
    __tablename__ = "permiso"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(128), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    roles: Mapped[List["Rol"]] = relationship(
        "Rol", secondary=rol_permiso, back_populates="permisos"
    )


class MedioPago(Base):
    """
    Medio de pago aceptado por el negocio (efectivo, tarjeta, transferencia, etc.).
    codigo: identificador único usado en ventas/caja (ej. EFECTIVO, TARJETA_DEBITO).
    """
    __tablename__ = "medio_pago"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(128), nullable=False)
    activo: Mapped[bool] = mapped_column(default=True)
    comision: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    dias_acreditacion: Mapped[int] = mapped_column(default=0)


class ParametroSistema(Base):
    """
    Parámetros de sistema por clave (facturación, caja, etc.; docs Módulo 9 §5, §7).
    valor_json: objeto JSON con la configuración de la sección.
    """
    __tablename__ = "parametro_sistema"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    clave: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    valor_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
