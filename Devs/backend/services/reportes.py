# Servicios del dominio Reportes
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.models.venta import Venta, ItemVenta, EstadoVenta
from backend.models.inventario import Stock, MovimientoInventario
from backend.models.operaciones_comerciales import OperacionComercial, TipoOperacionComercial
from backend.models.producto import Producto, CategoriaProducto
from backend.models.usuario import Usuario
from backend.models.persona import (
    Persona,
    Cliente,
    CuentaCorrienteCliente,
    MovimientoCuentaCorriente,
)
from backend.models.compra import Compra, ItemCompra
from backend.models.caja import Caja, MovimientoCaja


def ventas_por_dia(
    sesion: Session,
    fecha: date,
) -> dict[str, Any]:
    """Ventas del día: cantidad de ventas, total facturado, ticket promedio (por fecha local/date part)."""
    fecha_str = fecha.isoformat()
    stmt = (
        select(
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total"),
        )
        .where(func.date(Venta.creado_en) == fecha_str)
    )
    row = sesion.execute(stmt).one()
    cantidad = row.cantidad_ventas or 0
    total = row.total or Decimal("0")
    ticket_promedio = total / cantidad if cantidad else Decimal("0")
    return {
        "fecha": fecha.isoformat(),
        "cantidad_ventas": cantidad,
        "total": total,
        "ticket_promedio": round(ticket_promedio, 2),
    }


def ventas_por_producto(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
) -> Sequence[dict[str, Any]]:
    """Ventas agregadas por producto en el rango de fechas (por total vendido descendente)."""
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()
    stmt = (
        select(
            ItemVenta.producto_id,
            ItemVenta.nombre_producto,
            func.sum(ItemVenta.cantidad).label("cantidad_vendida"),
            func.sum(ItemVenta.subtotal).label("total_vendido"),
        )
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(ItemVenta.producto_id, ItemVenta.nombre_producto)
        .order_by(func.sum(ItemVenta.subtotal).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "producto_id": r.producto_id,
            "nombre_producto": r.nombre_producto,
            "cantidad_vendida": float(r.cantidad_vendida),
            "total_vendido": float(r.total_vendido),
        }
        for r in rows
    ]


def margen_por_producto(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
    orden_por: str = "margen_bruto",
) -> list[dict[str, Any]]:
    """
    Margen por producto en el rango de fechas (docs Módulo 7 / system_state).
    total_vendido = sum(ItemVenta.subtotal), total_costo = sum(cantidad * Producto.costo_actual),
    margen_bruto = total_vendido - total_costo, margen_pct = (margen_bruto / total_vendido * 100).
    orden_por: 'margen_bruto' (desc), 'margen_pct' (desc) o 'total_vendido' (desc).
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()
    total_costo_expr = func.coalesce(
        func.sum(ItemVenta.cantidad * Producto.costo_actual), Decimal("0")
    )
    total_vendido_expr = func.coalesce(func.sum(ItemVenta.subtotal), Decimal("0"))
    stmt = (
        select(
            ItemVenta.producto_id,
            ItemVenta.nombre_producto,
            total_vendido_expr.label("total_vendido"),
            total_costo_expr.label("total_costo"),
        )
        .select_from(ItemVenta)
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .join(Producto, Producto.id == ItemVenta.producto_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(ItemVenta.producto_id, ItemVenta.nombre_producto)
    )
    if orden_por == "margen_bruto":
        stmt = stmt.order_by((total_vendido_expr - total_costo_expr).desc())
    elif orden_por == "margen_pct":
        margen_pct_expr = (total_vendido_expr - total_costo_expr) / func.nullif(total_vendido_expr, 0)
        stmt = stmt.order_by(margen_pct_expr.desc().nullslast())
    else:  # total_vendido
        stmt = stmt.order_by(total_vendido_expr.desc())
    stmt = stmt.limit(limite)
    rows = sesion.execute(stmt).all()
    result = []
    for r in rows:
        tv = float(r.total_vendido)
        tc = float(r.total_costo)
        margen_bruto = tv - tc
        margen_pct = round((margen_bruto / tv * 100), 2) if tv else 0.0
        result.append({
            "producto_id": r.producto_id,
            "nombre_producto": r.nombre_producto,
            "total_vendido": tv,
            "total_costo": tc,
            "margen_bruto": round(margen_bruto, 2),
            "margen_pct": margen_pct,
        })
    return result


def margen_por_categoria(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
    orden_por: str = "margen_bruto",
) -> list[dict[str, Any]]:
    """
    Margen por categoría de producto en el rango de fechas.
    total_vendido = sum(ItemVenta.subtotal) por categoría,
    total_costo = sum(cantidad * Producto.costo_actual) por categoría,
    margen_bruto = total_vendido - total_costo,
    margen_pct = (margen_bruto / total_vendido * 100) cuando total_vendido > 0.
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    total_costo_expr = func.coalesce(
        func.sum(ItemVenta.cantidad * Producto.costo_actual), Decimal("0")
    )
    total_vendido_expr = func.coalesce(func.sum(ItemVenta.subtotal), Decimal("0"))

    stmt = (
        select(
            CategoriaProducto.id.label("categoria_id"),
            CategoriaProducto.nombre.label("categoria_nombre"),
            total_vendido_expr.label("total_vendido"),
            total_costo_expr.label("total_costo"),
        )
        .select_from(ItemVenta)
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .join(Producto, Producto.id == ItemVenta.producto_id)
        .outerjoin(CategoriaProducto, CategoriaProducto.id == Producto.categoria_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(CategoriaProducto.id, CategoriaProducto.nombre)
    )

    if orden_por == "margen_bruto":
        stmt = stmt.order_by((total_vendido_expr - total_costo_expr).desc())
    elif orden_por == "margen_pct":
        margen_pct_expr = (total_vendido_expr - total_costo_expr) / func.nullif(
            total_vendido_expr, 0
        )
        stmt = stmt.order_by(margen_pct_expr.desc().nullslast())
    else:  # total_vendido
        stmt = stmt.order_by(total_vendido_expr.desc())

    stmt = stmt.limit(limite)
    rows = sesion.execute(stmt).all()

    resultado: list[dict[str, Any]] = []
    for r in rows:
        tv = float(r.total_vendido)
        tc = float(r.total_costo)
        margen_bruto = tv - tc
        margen_pct = round((margen_bruto / tv * 100), 2) if tv else 0.0
        categoria_nombre = r.categoria_nombre or "Sin categoría"
        resultado.append(
            {
                "categoria_id": r.categoria_id,
                "categoria_nombre": categoria_nombre,
                "total_vendido": tv,
                "total_costo": tc,
                "margen_bruto": round(margen_bruto, 2),
                "margen_pct": margen_pct,
            }
        )

    return resultado


def ranking_productos_mas_vendidos(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 20,
    orden_por: str = "total",
) -> list[dict[str, Any]]:
    """
    Ranking de productos más vendidos en el rango (docs Módulo 7 §4 Rankings).
    orden_por: 'total' (por total_vendido desc) o 'cantidad' (por cantidad_vendida desc).
    Incluye posición (1-based) en el ranking.
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()
    order_col = (
        func.sum(ItemVenta.subtotal).desc()
        if orden_por == "total"
        else func.sum(ItemVenta.cantidad).desc()
    )
    stmt = (
        select(
            ItemVenta.producto_id,
            ItemVenta.nombre_producto,
            func.sum(ItemVenta.cantidad).label("cantidad_vendida"),
            func.sum(ItemVenta.subtotal).label("total_vendido"),
        )
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(ItemVenta.producto_id, ItemVenta.nombre_producto)
        .order_by(order_col)
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "posicion": i + 1,
            "producto_id": r.producto_id,
            "nombre_producto": r.nombre_producto,
            "cantidad_vendida": float(r.cantidad_vendida),
            "total_vendido": float(r.total_vendido),
        }
        for i, r in enumerate(rows)
    ]


def ventas_por_empleado(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
) -> Sequence[dict[str, Any]]:
    """
    Ventas agregadas por empleado en el rango de fechas:
    - cantidad de ventas
    - total vendido
    - nombre del empleado (Usuario.nombre o "Sin asignar" si venta sin usuario)
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            Venta.usuario_id.label("empleado_id"),
            func.coalesce(func.max(Usuario.nombre), "Sin asignar").label("empleado_nombre"),
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
        )
        .select_from(Venta)
        .outerjoin(Usuario, Venta.usuario_id == Usuario.id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(Venta.usuario_id)
        .order_by(func.coalesce(func.sum(Venta.total), 0).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "empleado_id": r.empleado_id,
            "empleado_nombre": r.empleado_nombre or "Sin asignar",
            "cantidad_ventas": int(r.cantidad_ventas or 0),
            "total_vendido": float(r.total_vendido or 0),
        }
        for r in rows
    ]


def ventas_por_cliente(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
) -> Sequence[dict[str, Any]]:
    """
    Ventas agregadas por cliente (persona) en el rango de fechas.
    Incluye ventas sin cliente como cliente_id=None, cliente_nombre="Sin asignar".
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()
    stmt = (
        select(
            Venta.cliente_id,
            func.max(Persona.nombre).label("nombre"),
            func.max(Persona.apellido).label("apellido"),
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
        )
        .select_from(Venta)
        .outerjoin(Persona, Venta.cliente_id == Persona.id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(Venta.cliente_id)
        .order_by(func.coalesce(func.sum(Venta.total), 0).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "cliente_id": r.cliente_id,
            "cliente_nombre": (
                f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
            ),
            "cantidad_ventas": int(r.cantidad_ventas or 0),
            "total_vendido": float(r.total_vendido or 0),
        }
        for r in rows
    ]


def ranking_clientes(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 20,
    orden_por: str = "total",
) -> list[dict[str, Any]]:
    """
    Ranking de clientes por ventas en el rango (posición 1-based).
    orden_por: 'total' (total_vendido desc) o 'cantidad' (cantidad_ventas desc).
    Incluye ventas sin cliente como "Sin asignar".
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()
    order_col = (
        func.coalesce(func.sum(Venta.total), 0).desc()
        if orden_por == "total"
        else func.count(Venta.id).desc()
    )
    stmt = (
        select(
            Venta.cliente_id,
            func.max(Persona.nombre).label("nombre"),
            func.max(Persona.apellido).label("apellido"),
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
        )
        .select_from(Venta)
        .outerjoin(Persona, Venta.cliente_id == Persona.id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(Venta.cliente_id)
        .order_by(order_col)
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "posicion": i + 1,
            "cliente_id": r.cliente_id,
            "cliente_nombre": (
                f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
            ),
            "cantidad_ventas": int(r.cantidad_ventas or 0),
            "total_vendido": float(r.total_vendido or 0),
        }
        for i, r in enumerate(rows)
    ]


def evolucion_ventas_diaria(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    """
    Devuelve una serie temporal diaria de ventas entre fecha_desde y fecha_hasta (inclusive),
    con:
    - fecha
    - cantidad_ventas
    - total_vendido
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            func.date(Venta.creado_en).label("dia"),
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
        )
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(func.date(Venta.creado_en))
        .order_by(func.date(Venta.creado_en).asc())
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "fecha": r.dia.isoformat() if hasattr(r.dia, "isoformat") else str(r.dia),
            "cantidad_ventas": int(r.cantidad_ventas or 0),
            "total_vendido": float(r.total_vendido or 0),
        }
        for r in rows
    ]


def resumen_ventas_rango(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
) -> dict[str, Any]:
    """
    Resumen agregado de ventas en un rango de fechas (inclusive):
    - cantidad_ventas
    - total_vendido
    - ticket_promedio
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()
    stmt = (
        select(
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
        )
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
    )
    row = sesion.execute(stmt).one()
    cantidad = row.cantidad_ventas or 0
    total = row.total_vendido or Decimal("0")
    ticket_promedio = total / cantidad if cantidad else Decimal("0")
    return {
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": fecha_hasta.isoformat(),
        "cantidad_ventas": cantidad,
        "total_vendido": float(total),
        "ticket_promedio": round(float(ticket_promedio), 2),
    }


# Tipos de movimiento de caja considerados ingresos vs egresos (alineado con tesoreria)
_INGRESOS_CAJA_TIPOS = ("VENTA", "INGRESO", "DEVOLUCION")
_EGRESOS_CAJA_TIPOS = ("GASTO", "RETIRO")


def reporte_consolidado(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
) -> dict[str, Any]:
    """
    Reporte consolidado del período (docs Módulo 7 §6): ventas + caja.
    Resumen: cantidad_ventas, total_vendido, ticket_promedio (ventas), total_ingresos_caja, total_egresos_caja.
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")
    resumen = resumen_ventas_rango(sesion, fecha_desde, fecha_hasta)
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt_ing = (
        select(func.coalesce(func.sum(MovimientoCaja.monto), 0))
        .where(MovimientoCaja.tipo.in_(_INGRESOS_CAJA_TIPOS))
        .where(func.date(MovimientoCaja.fecha) >= desde_str)
        .where(func.date(MovimientoCaja.fecha) <= hasta_str)
    )
    stmt_eg = (
        select(func.coalesce(func.sum(MovimientoCaja.monto), 0))
        .where(MovimientoCaja.tipo.in_(_EGRESOS_CAJA_TIPOS))
        .where(func.date(MovimientoCaja.fecha) >= desde_str)
        .where(func.date(MovimientoCaja.fecha) <= hasta_str)
    )
    total_ingresos_caja = sesion.execute(stmt_ing).scalar() or Decimal("0")
    total_egresos_caja = sesion.execute(stmt_eg).scalar() or Decimal("0")

    resumen["total_ingresos_caja"] = float(total_ingresos_caja)
    resumen["total_egresos_caja"] = float(total_egresos_caja)
    return {"resumen": resumen}


def reporte_consolidado_diario(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
) -> dict[str, Any]:
    """
    Reporte consolidado diario del período (tabla analítica por día).

    Para cada día del rango [fecha_desde, fecha_hasta] incluye:
    - fecha
    - cantidad_ventas
    - total_ventas
    - ticket_promedio
    - total_ingresos_caja
    - total_egresos_caja
    - flujo_caja (ingresos - egresos)

    Además devuelve un resumen global similar a `reporte_consolidado` pero
    agregando `flujo_caja` global para el período.
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    # Ventas agrupadas por día (excluye CANCELADA del conteo principal)
    ventas_stmt = (
        select(
            func.date(Venta.creado_en).label("dia"),
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
            func.count(
                case(
                    (Venta.estado == EstadoVenta.FIADA.value, Venta.id),
                    else_=None,
                )
            ).label("ventas_fiadas"),
            func.count(
                case(
                    (Venta.estado == EstadoVenta.CANCELADA.value, Venta.id),
                    else_=None,
                )
            ).label("cancelaciones"),
            func.count(
                func.distinct(
                    case(
                        (Venta.cliente_id.isnot(None), Venta.cliente_id),
                        else_=None,
                    )
                )
            ).label("clientes_activos"),
        )
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(func.date(Venta.creado_en))
    )
    ventas_rows = sesion.execute(ventas_stmt).all()
    ventas_por_dia: dict[str, dict] = {}
    for r in ventas_rows:
        dia_str = r.dia.isoformat() if hasattr(r.dia, "isoformat") else str(r.dia)
        ventas_por_dia[dia_str] = {
            "cantidad": int(r.cantidad_ventas or 0),
            "total": r.total_vendido or Decimal("0"),
            "ventas_fiadas": int(r.ventas_fiadas or 0),
            "cancelaciones": int(r.cancelaciones or 0),
            "clientes_activos": int(r.clientes_activos or 0),
        }

    # Items por día: unidades, productos distintos, margen estimado (excluye CANCELADA)
    items_stmt = (
        select(
            func.date(Venta.creado_en).label("dia"),
            func.coalesce(func.sum(ItemVenta.cantidad), 0).label("unidades_vendidas"),
            func.count(func.distinct(ItemVenta.producto_id)).label("productos_distintos"),
            func.coalesce(
                func.sum(ItemVenta.subtotal)
                - func.sum(ItemVenta.cantidad * Producto.costo_actual),
                0,
            ).label("margen_estimado"),
        )
        .select_from(ItemVenta)
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .join(Producto, Producto.id == ItemVenta.producto_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .where(Venta.estado != EstadoVenta.CANCELADA.value)
        .group_by(func.date(Venta.creado_en))
    )
    items_rows = sesion.execute(items_stmt).all()
    items_por_dia: dict[str, dict] = {}
    for r in items_rows:
        dia_str = r.dia.isoformat() if hasattr(r.dia, "isoformat") else str(r.dia)
        items_por_dia[dia_str] = {
            "unidades_vendidas": float(r.unidades_vendidas or 0),
            "productos_distintos": int(r.productos_distintos or 0),
            "margen_estimado": float(r.margen_estimado or 0),
        }

    # Movimientos de caja (ingresos/egresos) agrupados por día
    caja_stmt = (
        select(
            func.date(MovimientoCaja.fecha).label("dia"),
            func.coalesce(
                func.sum(
                    case(
                        (MovimientoCaja.tipo.in_(_INGRESOS_CAJA_TIPOS), MovimientoCaja.monto),
                        else_=Decimal("0"),
                    )
                ),
                0,
            ).label("total_ingresos"),
            func.coalesce(
                func.sum(
                    case(
                        (MovimientoCaja.tipo.in_(_EGRESOS_CAJA_TIPOS), MovimientoCaja.monto),
                        else_=Decimal("0"),
                    )
                ),
                0,
            ).label("total_egresos"),
        )
        .where(func.date(MovimientoCaja.fecha) >= desde_str)
        .where(func.date(MovimientoCaja.fecha) <= hasta_str)
        .group_by(func.date(MovimientoCaja.fecha))
    )
    caja_rows = sesion.execute(caja_stmt).all()
    caja_por_dia: dict[str, tuple[Decimal, Decimal]] = {}
    for r in caja_rows:
        dia_str = r.dia.isoformat() if hasattr(r.dia, "isoformat") else str(r.dia)
        total_ing = r.total_ingresos or Decimal("0")
        total_eg = r.total_egresos or Decimal("0")
        caja_por_dia[dia_str] = (total_ing, total_eg)

    # Construir filas por día presente en ventas, caja o items
    dias = sorted(
        set(ventas_por_dia.keys()) | set(caja_por_dia.keys()) | set(items_por_dia.keys())
    )
    filas: list[dict[str, Any]] = []
    total_ingresos_global = Decimal("0")
    total_egresos_global = Decimal("0")

    for dia_str in dias:
        v = ventas_por_dia.get(dia_str, {})
        cantidad_ventas = v.get("cantidad", 0)
        total_ventas = v.get("total", Decimal("0"))
        ventas_fiadas = v.get("ventas_fiadas", 0)
        cancelaciones = v.get("cancelaciones", 0)
        clientes_activos = v.get("clientes_activos", 0)

        it = items_por_dia.get(dia_str, {})
        unidades_vendidas = it.get("unidades_vendidas", 0.0)
        productos_distintos = it.get("productos_distintos", 0)
        margen_estimado = it.get("margen_estimado", 0.0)

        ingresos_caja, egresos_caja = caja_por_dia.get(
            dia_str, (Decimal("0"), Decimal("0"))
        )
        ticket_promedio = (
            (total_ventas / cantidad_ventas) if cantidad_ventas else Decimal("0")
        )
        flujo_caja = ingresos_caja - egresos_caja

        total_ingresos_global += ingresos_caja
        total_egresos_global += egresos_caja

        filas.append(
            {
                "fecha": dia_str,
                "cantidad_ventas": cantidad_ventas,
                "total_ventas": float(total_ventas),
                "ticket_promedio": round(float(ticket_promedio), 2),
                "ventas_fiadas": ventas_fiadas,
                "cancelaciones": cancelaciones,
                "clientes_activos": clientes_activos,
                "unidades_vendidas": round(unidades_vendidas, 3),
                "productos_distintos": productos_distintos,
                "margen_estimado": round(margen_estimado, 2),
                "total_ingresos_caja": float(ingresos_caja),
                "total_egresos_caja": float(egresos_caja),
                "flujo_caja": float(flujo_caja),
            }
        )

    # Resumen global usando la lógica ya existente de ventas + caja
    resumen = resumen_ventas_rango(sesion, fecha_desde, fecha_hasta)
    resumen["total_ingresos_caja"] = float(total_ingresos_global)
    resumen["total_egresos_caja"] = float(total_egresos_global)
    resumen["flujo_caja"] = float(total_ingresos_global - total_egresos_global)

    return {"resumen": resumen, "filas": filas}


def _clave_agrupacion(fecha_str: str, agrupacion: str) -> str:
    """
    Devuelve una clave de agrupación a partir de una fecha ISO (YYYY-MM-DD) y
    el tipo de agrupación:

    - "dia": mismo valor de fecha_str
    - "semana": año ISO y número de semana (YYYY-Www)
    - "mes": año y mes (YYYY-MM)
    """
    año, mes, dia = map(int, fecha_str.split("-"))
    d = date(año, mes, dia)
    if agrupacion == "dia":
        return fecha_str
    if agrupacion == "mes":
        return f"{d.year:04d}-{d.month:02d}"
    # semana ISO
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year:04d}-W{iso_week:02d}"


def reporte_consolidado_agrupado(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    agrupacion: str = "dia",
) -> dict[str, Any]:
    """
    Reporte consolidado agregado por período (día/semana/mes) a partir del
    consolidado diario existente.

    Para cada período incluye:
    - periodo: clave temporal (YYYY-MM-DD, YYYY-Www o YYYY-MM)
    - cantidad_ventas
    - total_ventas
    - ticket_promedio
    - total_ingresos_caja
    - total_egresos_caja
    - flujo_caja

    El resumen global es el mismo que el de `reporte_consolidado_diario`,
    añadiendo el campo `agrupacion`.
    """
    if agrupacion not in {"dia", "semana", "mes"}:
        raise ValueError("agrupacion inválida; debe ser 'dia', 'semana' o 'mes'")

    base = reporte_consolidado_diario(sesion, fecha_desde, fecha_hasta)

    # Si la agrupación es por día devolvemos tal cual el consolidado diario.
    if agrupacion == "dia":
        resumen = dict(base["resumen"])
        resumen["agrupacion"] = "dia"
        return {"resumen": resumen, "filas": base["filas"]}

    agrupados: dict[str, dict[str, Any]] = {}
    for fila in base["filas"]:
        fecha_str = fila["fecha"]
        clave = _clave_agrupacion(fecha_str, agrupacion)
        bucket = agrupados.get(clave)
        if bucket is None:
            bucket = {
                "periodo": clave,
                "cantidad_ventas": 0,
                "total_ventas": 0.0,
                "total_ingresos_caja": 0.0,
                "total_egresos_caja": 0.0,
            }
            agrupados[clave] = bucket

        bucket["cantidad_ventas"] += int(fila["cantidad_ventas"])
        bucket["total_ventas"] += float(fila["total_ventas"])
        bucket["total_ingresos_caja"] += float(fila["total_ingresos_caja"])
        bucket["total_egresos_caja"] += float(fila["total_egresos_caja"])

    filas_agrupadas: list[dict[str, Any]] = []
    for clave in sorted(agrupados.keys()):
        bucket = agrupados[clave]
        cantidad = bucket["cantidad_ventas"]
        total_ventas = bucket["total_ventas"]
        ingresos = bucket["total_ingresos_caja"]
        egresos = bucket["total_egresos_caja"]
        ticket_promedio = round(total_ventas / cantidad, 2) if cantidad else 0.0
        flujo_caja = ingresos - egresos
        filas_agrupadas.append(
            {
                "periodo": bucket["periodo"],
                "cantidad_ventas": cantidad,
                "total_ventas": round(total_ventas, 2),
                "ticket_promedio": ticket_promedio,
                "total_ingresos_caja": round(ingresos, 2),
                "total_egresos_caja": round(egresos, 2),
                "flujo_caja": round(flujo_caja, 2),
            }
        )

    resumen = dict(base["resumen"])
    resumen["agrupacion"] = agrupacion
    return {"resumen": resumen, "filas": filas_agrupadas}


def inventario_valorizado(sesion: Session) -> dict[str, Any]:
    """
    Devuelve el inventario valorizado por producto y el total general.

    Calcula la cantidad total en stock por producto (todas las ubicaciones) y
    multiplica por el precio_venta del producto.
    """
    stmt = (
        select(
            Producto.id.label("producto_id"),
            Producto.nombre.label("nombre_producto"),
            func.coalesce(func.sum(Stock.cantidad), 0).label("stock_total"),
            Producto.precio_venta.label("precio_venta"),
        )
        .join(Stock, Stock.producto_id == Producto.id)
        .group_by(Producto.id, Producto.nombre, Producto.precio_venta)
    )
    rows = sesion.execute(stmt).all()
    productos: list[dict[str, Any]] = []
    total_global = Decimal("0")
    for r in rows:
        stock_total = r.stock_total or Decimal("0")
        precio = r.precio_venta or Decimal("0")
        valor_total = stock_total * precio
        total_global += valor_total
        productos.append(
            {
                "producto_id": r.producto_id,
                "nombre_producto": r.nombre_producto,
                "stock_total": float(stock_total),
                "precio_venta": float(precio),
                "valor_total": float(valor_total),
            }
        )
    return {
        "productos": productos,
        "total_inventario": float(total_global),
    }


def rotacion_inventario(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Rotación de inventario por producto en un rango de fechas.

    Aproxima la rotación usando:
    - unidades_vendidas: suma de ItemVenta.cantidad en el rango
    - stock_promedio: se aproxima con el stock_total actual registrado en Stock
    - rotacion = unidades_vendidas / stock_promedio cuando stock_promedio > 0
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    # Unidades vendidas por producto en el rango
    ventas_stmt = (
        select(
            ItemVenta.producto_id,
            ItemVenta.nombre_producto,
            func.coalesce(func.sum(ItemVenta.cantidad), 0).label("unidades_vendidas"),
        )
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(ItemVenta.producto_id, ItemVenta.nombre_producto)
    )
    ventas_rows = sesion.execute(ventas_stmt).all()
    if not ventas_rows:
        return []

    # Stock actual total por producto
    stock_stmt = (
        select(
            Stock.producto_id,
            func.coalesce(func.sum(Stock.cantidad), 0).label("stock_total"),
        )
        .group_by(Stock.producto_id)
    )
    stock_rows = sesion.execute(stock_stmt).all()
    stock_por_producto: dict[int, Decimal] = {
        r.producto_id: r.stock_total or Decimal("0") for r in stock_rows
    }

    resultados: list[dict[str, Any]] = []
    for r in ventas_rows:
        unidades = Decimal(r.unidades_vendidas or 0)
        stock_total = stock_por_producto.get(r.producto_id, Decimal("0"))
        if stock_total <= 0:
            rotacion = Decimal("0")
        else:
            rotacion = unidades / stock_total
        resultados.append(
            {
                "producto_id": r.producto_id,
                "nombre_producto": r.nombre_producto,
                "unidades_vendidas": float(unidades),
                "stock_promedio_aprox": float(stock_total),
                "rotacion": float(round(rotacion, 2)),
            }
        )

    # Ordenamos por rotación descendente y aplicamos límite
    resultados.sort(key=lambda x: x["rotacion"], reverse=True)
    return resultados[:limite]


def clientes_actividad(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Actividad de clientes en un rango de fechas.

    Para cada cliente con ventas en el rango devuelve:
    - cliente_id
    - cliente_nombre
    - cantidad_ventas
    - total_vendido
    - ticket_promedio_cliente
    - fecha_ultima_venta
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            Venta.cliente_id,
            func.max(Persona.nombre).label("nombre"),
            func.max(Persona.apellido).label("apellido"),
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
            func.max(Venta.creado_en).label("ultima_venta"),
        )
        .select_from(Venta)
        .outerjoin(Persona, Venta.cliente_id == Persona.id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(Venta.cliente_id)
        .order_by(func.coalesce(func.sum(Venta.total), 0).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    resultados: list[dict[str, Any]] = []
    for r in rows:
        cantidad = int(r.cantidad_ventas or 0)
        total = Decimal(str(r.total_vendido or 0))
        ticket_promedio_cliente = total / cantidad if cantidad else Decimal("0")
        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )
        resultados.append(
            {
                "cliente_id": r.cliente_id,
                "cliente_nombre": nombre_completo,
                "cantidad_ventas": cantidad,
                "total_vendido": float(total),
                "ticket_promedio_cliente": float(round(ticket_promedio_cliente, 2)),
                "fecha_ultima_venta": r.ultima_venta.isoformat()
                if getattr(r.ultima_venta, "isoformat", None)
                else str(r.ultima_venta),
            }
        )
    return resultados


def clientes_inactivos(
    sesion: Session,
    fecha_corte: date,
    dias_inactividad: int = 30,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Clientes inactivos a una fecha de corte.

    Se consideran inactivos quienes:
    - nunca han realizado una venta, o
    - su última venta es anterior a (fecha_corte - dias_inactividad).
    """
    if dias_inactividad < 0:
        raise ValueError("dias_inactividad debe ser mayor o igual que 0")

    cutoff_date = fecha_corte - timedelta(days=dias_inactividad)
    cutoff_str = cutoff_date.isoformat()

    # Por cada persona calculamos fecha_ultima_venta (puede ser NULL).
    stmt = (
        select(
            Persona.id.label("cliente_id"),
            Persona.nombre.label("nombre"),
            Persona.apellido.label("apellido"),
            func.max(Venta.creado_en).label("ultima_venta"),
        )
        .select_from(Persona)
        .outerjoin(Venta, Venta.cliente_id == Persona.id)
        .group_by(Persona.id)
    )
    rows = sesion.execute(stmt).all()

    inactivos: list[dict[str, Any]] = []
    for r in rows:
        ultima = r.ultima_venta
        es_inactivo = False
        if ultima is None:
            es_inactivo = True
            ultima_iso = None
        else:
            ultima_fecha_str = getattr(ultima, "date", lambda: ultima)()
            # normalizamos a string YYYY-MM-DD para comparar
            if hasattr(ultima_fecha_str, "isoformat"):
                ultima_iso = ultima_fecha_str.isoformat()
            else:
                ultima_iso = str(ultima_fecha_str)
            es_inactivo = ultima_iso < cutoff_str

        if not es_inactivo:
            continue

        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )
        inactivos.append(
            {
                "cliente_id": r.cliente_id,
                "cliente_nombre": nombre_completo,
                "fecha_ultima_venta": ultima.isoformat()
                if ultima is not None and hasattr(ultima, "isoformat")
                else None,
            }
        )

    # Ordenamos por fecha_ultima_venta (None primero) y aplicamos límite
    def _orden(item: dict[str, Any]) -> tuple[int, str]:
        fv = item["fecha_ultima_venta"]
        return (0, "") if fv is None else (1, fv)

    inactivos.sort(key=_orden)
    return inactivos[:limite]


def reporte_caja_resumen(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    """
    Reporte de resumen de caja (submódulo Caja en Reportes) en un rango de fechas.

    Incluye para cada caja con actividad en el rango:
    - caja_id
    - fecha_apertura, fecha_cierre
    - saldo_inicial, saldo_final
    - total_ingresos, total_egresos (por tipos de movimiento)
    - saldo_teorico = saldo_inicial + ingresos - egresos
    - diferencia = saldo_final - saldo_teorico (si saldo_final está informado)
    - cantidad_ventas_caja, total_ventas_caja (ventas asociadas a esa caja)
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_dt = fecha_desde.isoformat()
    hasta_dt = fecha_hasta.isoformat()

    # Cajas con actividad (apertura o movimientos) en el rango.
    cajas_stmt = (
        select(Caja.id, Caja.fecha_apertura, Caja.fecha_cierre, Caja.saldo_inicial, Caja.saldo_final)
        .where(func.date(Caja.fecha_apertura) <= hasta_dt)
        .where(
            func.coalesce(func.date(Caja.fecha_cierre), hasta_dt) >= desde_dt
        )
    )
    cajas_rows = sesion.execute(cajas_stmt).all()
    if not cajas_rows:
        return []

    caja_ids = [r.id for r in cajas_rows]

    # Movimientos de caja por caja en el rango.
    movs_stmt = (
        select(
            MovimientoCaja.caja_id,
            MovimientoCaja.tipo,
            func.coalesce(func.sum(MovimientoCaja.monto), 0).label("total_monto"),
        )
        .where(MovimientoCaja.caja_id.in_(caja_ids))
        .where(func.date(MovimientoCaja.fecha) >= desde_dt)
        .where(func.date(MovimientoCaja.fecha) <= hasta_dt)
        .group_by(MovimientoCaja.caja_id, MovimientoCaja.tipo)
    )
    movs_rows = sesion.execute(movs_stmt).all()
    movs_por_caja: dict[int, dict[str, Decimal]] = {}
    for r in movs_rows:
        bucket = movs_por_caja.setdefault(r.caja_id, {})
        bucket[str(r.tipo)] = Decimal(str(r.total_monto))

    # Ventas asociadas a cada caja en el rango.
    ventas_stmt = (
        select(
            Venta.caja_id,
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_ventas"),
        )
        .where(Venta.caja_id.in_(caja_ids))
        .where(func.date(Venta.creado_en) >= desde_dt)
        .where(func.date(Venta.creado_en) <= hasta_dt)
        .group_by(Venta.caja_id)
    )
    ventas_rows = sesion.execute(ventas_stmt).all()
    ventas_por_caja: dict[int, tuple[int, Decimal]] = {}
    for r in ventas_rows:
        ventas_por_caja[r.caja_id] = (
            int(r.cantidad_ventas or 0),
            Decimal(str(r.total_ventas or 0)),
        )

    resultados: list[dict[str, Any]] = []
    ingresos_tipos = _INGRESOS_CAJA_TIPOS
    egresos_tipos = _EGRESOS_CAJA_TIPOS

    for caja in cajas_rows:
        totales_tipo = movs_por_caja.get(caja.id, {})
        total_ingresos = sum(
            (totales_tipo.get(t, Decimal("0")) for t in ingresos_tipos),
            start=Decimal("0"),
        )
        total_egresos = sum(
            (totales_tipo.get(t, Decimal("0")) for t in egresos_tipos),
            start=Decimal("0"),
        )
        saldo_inicial = Decimal(str(caja.saldo_inicial or 0))
        saldo_teorico = saldo_inicial + total_ingresos - total_egresos
        saldo_final = Decimal(str(caja.saldo_final)) if caja.saldo_final is not None else None
        diferencia = (
            (saldo_final - saldo_teorico) if saldo_final is not None else None
        )

        cant_ventas, total_ventas = ventas_por_caja.get(
            caja.id, (0, Decimal("0"))
        )

        resultados.append(
            {
                "caja_id": caja.id,
                "fecha_apertura": caja.fecha_apertura.isoformat()
                if caja.fecha_apertura
                else None,
                "fecha_cierre": caja.fecha_cierre.isoformat()
                if caja.fecha_cierre
                else None,
                "saldo_inicial": float(saldo_inicial),
                "saldo_final": float(saldo_final) if saldo_final is not None else None,
                "total_ingresos": float(total_ingresos),
                "total_egresos": float(total_egresos),
                "saldo_teorico": float(saldo_teorico),
                "diferencia": float(diferencia) if diferencia is not None else None,
                "cantidad_ventas_caja": cant_ventas,
                "total_ventas_caja": float(total_ventas),
            }
        )

    # Ordenamos por fecha_apertura descendente
    resultados.sort(key=lambda x: x["fecha_apertura"] or "", reverse=True)
    return resultados


def ventas_por_franja_horaria(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    """
    Analítica de ventas por franja horaria en un rango de fechas.

    Se agrupan las ventas por hora (0-23) usando la hora de `Venta.creado_en`
    y luego se agrupan en franjas de 2 horas:

    00:00-02:00, 02:00-04:00, ..., 22:00-24:00

    Para cada franja se calcula:
    - cantidad_ventas
    - total_vendido
    - ticket_promedio (total_vendido / cantidad_ventas)
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    # Primero agregamos por hora (0-23)
    hora_expr = func.strftime("%H", Venta.creado_en).label("hora")
    stmt = (
        select(
            hora_expr,
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
        )
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(hora_expr)
    )
    rows = sesion.execute(stmt).all()

    # Definimos franjas de 2 horas sobre el día completo
    franjas: list[tuple[int, int]] = [(h, h + 2) for h in range(0, 24, 2)]

    agregados: dict[str, dict[str, Any]] = {}

    def _label(inicio: int, fin: int) -> str:
        return f"{inicio:02d}:00-{fin:02d}:00"

    # Inicializar solo franjas que tengan datos para mantener la respuesta compacta
    for r in rows:
        hora_str = r.hora
        try:
            h = int(hora_str)
        except (TypeError, ValueError):
            continue
        # Encontrar la franja correspondiente
        for inicio, fin in franjas:
            if inicio <= h < fin:
                clave = _label(inicio, fin)
                bucket = agregados.get(clave)
                if bucket is None:
                    bucket = {
                        "franja": clave,
                        "cantidad_ventas": 0,
                        "total_vendido": 0.0,
                    }
                    agregados[clave] = bucket
                bucket["cantidad_ventas"] += int(r.cantidad_ventas or 0)
                bucket["total_vendido"] += float(r.total_vendido or 0)
                break

    # Ordenamos por inicio de franja (usando la clave textual)
    resultado: list[dict[str, Any]] = []
    for inicio, fin in franjas:
        clave = _label(inicio, fin)
        if clave in agregados:
            bucket = agregados[clave]
            total = bucket["total_vendido"]
            cantidad = bucket["cantidad_ventas"]
            ticket_promedio = round(total / cantidad, 2) if cantidad else 0.0
            resultado.append(
                {
                    "franja": bucket["franja"],
                    "cantidad_ventas": cantidad,
                    "total_vendido": round(total, 2),
                    "ticket_promedio": ticket_promedio,
                }
            )

    return resultado


def ventas_por_medio_pago(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    """
    Ventas agregadas por medio de pago en un rango de fechas.

    Para cada `Venta.metodo_pago` devuelve:
    - metodo_pago
    - cantidad_ventas
    - total_vendido
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            Venta.metodo_pago.label("metodo_pago"),
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
        )
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(Venta.metodo_pago)
        .order_by(func.coalesce(func.sum(Venta.total), 0).desc())
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "metodo_pago": r.metodo_pago,
            "cantidad_ventas": int(r.cantidad_ventas or 0),
            "total_vendido": float(r.total_vendido or 0),
        }
        for r in rows
    ]


def clientes_rentabilidad(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Rentabilidad por cliente en un rango de fechas.

    Para cada cliente devuelve:
    - cliente_id
    - cliente_nombre
    - cantidad_ventas
    - total_vendido
    - total_costo
    - margen_bruto
    - margen_pct
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    total_costo_expr = func.coalesce(
        func.sum(ItemVenta.cantidad * Producto.costo_actual), Decimal("0")
    )
    total_vendido_expr = func.coalesce(func.sum(ItemVenta.subtotal), Decimal("0"))

    stmt = (
        select(
            Venta.cliente_id,
            func.max(Persona.nombre).label("nombre"),
            func.max(Persona.apellido).label("apellido"),
            func.count(Venta.id).label("cantidad_ventas"),
            total_vendido_expr.label("total_vendido"),
            total_costo_expr.label("total_costo"),
        )
        .select_from(Venta)
        .outerjoin(Persona, Venta.cliente_id == Persona.id)
        .join(ItemVenta, ItemVenta.venta_id == Venta.id)
        .join(Producto, Producto.id == ItemVenta.producto_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(Venta.cliente_id)
        .order_by((total_vendido_expr - total_costo_expr).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()

    resultados: list[dict[str, Any]] = []
    for r in rows:
        tv = float(r.total_vendido)
        tc = float(r.total_costo)
        margen_bruto = tv - tc
        margen_pct = round((margen_bruto / tv * 100), 2) if tv else 0.0
        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )
        resultados.append(
            {
                "cliente_id": r.cliente_id,
                "cliente_nombre": nombre_completo,
                "cantidad_ventas": int(r.cantidad_ventas or 0),
                "total_vendido": tv,
                "total_costo": tc,
                "margen_bruto": round(margen_bruto, 2),
                "margen_pct": margen_pct,
            }
        )

    return resultados


def proveedores_volumen_compras(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
) -> list[dict[str, Any]]:
    """
    Volumen de compras por proveedor en un rango de fechas.

    Devuelve por proveedor:
    - proveedor_id
    - proveedor_nombre
    - cantidad_compras
    - total_comprado
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            Compra.proveedor_id,
            func.max(Persona.nombre).label("nombre"),
            func.max(Persona.apellido).label("apellido"),
            func.count(Compra.id).label("cantidad_compras"),
            func.coalesce(func.sum(Compra.total), 0).label("total_comprado"),
        )
        .select_from(Compra)
        .join(Persona, Compra.proveedor_id == Persona.id)
        .where(func.date(Compra.fecha) >= desde_str)
        .where(func.date(Compra.fecha) <= hasta_str)
        .group_by(Compra.proveedor_id)
        .order_by(func.coalesce(func.sum(Compra.total), 0).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    resultados: list[dict[str, Any]] = []
    for r in rows:
        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )
        resultados.append(
            {
                "proveedor_id": r.proveedor_id,
                "proveedor_nombre": nombre_completo,
                "cantidad_compras": int(r.cantidad_compras or 0),
                "total_comprado": float(r.total_comprado or 0),
            }
        )
    return resultados


def proveedores_productos_suministrados(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    proveedor_id: int | None = None,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Productos suministrados por proveedor en un rango de fechas.

    Devuelve filas con:
    - proveedor_id
    - proveedor_nombre
    - producto_id
    - nombre_producto
    - cantidad_comprada
    - total_comprado
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            Compra.proveedor_id,
            func.max(Persona.nombre).label("nombre"),
            func.max(Persona.apellido).label("apellido"),
            ItemCompra.producto_id,
            func.max(ItemCompra.nombre_producto).label("nombre_producto"),
            func.coalesce(func.sum(ItemCompra.cantidad), 0).label("cantidad_comprada"),
            func.coalesce(func.sum(ItemCompra.subtotal), 0).label("total_comprado"),
        )
        .select_from(Compra)
        .join(Persona, Compra.proveedor_id == Persona.id)
        .join(ItemCompra, ItemCompra.compra_id == Compra.id)
        .where(func.date(Compra.fecha) >= desde_str)
        .where(func.date(Compra.fecha) <= hasta_str)
    )
    if proveedor_id is not None:
        stmt = stmt.where(Compra.proveedor_id == proveedor_id)

    stmt = (
        stmt.group_by(Compra.proveedor_id, ItemCompra.producto_id)
        .order_by(func.coalesce(func.sum(ItemCompra.subtotal), 0).desc())
        .limit(limite)
    )

    rows = sesion.execute(stmt).all()
    resultados: list[dict[str, Any]] = []
    for r in rows:
        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )
        resultados.append(
            {
                "proveedor_id": r.proveedor_id,
                "proveedor_nombre": nombre_completo,
                "producto_id": r.producto_id,
                "nombre_producto": r.nombre_producto,
                "cantidad_comprada": float(r.cantidad_comprada or 0),
                "total_comprado": float(r.total_comprado or 0),
            }
        )
    return resultados


def ranking_proveedores(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 20,
    orden_por: str = "total",
) -> list[dict[str, Any]]:
    """
    Ranking de proveedores según volumen de compras en el rango.

    orden_por:
    - 'total': ordena por total_comprado descendente
    - 'cantidad': ordena por cantidad_compras descendente
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    cantidad_expr = func.count(Compra.id)
    total_expr = func.coalesce(func.sum(Compra.total), 0)

    order_col = total_expr.desc() if orden_por == "total" else cantidad_expr.desc()

    stmt = (
        select(
            Compra.proveedor_id,
            func.max(Persona.nombre).label("nombre"),
            func.max(Persona.apellido).label("apellido"),
            cantidad_expr.label("cantidad_compras"),
            total_expr.label("total_comprado"),
        )
        .select_from(Compra)
        .join(Persona, Compra.proveedor_id == Persona.id)
        .where(func.date(Compra.fecha) >= desde_str)
        .where(func.date(Compra.fecha) <= hasta_str)
        .group_by(Compra.proveedor_id)
        .order_by(order_col)
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    resultados: list[dict[str, Any]] = []
    for i, r in enumerate(rows):
        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )
        resultados.append(
            {
                "posicion": i + 1,
                "proveedor_id": r.proveedor_id,
                "proveedor_nombre": nombre_completo,
                "cantidad_compras": int(r.cantidad_compras or 0),
                "total_comprado": float(r.total_comprado or 0),
            }
        )
    return resultados


def variacion_costos_productos(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Variación de costos de productos en un rango de fechas (submódulo Proveedores).

    Para cada producto con compras registradas en el rango calcula:
    - producto_id
    - nombre_producto
    - costo_min
    - costo_max
    - costo_promedio
    - variacion_absoluta = costo_max - costo_min
    - variacion_pct = (variacion_absoluta / costo_min * 100) cuando costo_min > 0
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    costo_min_expr = func.min(ItemCompra.costo_unitario)
    costo_max_expr = func.max(ItemCompra.costo_unitario)
    costo_prom_expr = func.avg(ItemCompra.costo_unitario)

    stmt = (
        select(
            ItemCompra.producto_id,
            func.max(ItemCompra.nombre_producto).label("nombre_producto"),
            costo_min_expr.label("costo_min"),
            costo_max_expr.label("costo_max"),
            costo_prom_expr.label("costo_promedio"),
        )
        .select_from(Compra)
        .join(ItemCompra, ItemCompra.compra_id == Compra.id)
        .where(func.date(Compra.fecha) >= desde_str)
        .where(func.date(Compra.fecha) <= hasta_str)
        .group_by(ItemCompra.producto_id)
        .order_by(costo_prom_expr.desc())
        .limit(limite)
    )

    rows = sesion.execute(stmt).all()
    resultados: list[dict[str, Any]] = []
    for r in rows:
        costo_min = float(r.costo_min or 0)
        costo_max = float(r.costo_max or 0)
        costo_prom = float(r.costo_promedio or 0)
        variacion_abs = costo_max - costo_min
        variacion_pct = round((variacion_abs / costo_min * 100), 2) if costo_min > 0 else 0.0
        resultados.append(
            {
                "producto_id": r.producto_id,
                "nombre_producto": r.nombre_producto,
                "costo_min": round(costo_min, 2),
                "costo_max": round(costo_max, 2),
                "costo_promedio": round(costo_prom, 2),
                "variacion_absoluta": round(variacion_abs, 2),
                "variacion_pct": variacion_pct,
            }
        )

    return resultados


def proveedores_impacto_costos(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
) -> list[dict[str, Any]]:
    """
    Impacto combinado de costos por proveedor en un rango de fechas.

    Para cada proveedor calcula:
    - proveedor_id, proveedor_nombre
    - total_comprado (volumen económico)
    - costo_min, costo_max, costo_promedio (sobre todos los ítems comprados)
    - variacion_absoluta = costo_max - costo_min
    - variacion_pct = (variacion_absoluta / costo_min * 100) cuando costo_min > 0

    Útil para priorizar proveedores con mayor peso económico y mayor variación de costos.
    """
    if fecha_desde > fecha_hasta:
        raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    costo_min_expr = func.min(ItemCompra.costo_unitario)
    costo_max_expr = func.max(ItemCompra.costo_unitario)
    costo_prom_expr = func.avg(ItemCompra.costo_unitario)
    total_expr = func.coalesce(func.sum(ItemCompra.subtotal), 0)

    stmt = (
        select(
            Compra.proveedor_id,
            func.max(Persona.nombre).label("nombre"),
            func.max(Persona.apellido).label("apellido"),
            total_expr.label("total_comprado"),
            costo_min_expr.label("costo_min"),
            costo_max_expr.label("costo_max"),
            costo_prom_expr.label("costo_promedio"),
        )
        .select_from(Compra)
        .join(Persona, Compra.proveedor_id == Persona.id)
        .join(ItemCompra, ItemCompra.compra_id == Compra.id)
        .where(func.date(Compra.fecha) >= desde_str)
        .where(func.date(Compra.fecha) <= hasta_str)
        .group_by(Compra.proveedor_id)
        .order_by(total_expr.desc())
        .limit(limite)
    )

    rows = sesion.execute(stmt).all()
    resultados: list[dict[str, Any]] = []
    for r in rows:
        total_comprado = float(r.total_comprado or 0)
        costo_min = float(r.costo_min or 0)
        costo_max = float(r.costo_max or 0)
        costo_prom = float(r.costo_promedio or 0)
        variacion_abs = costo_max - costo_min
        variacion_pct = round((variacion_abs / costo_min * 100), 2) if costo_min > 0 else 0.0
        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )
        resultados.append(
            {
                "proveedor_id": r.proveedor_id,
                "proveedor_nombre": nombre_completo,
                "total_comprado": round(total_comprado, 2),
                "costo_min": round(costo_min, 2),
                "costo_max": round(costo_max, 2),
                "costo_promedio": round(costo_prom, 2),
                "variacion_absoluta": round(variacion_abs, 2),
                "variacion_pct": variacion_pct,
            }
        )

    return resultados


def proveedores_riesgo_costos(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
) -> list[dict[str, Any]]:
    """
    Ranking de proveedores por "riesgo de costos" en un rango de fechas.

    Define una métrica de riesgo simple:
    - riesgo = total_comprado * (variacion_pct / 100)

    donde:
    - total_comprado = sum(ItemCompra.subtotal) por proveedor
    - variacion_pct se calcula como en `proveedores_impacto_costos`.

    Devuelve proveedores ordenados descendentemente por riesgo.
    """
    impacto = proveedores_impacto_costos(sesion, fecha_desde, fecha_hasta, limite=limite)
    for fila in impacto:
        total = float(fila.get("total_comprado", 0) or 0)
        var_pct = float(fila.get("variacion_pct", 0) or 0)
        riesgo = total * (var_pct / 100.0)
        fila["riesgo_costos"] = round(riesgo, 2)
    impacto.sort(key=lambda x: x["riesgo_costos"], reverse=True)
    return impacto[:limite]


def clientes_cartera_riesgo(
    sesion: Session,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Panorama de riesgo de cartera de clientes basado en cuenta corriente.

    Para cada cliente con cuenta corriente devuelve:
    - cliente_id (Persona.id)
    - cliente_nombre
    - saldo (deuda actual; > 0 implica deuda)
    - limite_credito
    - porcentaje_utilizado = saldo / limite_credito * 100 (cuando limite_credito > 0)

    Ordenado por saldo descendente.
    """
    stmt = (
        select(
            Persona.id.label("persona_id"),
            Persona.nombre.label("nombre"),
            Persona.apellido.label("apellido"),
            CuentaCorrienteCliente.saldo.label("saldo"),
            Cliente.limite_credito.label("limite_credito"),
        )
        .select_from(CuentaCorrienteCliente)
        .join(Cliente, CuentaCorrienteCliente.cliente_id == Cliente.id)
        .join(Persona, Cliente.persona_id == Persona.id)
        .order_by(CuentaCorrienteCliente.saldo.desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()

    resultados: list[dict[str, Any]] = []
    for r in rows:
        saldo = Decimal(str(r.saldo or 0))
        limite_credito = (
            Decimal(str(r.limite_credito)) if r.limite_credito is not None else None
        )
        if limite_credito and limite_credito > 0:
            pct = float(round((saldo / limite_credito) * 100, 2))
        else:
            pct = 0.0
        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )
        resultados.append(
            {
                "cliente_id": r.persona_id,
                "cliente_nombre": nombre_completo,
                "saldo": float(saldo),
                "limite_credito": float(limite_credito)
                if limite_credito is not None
                else None,
                "porcentaje_utilizado": pct,
            }
        )
    return resultados


def clientes_cartera_morosidad(
    sesion: Session,
    fecha_corte: date | None = None,
    limite: int = 100,
) -> dict[str, Any]:
    """
    Análisis de morosidad de cartera de clientes basado en cuenta corriente.

    Para cada cliente con saldo > 0 devuelve:
    - cliente_id (Persona.id)
    - cliente_nombre
    - saldo (deuda actual)
    - limite_credito
    - porcentaje_utilizado
    - dias_morosidad: días desde la última venta/ajuste que incrementó la deuda
    - tramo_morosidad: bucket de mora según dias_morosidad:
        - 'al_dia' (<= 30 días)
        - 'vencido_31_60'
        - 'vencido_61_90'
        - 'vencido_90_mas'
        - 'sin_movimientos' (no se detectan movimientos que incrementen deuda)

    Además devuelve un resumen agregado con:
    - fecha_corte
    - total_clientes
    - saldo_total
    - saldo_vencido_total (suma de saldos en tramos vencidos)
    - distribucion_tramos: dict tramo -> {'clientes', 'saldo'}
    """
    if fecha_corte is None:
        fecha_corte = date.today()

    # Para estimar morosidad tomamos la última fecha de movimiento que incrementó la deuda:
    # - VENTA siempre incrementa
    # - AJUSTE puede incrementar o no, pero a efectos de simplicidad lo consideramos como
    #   fecha relevante de actualización de deuda cuando existe.
    ultima_venta_expr = func.max(
        case(
            (
                MovimientoCuentaCorriente.tipo.in_(("VENTA", "AJUSTE")),
                MovimientoCuentaCorriente.fecha,
            ),
            else_=None,
        )
    ).label("ultima_venta_credito")

    stmt = (
        select(
            Persona.id.label("persona_id"),
            Persona.nombre.label("nombre"),
            Persona.apellido.label("apellido"),
            CuentaCorrienteCliente.saldo.label("saldo"),
            Cliente.limite_credito.label("limite_credito"),
            ultima_venta_expr,
        )
        .select_from(CuentaCorrienteCliente)
        .join(Cliente, CuentaCorrienteCliente.cliente_id == Cliente.id)
        .join(Persona, Cliente.persona_id == Persona.id)
        .outerjoin(
            MovimientoCuentaCorriente,
            MovimientoCuentaCorriente.cuenta_id == CuentaCorrienteCliente.id,
        )
        .where(CuentaCorrienteCliente.saldo > 0)
        .group_by(
            Persona.id,
            Persona.nombre,
            Persona.apellido,
            CuentaCorrienteCliente.saldo,
            Cliente.limite_credito,
        )
        .order_by(CuentaCorrienteCliente.saldo.desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()

    def _clasificar_tramo(dias: int | None) -> str:
        if dias is None:
            return "sin_movimientos"
        if dias <= 30:
            return "al_dia"
        if dias <= 60:
            return "vencido_31_60"
        if dias <= 90:
            return "vencido_61_90"
        return "vencido_90_mas"

    filas: list[dict[str, Any]] = []
    saldo_total = Decimal("0")
    saldo_vencido_total = Decimal("0")
    distribucion_tramos: dict[str, dict[str, Any]] = {}

    for r in rows:
        saldo = Decimal(str(r.saldo or 0))
        limite_credito = (
            Decimal(str(r.limite_credito)) if r.limite_credito is not None else None
        )
        if limite_credito and limite_credito > 0:
            pct = float(round((saldo / limite_credito) * 100, 2))
        else:
            pct = 0.0

        ultima = getattr(r, "ultima_venta_credito", None)
        if ultima is not None:
            # Normalizamos a date
            if hasattr(ultima, "date"):
                dia_mov = ultima.date()
            else:
                dia_mov = ultima  # asumimos que ya es date
            dias_mora = max((fecha_corte - dia_mov).days, 0)
        else:
            dias_mora = None

        tramo = _clasificar_tramo(dias_mora)
        nombre_completo = (
            f"{r.nombre or ''} {r.apellido or ''}".strip() or "Sin asignar"
        )

        filas.append(
            {
                "cliente_id": r.persona_id,
                "cliente_nombre": nombre_completo,
                "saldo": float(saldo),
                "limite_credito": float(limite_credito)
                if limite_credito is not None
                else None,
                "porcentaje_utilizado": pct,
                "dias_morosidad": dias_mora,
                "tramo_morosidad": tramo,
            }
        )

        saldo_total += saldo
        # Consideramos vencido todo saldo que no esté 'al_dia' ni 'sin_movimientos'
        if tramo not in {"al_dia", "sin_movimientos"}:
            saldo_vencido_total += saldo

        dist = distribucion_tramos.setdefault(
            tramo, {"clientes": 0, "saldo": Decimal("0")}
        )
        dist["clientes"] += 1
        dist["saldo"] += saldo

    # Normalizar distribución a floats
    distribucion_tramos_float: dict[str, dict[str, Any]] = {}
    for tramo, data in distribucion_tramos.items():
        distribucion_tramos_float[tramo] = {
            "clientes": data["clientes"],
            "saldo": float(data["saldo"]),
        }

    resumen = {
        "fecha_corte": fecha_corte.isoformat(),
        "total_clientes": len(filas),
        "saldo_total": float(saldo_total),
        "saldo_vencido_total": float(saldo_vencido_total),
        "distribucion_tramos": distribucion_tramos_float,
    }

    return {"resumen": resumen, "filas": filas}


# ---------------------------------------------------------------------------
# Nuevas funciones — brechas funcionales Módulo 7 (Reportes)
# ---------------------------------------------------------------------------


def ventas_por_categoria(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 50,
) -> list[dict[str, Any]]:
    """
    Ventas agrupadas por categoría de producto en el rango de fechas (docs §9).
    Devuelve: categoria_id, categoria_nombre, cantidad_vendida, total_vendido.
    Ventas canceladas se excluyen.
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()
    stmt = (
        select(
            CategoriaProducto.id.label("categoria_id"),
            CategoriaProducto.nombre.label("categoria_nombre"),
            func.coalesce(func.sum(ItemVenta.cantidad), 0).label("cantidad_vendida"),
            func.coalesce(func.sum(ItemVenta.subtotal), 0).label("total_vendido"),
        )
        .select_from(ItemVenta)
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .join(Producto, Producto.id == ItemVenta.producto_id)
        .outerjoin(CategoriaProducto, CategoriaProducto.id == Producto.categoria_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .where(Venta.estado != EstadoVenta.CANCELADA.value)
        .group_by(CategoriaProducto.id, CategoriaProducto.nombre)
        .order_by(func.coalesce(func.sum(ItemVenta.subtotal), 0).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "categoria_id": r.categoria_id,
            "categoria_nombre": r.categoria_nombre or "Sin categoría",
            "cantidad_vendida": float(r.cantidad_vendida or 0),
            "total_vendido": float(r.total_vendido or 0),
        }
        for r in rows
    ]


def ventas_canceladas(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 100,
) -> dict[str, Any]:
    """
    Reporte de ventas canceladas en el rango de fechas (docs §7).
    Devuelve resumen (total_canceladas, monto_total) y filas de detalle.
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            Venta.id,
            Venta.numero_ticket,
            Venta.total,
            Venta.metodo_pago,
            Venta.creado_en,
            Venta.usuario_id,
            func.coalesce(
                func.max(Persona.nombre + " " + func.coalesce(Persona.apellido, "")),
                "Sin asignar",
            ).label("cliente_nombre"),
        )
        .select_from(Venta)
        .outerjoin(Persona, Venta.cliente_id == Persona.id)
        .where(Venta.estado == EstadoVenta.CANCELADA.value)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .group_by(
            Venta.id,
            Venta.numero_ticket,
            Venta.total,
            Venta.metodo_pago,
            Venta.creado_en,
            Venta.usuario_id,
        )
        .order_by(Venta.creado_en.desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()

    stmt_resumen = select(
        func.count(Venta.id).label("total_canceladas"),
        func.coalesce(func.sum(Venta.total), 0).label("monto_total"),
    ).where(
        Venta.estado == EstadoVenta.CANCELADA.value,
        func.date(Venta.creado_en) >= desde_str,
        func.date(Venta.creado_en) <= hasta_str,
    )
    res = sesion.execute(stmt_resumen).one()

    return {
        "resumen": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "total_canceladas": int(res.total_canceladas or 0),
            "monto_total": float(res.monto_total or 0),
        },
        "filas": [
            {
                "venta_id": r.id,
                "numero_ticket": r.numero_ticket,
                "total": float(r.total or 0),
                "metodo_pago": r.metodo_pago,
                "creado_en": r.creado_en.isoformat() if r.creado_en else None,
                "cliente_nombre": (r.cliente_nombre or "Sin asignar").strip() or "Sin asignar",
            }
            for r in rows
        ],
    }


def inventario_bajo_minimo(
    sesion: Session,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Listado de productos cuyo stock total es inferior al stock mínimo configurado (docs §10).
    Devuelve: producto_id, nombre_producto, stock_actual, stock_minimo, diferencia.
    """
    stmt = (
        select(
            Producto.id.label("producto_id"),
            Producto.nombre.label("nombre_producto"),
            func.coalesce(func.sum(Stock.cantidad), 0).label("stock_actual"),
            Producto.stock_minimo.label("stock_minimo"),
        )
        .select_from(Producto)
        .outerjoin(Stock, Stock.producto_id == Producto.id)
        .where(Producto.stock_minimo > 0)
        .group_by(Producto.id, Producto.nombre, Producto.stock_minimo)
        .having(func.coalesce(func.sum(Stock.cantidad), 0) < Producto.stock_minimo)
        .order_by(
            (Producto.stock_minimo - func.coalesce(func.sum(Stock.cantidad), 0)).desc()
        )
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "producto_id": r.producto_id,
            "nombre_producto": r.nombre_producto,
            "stock_actual": float(r.stock_actual or 0),
            "stock_minimo": float(r.stock_minimo or 0),
            "diferencia": round(float(r.stock_minimo or 0) - float(r.stock_actual or 0), 3),
        }
        for r in rows
    ]


def mermas_por_periodo(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    limite: int = 100,
) -> dict[str, Any]:
    """
    Reporte de mermas registradas en MovimientoInventario en el rango de fechas (docs §10).
    Devuelve resumen (total_movimientos, total_unidades_merma) y filas agrupadas por producto.
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()
    stmt = (
        select(
            Producto.id.label("producto_id"),
            Producto.nombre.label("nombre_producto"),
            func.count(MovimientoInventario.id).label("cantidad_registros"),
            func.coalesce(func.sum(MovimientoInventario.cantidad), 0).label("total_unidades"),
        )
        .select_from(MovimientoInventario)
        .join(Producto, Producto.id == MovimientoInventario.producto_id)
        .where(MovimientoInventario.tipo == "MERMA")
        .where(func.date(MovimientoInventario.fecha) >= desde_str)
        .where(func.date(MovimientoInventario.fecha) <= hasta_str)
        .group_by(Producto.id, Producto.nombre)
        .order_by(func.coalesce(func.sum(MovimientoInventario.cantidad), 0).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()
    filas = [
        {
            "producto_id": r.producto_id,
            "nombre_producto": r.nombre_producto,
            "cantidad_registros": int(r.cantidad_registros or 0),
            "total_unidades": float(r.total_unidades or 0),
        }
        for r in rows
    ]
    total_movimientos = sum(f["cantidad_registros"] for f in filas)
    total_unidades = sum(f["total_unidades"] for f in filas)
    return {
        "resumen": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "total_movimientos": total_movimientos,
            "total_unidades_merma": round(total_unidades, 3),
        },
        "filas": filas,
    }


# ---------------------------------------------------------------------------
# Reporte de operaciones comerciales (docs §7 — devoluciones, notas, cambios)
# ---------------------------------------------------------------------------

def reporte_operaciones_comerciales(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    *,
    tipo: str | None = None,
    limite: int = 200,
) -> dict[str, Any]:
    """
    Reporte de operaciones comerciales post-venta en el rango de fechas.
    Incluye: DEVOLUCION, CAMBIO_PRODUCTO, NOTA_CREDITO, NOTA_DEBITO,
    CREDITO_CUENTA_CORRIENTE, ANULACION.
    Docs Módulo 7 §7 — Ventas: devoluciones, notas de crédito/débito.
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            OperacionComercial.id,
            OperacionComercial.tipo,
            OperacionComercial.estado,
            OperacionComercial.importe_total,
            OperacionComercial.motivo,
            OperacionComercial.creado_en,
            OperacionComercial.venta_id,
            OperacionComercial.cliente_id,
            func.coalesce(
                Persona.nombre + " " + func.coalesce(Persona.apellido, ""),
                "Sin asignar",
            ).label("cliente_nombre"),
        )
        .outerjoin(Persona, OperacionComercial.cliente_id == Persona.id)
        .where(func.date(OperacionComercial.creado_en) >= desde_str)
        .where(func.date(OperacionComercial.creado_en) <= hasta_str)
    )
    if tipo:
        stmt = stmt.where(OperacionComercial.tipo == tipo.upper())
    stmt = stmt.order_by(OperacionComercial.creado_en.desc()).limit(limite)
    rows = sesion.execute(stmt).all()

    # Resumen por tipo
    stmt_resumen = (
        select(
            OperacionComercial.tipo,
            func.count(OperacionComercial.id).label("cantidad"),
            func.coalesce(func.sum(OperacionComercial.importe_total), 0).label("importe_total"),
        )
        .where(func.date(OperacionComercial.creado_en) >= desde_str)
        .where(func.date(OperacionComercial.creado_en) <= hasta_str)
        .group_by(OperacionComercial.tipo)
    )
    if tipo:
        stmt_resumen = stmt_resumen.where(OperacionComercial.tipo == tipo.upper())
    resumen_rows = sesion.execute(stmt_resumen).all()

    por_tipo: dict[str, dict[str, Any]] = {}
    for r in resumen_rows:
        por_tipo[r.tipo] = {
            "cantidad": int(r.cantidad or 0),
            "importe_total": round(float(r.importe_total or 0), 2),
        }

    filas = [
        {
            "operacion_id": r.id,
            "tipo": r.tipo,
            "estado": r.estado,
            "importe_total": float(r.importe_total or 0),
            "motivo": r.motivo,
            "creado_en": r.creado_en.isoformat() if r.creado_en else None,
            "venta_id": r.venta_id,
            "cliente_id": r.cliente_id,
            "cliente_nombre": r.cliente_nombre,
        }
        for r in rows
    ]

    return {
        "resumen": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "total_operaciones": len(filas),
            "total_importe": round(sum(f["importe_total"] for f in filas), 2),
            "por_tipo": por_tipo,
        },
        "filas": filas,
    }


# ---------------------------------------------------------------------------
# Reporte de ventas por caja (docs §8 — submódulo Caja)
# ---------------------------------------------------------------------------

def ventas_por_caja(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    """
    Ventas agrupadas por caja en el período indicado.
    Docs Módulo 7 §8 — Caja: ventas por caja, ventas por cajero.
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            Venta.caja_id,
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_ventas"),
            func.coalesce(func.sum(
                case((Venta.estado == EstadoVenta.FIADA.value, Venta.total), else_=0)
            ), 0).label("total_fiadas"),
            func.coalesce(func.sum(
                case((Venta.estado == EstadoVenta.CANCELADA.value, Venta.total), else_=0)
            ), 0).label("total_canceladas"),
            func.count(
                case((Venta.estado == EstadoVenta.PAGADA.value, Venta.id))
            ).label("ventas_pagadas"),
        )
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .where(Venta.caja_id.isnot(None))
        .group_by(Venta.caja_id)
        .order_by(func.coalesce(func.sum(Venta.total), 0).desc())
    )
    rows = sesion.execute(stmt).all()

    resultado = []
    for r in rows:
        caja = sesion.get(Caja, r.caja_id)
        resultado.append({
            "caja_id": r.caja_id,
            "fecha_apertura": caja.fecha_apertura.isoformat() if caja and caja.fecha_apertura else None,
            "cantidad_ventas": int(r.cantidad_ventas or 0),
            "total_ventas": round(float(r.total_ventas or 0), 2),
            "total_fiadas": round(float(r.total_fiadas or 0), 2),
            "total_canceladas": round(float(r.total_canceladas or 0), 2),
            "ventas_pagadas": int(r.ventas_pagadas or 0),
        })
    return resultado


# ---------------------------------------------------------------------------
# Análisis de frecuencia de compra por cliente (docs §11)
# ---------------------------------------------------------------------------

def frecuencia_compra_clientes(
    sesion: Session,
    fecha_desde: date,
    fecha_hasta: date,
    *,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Frecuencia de compra por cliente en el período.
    Docs Módulo 7 §11 — Clientes: frecuencia de compra, valor promedio, volumen total.
    """
    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    stmt = (
        select(
            Venta.cliente_id,
            func.count(Venta.id).label("cantidad_compras"),
            func.coalesce(func.sum(Venta.total), 0).label("total_comprado"),
            func.coalesce(func.avg(Venta.total), 0).label("ticket_promedio"),
            func.min(func.date(Venta.creado_en)).label("primera_compra"),
            func.max(func.date(Venta.creado_en)).label("ultima_compra"),
        )
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .where(Venta.estado != EstadoVenta.CANCELADA.value)
        .where(Venta.cliente_id.isnot(None))
        .group_by(Venta.cliente_id)
        .order_by(func.count(Venta.id).desc())
        .limit(limite)
    )
    rows = sesion.execute(stmt).all()

    resultado = []
    for r in rows:
        persona = sesion.get(Persona, r.cliente_id)
        nombre = f"{persona.nombre} {persona.apellido}".strip() if persona else f"Cliente {r.cliente_id}"
        resultado.append({
            "cliente_id": r.cliente_id,
            "cliente_nombre": nombre,
            "cantidad_compras": int(r.cantidad_compras or 0),
            "total_comprado": round(float(r.total_comprado or 0), 2),
            "ticket_promedio": round(float(r.ticket_promedio or 0), 2),
            "primera_compra": r.primera_compra,
            "ultima_compra": r.ultima_compra,
        })
    return resultado
