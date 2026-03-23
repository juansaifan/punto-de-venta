"""Endpoints REST para Operaciones Comerciales (Módulo 2)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas.operaciones_comerciales import (
    AnulacionCrearRequest,
    AnulacionResponse,
    CambioProductoCrearRequest,
    CambioProductoResponse,
    DevolucionCrearRequest,
    DevolucionResponse,
    NotaDebitoCrearRequest,
    NotaDebitoResponse,
    CreditoCuentaCorrienteCrearRequest,
    CreditoCuentaCorrienteResponse,
    NotaCreditoCrearRequest,
    NotaCreditoResponse,
)
from backend.services import operaciones_comerciales as svc_ops

router = APIRouter(
    prefix="/operaciones-comerciales",
    tags=["operaciones-comerciales"],
)


@router.get("", response_model=list[dict])
def listar_por_venta(
    venta_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    """Lista operaciones comerciales asociadas a una venta (últimas primero)."""
    ops = svc_ops.listar_operaciones_por_venta(db, venta_id=venta_id)
    return [
        {
            "id": o.id,
            "venta_id": o.venta_id,
            "cliente_id": o.cliente_id,
            "tipo": o.tipo.value if hasattr(o.tipo, "value") else str(o.tipo),
            "estado": o.estado.value if hasattr(o.estado, "value") else str(o.estado),
            "motivo": o.motivo,
            "importe_total": float(o.importe_total),
            "creado_en": o.creado_en.isoformat() if o.creado_en else None,
        }
        for o in ops
    ]


@router.post("/devoluciones", response_model=DevolucionResponse)
def registrar_devolucion(body: DevolucionCrearRequest, db: Session = Depends(get_db)):
    try:
        op = svc_ops.registrar_devolucion(
            db,
            venta_id=body.venta_id,
            reintegro_tipo=body.reintegro_tipo,
            reintegro_metodo_pago=body.reintegro_metodo_pago,
            motivo=body.motivo,
            items=[
                {"item_venta_id": it.item_venta_id, "cantidad": it.cantidad}
                for it in body.items
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DevolucionResponse(
        id=op.id,
        venta_id=op.venta_id,
        tipo=op.tipo.value,
        estado=op.estado.value,
        importe_total=op.importe_total,
        motivo=op.motivo,
        creado_en=op.creado_en,
    )


@router.post("/notas-credito", response_model=NotaCreditoResponse)
def registrar_nota_credito(
    body: NotaCreditoCrearRequest, db: Session = Depends(get_db)
):
    try:
        op = svc_ops.registrar_nota_credito(
            db,
            venta_id=body.venta_id,
            reintegro_tipo=body.reintegro_tipo,
            reintegro_metodo_pago=body.reintegro_metodo_pago,
            importe=body.importe,
            motivo=body.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return NotaCreditoResponse(
        id=op.id,
        venta_id=op.venta_id,
        tipo=op.tipo.value,
        estado=op.estado.value,
        importe_total=op.importe_total,
        motivo=op.motivo,
        creado_en=op.creado_en,
    )


@router.post("/anulaciones", response_model=AnulacionResponse)
def anular_venta(body: AnulacionCrearRequest, db: Session = Depends(get_db)):
    try:
        op = svc_ops.anular_venta_pendiente(
            db,
            venta_id=body.venta_id,
            motivo=body.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AnulacionResponse(
        id=op.id,
        venta_id=op.venta_id,
        tipo=op.tipo.value,
        estado=op.estado.value,
        importe_total=op.importe_total,
        motivo=op.motivo,
        creado_en=op.creado_en,
    )


@router.post("/cambios", response_model=CambioProductoResponse)
def registrar_cambio_producto(
    body: CambioProductoCrearRequest,
    db: Session = Depends(get_db),
):
    try:
        op = svc_ops.registrar_cambio_producto(
            db,
            venta_id=body.venta_id,
            items_devueltos=[
                {"item_venta_id": it.item_venta_id, "cantidad": it.cantidad}
                for it in body.items_devueltos
            ],
            items_nuevos=[
                {
                    "producto_id": it.producto_id,
                    "cantidad": it.cantidad,
                    "precio_unitario": it.precio_unitario,
                }
                for it in body.items_nuevos
            ],
            reintegro_tipo_diferencia=body.reintegro_tipo_diferencia,
            reintegro_metodo_pago=body.reintegro_metodo_pago,
            motivo=body.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CambioProductoResponse(
        id=op.id,
        venta_id=op.venta_id,
        tipo=op.tipo.value,
        estado=op.estado.value,
        importe_total=op.importe_total,
        motivo=op.motivo,
        creado_en=op.creado_en,
    )


@router.post("/notas-debito", response_model=NotaDebitoResponse)
def registrar_nota_debito(
    body: NotaDebitoCrearRequest,
    db: Session = Depends(get_db),
):
    try:
        op = svc_ops.registrar_nota_debito(
            db,
            venta_id=body.venta_id,
            reintegro_tipo=body.reintegro_tipo,
            reintegro_metodo_pago=body.reintegro_metodo_pago,
            importe=body.importe,
            motivo=body.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return NotaDebitoResponse(
        id=op.id,
        venta_id=op.venta_id,
        tipo=op.tipo.value,
        estado=op.estado.value,
        importe_total=op.importe_total,
        motivo=op.motivo,
        creado_en=op.creado_en,
    )


@router.post("/creditos-cuenta-corriente", response_model=CreditoCuentaCorrienteResponse)
def registrar_credito_cuenta_corriente(
    body: CreditoCuentaCorrienteCrearRequest,
    db: Session = Depends(get_db),
):
    try:
        op = svc_ops.registrar_credito_cuenta_corriente(
            db,
            venta_id=body.venta_id,
            importe=body.importe,
            motivo=body.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreditoCuentaCorrienteResponse(
        id=op.id,
        venta_id=op.venta_id,
        tipo=op.tipo.value,
        estado=op.estado.value,
        importe_total=op.importe_total,
        motivo=op.motivo,
        creado_en=op.creado_en,
    )

