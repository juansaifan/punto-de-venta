# Modelos de dominio (entidades)
# Importar aquí los que deban exponerse para registro en Base.metadata
from backend.models.persona import Persona
from backend.models.usuario import Usuario
from backend.models.rol import Rol
from backend.models.producto import Producto, CategoriaProducto
from backend.models.venta import Venta, ItemVenta
from backend.models.compra import Compra, ItemCompra
from backend.models.caja import Caja, MovimientoCaja
from backend.models.inventario import Lote, Stock, MovimientoInventario
from backend.models.finanzas import CuentaFinanciera, TransaccionFinanciera
from backend.models.configuracion import Empresa, MedioPago, ParametroSistema, Permiso, Sucursal
from backend.models.integracion import IntegracionConfig, IntegracionLog
from backend.models.eventos import EventoSistemaLog
from backend.models.solicitud_compra import SolicitudCompra, ItemSolicitudCompra
from backend.models.pagos import PaymentTransaction
from backend.models.pesables import PesableItem, EstadoPesableItem
from backend.models.operaciones_comerciales import (
    OperacionComercial,
    OperacionComercialDetalle,
    TipoOperacionComercial,
    EstadoOperacionComercial,
)

__all__ = [
    "Persona", "Usuario", "Rol",
    "Producto", "CategoriaProducto",
    "Venta", "ItemVenta",
    "Compra", "ItemCompra",
    "Caja", "MovimientoCaja",
    "Lote", "Stock", "MovimientoInventario",
    "CuentaFinanciera", "TransaccionFinanciera",
    "Empresa", "MedioPago", "ParametroSistema", "Permiso", "Sucursal",
    "IntegracionConfig", "IntegracionLog",
    "EventoSistemaLog",
    "SolicitudCompra", "ItemSolicitudCompra",
    "PaymentTransaction",
    "OperacionComercial",
    "OperacionComercialDetalle",
    "TipoOperacionComercial",
    "EstadoOperacionComercial",
    "PesableItem",
    "EstadoPesableItem",
]
