# Servicios del dominio Inventario (productos)
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.producto import CategoriaProducto, Producto, TipoProducto, TipoMedicion


def listar_productos(
    sesion: Session,
    *,
    activo_only: bool = True,
    pesable_only: bool | None = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Producto]:
    """Lista productos con paginación. Filtros opcionales: activo, pesable."""
    q = select(Producto).order_by(Producto.id)
    if activo_only:
        q = q.where(Producto.activo.is_(True))
    if pesable_only is True:
        q = q.where(Producto.pesable.is_(True)).where(Producto.plu.isnot(None))
    elif pesable_only is False:
        q = q.where(Producto.pesable.is_(False))
    q = q.limit(limite).offset(offset)
    return sesion.scalars(q).all()


def obtener_producto_por_id(sesion: Session, producto_id: int) -> Optional[Producto]:
    """Obtiene un producto por su ID."""
    return sesion.get(Producto, producto_id)


def obtener_producto_por_sku(sesion: Session, sku: str) -> Optional[Producto]:
    """Obtiene un producto por SKU."""
    return sesion.scalars(select(Producto).where(Producto.sku == sku)).first()


def crear_producto(
    sesion: Session,
    *,
    sku: str,
    nombre: str,
    precio_venta: Decimal | float = 0,
    costo_actual: Decimal | float = 0,
    descripcion: Optional[str] = None,
    codigo_barra: Optional[str] = None,
    stock_minimo: Decimal | float = 0,
    punto_reorden: Decimal | float = 0,
    activo: bool = True,
    categoria_id: Optional[int] = None,
    subcategoria_id: Optional[int] = None,
) -> Producto:
    """Crea un nuevo producto."""
    producto = Producto(
        sku=sku.strip(),
        nombre=nombre.strip(),
        descripcion=descripcion.strip() if descripcion else None,
        codigo_barra=codigo_barra.strip() if codigo_barra else None,
        precio_venta=Decimal(str(precio_venta)),
        costo_actual=Decimal(str(costo_actual)),
        stock_minimo=Decimal(str(stock_minimo)),
        punto_reorden=Decimal(str(punto_reorden)),
        activo=activo,
        tipo_producto=TipoProducto.INVENTARIABLE.value,
        tipo_medicion=TipoMedicion.UNIDAD.value,
        categoria_id=categoria_id,
        subcategoria_id=subcategoria_id,
    )
    sesion.add(producto)
    sesion.flush()
    sesion.refresh(producto)
    return producto


def actualizar_producto(
    sesion: Session,
    producto_id: int,
    *,
    nombre: Optional[str] = None,
    descripcion: Optional[str] = None,
    precio_venta: Optional[Decimal | float] = None,
    costo_actual: Optional[Decimal | float] = None,
    codigo_barra: Optional[str] = None,
    stock_minimo: Optional[Decimal | float] = None,
    punto_reorden: Optional[Decimal | float] = None,
    activo: Optional[bool] = None,
    categoria_id: Optional[int] = None,
    subcategoria_id: Optional[int] = None,
) -> Optional[Producto]:
    """Actualiza un producto existente."""
    producto = sesion.get(Producto, producto_id)
    if producto is None:
        return None
    if nombre is not None:
        producto.nombre = nombre.strip()
    if descripcion is not None:
        producto.descripcion = descripcion.strip() if descripcion else None
    if precio_venta is not None:
        producto.precio_venta = Decimal(str(precio_venta))
    if costo_actual is not None:
        producto.costo_actual = Decimal(str(costo_actual))
    if codigo_barra is not None:
        producto.codigo_barra = codigo_barra.strip() if codigo_barra else None
    if stock_minimo is not None:
        producto.stock_minimo = Decimal(str(stock_minimo))
    if punto_reorden is not None:
        producto.punto_reorden = Decimal(str(punto_reorden))
    if activo is not None:
        producto.activo = activo
    if categoria_id is not None:
        categoria = sesion.get(CategoriaProducto, categoria_id)
        if categoria is None:
            raise ValueError("Categoría no encontrada")
        producto.categoria_id = categoria_id
    if subcategoria_id is not None:
        subcat = sesion.get(CategoriaProducto, subcategoria_id)
        if subcat is None:
            raise ValueError("Subcategoría no encontrada")
        producto.subcategoria_id = subcategoria_id
    sesion.flush()
    sesion.refresh(producto)
    return producto
