"""Schemas Pydantic para inventario (stock y movimientos)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class IngresarStockRequest(BaseModel):
    """Payload para ingresar stock a un producto."""
    producto_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=0)
    ubicacion: Optional[str] = Field(None, description="Ubicación de stock (GONDOLA/DEPOSITO). Por defecto GONDOLA.")


class StockResponse(BaseModel):
    """Cantidad en stock para un producto (ubicación por defecto)."""
    producto_id: int
    cantidad: Decimal


class MovimientoInventarioResponse(BaseModel):
    """Un movimiento de inventario (entrada/salida/ajuste)."""
    id: int
    producto_id: int
    tipo: str
    cantidad: Decimal
    ubicacion: Optional[str] = None
    fecha: datetime
    referencia: Optional[str] = None

    model_config = {"from_attributes": True}


class CategoriaProductoResponse(BaseModel):
    """Categoría de producto (inventario, docs Módulo 5 §3)."""
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    categoria_padre_id: Optional[int] = None

    model_config = {"from_attributes": True}


class TransferirStockRequest(BaseModel):
    """Payload para transferir stock entre ubicaciones (p.ej. DEPOSITO -> GONDOLA)."""

    producto_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=0)
    origen: str = Field(..., min_length=1, max_length=32, description="Ubicación origen (GONDOLA/DEPOSITO)")
    destino: str = Field(..., min_length=1, max_length=32, description="Ubicación destino (GONDOLA/DEPOSITO)")
    referencia: Optional[str] = Field(None, max_length=256)


class TransferirStockResponse(BaseModel):
    """Respuesta con los dos movimientos (salida/entrada) generados por la transferencia."""

    salida: MovimientoInventarioResponse
    entrada: MovimientoInventarioResponse


class RevertirMovimientoInventarioRequest(BaseModel):
    """Payload opcional para registrar una reversión de un movimiento existente."""

    referencia: Optional[str] = Field(None, max_length=256)


class DistribucionStockItemResponse(BaseModel):
    """Fila para la tabla de distribución del inventario (producto + ubicación + cantidad)."""

    producto_id: int
    ubicacion: str
    cantidad: Decimal


class ConteoManualItemRequest(BaseModel):
    """Ítem contado para conteo manual de inventario."""

    producto_id: int = Field(..., gt=0)
    ubicacion: str = Field(..., min_length=1, max_length=32, description="Ubicación (GONDOLA/DEPOSITO)")
    cantidad_contada: Decimal = Field(..., ge=0)


class ConteoManualRequest(BaseModel):
    """Payload para conteo manual de inventario (ajusta stock y registra movimientos AJUSTE)."""

    items: list[ConteoManualItemRequest] = Field(..., min_length=1)
    referencia: Optional[str] = Field(None, max_length=256)


class ConteoManualResponse(BaseModel):
    movimientos: list[MovimientoInventarioResponse]


class ConteoManualChecklistItemResponse(BaseModel):
    """Item para checklist de conteo manual."""

    producto_id: int
    sku: str
    nombre: str
    ubicacion: str
    stock_actual: Decimal
    cantidad_contada: Optional[Decimal] = None
    verificado: bool = False


class MovimientoManualRequest(BaseModel):
    """Payload para registrar un movimiento de inventario manual (ajuste/merma/etc.)."""

    producto_id: int = Field(..., gt=0)
    tipo: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Tipo de movimiento (ej: COMPRA, VENTA, DEVOLUCION, TRANSFERENCIA, AJUSTE, MERMA, CONSUMO_INTERNO).",
    )
    cantidad: Decimal = Field(..., description="Cantidad con signo (+ suma stock, - descuenta).")
    ubicacion: str = Field(..., min_length=1, max_length=32, description="Ubicación (GONDOLA/DEPOSITO)")
    referencia: Optional[str] = Field(None, max_length=256)


