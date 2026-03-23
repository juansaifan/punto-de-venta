"""Schemas Pydantic para Operaciones Comerciales (Módulo 2 - POS).

Incluye:
- Devolución
- Nota de crédito
- Anulación de venta/pedido pendiente
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ItemDevolucionCrear(BaseModel):
    item_venta_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=0)


class DevolucionCrearRequest(BaseModel):
    venta_id: int = Field(..., gt=0)
    reintegro_tipo: str = Field(..., max_length=32, description="EFECTIVO | MEDIO_PAGO_ORIGINAL | CUENTA_CORRIENTE")
    reintegro_metodo_pago: Optional[str] = Field(None, max_length=32)
    motivo: Optional[str] = Field(None, max_length=256)
    items: List[ItemDevolucionCrear] = Field(..., min_length=1)


class DevolucionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venta_id: int
    tipo: str
    estado: str
    importe_total: Decimal
    motivo: Optional[str]
    creado_en: datetime


class NotaCreditoCrearRequest(BaseModel):
    venta_id: int = Field(..., gt=0)
    reintegro_tipo: str = Field(
        ...,
        max_length=32,
        description="EFECTIVO | MEDIO_PAGO_ORIGINAL | CUENTA_CORRIENTE",
    )
    reintegro_metodo_pago: Optional[str] = Field(None, max_length=32)
    importe: Decimal = Field(..., gt=0)
    motivo: Optional[str] = Field(None, max_length=256)


class NotaCreditoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venta_id: int
    tipo: str
    estado: str
    importe_total: Decimal
    motivo: Optional[str]
    creado_en: datetime


class AnulacionCrearRequest(BaseModel):
    venta_id: int = Field(..., gt=0)
    motivo: Optional[str] = Field(None, max_length=256)


class AnulacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venta_id: int
    tipo: str
    estado: str
    importe_total: Decimal
    motivo: Optional[str]
    creado_en: datetime


class ItemCambioProductoDevueltoCrear(BaseModel):
    item_venta_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=0)


class ItemCambioProductoNuevoCrear(BaseModel):
    producto_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=0)
    precio_unitario: Optional[Decimal] = Field(None, ge=0)


class CambioProductoCrearRequest(BaseModel):
    venta_id: int = Field(..., gt=0)
    items_devueltos: List[ItemCambioProductoDevueltoCrear] = Field(
        ..., min_length=1
    )
    items_nuevos: List[ItemCambioProductoNuevoCrear] = Field(..., min_length=1)
    reintegro_tipo_diferencia: str = Field(
        ...,
        max_length=32,
        description="EFECTIVO | MEDIO_PAGO_ORIGINAL | CUENTA_CORRIENTE",
    )
    reintegro_metodo_pago: Optional[str] = Field(None, max_length=32)
    motivo: Optional[str] = Field(None, max_length=256)


class CambioProductoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venta_id: int
    tipo: str
    estado: str
    importe_total: Decimal
    motivo: Optional[str]
    creado_en: datetime


class NotaDebitoCrearRequest(BaseModel):
    venta_id: int = Field(..., gt=0)
    reintegro_tipo: str = Field(
        ...,
        max_length=32,
        description="EFECTIVO | MEDIO_PAGO_ORIGINAL | CUENTA_CORRIENTE",
    )
    reintegro_metodo_pago: Optional[str] = Field(None, max_length=32)
    importe: Decimal = Field(..., gt=0)
    motivo: Optional[str] = Field(None, max_length=256)


class NotaDebitoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venta_id: int
    tipo: str
    estado: str
    importe_total: Decimal
    motivo: Optional[str]
    creado_en: datetime


class CreditoCuentaCorrienteCrearRequest(BaseModel):
    venta_id: int = Field(..., gt=0)
    importe: Decimal = Field(..., gt=0)
    motivo: Optional[str] = Field(None, max_length=256)


class CreditoCuentaCorrienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venta_id: int
    tipo: str
    estado: str
    importe_total: Decimal
    motivo: Optional[str]
    creado_en: datetime

