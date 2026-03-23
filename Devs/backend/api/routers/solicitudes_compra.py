"""Endpoints REST para solicitudes de compra (abastecimiento)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import solicitudes_compra as svc_solicitudes
from backend.services import compras as svc_compras
from backend.services import inventario as svc_inventario
from backend.services import finanzas as svc_finanzas
from backend.models.producto import Producto


router = APIRouter(prefix="/inventario/solicitudes-compra", tags=["inventario"])


@router.get("")
def listar_solicitudes(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items = svc_solicitudes.listar_solicitudes(db, limite=limite, offset=offset)
    return [
        {
            "id": s.id,
            "estado": s.estado,
            "creada_en": s.creada_en.isoformat() if s.creada_en else None,
            "referencia": s.referencia,
        }
        for s in items
    ]


@router.get("/{solicitud_id}")
def obtener_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    s = svc_solicitudes.obtener_solicitud(db, solicitud_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    items = svc_solicitudes.listar_items_solicitud(db, solicitud_id)
    return {
        "id": s.id,
        "estado": s.estado,
        "creada_en": s.creada_en.isoformat() if s.creada_en else None,
        "referencia": s.referencia,
        "items": [
            {
                "id": it.id,
                "producto_id": it.producto_id,
                "cantidad": float(it.cantidad),
                "motivo": it.motivo,
            }
            for it in items
        ],
    }


@router.post("/{solicitud_id}/convertir-a-compra", status_code=201)
def convertir_a_compra(solicitud_id: int, body: dict, db: Session = Depends(get_db)):
    """Convierte una solicitud en una compra confirmada e ingresa stock.

    Body:
    - proveedor_id: int
    """
    proveedor_id = body.get("proveedor_id")
    if proveedor_id is None:
        raise HTTPException(status_code=422, detail="proveedor_id es obligatorio")

    sol = svc_solicitudes.obtener_solicitud(db, solicitud_id)
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if (sol.estado or "").upper() != "PENDIENTE":
        raise HTTPException(status_code=409, detail="La solicitud no está pendiente")

    items_sol = svc_solicitudes.listar_items_solicitud(db, solicitud_id)
    if not items_sol:
        raise HTTPException(status_code=400, detail="Solicitud sin ítems")

    items_compra = []
    for it in items_sol:
        prod = db.get(Producto, it.producto_id)
        if prod is None:
            raise HTTPException(status_code=404, detail=f"Producto {it.producto_id} no encontrado")
        items_compra.append(
            {
                "producto_id": it.producto_id,
                "cantidad": str(it.cantidad),
                "costo_unitario": str(prod.costo_actual or 0),
            }
        )

    try:
        compra = svc_compras.crear_compra(
            db,
            proveedor_id=int(proveedor_id),
            items=items_compra,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # Ingresar stock por compra
    for item in items_compra:
        svc_inventario.ingresar_stock(
            db,
            producto_id=int(item["producto_id"]),
            cantidad=item["cantidad"],
            tipo="COMPRA",
            referencia=f"Compra #{compra.id} (desde SolicitudCompra #{solicitud_id})",
        )

    # Finanzas: registrar gasto (misma estrategia que /api/compras)
    try:
        cuentas = svc_finanzas.listar_cuentas(db, limite=1, offset=0)
        if cuentas:
            cuenta = cuentas[0]
            svc_finanzas.registrar_transaccion(
                db,
                cuenta_id=cuenta.id,
                tipo="gasto",
                monto=compra.total,
                descripcion=f"Compra #{compra.id} (desde SolicitudCompra #{solicitud_id})",
            )
    except ValueError:
        pass

    svc_solicitudes.marcar_solicitud_estado(db, solicitud_id=sol.id, estado="ATENDIDA")

    return {
        "compra": {
            "id": compra.id,
            "proveedor_id": compra.proveedor_id,
            "fecha": compra.fecha.isoformat(),
            "total": float(compra.total),
            "estado": compra.estado,
        },
        "solicitud_id": sol.id,
    }

