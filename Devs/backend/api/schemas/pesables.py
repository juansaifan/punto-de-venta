"""Schemas Pydantic del submódulo Pesables (Módulo 2)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Cálculo bidireccional
# ---------------------------------------------------------------------------

class CalcularPesableRequest(BaseModel):
    """Solicitud de cálculo bidireccional peso ↔ precio."""
    precio_unitario: Decimal = Field(..., gt=0, description="Precio por kg del producto")
    peso: Optional[Decimal] = Field(None, gt=0, description="Peso en kg (se calcula precio si se provee)")
    precio: Optional[Decimal] = Field(None, gt=0, description="Precio total (se calcula peso si se provee)")


class CalcularPesableResponse(BaseModel):
    """Resultado del cálculo bidireccional."""
    peso: Decimal
    precio_unitario: Decimal
    precio_total: Decimal


# ---------------------------------------------------------------------------
# Preparar ítem(s) pesable(s)
# ---------------------------------------------------------------------------

class PrepararItemRequest(BaseModel):
    """Solicitud para preparar un ítem pesable."""
    producto_id: int = Field(..., gt=0)
    peso: Optional[Decimal] = Field(None, gt=0, description="Peso en kg")
    precio: Optional[Decimal] = Field(None, gt=0, description="Precio total deseado")


class PrepararItemsBatchRequest(BaseModel):
    """Solicitud batch para preparar múltiples ítems."""
    items: list[PrepararItemRequest] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Respuesta de ítem pesable
# ---------------------------------------------------------------------------

class PesableItemResponse(BaseModel):
    """Datos completos de un PesableItem."""
    id: int
    producto_id: int
    nombre_producto: str
    plu: int
    peso: Decimal
    precio_unitario: Decimal
    precio_total: Decimal
    barcode: str
    estado: str
    creado_en: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Etiquetas
# ---------------------------------------------------------------------------

class EtiquetaItemResponse(BaseModel):
    """Data necesaria para imprimir una etiqueta."""
    item_id: int
    producto_id: int
    nombre_producto: str
    plu: int
    peso: float
    precio_unitario: float
    precio_total: float
    barcode: str
    estado: str


class GenerarEtiquetasRequest(BaseModel):
    """IDs de los ítems a etiquetar (batch)."""
    item_ids: list[int] = Field(..., min_length=1)


class GenerarEtiquetasResponse(BaseModel):
    etiquetas: list[EtiquetaItemResponse]


# ---------------------------------------------------------------------------
# Actualizar producto como pesable
# ---------------------------------------------------------------------------

class HabilitarPesableRequest(BaseModel):
    """Habilita un producto como pesable y le asigna un PLU."""
    plu: int = Field(..., ge=1, le=99999, description="PLU único de 5 dígitos para el producto pesable")
