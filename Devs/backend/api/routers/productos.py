"""Endpoints REST para productos (dominio Inventario)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas.producto import ProductoCreate, ProductoUpdate, ProductoResponse
from backend.services import productos as svc_productos

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("", response_model=list[ProductoResponse])
def listar_productos(
    db: Session = Depends(get_db),
    activo_only: bool = Query(True, description="Solo productos activos"),
    pesable: bool | None = Query(None, description="Filtrar por pesable: true=solo pesables, false=no pesables"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista productos con paginación. Filtro opcional ?pesable=true|false."""
    items = svc_productos.listar_productos(
        db, activo_only=activo_only, pesable_only=pesable, limite=limite, offset=offset
    )
    return list(items)


@router.get("/por-sku/{sku}", response_model=ProductoResponse)
def obtener_producto_por_sku(sku: str, db: Session = Depends(get_db)):
    """Obtiene un producto por SKU."""
    producto = svc_productos.obtener_producto_por_sku(db, sku)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    """Obtiene un producto por ID."""
    producto = svc_productos.obtener_producto_por_id(db, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("", response_model=ProductoResponse, status_code=201)
def crear_producto(payload: ProductoCreate, db: Session = Depends(get_db)):
    """Crea un nuevo producto."""
    existente = svc_productos.obtener_producto_por_sku(db, payload.sku)
    if existente is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un producto con SKU '{payload.sku}'",
        )
    producto = svc_productos.crear_producto(
        db,
        sku=payload.sku,
        nombre=payload.nombre,
        precio_venta=payload.precio_venta,
        costo_actual=payload.costo_actual,
        descripcion=payload.descripcion,
        codigo_barra=payload.codigo_barra,
        stock_minimo=payload.stock_minimo,
        punto_reorden=payload.punto_reorden,
        activo=payload.activo,
        categoria_id=payload.categoria_id,
        subcategoria_id=payload.subcategoria_id,
    )
    db.refresh(producto)
    return producto


@router.patch("/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(
    producto_id: int,
    payload: ProductoUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza un producto existente."""
    try:
        producto = svc_productos.actualizar_producto(
            db,
            producto_id,
            nombre=payload.nombre,
            descripcion=payload.descripcion,
            precio_venta=payload.precio_venta,
            costo_actual=payload.costo_actual,
            codigo_barra=payload.codigo_barra,
            stock_minimo=payload.stock_minimo,
            punto_reorden=payload.punto_reorden,
            activo=payload.activo,
            categoria_id=payload.categoria_id,
            subcategoria_id=payload.subcategoria_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.refresh(producto)
    return producto
