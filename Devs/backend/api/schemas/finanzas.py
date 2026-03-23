from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CuentaFinancieraResponse(BaseModel):
    id: int
    nombre: str
    tipo: str
    saldo: float
    estado: str = "activa"
    observaciones: Optional[str] = None

    model_config = {"from_attributes": True}


class TransaccionFinancieraResponse(BaseModel):
    id: int
    cuenta_id: int
    tipo: Literal["ingreso", "gasto"]
    monto: float
    descripcion: Optional[str] = None
    conciliada: bool = False
    fecha_conciliacion: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CrearCuentaRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=128)
    tipo: str = Field(default="GENERAL", max_length=32)
    saldo_inicial: Decimal = Field(default=Decimal("0"), ge=0)
    observaciones: Optional[str] = None


class ActualizarCuentaRequest(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=128)
    tipo: Optional[str] = Field(default=None, max_length=32)
    estado: Optional[Literal["activa", "inactiva"]] = None
    observaciones: Optional[str] = None


class TransferirEntreCuentasRequest(BaseModel):
    cuenta_origen_id: int
    cuenta_destino_id: int
    importe: Decimal = Field(..., gt=0)
    motivo: Optional[str] = Field(default=None, max_length=256)


class TransferirEntreCuentasResponse(BaseModel):
    cuenta_origen_id: int
    cuenta_destino_id: int
    importe: float
    motivo: Optional[str] = None
    transaccion_egreso_id: int
    transaccion_ingreso_id: int

