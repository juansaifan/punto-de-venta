"""Endpoints REST para Tesorería / Cuentas Corrientes de Clientes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas.cuentas_corrientes import (
    CuentaCorrienteResumenResponse,
    MovimientoCuentaCorrienteCreate,
    MovimientoCuentaCorrienteResponse,
)
from backend.services import cuentas_corrientes as svc_cc

router = APIRouter(
    prefix="/tesoreria/cuentas-corrientes",
    tags=["tesoreria-cuentas-corrientes"],
)


@router.get("/aging")
def aging_cuentas_corrientes(db: Session = Depends(get_db)):
    """
    Reporte de aging de cuentas corrientes: agrupa deudas en tramos de 0-30, 31-60, 61-90 y +90 días.
    Docs Módulo 3 §5 — control de deuda / morosidad.
    """
    return svc_cc.aging_cuentas_corrientes(db)


@router.get("/deudores")
def reporte_deudores(
    db: Session = Depends(get_db),
    saldo_minimo: float = Query(0.01, ge=0, description="Saldo mínimo para incluir en el reporte"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Lista de clientes con deuda activa, ordenados por saldo descendente.
    Incluye días desde última venta y último pago.
    Docs Módulo 3 §5 — gestión de morosidad.
    """
    return svc_cc.reporte_deudores(db, saldo_minimo=saldo_minimo, limite=limite, offset=offset)


@router.get("/clientes/{cliente_id}/estadisticas-pagos")
def estadisticas_pagos_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    fecha_desde: str | None = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha fin YYYY-MM-DD"),
):
    """
    Estadísticas de pagos de un cliente: total facturado en cc, total pagado, promedio de pago, fechas.
    Docs Módulo 3 §10 — Historial de movimientos.
    """
    from datetime import datetime as dt

    def parse_date(s: str | None):
        if not s:
            return None
        try:
            return dt.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Fecha inválida: {s}. Use YYYY-MM-DD")

    try:
        return svc_cc.estadisticas_pagos_cliente(
            db,
            cliente_id=cliente_id,
            fecha_desde=parse_date(fecha_desde),
            fecha_hasta=parse_date(fecha_hasta),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", summary="Listar todas las cuentas corrientes de clientes")
def listar_cuentas_corrientes(
    db: Session = Depends(get_db),
    solo_con_saldo: bool = Query(False, description="Si True, solo devuelve cuentas con saldo > 0"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Listado global de cuentas corrientes de clientes con saldo y límite de crédito.
    Permite obtener una vista consolidada de deudas activas.
    """
    cuentas = svc_cc.listar_cuentas_corrientes(
        db,
        solo_con_saldo=solo_con_saldo,
        limite=limite,
        offset=offset,
    )
    return [
        {
            "cuenta_id": c["cuenta_id"],
            "cliente_id": c["cliente_id"],
            "saldo": float(c["saldo"]),
            "limite_credito": float(c["limite_credito"]) if c["limite_credito"] is not None else None,
            "disponible": float(c["disponible"]) if c["disponible"] is not None else None,
        }
        for c in cuentas
    ]


@router.get(
    "/clientes/{cliente_id}/resumen",
    response_model=CuentaCorrienteResumenResponse,
)
def obtener_resumen_cuenta_corriente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    """
    Devuelve el resumen de la cuenta corriente del cliente:
    - saldo actual (deuda)
    - limite_credito (si está configurado en el cliente)
    - disponible (limite_credito - saldo, si aplica)
    """
    try:
        resumen = svc_cc.obtener_resumen_cuenta_corriente(
            db,
            cliente_id=cliente_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return CuentaCorrienteResumenResponse(
        cliente_id=resumen["cliente_id"],
        saldo=float(resumen["saldo"]),
        limite_credito=float(resumen["limite_credito"])
        if resumen["limite_credito"] is not None
        else None,
        disponible=float(resumen["disponible"])
        if resumen["disponible"] is not None
        else None,
    )


@router.post(
    "/clientes/{cliente_id}/movimientos",
    response_model=MovimientoCuentaCorrienteResponse,
    status_code=201,
)
def registrar_movimiento_cuenta_corriente(
    cliente_id: int,
    payload: MovimientoCuentaCorrienteCreate,
    db: Session = Depends(get_db),
):
    """
    Registra un movimiento de cuenta corriente para un cliente.

    Tipos admitidos: VENTA, PAGO, AJUSTE.
    """
    try:
        mov = svc_cc.registrar_movimiento_cuenta_corriente(
            db,
            cliente_id=cliente_id,
            tipo=payload.tipo,
            monto=payload.monto,
            descripcion=payload.descripcion,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return MovimientoCuentaCorrienteResponse(
        id=mov.id,
        cuenta_id=mov.cuenta_id,
        tipo=mov.tipo,
        monto=float(mov.monto),
        descripcion=mov.descripcion,
        fecha=mov.fecha.isoformat(),
    )


@router.get(
    "/clientes/{cliente_id}/movimientos",
    response_model=list[MovimientoCuentaCorrienteResponse],
)
def listar_movimientos_cuenta_corriente(
    cliente_id: int,
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Lista movimientos de cuenta corriente para un cliente, ordenados por fecha descendente.
    """
    try:
        movimientos = svc_cc.listar_movimientos_cuenta_corriente(
            db,
            cliente_id=cliente_id,
            limite=limite,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return [
        MovimientoCuentaCorrienteResponse(
            id=m.id,
            cuenta_id=m.cuenta_id,
            tipo=m.tipo,
            monto=float(m.monto),
            descripcion=m.descripcion,
            fecha=m.fecha.isoformat(),
        )
        for m in movimientos
    ]

