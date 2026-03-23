"""Schemas Pydantic para el submódulo Tesorería / Cuentas Corrientes de Clientes."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MovimientoCuentaCorrienteBase(BaseModel):
    """Datos base de un movimiento de cuenta corriente."""

    tipo: str = Field(
        ...,
        description="Tipo de movimiento: VENTA, PAGO, AJUSTE, NOTA_CREDITO, NOTA_DEBITO",
        min_length=1,
        max_length=16,
    )
    monto: float = Field(..., description="Monto del movimiento (positivo para todos los tipos; AJUSTE puede ser negativo)")
    descripcion: Optional[str] = Field(None, description="Descripción opcional")


class MovimientoCuentaCorrienteCreate(MovimientoCuentaCorrienteBase):
    """Payload para registrar un movimiento de cuenta corriente."""

    pass


class MovimientoCuentaCorrienteResponse(MovimientoCuentaCorrienteBase):
    """Respuesta de movimiento de cuenta corriente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cuenta_id: int
    fecha: str


class CuentaCorrienteResumenResponse(BaseModel):
    """Resumen de cuenta corriente por cliente."""

    cliente_id: int
    saldo: float
    limite_credito: Optional[float] = None
    disponible: Optional[float] = None

