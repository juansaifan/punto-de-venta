"""Endpoints REST para Tesorería (caja)."""
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas.caja import (
    CajaAbrirRequest,
    CajaCerrarRequest,
    CajaResponse,
    MovimientoCajaCreate,
    MovimientoCajaResponse,
    TicketPendienteResponse,
    CobrarTicketRequest,
    CobrarTicketResponse,
)
from backend.api.schemas.venta import VentaResponse
from backend.services import tesoreria as svc_tesoreria
from backend.services import caja_tickets as svc_tickets
from backend.services import ventas as svc_ventas

router = APIRouter(prefix="/caja", tags=["caja"])


@router.post("/abrir", response_model=CajaResponse)
def abrir_caja(
    body: CajaAbrirRequest | None = Body(None),
    db: Session = Depends(get_db),
):
    """Abre una nueva caja. Solo puede haber una caja abierta a la vez."""
    data = body or CajaAbrirRequest()
    try:
        caja = svc_tesoreria.abrir_caja(
            db,
            saldo_inicial=data.saldo_inicial,
            usuario_id=data.usuario_id,
        )
    except ValueError as e:
        if "abierta" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return caja


@router.post("/{caja_id}/cerrar", response_model=CajaResponse)
def cerrar_caja(
    caja_id: int,
    body: CajaCerrarRequest | None = None,
    db: Session = Depends(get_db),
):
    """Cierra la caja indicada (opcionalmente con saldo_final)."""
    saldo_final = body.saldo_final if body else None
    supervisor_autorizado = body.supervisor_autorizado if body else False
    try:
        caja = svc_tesoreria.cerrar_caja(
            db,
            caja_id,
            saldo_final=saldo_final,
            supervisor_autorizado=supervisor_autorizado,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrada" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        if "autorizaci" in msg or "supervisor" in msg:
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return caja


@router.get("/abierta", response_model=CajaResponse | None)
def obtener_caja_abierta(db: Session = Depends(get_db)):
    """Obtiene la caja actualmente abierta (None si no hay ninguna)."""
    caja = svc_tesoreria.obtener_caja_abierta(db)
    return caja


@router.get("/resumen-global")
def resumen_global_cajas(db: Session = Depends(get_db)):
    """
    Resumen consolidado histórico de todas las cajas.
    Incluye totales de ingresos/egresos, cantidad de cajas abiertas y cerradas.
    """
    resumen = svc_tesoreria.resumen_global_cajas(db)
    return {
        "cantidad_cajas_total": resumen["cantidad_cajas_total"],
        "cantidad_cajas_abiertas": resumen["cantidad_cajas_abiertas"],
        "cantidad_cajas_cerradas": resumen["cantidad_cajas_cerradas"],
        "total_ingresos_historico": str(resumen["total_ingresos_historico"]),
        "total_egresos_historico": str(resumen["total_egresos_historico"]),
        "saldo_neto_historico": str(resumen["saldo_neto_historico"]),
    }


@router.get("/movimientos-global", response_model=list[MovimientoCajaResponse])
def listar_movimientos_global(
    db: Session = Depends(get_db),
    tipo: str | None = Query(None, description="Filtrar por tipo: INGRESO, GASTO, VENTA, RETIRO, DEVOLUCION"),
    caja_id: int | None = Query(None, description="Filtrar por ID de caja"),
    desde: datetime | None = Query(None, description="Desde esta fecha (inclusive)"),
    hasta: datetime | None = Query(None, description="Hasta esta fecha (inclusive)"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Historial global de movimientos de caja con filtros opcionales (doc §5 Movimientos).
    Permite auditar movimientos de todas las cajas.
    """
    movs = svc_tesoreria.listar_movimientos_global(
        db,
        tipo=tipo,
        caja_id=caja_id,
        desde=desde,
        hasta=hasta,
        limite=limite,
        offset=offset,
    )
    return list(movs)


@router.get("/{caja_id}", response_model=CajaResponse)
def obtener_caja(caja_id: int, db: Session = Depends(get_db)):
    """Obtiene una caja por ID."""
    caja = svc_tesoreria.obtener_caja_por_id(db, caja_id)
    if caja is None:
        raise HTTPException(status_code=404, detail="Caja no encontrada")
    return caja


@router.get("", response_model=list[CajaResponse])
def listar_cajas(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista cajas (más recientes primero)."""
    cajas = svc_tesoreria.listar_cajas(db, limite=limite, offset=offset)
    return list(cajas)


@router.post("/{caja_id}/movimientos", response_model=MovimientoCajaResponse)
def registrar_movimiento(
    caja_id: int,
    body: MovimientoCajaCreate,
    db: Session = Depends(get_db),
):
    """Registra un movimiento de caja (INGRESO, GASTO, RETIRO, etc.). La caja debe estar abierta."""
    try:
        mov = svc_tesoreria.registrar_movimiento_caja(
            db,
            caja_id,
            tipo=body.tipo,
            monto=body.monto,
            referencia=body.referencia,
            medio_pago=body.medio_pago or "EFECTIVO",
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrada" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        if "cerrada" in msg:
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return mov


@router.get("/{caja_id}/movimientos", response_model=list[MovimientoCajaResponse])
def listar_movimientos(
    caja_id: int,
    db: Session = Depends(get_db),
    tipo: str | None = Query(None, description="Filtrar por tipo: INGRESO, GASTO, VENTA, RETIRO, DEVOLUCION"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista movimientos de una caja. Opcionalmente filtra por tipo."""
    if svc_tesoreria.obtener_caja_por_id(db, caja_id) is None:
        raise HTTPException(status_code=404, detail="Caja no encontrada")
    movs = svc_tesoreria.listar_movimientos_caja(db, caja_id, tipo=tipo, limite=limite, offset=offset)
    return list(movs)


@router.get("/{caja_id}/resumen")
def obtener_resumen_caja(caja_id: int, db: Session = Depends(get_db)):
    """
    Devuelve un resumen (arqueo teórico) de la caja:
    - saldo_inicial
    - total_ingresos
    - total_egresos
    - saldo_teorico
    """
    try:
        resumen = svc_tesoreria.obtener_resumen_caja(db, caja_id)
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrada" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    out = {
        "caja_id": resumen["caja_id"],
        "saldo_inicial": str(resumen["saldo_inicial"]),
        "total_ingresos": str(resumen["total_ingresos"]),
        "total_egresos": str(resumen["total_egresos"]),
        "saldo_teorico": str(resumen["saldo_teorico"]),
    }

    # Campos adicionales solo si el cierre ya fue ejecutado (saldo_final/diferencia).
    if "saldo_final" in resumen:
        out["saldo_final"] = str(resumen["saldo_final"])
    if "diferencia" in resumen:
        out["diferencia"] = str(resumen["diferencia"])

    return out


@router.get("/{caja_id}/movimientos/exportar", response_class=PlainTextResponse)
def exportar_movimientos_caja(
    caja_id: int,
    db: Session = Depends(get_db),
):
    """
    Exporta movimientos de una caja como CSV para reconciliación/auditoría.
    Columnas: id, fecha, tipo, monto, medio_pago, referencia.
    """
    try:
        csv_content = svc_tesoreria.exportar_movimientos_caja_csv(db, caja_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PlainTextResponse(content=csv_content, media_type="text/csv")


@router.get("/tickets/buscar")
def buscar_tickets_pendientes(
    q: str = Query(..., min_length=1, description="Buscar por ticket, cliente, DNI o producto"),
    db: Session = Depends(get_db),
    limite: int = Query(50, ge=1, le=200),
):
    """
    Búsqueda de tickets PENDIENTES por número de ticket, nombre de cliente, DNI o nombre de producto.
    Docs Módulo 2 §5 — área de escaneo / cola de tickets pendientes.
    """
    resultados = svc_ventas.buscar_ventas(db, q=q, limite=limite)
    return [r for r in resultados if r["estado"] == "PENDIENTE"]


@router.get("/tickets/pendientes", response_model=list[TicketPendienteResponse])
def listar_tickets_pendientes(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista ventas/tickets pendientes de cobro (TEU_OFF)."""
    tickets = svc_tickets.listar_tickets_pendientes(db, limite=limite, offset=offset)
    return tickets


@router.get("/tickets/{venta_id}", response_model=VentaResponse)
def obtener_ticket(
    venta_id: int,
    db: Session = Depends(get_db),
):
    """Obtiene detalle de un ticket por venta_id."""
    venta = svc_tickets.obtener_ticket_por_id(db, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return venta


@router.post("/tickets/{venta_id}/cobrar", response_model=CobrarTicketResponse)
def cobrar_ticket(
    venta_id: int,
    body: CobrarTicketRequest,
    db: Session = Depends(get_db),
):
    """Ejecuta el cobro de un ticket pendiente."""
    try:
        venta = svc_tickets.cobro_ticket(
            db,
            venta_id=venta_id,
            pagos=[
                {
                    "metodo_pago": p.metodo_pago,
                    "importe": p.importe,
                    "medio_pago": p.medio_pago,
                    "cobrador": p.cobrador,
                }
                for p in body.pagos
            ],
            observaciones=body.observaciones,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no hay caja" in msg:
            raise HTTPException(status_code=400, detail=str(e))
        if "no encontrada" in msg or "no encontrada" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    return CobrarTicketResponse(
        venta_id=venta.id,
        numero_ticket=venta.numero_ticket,
        estado=venta.estado,
        metodo_pago=venta.metodo_pago,
        total=venta.total,
        caja_id=venta.caja_id,
    )
