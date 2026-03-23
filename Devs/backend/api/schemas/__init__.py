# Schemas Pydantic para la API
from backend.api.schemas.producto import (
    ProductoCreate,
    ProductoUpdate,
    ProductoResponse,
)
from backend.api.schemas.persona import (
    PersonaCreate,
    PersonaUpdate,
    PersonaResponse,
)
from backend.api.schemas.venta import (
    ItemVentaCrear,
    VentaRegistrarRequest,
    VentaResponse,
    VentaRegistradaResponse,
)
from backend.api.schemas.operaciones_comerciales import (
    DevolucionCrearRequest,
    DevolucionResponse,
    NotaCreditoCrearRequest,
    NotaCreditoResponse,
    AnulacionCrearRequest,
    AnulacionResponse,
    CambioProductoCrearRequest,
    CambioProductoResponse,
    NotaDebitoCrearRequest,
    NotaDebitoResponse,
    CreditoCuentaCorrienteCrearRequest,
    CreditoCuentaCorrienteResponse,
)

__all__ = [
    "ProductoCreate", "ProductoUpdate", "ProductoResponse",
    "PersonaCreate", "PersonaUpdate", "PersonaResponse",
    "ItemVentaCrear", "VentaRegistrarRequest", "VentaResponse", "VentaRegistradaResponse",
    "DevolucionCrearRequest",
    "DevolucionResponse",
    "NotaCreditoCrearRequest",
    "NotaCreditoResponse",
    "AnulacionCrearRequest",
    "AnulacionResponse",
    "CambioProductoCrearRequest",
    "CambioProductoResponse",
    "NotaDebitoCrearRequest",
    "NotaDebitoResponse",
    "CreditoCuentaCorrienteCrearRequest",
    "CreditoCuentaCorrienteResponse",
]
