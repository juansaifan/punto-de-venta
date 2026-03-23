"""Endpoints REST para ventas (dominio Punto de Venta)."""
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas.venta import (
    VentaRegistrarRequest,
    VentaRegistradaResponse,
    VentaResponse,
)
from backend.events import emit as emit_event
from backend.services import ventas as svc_ventas
from backend.services import inventario as svc_inventario
from backend.services import tesoreria as svc_tesoreria
from backend.models.venta import EstadoVenta

router = APIRouter(prefix="/ventas", tags=["ventas"])


class CancelarVentaRequest(BaseModel):
    motivo: Optional[str] = None


class AgregarItemRequest(BaseModel):
    producto_id: int
    cantidad: Decimal
    precio_unitario: Optional[Decimal] = None


class ActualizarItemRequest(BaseModel):
    cantidad: Optional[Decimal] = None
    precio_unitario: Optional[Decimal] = None


class AplicarDescuentoRequest(BaseModel):
    descuento: Decimal


@router.post("", response_model=VentaRegistradaResponse)
def registrar_venta(
    body: VentaRegistrarRequest,
    db: Session = Depends(get_db),
):
    """
    Registra una venta: crea la venta con ítems, descuento y método de pago.
    Cada ítem debe referenciar un producto existente; opcionalmente se puede
    indicar precio_unitario (si no se envía se usa el precio_venta del producto).
    """
    items_payload = [
        {"producto_id": it.producto_id, "cantidad": it.cantidad}
        for it in body.items
    ]
    for i, it in enumerate(body.items):
        if it.precio_unitario is not None:
            items_payload[i]["precio_unitario"] = it.precio_unitario

    try:
        modo_norm = (body.modo_venta or "TEU_ON").strip().upper()
        venta = svc_ventas.registrar_venta(
            db,
            items=items_payload,
            descuento=body.descuento,
            metodo_pago=body.metodo_pago,
            cliente_id=body.cliente_id,
            modo_venta=modo_norm,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # Descontar stock por cada ítem (dominio Inventario)
    try:
        for item in venta.items:
            svc_inventario.descontar_stock_por_venta(
                db,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                referencia=f"Venta #{venta.id}",
            )
    except ValueError as e:
        msg = str(e)
        if "insuficiente" in msg.lower() or "stock" in msg.lower():
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # Vincular a caja abierta y registrar movimiento de caja SOLO en TEU_ON.
    if modo_norm == "TEU_ON":
        caja_abierta = svc_tesoreria.obtener_caja_abierta(db)
        if caja_abierta is not None:
            venta.caja_id = caja_abierta.id
            db.flush()
            try:
                svc_tesoreria.registrar_movimiento_caja(
                    db,
                    caja_abierta.id,
                    tipo="VENTA",
                    monto=venta.total,
                    referencia=f"Venta #{venta.id}",
                    medio_pago=venta.metodo_pago or "EFECTIVO",
                )
            except ValueError:
                pass  # no bloquear la venta si falla el movimiento

    # Evento VentaRegistrada (EVENTOS.md)
    emit_event(
        "VentaRegistrada",
        {
            "venta_id": venta.id,
            "fecha": venta.creado_en.isoformat(),
            "total": float(venta.total),
            "caja_id": venta.caja_id,
        },
    )

    return VentaRegistradaResponse(
        venta_id=venta.id,
        total=venta.total,
    )


@router.get("/buscar")
def buscar_ventas(
    q: str = Query(..., min_length=1, description="Buscar por ticket, cliente, DNI o producto"),
    db: Session = Depends(get_db),
    limite: int = Query(50, ge=1, le=200),
):
    """
    Búsqueda de ventas por número de ticket, nombre/apellido de cliente, DNI o nombre de producto.
    Docs Módulo 2 §3 — Operaciones Comerciales / búsqueda de operaciones.
    """
    return svc_ventas.buscar_ventas(db, q=q, limite=limite)


@router.get("/{venta_id}", response_model=VentaResponse)
def obtener_venta(venta_id: int, db: Session = Depends(get_db)):
    """Obtiene una venta por ID con sus ítems."""
    venta = svc_ventas.obtener_venta_por_id(db, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return venta


@router.get("", response_model=list[VentaResponse])
def listar_ventas(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    estado: Optional[str] = Query(None, description="Filtrar por estado: PENDIENTE, PAGADA, FIADA, CANCELADA, SUSPENDIDA"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente (persona ID)"),
    fecha_desde: Optional[date] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin YYYY-MM-DD"),
):
    """Lista ventas con filtros opcionales por estado, cliente y fechas."""
    ventas = svc_ventas.listar_ventas(
        db,
        limite=limite,
        offset=offset,
        estado=estado,
        cliente_id=cliente_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return list(ventas)


@router.post("/{venta_id}/suspender")
def suspender_venta(
    venta_id: int,
    db: Session = Depends(get_db),
):
    """Suspende una venta/ticket PENDIENTE (TEU_OFF multi-pestañas)."""
    try:
        venta = svc_ventas.suspender_venta_pendiente(db, venta_id=venta_id)
    except ValueError as e:
        msg = str(e)
        if "solo se pueden suspender" in msg.lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=404 if "no encontrada" in msg.lower() else 400, detail=str(e))
    return venta


@router.post("/{venta_id}/reanudar")
def reanudar_venta(
    venta_id: int,
    db: Session = Depends(get_db),
):
    """Reanuda una venta/ticket suspendida."""
    try:
        venta = svc_ventas.reanudar_venta_suspensada(db, venta_id=venta_id)
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return venta


@router.post("/{venta_id}/cancelar")
def cancelar_venta(
    venta_id: int,
    body: CancelarVentaRequest = CancelarVentaRequest(),
    db: Session = Depends(get_db),
):
    """
    Cancela una venta en estado PENDIENTE o SUSPENDIDA.
    Docs Módulo 2 §13 — estados de la venta (CANCELADA).
    """
    try:
        venta = svc_ventas.cancelar_venta(db, venta_id=venta_id, motivo=body.motivo)
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {"venta_id": venta.id, "estado": venta.estado, "numero_ticket": venta.numero_ticket}


@router.post("/{venta_id}/items", response_model=VentaResponse)
def agregar_item(
    venta_id: int,
    body: AgregarItemRequest,
    db: Session = Depends(get_db),
):
    """
    Agrega un producto al carrito de una venta PENDIENTE.
    Si el producto ya existe en el carrito, se incrementa la cantidad.
    Docs Módulo 2 §8 — carrito de venta.
    """
    try:
        venta = svc_ventas.agregar_item_a_venta(
            db,
            venta_id=venta_id,
            producto_id=body.producto_id,
            cantidad=body.cantidad,
            precio_unitario=body.precio_unitario,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return venta


@router.patch("/{venta_id}/items/{item_id}", response_model=VentaResponse)
def actualizar_item(
    venta_id: int,
    item_id: int,
    body: ActualizarItemRequest,
    db: Session = Depends(get_db),
):
    """
    Modifica la cantidad y/o precio de un ítem en una venta PENDIENTE.
    Docs Módulo 2 §8 — carrito (modificar cantidad).
    """
    try:
        venta = svc_ventas.actualizar_item_de_venta(
            db,
            venta_id=venta_id,
            item_id=item_id,
            cantidad=body.cantidad,
            precio_unitario=body.precio_unitario,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return venta


@router.delete("/{venta_id}/items/{item_id}", response_model=VentaResponse)
def eliminar_item(
    venta_id: int,
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Elimina un ítem del carrito de una venta PENDIENTE.
    Docs Módulo 2 §8 — carrito (eliminar producto).
    """
    try:
        venta = svc_ventas.eliminar_item_de_venta(db, venta_id=venta_id, item_id=item_id)
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return venta


@router.patch("/{venta_id}/descuento", response_model=VentaResponse)
def aplicar_descuento(
    venta_id: int,
    body: AplicarDescuentoRequest,
    db: Session = Depends(get_db),
):
    """
    Aplica un descuento global a una venta PENDIENTE.
    Docs Módulo 2 §8 — carrito (aplicar descuento).
    """
    try:
        venta = svc_ventas.aplicar_descuento_a_venta(db, venta_id=venta_id, descuento=body.descuento)
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return venta


# ---------------------------------------------------------------------------
# Integración POS ↔ Pesables (escaneo EAN-13)
# ---------------------------------------------------------------------------

class AgregarPesableBarcodeRequest(BaseModel):
    barcode: str


@router.post("/{venta_id}/items/pesable-barcode", response_model=VentaResponse)
def agregar_pesable_por_barcode(
    venta_id: int,
    body: AgregarPesableBarcodeRequest,
    db: Session = Depends(get_db),
):
    """
    Integración POS↔Pesables (docs submodulo_pesables.md §13).

    Recibe el barcode EAN-13 escaneado en el POS y añade el ítem pesable a la venta.
    El precio proviene del barcode (precio codificado); el POS NO recalcula.
    El PesableItem queda marcado como 'used' para evitar reutilización de etiquetas.
    """
    try:
        venta = svc_ventas.agregar_pesable_por_barcode(db, venta_id=venta_id, barcode=body.barcode)
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return venta


@router.get("/pesable/resolver-barcode")
def resolver_barcode_pesable(
    barcode: str = Query(..., description="Código EAN-13 del ítem pesable"),
    db: Session = Depends(get_db),
):
    """
    Resuelve un barcode EAN-13 pesable sin añadirlo a ninguna venta.
    Útil para previsualización en POS antes de confirmar el escaneo.
    Devuelve: item_id, producto_id, nombre_producto, peso, precio_unitario, precio_total, estado.
    """
    try:
        return svc_ventas.resolver_barcode_pesable(db, barcode=barcode)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
