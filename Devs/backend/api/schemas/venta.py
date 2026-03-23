"""Schemas Pydantic para el recurso Venta."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ItemVentaCrear(BaseModel):
    """Payload para un ítem al registrar una venta."""
    producto_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=0)
    precio_unitario: Optional[Decimal] = Field(None, ge=0)


class VentaRegistrarRequest(BaseModel):
    """Payload para registrar una venta completa."""
    items: List[ItemVentaCrear] = Field(..., min_length=1)
    descuento: Decimal = Field(default=Decimal("0"), ge=0)
    # TEU_ON: POS + cobro inmediato (requiere método de pago)
    # TEU_OFF: vendedor genera ticket; caja cobra (método de pago se define en el cobro)
    modo_venta: str = Field(default="TEU_ON", max_length=16)
    metodo_pago: Optional[str] = Field(default=None, max_length=32)
    cliente_id: Optional[int] = Field(None, gt=0, description="ID de persona (cliente) asociado")


class ItemVentaResponse(BaseModel):
    """Una línea de venta en la respuesta."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    nombre_producto: str
    cantidad: Decimal
    precio_unitario: Decimal
    subtotal: Decimal


class VentaResponse(BaseModel):
    """Respuesta con datos de una venta."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_ticket: Optional[str] = None
    subtotal: Decimal
    descuento: Decimal
    impuesto: Decimal
    total: Decimal
    metodo_pago: str
    estado: Optional[str] = None
    creado_en: datetime
    caja_id: Optional[int] = None
    cliente_id: Optional[int] = None
    items: List[ItemVentaResponse] = []


class VentaRegistradaResponse(BaseModel):
    """Respuesta al registrar una venta (resumen)."""
    venta_id: int
    total: Decimal
    mensaje: str = "Venta registrada correctamente"
