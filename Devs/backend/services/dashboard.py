# Servicios del dominio Dashboard (observabilidad)
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.venta import Venta, ItemVenta
from backend.models.inventario import Lote, Stock
from backend.models.caja import Caja
from backend.models.producto import Producto
from backend.services import tesoreria as svc_tesoreria
from backend.services import alertas_inventario as svc_alertas_inventario
from backend.services import configuracion as svc_configuracion


def _indicadores_ventas_fecha(sesion: Session, dia: date) -> tuple[int, float, float]:
    """Para una fecha: (cantidad_ventas, total_ventas, ticket_promedio)."""
    fecha_str = dia.isoformat()
    stmt = (
        select(
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_ventas"),
        )
        .where(func.date(Venta.creado_en) == fecha_str)
    )
    row = sesion.execute(stmt).one()
    cantidad = row.cantidad_ventas or 0
    total = float(row.total_ventas or 0)
    ticket = total / cantidad if cantidad else 0.0
    return cantidad, total, ticket


def indicadores_hoy(sesion: Session) -> dict[str, Any]:
    """Indicadores del día: ventas, ticket promedio, caja abierta, stock bajo, valor inventario y flujo de caja."""
    hoy = date.today()
    cantidad, total, ticket_promedio = _indicadores_ventas_fecha(sesion, hoy)
    total = Decimal(str(total))
    ticket_promedio = Decimal(str(ticket_promedio))

    caja_abierta = (
        sesion.execute(select(Caja).where(Caja.fecha_cierre.is_(None)).limit(1))
        .scalars()
        .first()
    )
    hay_caja_abierta = caja_abierta is not None

    saldo_caja_teorico: float | None
    if caja_abierta is not None:
        resumen = svc_tesoreria.obtener_resumen_caja(sesion, caja_abierta.id)
        saldo_caja_teorico = float(resumen["saldo_teorico"])
    else:
        saldo_caja_teorico = None

    stock_bajo = (
        sesion.execute(
            select(func.count(Stock.id))
            .join(Producto, Producto.id == Stock.producto_id)
            .where(Stock.cantidad <= Producto.stock_minimo)
        ).scalar()
        or 0
    )

    # Valor total del inventario (todas las ubicaciones)
    stmt_inventario = (
        select(
            func.coalesce(func.sum(Stock.cantidad * Producto.precio_venta), 0).label(
                "valor_total"
            )
        )
        .join(Producto, Producto.id == Stock.producto_id)
    )
    valor_total = sesion.execute(stmt_inventario).scalar() or Decimal("0")

    return {
        "fecha": hoy.isoformat(),
        "ventas_del_dia": cantidad,
        "total_ventas_del_dia": float(total),
        "ticket_promedio": round(float(ticket_promedio), 2),
        "caja_abierta": hay_caja_abierta,
        "saldo_caja_teorico": saldo_caja_teorico,
        "productos_stock_bajo": stock_bajo,
        "valor_inventario": float(valor_total),
    }


def ventas_por_hora_del_dia(sesion: Session, dia: date | None = None) -> list[dict[str, Any]]:
    """
    Ventas del día agrupadas por hora (00 a 23) para el gráfico del dashboard.
    Devuelve 24 puntos: cantidad_ventas y total_vendido por hora.
    Si no hay ventas en una hora, se devuelve 0.
    """
    fecha = dia or date.today()
    fecha_str = fecha.isoformat()

    # SQLite: strftime('%H', creado_en) devuelve '00'..'23'
    stmt = (
        select(
            func.strftime("%H", Venta.creado_en).label("hora"),
            func.count(Venta.id).label("cantidad_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_vendido"),
        )
        .where(func.date(Venta.creado_en) == fecha_str)
        .group_by(func.strftime("%H", Venta.creado_en))
    )
    rows = sesion.execute(stmt).all()
    por_hora: dict[str, dict[str, Any]] = {
        f"{h:02d}": {"hora": f"{h:02d}", "cantidad_ventas": 0, "total_vendido": 0.0}
        for h in range(24)
    }
    for r in rows:
        hora_key = (r.hora or "00") if len(str(r.hora or "00")) == 2 else f"0{r.hora}"
        if hora_key not in por_hora:
            por_hora[hora_key] = {"hora": hora_key, "cantidad_ventas": 0, "total_vendido": 0.0}
        por_hora[hora_key]["cantidad_ventas"] = int(r.cantidad_ventas or 0)
        por_hora[hora_key]["total_vendido"] = float(r.total_vendido or 0)

    return [por_hora[f"{h:02d}"] for h in range(24)]


def indicadores_con_comparativa(
    sesion: Session, dia: date | None = None
) -> dict[str, Any]:
    """
    Indicadores del día con comparación vs día anterior (docs Módulo 1: valor principal,
    comparación vs periodo anterior, variación porcentual).
    Incluye todos los campos de indicadores_hoy más: fecha_anterior, ventas_del_dia_anterior,
    total_ventas_del_dia_anterior, ticket_promedio_anterior, variacion_pct_cantidad_ventas,
    variacion_pct_total_ventas, variacion_pct_ticket_promedio.
    variacion_pct es None cuando el valor anterior es 0 (no definible).
    """
    fecha = dia or date.today()
    base = indicadores_hoy(sesion) if fecha == date.today() else _indicadores_hoy_para_fecha(sesion, fecha)
    dia_anterior = fecha - timedelta(days=1)
    cant_ant, total_ant, ticket_ant = _indicadores_ventas_fecha(sesion, dia_anterior)

    def _var(actual: float, anterior: float) -> float | None:
        if anterior == 0:
            return None
        return round((actual - anterior) / anterior * 100, 2)

    cant_act = base["ventas_del_dia"]
    total_act = base["total_ventas_del_dia"]
    ticket_act = base["ticket_promedio"]

    base["comparativa"] = {
        "fecha_anterior": dia_anterior.isoformat(),
        "ventas_del_dia_anterior": cant_ant,
        "total_ventas_del_dia_anterior": round(total_ant, 2),
        "ticket_promedio_anterior": round(ticket_ant, 2),
        "variacion_pct_cantidad_ventas": _var(float(cant_act), float(cant_ant)),
        "variacion_pct_total_ventas": _var(total_act, total_ant),
        "variacion_pct_ticket_promedio": _var(ticket_act, ticket_ant),
    }
    return base


def _indicadores_hoy_para_fecha(sesion: Session, dia: date) -> dict[str, Any]:
    """Misma estructura que indicadores_hoy pero para una fecha dada (sin caja/stock del día)."""
    cantidad, total, ticket_promedio = _indicadores_ventas_fecha(sesion, dia)
    return {
        "fecha": dia.isoformat(),
        "ventas_del_dia": cantidad,
        "total_ventas_del_dia": round(total, 2),
        "ticket_promedio": round(ticket_promedio, 2),
        "caja_abierta": (
            sesion.execute(select(Caja).where(Caja.fecha_cierre.is_(None)).limit(1))
            .scalars().first() is not None
        ),
        "saldo_caja_teorico": None,
        "productos_stock_bajo": (
            sesion.execute(
                select(func.count(Stock.id))
                .join(Producto, Producto.id == Stock.producto_id)
                .where(Stock.cantidad <= Producto.stock_minimo)
            ).scalar() or 0
        ),
        "valor_inventario": float(
            sesion.execute(
                select(
                    func.coalesce(
                        func.sum(Stock.cantidad * Producto.precio_venta), 0
                    ).label("v")
                ).join(Producto, Producto.id == Stock.producto_id)
            ).scalar() or 0
        ),
    }


def productos_stock_bajo(sesion: Session) -> list[dict[str, Any]]:
    """
    Lista de productos con stock actual <= stock mínimo (alertas de reposición).
    Para cada uno: producto_id, nombre, stock_actual, stock_minimo.
    Suma stock en todas las ubicaciones por producto; sin registros de stock = 0.
    """
    stmt_agregado = (
        select(
            Stock.producto_id,
            func.sum(Stock.cantidad).label("stock_total"),
        )
        .group_by(Stock.producto_id)
    )
    subq = stmt_agregado.subquery()
    stmt = (
        select(
            Producto.id.label("producto_id"),
            Producto.nombre,
            func.coalesce(subq.c.stock_total, 0).label("stock_actual"),
            Producto.stock_minimo,
        )
        .outerjoin(subq, Producto.id == subq.c.producto_id)
        .where(func.coalesce(subq.c.stock_total, 0) <= Producto.stock_minimo)
        .order_by(func.coalesce(subq.c.stock_total, 0).asc())
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "producto_id": r.producto_id,
            "nombre": r.nombre,
            "stock_actual": float(r.stock_actual),
            "stock_minimo": float(r.stock_minimo),
        }
        for r in rows
    ]


def productos_proximos_vencer(
    sesion: Session,
    dias: int = 30,
) -> list[dict[str, Any]]:
    """
    Lista de lotes con fecha de vencimiento dentro de los próximos N días (docs Módulo 1 §3.3.1).
    Para cada lote: producto_id, nombre, lote_id, cantidad, fecha_vencimiento, dias_restantes.
    Ordenado por fecha_vencimiento ascendente.
    """
    hoy = date.today()
    limite_fecha = hoy + timedelta(days=dias)
    stmt = (
        select(Lote, Producto.nombre)
        .join(Producto, Producto.id == Lote.producto_id)
        .where(Lote.fecha_vencimiento >= hoy)
        .where(Lote.fecha_vencimiento <= limite_fecha)
        .order_by(Lote.fecha_vencimiento.asc(), Lote.id.asc())
    )
    rows = sesion.execute(stmt).all()
    return [
        {
            "producto_id": lote.producto_id,
            "nombre": nombre,
            "lote_id": lote.id,
            "cantidad": float(lote.cantidad),
            "fecha_vencimiento": lote.fecha_vencimiento.isoformat(),
            "dias_restantes": (lote.fecha_vencimiento - hoy).days,
        }
        for lote, nombre in rows
    ]


def alertas_operativas(
    sesion: Session,
    *,
    dias_vencimiento: int = 30,
    incluir_inventario: bool = True,
    incluir_tesoreria: bool = True,
) -> dict[str, Any]:
    """Consolidado de alertas operativas para Dashboard en una sola llamada."""
    out: dict[str, Any] = {"inventario": None, "tesoreria": None}

    if incluir_inventario:
        out["inventario"] = svc_alertas_inventario.detectar_alertas(
            sesion,
            ubicacion="GONDOLA",
            dias_vencimiento=dias_vencimiento,
            solo_activos=True,
            emitir_eventos=False,
        )

    if incluir_tesoreria:
        caja = svc_tesoreria.obtener_caja_abierta(sesion)
        if caja is None:
            out["tesoreria"] = {"caja_abierta": False, "caja_id": None, "saldo_caja_teorico": None}
        else:
            resumen = svc_tesoreria.obtener_resumen_caja(sesion, caja.id)
            out["tesoreria"] = {
                "caja_abierta": True,
                "caja_id": caja.id,
                "saldo_caja_teorico": float(resumen["saldo_teorico"]),
            }

    return out


def calcular_margen_dia(sesion: Session, dia: date) -> dict[str, Any]:
    """
    Calcula el margen bruto del día indicado (docs Módulo 1 §4.8).

    margen_bruto = SUM((precio_unitario - costo_actual) * cantidad)
    margen_pct   = margen_bruto / total_ingresos * 100  (None si ingresos == 0)

    Solo considera ventas no canceladas.
    """
    fecha_str = dia.isoformat()

    stmt = (
        select(
            func.coalesce(
                func.sum(
                    (ItemVenta.precio_unitario - Producto.costo_actual) * ItemVenta.cantidad
                ),
                0,
            ).label("margen_bruto"),
            func.coalesce(func.sum(ItemVenta.subtotal), 0).label("total_ingresos"),
            func.coalesce(func.count(func.distinct(Venta.id)), 0).label("cantidad_ventas"),
        )
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .join(Producto, Producto.id == ItemVenta.producto_id)
        .where(func.date(Venta.creado_en) == fecha_str)
        .where(Venta.estado != "CANCELADA")
    )
    row = sesion.execute(stmt).one()
    margen_bruto = float(row.margen_bruto or 0)
    total_ingresos = float(row.total_ingresos or 0)
    margen_pct = round(margen_bruto / total_ingresos * 100, 2) if total_ingresos > 0 else None

    return {
        "fecha": fecha_str,
        "margen_bruto": round(margen_bruto, 2),
        "total_ingresos": round(total_ingresos, 2),
        "margen_pct": margen_pct,
    }


def top_productos(
    sesion: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """
    Top productos por total facturado en el período.
    Docs Módulo 1 §3.1 — KPIs principales / análisis comercial.
    """
    from backend.models.venta import ItemVenta, Venta

    stmt = (
        select(
            ItemVenta.producto_id,
            ItemVenta.nombre_producto,
            func.count(func.distinct(Venta.id)).label("cantidad_ventas"),
            func.sum(ItemVenta.cantidad).label("unidades_vendidas"),
            func.sum(ItemVenta.subtotal).label("total_facturado"),
        )
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .where(Venta.estado != "CANCELADA")
        .group_by(ItemVenta.producto_id, ItemVenta.nombre_producto)
        .order_by(func.sum(ItemVenta.subtotal).desc())
        .limit(limite)
    )
    if fecha_desde:
        stmt = stmt.where(func.date(Venta.creado_en) >= fecha_desde.isoformat())
    if fecha_hasta:
        stmt = stmt.where(func.date(Venta.creado_en) <= fecha_hasta.isoformat())

    rows = sesion.execute(stmt).all()
    return [
        {
            "posicion": i + 1,
            "producto_id": r.producto_id,
            "nombre": r.nombre_producto,
            "cantidad_ventas": int(r.cantidad_ventas or 0),
            "unidades_vendidas": float(r.unidades_vendidas or 0),
            "total_facturado": round(float(r.total_facturado or 0), 2),
        }
        for i, r in enumerate(rows)
    ]


def tendencias_ventas(
    sesion: Session,
    *,
    periodo: str = "semanal",
    cantidad_periodos: int = 8,
) -> list[dict[str, Any]]:
    """
    Tendencias de ventas en los últimos N períodos (diario, semanal, mensual).
    Docs Módulo 1 §3.1 — KPIs con comparación vs período anterior.
    periodo: 'diario' | 'semanal' | 'mensual'
    """
    from backend.models.venta import Venta

    hoy = date.today()
    resultado = []

    if periodo == "diario":
        for i in range(cantidad_periodos - 1, -1, -1):
            d = hoy - timedelta(days=i)
            cant, total, ticket = _indicadores_ventas_fecha(sesion, d)
            resultado.append({
                "periodo": d.isoformat(),
                "etiqueta": d.strftime("%d/%m"),
                "cantidad_ventas": cant,
                "total_ventas": round(total, 2),
                "ticket_promedio": round(ticket, 2),
            })

    elif periodo == "semanal":
        lunes_actual = hoy - timedelta(days=hoy.weekday())
        for i in range(cantidad_periodos - 1, -1, -1):
            inicio = lunes_actual - timedelta(weeks=i)
            fin = inicio + timedelta(days=6)
            fin = min(fin, hoy)
            row = sesion.execute(
                select(
                    func.count(Venta.id).label("cnt"),
                    func.coalesce(func.sum(Venta.total), 0).label("total"),
                )
                .where(func.date(Venta.creado_en) >= inicio.isoformat())
                .where(func.date(Venta.creado_en) <= fin.isoformat())
                .where(Venta.estado != "CANCELADA")
            ).one()
            cnt = int(row.cnt or 0)
            total = float(row.total or 0)
            resultado.append({
                "periodo": f"{inicio.isoformat()}/{fin.isoformat()}",
                "etiqueta": f"S{inicio.strftime('%W')} {inicio.strftime('%d/%m')}",
                "cantidad_ventas": cnt,
                "total_ventas": round(total, 2),
                "ticket_promedio": round(total / cnt, 2) if cnt else 0.0,
            })

    elif periodo == "mensual":
        for i in range(cantidad_periodos - 1, -1, -1):
            mes_offset = hoy.month - i
            anio = hoy.year + (mes_offset - 1) // 12
            mes = ((mes_offset - 1) % 12) + 1
            inicio = date(anio, mes, 1)
            if mes == 12:
                fin = date(anio + 1, 1, 1) - timedelta(days=1)
            else:
                fin = date(anio, mes + 1, 1) - timedelta(days=1)
            fin = min(fin, hoy)
            row = sesion.execute(
                select(
                    func.count(Venta.id).label("cnt"),
                    func.coalesce(func.sum(Venta.total), 0).label("total"),
                )
                .where(func.date(Venta.creado_en) >= inicio.isoformat())
                .where(func.date(Venta.creado_en) <= fin.isoformat())
                .where(Venta.estado != "CANCELADA")
            ).one()
            cnt = int(row.cnt or 0)
            total = float(row.total or 0)
            resultado.append({
                "periodo": inicio.strftime("%Y-%m"),
                "etiqueta": inicio.strftime("%b %Y"),
                "cantidad_ventas": cnt,
                "total_ventas": round(total, 2),
                "ticket_promedio": round(total / cnt, 2) if cnt else 0.0,
            })

    else:
        raise ValueError("periodo inválido; opciones: diario, semanal, mensual")

    return resultado


def _calcular_ingresos_periodo(
    sesion: Session,
    fecha_inicio: date,
    fecha_fin: date,
) -> float:
    """Suma total de ventas en el rango [fecha_inicio, fecha_fin] (incluye extremos)."""
    stmt = (
        select(func.coalesce(func.sum(Venta.total), 0))
        .where(func.date(Venta.creado_en) >= fecha_inicio.isoformat())
        .where(func.date(Venta.creado_en) <= fecha_fin.isoformat())
        .where(Venta.estado != "CANCELADA")
    )
    return float(sesion.execute(stmt).scalar() or 0)


def panel_lateral(sesion: Session, *, dia: date | None = None) -> dict[str, Any]:
    """
    Datos para panel lateral del dashboard (docs Módulo 1 §4).

    Calcula métricas operativas y de proyección usando:
    - ventas del día (hoy por defecto)
    - promedios históricos (últimos N días y por día de semana)
    - pronóstico simple basado en ritmo actual (total acumulado / fracción del día transcurrida)
    - punto_equilibrio y objetivo (opcionales) desde parámetro `dashboard`
    """
    fecha = dia or date.today()
    fecha_str = fecha.isoformat()

    # Config opcional
    cfg = svc_configuracion.get_parametro(sesion, "dashboard")

    def _cfg_float(key: str) -> float | None:
        v = cfg.get(key)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    punto_equilibrio = _cfg_float("punto_equilibrio_diario")
    objetivo_diario = _cfg_float("objetivo_diario")
    objetivo_semanal = _cfg_float("objetivo_semanal")
    objetivo_mensual = _cfg_float("objetivo_mensual")

    cant_hoy, total_hoy, _ticket = _indicadores_ventas_fecha(sesion, fecha)

    # Promedio últimos 7 días (excluyendo hoy): ingresos y tickets
    fin_ayer = fecha - timedelta(days=1)
    inicio_7 = fecha - timedelta(days=7)
    stmt_7 = (
        select(
            func.coalesce(func.sum(Venta.total), 0).label("total"),
            func.coalesce(func.count(Venta.id), 0).label("tickets"),
        )
        .where(func.date(Venta.creado_en) >= inicio_7.isoformat())
        .where(func.date(Venta.creado_en) <= fin_ayer.isoformat())
    )
    row_7 = sesion.execute(stmt_7).one()
    total_7 = float(row_7.total or 0)
    tickets_7 = int(row_7.tickets or 0)
    promedio_7 = round(total_7 / 7, 2)
    tickets_promedio_7 = round(tickets_7 / 7, 2)

    # Promedio para este día de la semana (últimas 8 semanas excluyendo hoy)
    dow = int(fecha.strftime("%w"))  # 0=domingo..6
    inicio_8w = fecha - timedelta(days=56)
    stmt_dow = (
        select(
            func.coalesce(func.sum(Venta.total), 0).label("total"),
            func.count(func.distinct(func.date(Venta.creado_en))).label("dias"),
        )
        .where(func.date(Venta.creado_en) >= inicio_8w.isoformat())
        .where(func.date(Venta.creado_en) <= fin_ayer.isoformat())
        .where(func.strftime("%w", Venta.creado_en) == str(dow))
    )
    row_dow = sesion.execute(stmt_dow).one()
    total_dow = float(row_dow.total or 0)
    dias_dow = int(row_dow.dias or 0)
    promedio_dow = round((total_dow / dias_dow), 2) if dias_dow else 0.0

    # Pronóstico simple: total_hoy / fracción del día transcurrida
    ahora = func.datetime("now")
    hora_actual = int(sesion.execute(select(func.strftime("%H", ahora))).scalar() or 0)
    minuto_actual = int(sesion.execute(select(func.strftime("%M", ahora))).scalar() or 0)
    segundos_transcurridos = hora_actual * 3600 + minuto_actual * 60
    fraccion = max(1 / 86400, min(1.0, segundos_transcurridos / 86400))
    pronostico = round(total_hoy / fraccion, 2) if total_hoy else 0.0

    # Salud del negocio (verde/amarillo/rojo)
    estado = "AMARILLO"
    if punto_equilibrio is not None:
        estado = "VERDE" if total_hoy >= punto_equilibrio else "ROJO"
    if objetivo_diario is not None:
        if total_hoy >= objetivo_diario:
            estado = "VERDE"
        elif punto_equilibrio is None and total_hoy > 0:
            estado = "AMARILLO"

    # Métricas complementarias
    ganancia_actual: float | None = None
    cumplimiento_pe_pct: float | None = None
    cumplimiento_obj_pct: float | None = None
    porcentaje_cumplimiento_pronostico_obj: float | None = None

    if punto_equilibrio is not None:
        ganancia_actual = round(total_hoy - punto_equilibrio, 2)
        if punto_equilibrio != 0:
            cumplimiento_pe_pct = round((total_hoy / punto_equilibrio) * 100, 2)

    if objetivo_diario is not None and objetivo_diario != 0:
        cumplimiento_obj_pct = round((total_hoy / objetivo_diario) * 100, 2)
        porcentaje_cumplimiento_pronostico_obj = round((pronostico / objetivo_diario) * 100, 2)

    # §4.7 Objetivos semanal y mensual (desde inicio de semana/mes hasta hoy)
    inicio_semana = fecha - timedelta(days=fecha.weekday())  # Lunes de la semana actual
    inicio_mes = fecha.replace(day=1)
    total_semana = _calcular_ingresos_periodo(sesion, inicio_semana, fecha)
    total_mes = _calcular_ingresos_periodo(sesion, inicio_mes, fecha)

    cumplimiento_obj_semanal_pct: float | None = None
    cumplimiento_obj_mensual_pct: float | None = None
    if objetivo_semanal is not None and objetivo_semanal != 0:
        cumplimiento_obj_semanal_pct = round((total_semana / objetivo_semanal) * 100, 2)
    if objetivo_mensual is not None and objetivo_mensual != 0:
        cumplimiento_obj_mensual_pct = round((total_mes / objetivo_mensual) * 100, 2)

    # §4.8 Margen promedio del día
    margen_info = calcular_margen_dia(sesion, fecha)
    # Tendencia vs día anterior
    margen_ayer = calcular_margen_dia(sesion, fecha - timedelta(days=1))
    tendencia_margen_pct: float | None = None
    if margen_ayer["margen_bruto"] > 0:
        tendencia_margen_pct = round(
            (margen_info["margen_bruto"] - margen_ayer["margen_bruto"])
            / margen_ayer["margen_bruto"]
            * 100,
            2,
        )

    return {
        "fecha": fecha_str,
        "ventas_del_dia": cant_hoy,
        "total_ventas_del_dia": round(total_hoy, 2),
        "punto_equilibrio_diario": punto_equilibrio,
        "objetivo_diario": objetivo_diario,
        "objetivo_semanal": objetivo_semanal,
        "objetivo_mensual": objetivo_mensual,
        "salud": {"estado": estado, "ingresos": round(total_hoy, 2)},
        "ganancia_actual": ganancia_actual,
        "cumplimiento_punto_equilibrio_diario_pct": cumplimiento_pe_pct,
        "cumplimiento_objetivo_diario_pct": cumplimiento_obj_pct,
        "cumplimiento_objetivo_semanal_pct": cumplimiento_obj_semanal_pct,
        "cumplimiento_objetivo_mensual_pct": cumplimiento_obj_mensual_pct,
        "ingresos_semana_actual": round(total_semana, 2),
        "ingresos_mes_actual": round(total_mes, 2),
        "promedios": {
            "ingresos_ultimos_7_dias": promedio_7,
            "tickets_ultimos_7_dias": tickets_promedio_7,
            "ingresos_este_dia_semana": promedio_dow,
        },
        "pronostico": {
            "total_hoy": pronostico,
            "porcentaje_cumplimiento_objetivo_diario_pct": porcentaje_cumplimiento_pronostico_obj,
        },
        "margen_dia": {
            "margen_bruto": margen_info["margen_bruto"],
            "margen_pct": margen_info["margen_pct"],
            "tendencia_vs_ayer_pct": tendencia_margen_pct,
        },
    }
