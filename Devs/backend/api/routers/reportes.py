"""Endpoints REST para Reportes."""
from datetime import date
from typing import Iterable, Mapping

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import reportes as svc_reportes
from backend.services import cuentas_corrientes as svc_cuentas_corrientes

router = APIRouter(prefix="/reportes", tags=["reportes"])


def _validar_rango_fechas(fecha_desde: date, fecha_hasta: date) -> None:
    """Lanza HTTPException 400 si fecha_desde > fecha_hasta."""
    if fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=400,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )


def _to_csv(rows: Iterable[Mapping[str, object]], columnas: list[str]) -> str:
    """
    Serializa una secuencia de dicts a CSV simple (cabecera + filas).

    - columnas define el orden y subconjunto de claves a exportar.
    - Los valores se convierten a str y se separan por comas.
    Pensado para exportación rápida a Excel/Sheets.
    """
    lineas: list[str] = []
    lineas.append(",".join(columnas))
    for row in rows:
        valores: list[str] = []
        for col in columnas:
            val = row.get(col, "")
            valores.append(str(val) if val is not None else "")
        lineas.append(",".join(valores))
    return "\n".join(lineas)


@router.get("/ventas-por-dia")
def get_ventas_por_dia(
    db: Session = Depends(get_db),
    fecha: date = Query(..., description="Fecha (YYYY-MM-DD)"),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Ventas del día (submódulo Ventas, docs Módulo 7 §7):
    cantidad de ventas, total facturado y ticket promedio para la fecha dada.
    """
    data = svc_reportes.ventas_por_dia(db, fecha)
    if formato == "csv":
        csv = _to_csv(
            [data],
            columnas=["fecha", "cantidad_ventas", "total", "ticket_promedio"],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/ventas-por-producto")
def get_ventas_por_producto(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """Ventas agregadas por producto en el rango de fechas."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    filas = list(svc_reportes.ventas_por_producto(db, fecha_desde, fecha_hasta, limite))
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "producto_id",
                "nombre_producto",
                "cantidad_vendida",
                "total_vendido",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/margen-producto")
def get_margen_producto(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    orden_por: str = Query("margen_bruto", description="Orden: 'margen_bruto', 'margen_pct' o 'total_vendido'"),
):
    """Margen por producto en el rango: total_vendido, total_costo, margen_bruto y margen_pct."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    if orden_por not in ("margen_bruto", "margen_pct", "total_vendido"):
        raise HTTPException(
            status_code=400,
            detail="orden_por debe ser 'margen_bruto', 'margen_pct' o 'total_vendido'",
        )
    return list(
        svc_reportes.margen_por_producto(
            db, fecha_desde, fecha_hasta, limite=limite, orden_por=orden_por
        )
    )


@router.get("/margen-categoria")
def get_margen_categoria(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    orden_por: str = Query(
        "margen_bruto",
        description="Orden: 'margen_bruto', 'margen_pct' o 'total_vendido'",
    ),
):
    """
    Margen por categoría de producto en el rango:
    total_vendido, total_costo, margen_bruto y margen_pct por categoría.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    if orden_por not in ("margen_bruto", "margen_pct", "total_vendido"):
        raise HTTPException(
            status_code=400,
            detail="orden_por debe ser 'margen_bruto', 'margen_pct' o 'total_vendido'",
        )
    return list(
        svc_reportes.margen_por_categoria(
            db, fecha_desde, fecha_hasta, limite=limite, orden_por=orden_por
        )
    )


@router.get("/ranking-productos")
def get_ranking_productos(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(20, ge=1, le=100),
    orden_por: str = Query("total", description="Orden: 'total' o 'cantidad'"),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """Ranking de productos más vendidos en el rango (posición 1-based)."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    if orden_por not in ("total", "cantidad"):
        raise HTTPException(
            status_code=400,
            detail="orden_por debe ser 'total' o 'cantidad'",
        )
    filas = list(
        svc_reportes.ranking_productos_mas_vendidos(
            db, fecha_desde, fecha_hasta, limite=limite, orden_por=orden_por
        )
    )
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "posicion",
                "producto_id",
                "nombre_producto",
                "cantidad_vendida",
                "total_vendido",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/ventas-por-empleado")
def get_ventas_por_empleado(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
):
    """Ventas agregadas por empleado en el rango de fechas."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    return list(svc_reportes.ventas_por_empleado(db, fecha_desde, fecha_hasta, limite))


@router.get("/ventas-por-cliente")
def get_ventas_por_cliente(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """Ventas agregadas por cliente (persona) en el rango de fechas. Incluye 'Sin asignar' si no hay cliente."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    filas = list(svc_reportes.ventas_por_cliente(db, fecha_desde, fecha_hasta, limite))
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "cliente_id",
                "cliente_nombre",
                "cantidad_ventas",
                "total_vendido",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/ranking-clientes")
def get_ranking_clientes(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(20, ge=1, le=100),
    orden_por: str = Query("total", description="Orden: 'total' o 'cantidad'"),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """Ranking de clientes por ventas en el rango (posición 1-based)."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    if orden_por not in ("total", "cantidad"):
        raise HTTPException(
            status_code=400,
            detail="orden_por debe ser 'total' o 'cantidad'",
        )
    filas = list(
        svc_reportes.ranking_clientes(
            db, fecha_desde, fecha_hasta, limite=limite, orden_por=orden_por
        )
    )
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "posicion",
                "cliente_id",
                "cliente_nombre",
                "cantidad_ventas",
                "total_vendido",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/clientes-actividad")
def get_clientes_actividad(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Reporte de actividad de clientes en el rango:
    - cantidad_ventas y total_vendido por cliente
    - ticket_promedio_cliente
    - fecha_ultima_venta
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.clientes_actividad(
            db, fecha_desde, fecha_hasta, limite=limite
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Enriquecer con saldo de cuenta corriente cuando haya cliente_id
    enriquecidas: list[dict] = []
    for fila in filas:
        cid = fila.get("cliente_id")
        if cid is not None:
            try:
                resumen = svc_cuentas_corrientes.obtener_resumen_cuenta_corriente(
                    db, cid
                )
                fila = {
                    **fila,
                    "saldo_cuenta_corriente": float(resumen["saldo"]),
                    "limite_credito": float(resumen["limite_credito"])
                    if resumen["limite_credito"] is not None
                    else None,
                }
            except ValueError:
                fila = {
                    **fila,
                    "saldo_cuenta_corriente": 0.0,
                    "limite_credito": None,
                }
        else:
            fila = {**fila, "saldo_cuenta_corriente": 0.0, "limite_credito": None}
        enriquecidas.append(fila)

    if formato == "csv":
        csv = _to_csv(
            enriquecidas,
            columnas=[
                "cliente_id",
                "cliente_nombre",
                "cantidad_ventas",
                "total_vendido",
                "ticket_promedio_cliente",
                "fecha_ultima_venta",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return enriquecidas


@router.get("/clientes-inactivos")
def get_clientes_inactivos(
    db: Session = Depends(get_db),
    fecha_corte: date = Query(..., description="Fecha de corte (YYYY-MM-DD)"),
    dias_inactividad: int = Query(
        30,
        ge=0,
        description="Días sin compras a partir de la fecha_corte para considerar inactivo.",
    ),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Reporte de clientes inactivos:
    - Nunca compraron o su última compra es anterior a fecha_corte - dias_inactividad.
    """
    try:
        filas = svc_reportes.clientes_inactivos(
            db,
            fecha_corte=fecha_corte,
            dias_inactividad=dias_inactividad,
            limite=limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "cliente_id",
                "cliente_nombre",
                "fecha_ultima_venta",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/clientes-rentabilidad")
def get_clientes_rentabilidad(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Rentabilidad por cliente en un rango de fechas.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.clientes_rentabilidad(
            db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limite=limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Enriquecer con saldo de cuenta corriente cuando haya cliente_id
    enriquecidas: list[dict] = []
    for fila in filas:
        cid = fila.get("cliente_id")
        if cid is not None:
            try:
                resumen = svc_cuentas_corrientes.obtener_resumen_cuenta_corriente(
                    db, cid
                )
                fila = {
                    **fila,
                    "saldo_cuenta_corriente": float(resumen["saldo"]),
                    "limite_credito": float(resumen["limite_credito"])
                    if resumen["limite_credito"] is not None
                    else None,
                }
            except ValueError:
                fila = {
                    **fila,
                    "saldo_cuenta_corriente": 0.0,
                    "limite_credito": None,
                }
        else:
            fila = {**fila, "saldo_cuenta_corriente": 0.0, "limite_credito": None}
        enriquecidas.append(fila)

    if formato == "csv":
        csv = _to_csv(
            enriquecidas,
            columnas=[
                "cliente_id",
                "cliente_nombre",
                "cantidad_ventas",
                "total_vendido",
                "total_costo",
                "margen_bruto",
                "margen_pct",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return enriquecidas


@router.get("/evolucion-ventas-diaria")
def get_evolucion_ventas_diaria(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """Serie temporal diaria de ventas (cantidad y total) en el rango de fechas."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    filas = list(svc_reportes.evolucion_ventas_diaria(db, fecha_desde, fecha_hasta))
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=["fecha", "cantidad_ventas", "total_vendido"],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/resumen-rango")
def get_resumen_rango(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
):
    """Resumen agregado de ventas en el rango: cantidad, total y ticket promedio."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        return svc_reportes.resumen_ventas_rango(db, fecha_desde, fecha_hasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/consolidado")
def get_reporte_consolidado(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
):
    """Reporte consolidado del período (docs Módulo 7 §6): ventas + ingresos/egresos de caja."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        return svc_reportes.reporte_consolidado(db, fecha_desde, fecha_hasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inventario-valorizado")
def get_inventario_valorizado(
    db: Session = Depends(get_db),
):
    """Inventario valorizado por producto y total general."""
    return svc_reportes.inventario_valorizado(db)


@router.get("/consolidado-diario")
def get_reporte_consolidado_diario(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar filas diarias.",
    ),
):
    """
    Reporte consolidado diario del período: tabla analítica por día con:
    - cantidad_ventas, total_ventas, ticket_promedio
    - total_ingresos_caja, total_egresos_caja, flujo_caja
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        data = svc_reportes.reporte_consolidado_diario(db, fecha_desde, fecha_hasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if formato == "csv":
        filas = data.get("filas", [])
        csv = _to_csv(
            filas,
            columnas=[
                "fecha",
                "cantidad_ventas",
                "total_ventas",
                "ticket_promedio",
                "ventas_fiadas",
                "cancelaciones",
                "clientes_activos",
                "unidades_vendidas",
                "productos_distintos",
                "margen_estimado",
                "total_ingresos_caja",
                "total_egresos_caja",
                "flujo_caja",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/consolidado-agrupado")
def get_reporte_consolidado_agrupado(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    agrupacion: str = Query(
        "dia",
        description="Nivel de agregación: 'dia', 'semana' o 'mes'",
    ),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar filas agrupadas.",
    ),
):
    """
    Reporte consolidado agregado por período (día/semana/mes) a partir del
    consolidado diario.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    if agrupacion not in {"dia", "semana", "mes"}:
        raise HTTPException(
            status_code=400,
            detail="agrupacion debe ser 'dia', 'semana' o 'mes'",
        )
    try:
        data = svc_reportes.reporte_consolidado_agrupado(
            db,
            fecha_desde,
            fecha_hasta,
            agrupacion=agrupacion,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if formato == "csv":
        filas = data.get("filas", [])
        csv = _to_csv(
            filas,
            columnas=[
                "periodo",
                "cantidad_ventas",
                "total_ventas",
                "ticket_promedio",
                "total_ingresos_caja",
                "total_egresos_caja",
                "flujo_caja",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/ventas-por-franja-horaria")
def get_ventas_por_franja_horaria(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
):
    """
    Reporte analítico de ventas agrupadas por franjas de 2 horas
    (00:00-02:00, 02:00-04:00, ..., 22:00-24:00) en un rango de fechas.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        return svc_reportes.ventas_por_franja_horaria(db, fecha_desde, fecha_hasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ventas-por-medio-pago")
def get_ventas_por_medio_pago(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Ventas agregadas por medio de pago en un rango de fechas.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.ventas_por_medio_pago(db, fecha_desde, fecha_hasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "metodo_pago",
                "cantidad_ventas",
                "total_vendido",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return filas


@router.get("/rotacion-inventario")
def get_rotacion_inventario(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Reporte de rotación de inventario por producto en un rango de fechas.

    Para cada producto con ventas en el rango calcula:
    - unidades_vendidas (en el rango)
    - stock_promedio_aprox (stock actual como aproximación)
    - rotacion (unidades_vendidas / stock_promedio_aprox cuando stock > 0)
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.rotacion_inventario(
            db, fecha_desde, fecha_hasta, limite=limite
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "producto_id",
                "nombre_producto",
                "unidades_vendidas",
                "stock_promedio_aprox",
                "rotacion",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/caja-resumen")
def get_caja_resumen(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Reporte de resumen de caja por caja en un rango de fechas (submódulo Caja).

    Para cada caja con actividad en el rango devuelve:
    - caja_id, fechas de apertura y cierre
    - saldo_inicial, saldo_final
    - total_ingresos, total_egresos
    - saldo_teorico y diferencia (si hay saldo_final)
    - cantidad_ventas_caja y total_ventas_caja
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.reporte_caja_resumen(db, fecha_desde, fecha_hasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "caja_id",
                "fecha_apertura",
                "fecha_cierre",
                "saldo_inicial",
                "saldo_final",
                "total_ingresos",
                "total_egresos",
                "saldo_teorico",
                "diferencia",
                "cantidad_ventas_caja",
                "total_ventas_caja",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return filas


@router.get("/proveedores-volumen-compras")
def get_proveedores_volumen_compras(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Volumen de compras por proveedor en un rango de fechas.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.proveedores_volumen_compras(
            db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limite=limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "proveedor_id",
                "proveedor_nombre",
                "cantidad_compras",
                "total_comprado",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return filas


@router.get("/proveedores-productos")
def get_proveedores_productos_suministrados(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    proveedor_id: int | None = Query(
        default=None,
        description="Filtrar por proveedor específico (opcional).",
    ),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Productos suministrados por proveedor en un rango de fechas.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.proveedores_productos_suministrados(
            db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            proveedor_id=proveedor_id,
            limite=limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "proveedor_id",
                "proveedor_nombre",
                "producto_id",
                "nombre_producto",
                "cantidad_comprada",
                "total_comprado",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return filas


@router.get("/ranking-proveedores")
def get_ranking_proveedores(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(20, ge=1, le=100),
    orden_por: str = Query(
        "total",
        description="Orden: 'total' (total_comprado) o 'cantidad' (cantidad_compras)",
    ),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Ranking de proveedores según volumen de compras en el rango.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    if orden_por not in {"total", "cantidad"}:
        raise HTTPException(
            status_code=400,
            detail="orden_por debe ser 'total' o 'cantidad'",
        )
    try:
        filas = svc_reportes.ranking_proveedores(
            db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limite=limite,
            orden_por=orden_por,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "posicion",
                "proveedor_id",
                "proveedor_nombre",
                "cantidad_compras",
                "total_comprado",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return filas


@router.get("/variacion-costos-productos")
def get_variacion_costos_productos(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Reporte de variación de costos de productos en compras en un rango de fechas.

    Para cada producto con compras en el rango devuelve:
    - producto_id, nombre_producto
    - costo_min, costo_max, costo_promedio
    - variacion_absoluta y variacion_pct
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.variacion_costos_productos(
            db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limite=limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "producto_id",
                "nombre_producto",
                "costo_min",
                "costo_max",
                "costo_promedio",
                "variacion_absoluta",
                "variacion_pct",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return filas


@router.get("/proveedores-impacto-costos")
def get_proveedores_impacto_costos(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Análisis de impacto de costos por proveedor en un rango de fechas.

    Para cada proveedor devuelve:
    - proveedor_id, proveedor_nombre
    - total_comprado
    - costo_min, costo_max, costo_promedio
    - variacion_absoluta y variacion_pct
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.proveedores_impacto_costos(
            db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limite=limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "proveedor_id",
                "proveedor_nombre",
                "total_comprado",
                "costo_min",
                "costo_max",
                "costo_promedio",
                "variacion_absoluta",
                "variacion_pct",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return filas


@router.get("/proveedores-riesgo-costos")
def get_proveedores_riesgo_costos(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Ranking de proveedores por riesgo de costos en un rango de fechas.

    Métrica de riesgo:
    - riesgo_costos = total_comprado * (variacion_pct / 100)
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    try:
        filas = svc_reportes.proveedores_riesgo_costos(
            db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limite=limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "proveedor_id",
                "proveedor_nombre",
                "total_comprado",
                "costo_min",
                "costo_max",
                "costo_promedio",
                "variacion_absoluta",
                "variacion_pct",
                "riesgo_costos",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")

    return filas


@router.get("/ventas-por-categoria")
def get_ventas_por_categoria(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Ventas agrupadas por categoría de producto en el rango (docs §9).
    Devuelve categoria_id, categoria_nombre, cantidad_vendida, total_vendido.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    filas = svc_reportes.ventas_por_categoria(db, fecha_desde, fecha_hasta, limite)
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=["categoria_id", "categoria_nombre", "cantidad_vendida", "total_vendido"],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/ventas-canceladas")
def get_ventas_canceladas(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Reporte de ventas canceladas en el rango de fechas (docs §7).
    Devuelve resumen (total_canceladas, monto_total) y filas de detalle.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    data = svc_reportes.ventas_canceladas(db, fecha_desde, fecha_hasta, limite)
    if formato == "csv":
        csv = _to_csv(
            data.get("filas", []),
            columnas=["venta_id", "numero_ticket", "total", "metodo_pago", "creado_en", "cliente_nombre"],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/inventario-bajo-minimo")
def get_inventario_bajo_minimo(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Productos con stock actual inferior al stock mínimo configurado (docs §10).
    Devuelve producto_id, nombre_producto, stock_actual, stock_minimo, diferencia.
    """
    filas = svc_reportes.inventario_bajo_minimo(db, limite=limite)
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=["producto_id", "nombre_producto", "stock_actual", "stock_minimo", "diferencia"],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/mermas")
def get_mermas(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Mermas registradas en MovimientoInventario en el rango de fechas (docs §10).
    Devuelve resumen y filas agrupadas por producto.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    data = svc_reportes.mermas_por_periodo(db, fecha_desde, fecha_hasta, limite)
    if formato == "csv":
        csv = _to_csv(
            data.get("filas", []),
            columnas=["producto_id", "nombre_producto", "cantidad_registros", "total_unidades"],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/clientes-cartera-riesgo")
def get_clientes_cartera_riesgo(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Reporte de riesgo de cartera de clientes basado en cuenta corriente.

    Devuelve, ordenado por saldo descendente:
    - cliente_id (Persona.id)
    - cliente_nombre
    - saldo (deuda actual)
    - limite_credito
    - porcentaje_utilizado (saldo / limite_credito * 100 cuando limite_credito > 0)
    """
    filas = svc_reportes.clientes_cartera_riesgo(db, limite=limite)
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "cliente_id",
                "cliente_nombre",
                "saldo",
                "limite_credito",
                "porcentaje_utilizado",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/clientes-cartera-morosidad")
def get_clientes_cartera_morosidad(
    db: Session = Depends(get_db),
    fecha_corte: date = Query(..., description="Fecha de corte (YYYY-MM-DD)"),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar filas de clientes.",
    ),
):
    """
    Reporte de morosidad de cartera de clientes basado en cuenta corriente.

    JSON:
    - resumen: fecha_corte, total_clientes, saldo_total, saldo_vencido_total, distribucion_tramos
    - filas: detalle por cliente con tramo de morosidad.

    CSV:
    - Exporta solo las filas de clientes (sin resumen) con columnas:
      cliente_id, cliente_nombre, saldo, limite_credito, porcentaje_utilizado,
      dias_morosidad, tramo_morosidad.
    """
    data = svc_reportes.clientes_cartera_morosidad(
        db, fecha_corte=fecha_corte, limite=limite
    )
    if formato == "csv":
        filas = data.get("filas", [])
        csv = _to_csv(
            filas,
            columnas=[
                "cliente_id",
                "cliente_nombre",
                "saldo",
                "limite_credito",
                "porcentaje_utilizado",
                "dias_morosidad",
                "tramo_morosidad",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/operaciones-comerciales")
def get_operaciones_comerciales(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    tipo: str | None = Query(
        None,
        description="Filtrar por tipo: DEVOLUCION, CAMBIO_PRODUCTO, NOTA_CREDITO, NOTA_DEBITO, ANULACION",
    ),
    limite: int = Query(200, ge=1, le=1000),
    formato: str = Query("json", description="'json' o 'csv'"),
):
    """
    Reporte de operaciones comerciales post-venta (devoluciones, notas de crédito/débito,
    cambios de producto, anulaciones) en el rango de fechas.
    Docs Módulo 7 §7 — Ventas: devoluciones, notas de crédito y débito.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    data = svc_reportes.reporte_operaciones_comerciales(
        db, fecha_desde, fecha_hasta, tipo=tipo, limite=limite
    )
    if formato == "csv":
        csv = _to_csv(
            data.get("filas", []),
            columnas=[
                "operacion_id", "tipo", "estado", "importe_total",
                "motivo", "creado_en", "venta_id", "cliente_nombre",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/ventas-por-caja")
def get_ventas_por_caja(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    formato: str = Query("json", description="'json' o 'csv'"),
):
    """
    Ventas agrupadas por caja en el período.
    Docs Módulo 7 §8 — Caja: ventas por caja, arqueos y diferencias.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    filas = svc_reportes.ventas_por_caja(db, fecha_desde, fecha_hasta)
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "caja_id", "fecha_apertura", "cantidad_ventas",
                "total_ventas", "total_fiadas", "total_canceladas", "ventas_pagadas",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/frecuencia-compra-clientes")
def get_frecuencia_compra_clientes(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(100, ge=1, le=500),
    formato: str = Query("json", description="'json' o 'csv'"),
):
    """
    Frecuencia de compra por cliente: cantidad de compras, total comprado y ticket promedio.
    Docs Módulo 7 §11 — Clientes: frecuencia de compra, valor promedio, volumen total.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    filas = svc_reportes.frecuencia_compra_clientes(
        db, fecha_desde, fecha_hasta, limite=limite
    )
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=[
                "cliente_id", "cliente_nombre", "cantidad_compras",
                "total_comprado", "ticket_promedio", "primera_compra", "ultima_compra",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas
