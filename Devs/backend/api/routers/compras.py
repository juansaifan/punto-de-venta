"""Endpoints REST para Compras/Proveedores."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import compras as svc_compras
from backend.services import inventario as svc_inventario
from backend.services import tesoreria as svc_tesoreria
from backend.services import finanzas as svc_finanzas

router = APIRouter(prefix="/compras", tags=["compras"])


@router.post("", status_code=201)
def crear_compra(body: dict, db: Session = Depends(get_db)):
    """
    Crea una compra confirmada con sus ítems.

    Body esperado:
    - proveedor_id: int
    - items: lista de objetos con {producto_id, cantidad, costo_unitario}
    """
    proveedor_id = body.get("proveedor_id")
    items = body.get("items") or []
    if proveedor_id is None:
        raise HTTPException(status_code=422, detail="proveedor_id es obligatorio")
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=422, detail="items debe ser una lista no vacía")
    try:
        compra = svc_compras.crear_compra(
            db,
            proveedor_id=int(proveedor_id),
            items=items,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # Integración con Inventario: ingresar stock por cada ítem de la compra
    try:
        for item in items:
            svc_inventario.ingresar_stock(
                db,
                producto_id=int(item["producto_id"]),
                cantidad=item["cantidad"],
                tipo="COMPRA",
                referencia=f"Compra #{compra.id}",
            )
    except ValueError as e:
        # Si falla el ingreso de stock, devolvemos 400 para no dejar el sistema en estado inconsistente
        raise HTTPException(status_code=400, detail=str(e))

    # Integración con Finanzas: registrar gasto en cuenta principal (si existe)
    # Estrategia simple: usar la primera cuenta financiera disponible como cuenta de compras.
    try:
        cuentas = svc_finanzas.listar_cuentas(db, limite=1, offset=0)
        if cuentas:
            cuenta = cuentas[0]
            svc_finanzas.registrar_transaccion(
                db,
                cuenta_id=cuenta.id,
                tipo="gasto",
                monto=compra.total,
                descripcion=f"Compra #{compra.id} a proveedor {compra.proveedor_id}",
            )
    except ValueError:
        # No bloqueamos la compra si falla la parte financiera
        pass

    return {
        "id": compra.id,
        "proveedor_id": compra.proveedor_id,
        "fecha": compra.fecha.isoformat(),
        "total": float(compra.total),
        "estado": compra.estado,
    }


@router.get("")
def listar_compras(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista compras ordenadas por fecha descendente."""
    compras = svc_compras.listar_compras(db, limite=limite, offset=offset)
    return [
        {
            "id": c.id,
            "proveedor_id": c.proveedor_id,
            "fecha": c.fecha.isoformat(),
            "total": float(c.total),
            "estado": c.estado,
        }
        for c in compras
    ]

