"""Schemas Pydantic para el dominio Personas (persona base + roles)."""
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class PersonaBase(BaseModel):
    """Campos base de persona."""
    nombre: str = Field(..., min_length=1, max_length=128)
    apellido: str = Field(..., min_length=1, max_length=128)
    documento: Optional[str] = Field(None, max_length=32)
    telefono: Optional[str] = Field(None, max_length=32)
    activo: bool = True


class PersonaCreate(PersonaBase):
    """Payload para crear una persona."""
    pass


class PersonaUpdate(BaseModel):
    """Payload para actualizar una persona (todos opcionales)."""
    nombre: Optional[str] = Field(None, min_length=1, max_length=128)
    apellido: Optional[str] = Field(None, min_length=1, max_length=128)
    documento: Optional[str] = Field(None, max_length=32)
    telefono: Optional[str] = Field(None, max_length=32)
    activo: Optional[bool] = None


class PersonaResponse(PersonaBase):
    """Respuesta con datos de persona."""
    model_config = ConfigDict(from_attributes=True)

    id: int


# Clientes ----------------------------------------------------------------------


class ClienteBase(BaseModel):
    """Campos de configuración de cliente."""
    segmento: Optional[str] = Field(
        None, description="Segmento de cliente (ocasional, frecuente, mayorista, etc.)"
    )
    condicion_pago: Optional[str] = Field(
        None, description="Condición de pago preferida (contado, 30 días, etc.)"
    )
    limite_credito: Optional[float] = Field(
        None, description="Límite de crédito en la moneda configurada"
    )
    estado: str = Field(
        "ACTIVO",
        description="Estado operativo del cliente (ACTIVO/INACTIVO/BLOQUEADO, etc.)",
    )
    observaciones: Optional[str] = Field(None, description="Notas internas")


class ClienteCreate(ClienteBase):
    """Payload para crear un cliente a partir de una persona existente."""
    persona_id: int = Field(..., ge=1)


class ClienteResponse(ClienteBase):
    """Respuesta de cliente con persona asociada."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    persona_id: int


class ClienteLookupResponse(BaseModel):
    """Respuesta para búsqueda/selección rápida de clientes (incluye datos de persona)."""

    cliente_id: int
    persona_id: int
    nombre: str
    apellido: str
    documento: Optional[str] = None
    telefono: Optional[str] = None
    limite_credito: Optional[float] = None
    estado: str


class ClienteUpdate(BaseModel):
    """Payload para actualizar un cliente (todos los campos opcionales)."""
    segmento: Optional[str] = Field(None, max_length=64)
    condicion_pago: Optional[str] = Field(None, max_length=64)
    limite_credito: Optional[float] = Field(None, ge=0)
    estado: Optional[str] = Field(None, max_length=32)
    observaciones: Optional[str] = None


class ClienteAltaRapidaCreate(BaseModel):
    """Crea persona + rol cliente en una sola llamada (pensado para POS)."""

    nombre: str = Field(..., min_length=1, max_length=128)
    apellido: str = Field(..., min_length=1, max_length=128)
    documento: Optional[str] = Field(None, max_length=32)
    telefono: Optional[str] = Field(None, max_length=32)
    segmento: Optional[str] = None
    condicion_pago: Optional[str] = None
    limite_credito: Optional[float] = None
    estado: str = "ACTIVO"
    observaciones: Optional[str] = None


# Proveedores -------------------------------------------------------------------


class ProveedorBase(BaseModel):
    """Campos de proveedor (condiciones comerciales)."""
    cuit: Optional[str] = Field(None, max_length=32)
    condiciones_comerciales: Optional[str] = Field(
        None, description="Resumen de condiciones comerciales"
    )
    condiciones_pago: Optional[str] = Field(None, description="Condiciones de pago")
    lista_precios: Optional[str] = Field(
        None, description="Identificador o descripción de lista de precios"
    )
    estado: str = Field("ACTIVO", description="Estado del proveedor")
    frecuencia_entrega: Optional[str] = Field(
        None, description="Frecuencia típica de entrega (semanal, mensual, etc.)"
    )
    minimo_compra: Optional[float] = Field(
        None, description="Monto mínimo de compra sugerido"
    )
    tiempo_estimado_entrega: Optional[str] = Field(
        None, description="Tiempo estimado de entrega"
    )
    observaciones: Optional[str] = Field(None, description="Notas internas")


class ProveedorCreate(ProveedorBase):
    """Payload para crear un proveedor a partir de una persona existente."""
    persona_id: int = Field(..., ge=1)


class ProveedorUpdate(BaseModel):
    """Payload para actualizar un proveedor (todos los campos opcionales)."""
    cuit: Optional[str] = Field(None, max_length=32)
    condiciones_comerciales: Optional[str] = None
    condiciones_pago: Optional[str] = None
    lista_precios: Optional[str] = None
    estado: Optional[str] = Field(None, max_length=32)
    frecuencia_entrega: Optional[str] = None
    minimo_compra: Optional[float] = Field(None, ge=0)
    tiempo_estimado_entrega: Optional[str] = None
    observaciones: Optional[str] = None


class ProveedorResponse(ProveedorBase):
    """Respuesta de proveedor con persona asociada."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    persona_id: int


# Empleados ---------------------------------------------------------------------


class EmpleadoBase(BaseModel):
    """Datos básicos de empleado."""
    documento: Optional[str] = Field(None, max_length=32)
    cargo: Optional[str] = Field(None, max_length=64)
    estado: str = Field("ACTIVO", description="Estado del empleado")


class EmpleadoCreate(EmpleadoBase):
    """Payload para crear un empleado a partir de una persona existente."""
    persona_id: int = Field(..., ge=1)


class EmpleadoUpdate(BaseModel):
    """Payload para actualizar un empleado (todos los campos opcionales)."""
    documento: Optional[str] = Field(None, max_length=32)
    cargo: Optional[str] = Field(None, max_length=64)
    estado: Optional[str] = Field(None, max_length=32)


class EmpleadoResponse(EmpleadoBase):
    """Respuesta de empleado con persona asociada."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    persona_id: int


# Contactos ---------------------------------------------------------------------


class ContactoBase(BaseModel):
    """Datos de contacto asociado a una persona."""
    nombre: str = Field(..., min_length=1, max_length=128)
    cargo: Optional[str] = Field(None, max_length=64)
    telefono: Optional[str] = Field(None, max_length=32)
    email: Optional[str] = Field(None, max_length=128)
    observaciones: Optional[str] = Field(None)


class ContactoCreate(ContactoBase):
    """Payload para crear un contacto asociado a una persona."""
    persona_id: int = Field(..., ge=1)


class ContactoResponse(ContactoBase):
    """Respuesta de contacto con referencia a persona."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    persona_id: int



