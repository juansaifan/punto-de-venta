"""Router del submódulo Pesables (Módulo 2 – Punto de Venta).

Endpoints:
  POST   /api/pesables/calcular                   — cálculo bidireccional peso↔precio
  POST   /api/pesables/items                      — preparar ítem pesable
  POST   /api/pesables/items/batch                — preparar múltiples ítems
  GET    /api/pesables/items                      — listar ítems por estado/producto
  GET    /api/pesables/items/{item_id}            — obtener ítem por id
  PATCH  /api/pesables/items/{item_id}/imprimir   — marcar como impreso
  PATCH  /api/pesables/items/{item_id}/usar       — marcar como usado
  POST   /api/pesables/etiquetas                  — generar datos de etiquetas (batch)
  PATCH  /api/productos/{producto_id}/pesable     — habilitar producto como pesable
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import pesables as svc_pesables
from backend.api.schemas.pesables import (
    CalcularPesableRequest,
    CalcularPesableResponse,
    EtiquetaItemResponse,
    GenerarEtiquetasRequest,
    GenerarEtiquetasResponse,
    HabilitarPesableRequest,
    PesableItemResponse,
    PrepararItemRequest,
    PrepararItemsBatchRequest,
)

router = APIRouter(tags=["Pesables"])


# ---------------------------------------------------------------------------
# Cálculo bidireccional
# ---------------------------------------------------------------------------

@router.post("/pesables/calcular", response_model=CalcularPesableResponse)
def calcular_pesable(body: CalcularPesableRequest):
    """Calcula peso ↔ precio para un producto pesable sin persistir datos."""
    if body.peso is None and body.precio is None:
        raise HTTPException(status_code=400, detail="Proporcione 'peso' o 'precio'")
    if body.peso is not None and body.precio is not None:
        raise HTTPException(status_code=400, detail="Proporcione solo 'peso' o solo 'precio', no ambos")

    precio_unitario = body.precio_unitario
    if body.peso is not None:
        precio_total = svc_pesables.calcular_precio_por_peso(body.peso, precio_unitario)
        return CalcularPesableResponse(
            peso=body.peso,
            precio_unitario=precio_unitario,
            precio_total=precio_total,
        )
    else:
        try:
            peso = svc_pesables.calcular_peso_por_precio(body.precio, precio_unitario)  # type: ignore[arg-type]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        precio_total = svc_pesables.calcular_precio_por_peso(peso, precio_unitario)
        return CalcularPesableResponse(
            peso=peso,
            precio_unitario=precio_unitario,
            precio_total=precio_total,
        )


# ---------------------------------------------------------------------------
# Preparar ítems
# ---------------------------------------------------------------------------

@router.post("/pesables/items", response_model=PesableItemResponse, status_code=201)
def preparar_item(body: PrepararItemRequest, db: Session = Depends(get_db)):
    """Prepara un ítem pesable: calcula precio/peso y genera barcode EAN-13."""
    try:
        return svc_pesables.preparar_item(
            db,
            producto_id=body.producto_id,
            peso=body.peso,
            precio=body.precio,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pesables/items/batch", response_model=list[PesableItemResponse], status_code=201)
def preparar_items_batch(body: PrepararItemsBatchRequest, db: Session = Depends(get_db)):
    """Prepara múltiples ítems pesables en lote."""
    try:
        items = svc_pesables.preparar_items_batch(
            db,
            [it.model_dump() for it in body.items],
        )
        return list(items)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Listar y obtener ítems
# ---------------------------------------------------------------------------

@router.get("/pesables/items", response_model=list[PesableItemResponse])
def listar_items(
    db: Session = Depends(get_db),
    estado: Optional[str] = Query(None, description="Filtrar por estado: pending, printed, used"),
    producto_id: Optional[int] = Query(None, description="Filtrar por producto"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista ítems pesables con filtros opcionales."""
    return list(svc_pesables.listar_items(db, estado=estado, producto_id=producto_id, limite=limite, offset=offset))


@router.get("/pesables/items/{item_id}", response_model=PesableItemResponse)
def obtener_item(item_id: int, db: Session = Depends(get_db)):
    """Obtiene un ítem pesable por ID."""
    item = svc_pesables.obtener_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"PesableItem {item_id} no encontrado")
    return item


# ---------------------------------------------------------------------------
# Cambios de estado
# ---------------------------------------------------------------------------

@router.patch("/pesables/items/{item_id}/imprimir", response_model=PesableItemResponse)
def marcar_impreso(item_id: int, db: Session = Depends(get_db)):
    """Marca el ítem como impreso (pending → printed)."""
    try:
        return svc_pesables.marcar_item_impreso(db, item_id)
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.patch("/pesables/items/{item_id}/usar", response_model=PesableItemResponse)
def marcar_usado(item_id: int, db: Session = Depends(get_db)):
    """Marca el ítem como usado/vendido (→ used)."""
    try:
        return svc_pesables.marcar_item_usado(db, item_id)
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


# ---------------------------------------------------------------------------
# Etiquetas (batch)
# ---------------------------------------------------------------------------

@router.post("/pesables/etiquetas", response_model=GenerarEtiquetasResponse)
def generar_etiquetas(body: GenerarEtiquetasRequest, db: Session = Depends(get_db)):
    """Genera datos de etiquetas para impresión batch.

    Cambia el estado de los ítems de pending → printed automáticamente.
    """
    try:
        etiquetas = svc_pesables.generar_datos_etiquetas(db, body.item_ids)
        return GenerarEtiquetasResponse(
            etiquetas=[EtiquetaItemResponse(**e) for e in etiquetas]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Habilitar producto como pesable
# ---------------------------------------------------------------------------

@router.get("/pesables/productos")
def listar_productos_pesables(
    db: Session = Depends(get_db),
    activo_only: bool = Query(True, description="Solo productos activos"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Lista los productos habilitados como pesables (con PLU asignado).
    Flujo §3 docs: el operador selecciona el producto antes de ingresar peso/precio.
    Devuelve: id, sku, nombre, precio_venta, plu, activo.
    """
    return svc_pesables.listar_productos_pesables(
        db, activo_only=activo_only, limite=limite, offset=offset
    )


@router.delete("/pesables/items/{item_id}", status_code=204)
def eliminar_item_pesable(item_id: int, db: Session = Depends(get_db)):
    """
    Elimina un ítem pesable en estado 'pending'.
    Permite corregir errores antes de generar la etiqueta.
    No se puede eliminar si ya está impreso (printed) o vendido (used).
    """
    try:
        svc_pesables.eliminar_item_pendiente(db, item_id)
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.get("/pesables/resolver-barcode")
def resolver_barcode(
    barcode: str = Query(..., description="EAN-13 del ítem pesable"),
    db: Session = Depends(get_db),
):
    """
    Resuelve un barcode EAN-13 de pesable para previsualización en POS.
    Devuelve: item_id, producto_id, nombre_producto, peso, precio_unitario, precio_total, estado.
    Útil para que el cajero confirme datos antes de agregar a la venta.
    """
    from backend.services import ventas as svc_ventas
    try:
        return svc_ventas.resolver_barcode_pesable(db, barcode=barcode)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/pesables/productos/{producto_id}/habilitar", response_model=dict)
def habilitar_producto_pesable(
    producto_id: int,
    body: HabilitarPesableRequest,
    db: Session = Depends(get_db),
):
    """Habilita un producto como pesable y le asigna un PLU único (1–99999)."""
    from backend.models.producto import Producto
    from sqlalchemy import select

    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Verificar que el PLU no esté en uso por otro producto
    existente = db.scalars(
        select(Producto).where(Producto.plu == body.plu, Producto.id != producto_id)
    ).first()
    if existente is not None:
        raise HTTPException(
            status_code=409,
            detail=f"PLU {body.plu} ya está asignado al producto '{existente.nombre}' (id={existente.id})",
        )

    producto.pesable = True
    producto.plu = body.plu
    db.add(producto)
    db.flush()
    db.refresh(producto)
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "pesable": producto.pesable,
        "plu": producto.plu,
    }
