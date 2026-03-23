"""Entidades del dominio de productos."""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class TipoProducto(str, Enum):
    INVENTARIABLE = "inventariable"
    NO_INVENTARIABLE = "no_inventariable"


class TipoMedicion(str, Enum):
    UNIDAD = "unidad"
    PESO = "peso"


class CategoriaProducto(Base):
    __tablename__ = "categoria_producto"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(128))
    descripcion: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    categoria_padre_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categoria_producto.id"), nullable=True
    )

    subcategorias: Mapped[List["CategoriaProducto"]] = relationship(
        "CategoriaProducto", back_populates="categoria_padre"
    )
    categoria_padre: Mapped[Optional["CategoriaProducto"]] = relationship(
        "CategoriaProducto", remote_side="CategoriaProducto.id", back_populates="subcategorias"
    )
    productos: Mapped[List["Producto"]] = relationship(
        "Producto", foreign_keys="Producto.categoria_id", back_populates="categoria"
    )


class Producto(Base):
    __tablename__ = "producto"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    codigo_barra: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(256))
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    categoria_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categoria_producto.id"), nullable=True)
    subcategoria_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categoria_producto.id"), nullable=True)
    tipo_producto: Mapped[str] = mapped_column(String(32), default=TipoProducto.INVENTARIABLE.value)
    tipo_medicion: Mapped[str] = mapped_column(String(16), default=TipoMedicion.UNIDAD.value)
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    costo_actual: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    punto_reorden: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    categoria_fiscal: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    proveedor: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Pesables (Módulo 2 – submódulo Pesables)
    pesable: Mapped[bool] = mapped_column(Boolean, default=False, doc="True si el precio depende del peso")
    plu: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, doc="PLU 5 dígitos (solo pesables)")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    actualizado_en: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    categoria: Mapped[Optional["CategoriaProducto"]] = relationship(
        "CategoriaProducto", foreign_keys="Producto.categoria_id", back_populates="productos"
    )
