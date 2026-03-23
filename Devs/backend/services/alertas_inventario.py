"""Alertas operativas de Inventario.

Bloque funcional: detectar situaciones accionables:
- Stock bajo (cantidad <= mínimo).
- Lotes próximos a vencer (fecha_vencimiento dentro de N días).

Opcionalmente emite eventos para auditoría/automatizaciones.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.events import emit as emit_event
from backend.models.inventario import Lote, Stock
from backend.models.producto import Producto, TipoProducto
from backend.services import configuracion as svc_configuracion


def detectar_alertas(
    sesion: Session,
    *,
    ubicacion: str = "GONDOLA",
    dias_vencimiento: int = 7,
    solo_activos: bool = True,
    emitir_eventos: bool = False,
) -> dict[str, Any]:
    cfg = svc_configuracion.get_configuracion_inventario(sesion)
    stock_minimo_global = Decimal(str(cfg.get("stock_minimo_global", 0) or 0))
    control_vencimientos = bool(cfg.get("control_vencimientos", True))
    control_lotes = bool(cfg.get("control_lotes", True))

    # --- Stock bajo ---
    # Criterio: inventariable, activo (opcional) y (stock_actual <= max(stock_minimo_producto, stock_minimo_global))
    stmt_stock = (
        select(
            Producto.id,
            Producto.nombre,
            Producto.stock_minimo,
            Stock.cantidad,
        )
        .select_from(Producto)
        .join(
            Stock,
            and_(
                Stock.producto_id == Producto.id,
                Stock.ubicacion == ubicacion,
            ),
            isouter=True,
        )
        .where(Producto.tipo_producto == TipoProducto.INVENTARIABLE.value)
    )
    if solo_activos:
        stmt_stock = stmt_stock.where(Producto.activo.is_(True))

    filas = sesion.execute(stmt_stock).all()
    stock_bajo: list[dict[str, Any]] = []
    for pid, nombre, stock_min_prod, cant in filas:
        cantidad = Decimal(str(cant)) if cant is not None else Decimal("0")
        minimo_prod = Decimal(str(stock_min_prod)) if stock_min_prod is not None else Decimal("0")
        minimo = max(minimo_prod, stock_minimo_global)
        if minimo > 0 and cantidad <= minimo:
            stock_bajo.append(
                {
                    "producto_id": pid,
                    "producto_nombre": nombre,
                    "ubicacion": ubicacion,
                    "cantidad": float(cantidad),
                    "minimo": float(minimo),
                    "minimo_producto": float(minimo_prod),
                    "minimo_global": float(stock_minimo_global),
                }
            )

    # --- Próximos a vencer ---
    proximos_vencer: list[dict[str, Any]] = []
    if control_vencimientos and control_lotes:
        dias = max(0, int(dias_vencimiento))
        hoy = date.today()
        limite = hoy + timedelta(days=dias)
        stmt_lotes = (
            select(Lote.id, Lote.producto_id, Producto.nombre, Lote.cantidad, Lote.fecha_vencimiento)
            .select_from(Lote)
            .join(Producto, Producto.id == Lote.producto_id)
            .where(Lote.fecha_vencimiento <= limite)
        )
        if solo_activos:
            stmt_lotes = stmt_lotes.where(Producto.activo.is_(True))
        for lote_id, producto_id, prod_nombre, cantidad, fv in sesion.execute(stmt_lotes).all():
            proximos_vencer.append(
                {
                    "lote_id": lote_id,
                    "producto_id": producto_id,
                    "producto_nombre": prod_nombre,
                    "cantidad": float(Decimal(str(cantidad))),
                    "fecha_vencimiento": fv.isoformat(),
                    "dias_hasta_vencimiento": (fv - hoy).days,
                }
            )

    out = {
        "config": {
            "ubicacion": ubicacion,
            "dias_vencimiento": int(dias_vencimiento),
            "solo_activos": bool(solo_activos),
            "stock_minimo_global": float(stock_minimo_global),
            "control_vencimientos": control_vencimientos,
            "control_lotes": control_lotes,
        },
        "stock_bajo": stock_bajo,
        "proximos_vencer": proximos_vencer,
        "resumen": {
            "stock_bajo": len(stock_bajo),
            "proximos_vencer": len(proximos_vencer),
        },
    }

    if emitir_eventos:
        emit_event(
            "StockBajoDetectado",
            {
                "ubicacion": ubicacion,
                "total": len(stock_bajo),
                "items": stock_bajo[:50],
                "__sesion": sesion,
            },
        )
        emit_event(
            "LotesProximosAVencerDetectados",
            {
                "dias_vencimiento": int(dias_vencimiento),
                "total": len(proximos_vencer),
                "items": proximos_vencer[:50],
                "__sesion": sesion,
            },
        )

    return out

