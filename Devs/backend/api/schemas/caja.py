"""Schemas Pydantic para Tesorería (caja)."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class MovimientoCajaCreate(BaseModel):
    """Payload para registrar un movimiento de caja."""
    tipo: str = Field(..., min_length=1, max_length=32)
    monto: Decimal = Field(..., gt=0)
    referencia: Optional[str] = Field(None, max_length=256)
    medio_pago: str = Field(default="EFECTIVO", max_length=32)


class MovimientoCajaResponse(BaseModel):
    """Respuesta con un movimiento de caja."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    caja_id: int
    tipo: str
    monto: Decimal
    medio_pago: str
    fecha: datetime
    referencia: Optional[str] = None


class CajaAbrirRequest(BaseModel):
    """Payload para abrir caja."""
    saldo_inicial: Decimal = Field(default=Decimal("0"), ge=0)
    usuario_id: Optional[int] = Field(None, gt=0)


class CajaCerrarRequest(BaseModel):
    """Payload para cerrar caja."""
    saldo_final: Optional[Decimal] = Field(None, ge=0)
    supervisor_autorizado: bool = Field(
        default=False,
        description="Requerido si la configuración de caja no permite cerrar con diferencia y la diferencia es distinta de 0.",
    )


class CajaResponse(BaseModel):
    """Respuesta con datos de una caja."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime] = None
    saldo_inicial: Decimal
    saldo_final: Optional[Decimal] = None
    usuario_id: Optional[int] = None


class TicketPendienteResponse(BaseModel):
    """Ticket (venta) pendiente de cobro en modo TEU_OFF."""

    model_config = ConfigDict(from_attributes=True)

    venta_id: int
    numero_ticket: Optional[str] = None
    cliente_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    cliente_documento: Optional[str] = None
    total: Decimal
    creado_en: datetime
    estado: Optional[str] = None


class PagoCobroTicket(BaseModel):
    """Pago individual para el cobro de un ticket."""

    metodo_pago: str = Field(..., min_length=1, max_length=32)
    importe: Decimal = Field(..., gt=0)
    medio_pago: Optional[str] = Field(None, max_length=64)
    cobrador: Optional[str] = Field(None, max_length=128)


class CobrarTicketRequest(BaseModel):
    """Payload para cobrar un ticket pendiente."""

    pagos: List[PagoCobroTicket] = Field(..., min_length=1)
    observaciones: Optional[str] = Field(None, max_length=512)


class CobrarTicketResponse(BaseModel):
    """Respuesta mínima luego del cobro."""

    model_config = ConfigDict(from_attributes=True)

    venta_id: int
    numero_ticket: Optional[str] = None
    estado: Optional[str] = None
    metodo_pago: str
    total: Decimal
    caja_id: Optional[int] = None
