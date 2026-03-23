"""Schemas Pydantic para el recurso Producto."""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ProductoBase(BaseModel):
    """Campos base de producto."""
    sku: str = Field(..., min_length=1, max_length=64)
    nombre: str = Field(..., min_length=1, max_length=256)
    descripcion: Optional[str] = Field(None, max_length=2000)
    codigo_barra: Optional[str] = Field(None, max_length=32)
    precio_venta: Decimal = Field(default=Decimal("0"), ge=0)
    costo_actual: Decimal = Field(default=Decimal("0"), ge=0, description="Costo de compra/fabricación del producto (usado para calcular margen)")
    stock_minimo: Decimal = Field(default=Decimal("0"), ge=0)
    punto_reorden: Decimal = Field(default=Decimal("0"), ge=0, description="Nivel de stock que dispara solicitud de reposición/compra")
    activo: bool = True


class ProductoCreate(ProductoBase):
    """Payload para crear un producto."""
    categoria_id: Optional[int] = Field(None, ge=1, description="Categoría del producto")
    subcategoria_id: Optional[int] = Field(None, ge=1, description="Subcategoría del producto")


class ProductoUpdate(BaseModel):
    """Payload para actualizar un producto (todos opcionales)."""
    nombre: Optional[str] = Field(None, min_length=1, max_length=256)
    descripcion: Optional[str] = Field(None, max_length=2000)
    codigo_barra: Optional[str] = Field(None, max_length=32)
    precio_venta: Optional[Decimal] = Field(None, ge=0)
    costo_actual: Optional[Decimal] = Field(None, ge=0, description="Costo de compra/fabricación del producto")
    stock_minimo: Optional[Decimal] = Field(None, ge=0)
    punto_reorden: Optional[Decimal] = Field(None, ge=0, description="Nivel de stock que dispara solicitud de reposición/compra")
    activo: Optional[bool] = None
    categoria_id: Optional[int] = Field(None, ge=1, description="Categoría del producto (inventario).")
    subcategoria_id: Optional[int] = Field(None, ge=1, description="Subcategoría del producto (inventario).")


class ProductoResponse(ProductoBase):
    """Respuesta con datos de producto."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_producto: str = "inventariable"
    tipo_medicion: str = "unidad"
    pesable: bool = False
    plu: Optional[int] = None
    punto_reorden: Decimal = Decimal("0")
