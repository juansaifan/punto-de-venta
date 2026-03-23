"""Endpoints REST para Dashboard (indicadores)."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import dashboard as svc_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/margen-dia")
def get_margen_dia(
    db: Session = Depends(get_db),
    fecha: date | None = Query(None, description="Fecha (YYYY-MM-DD); por defecto hoy"),
):
    """
    Margen bruto del día: suma (precio_venta - costo) × cantidad para todas las ventas del día.
    Incluye margen_bruto, total_ingresos y margen_pct (docs Módulo 1 §4.8).
    """
    dia = fecha or date.today()
    return svc_dashboard.calcular_margen_dia(db, dia)


@router.get("/indicadores")
def get_indicadores(db: Session = Depends(get_db)):
    """Indicadores del día: ventas, ticket promedio, caja abierta, productos con stock bajo."""
    return svc_dashboard.indicadores_hoy(db)


@router.get("/indicadores-comparativos")
def get_indicadores_comparativos(
    db: Session = Depends(get_db),
    fecha: date | None = Query(None, description="Fecha (YYYY-MM-DD); por defecto hoy"),
):
    """Indicadores del día con comparación vs día anterior: valor anterior y variación porcentual por KPI."""
    return svc_dashboard.indicadores_con_comparativa(db, dia=fecha)


@router.get("/ventas-por-hora")
def get_ventas_por_hora(
    db: Session = Depends(get_db),
    fecha: date | None = Query(None, description="Fecha (YYYY-MM-DD); por defecto hoy"),
):
    """Ventas del día agrupadas por hora (00-23) para el gráfico: cantidad y total por hora."""
    return svc_dashboard.ventas_por_hora_del_dia(db, dia=fecha)


@router.get("/productos-stock-bajo")
def get_productos_stock_bajo(db: Session = Depends(get_db)):
    """Lista de productos con stock actual <= stock mínimo (alertas de reposición)."""
    return svc_dashboard.productos_stock_bajo(db)


@router.get("/productos-proximos-vencer")
def get_productos_proximos_vencer(
    db: Session = Depends(get_db),
    dias: int = 30,
):
    """Lista de lotes con fecha de vencimiento en los próximos N días (alertas operativas, docs Módulo 1 §3.3.1)."""
    if dias < 1:
        dias = 30
    return svc_dashboard.productos_proximos_vencer(db, dias=dias)


@router.get("/alertas-operativas")
def get_alertas_operativas(
    db: Session = Depends(get_db),
    dias_vencimiento: int = Query(30, ge=1, le=365),
    incluir_inventario: bool = Query(True),
    incluir_tesoreria: bool = Query(True),
):
    """Consolidado de alertas operativas (inventario + tesorería)."""
    return svc_dashboard.alertas_operativas(
        db,
        dias_vencimiento=dias_vencimiento,
        incluir_inventario=incluir_inventario,
        incluir_tesoreria=incluir_tesoreria,
    )


@router.get("/panel-lateral")
def get_panel_lateral(
    db: Session = Depends(get_db),
    fecha: date | None = Query(None, description="Fecha (YYYY-MM-DD); por defecto hoy"),
):
    """Panel lateral del dashboard (salud del negocio, promedios y pronóstico)."""
    return svc_dashboard.panel_lateral(db, dia=fecha)


@router.get("/top-productos")
def get_top_productos(
    db: Session = Depends(get_db),
    fecha_desde: date | None = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: date | None = Query(None, description="Fecha fin YYYY-MM-DD"),
    limite: int = Query(10, ge=1, le=50),
):
    """
    Top productos por total facturado en el período.
    Docs Módulo 1 §3.1 — KPIs / análisis comercial.
    """
    return svc_dashboard.top_productos(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limite=limite,
    )


@router.get("/tendencias")
def get_tendencias(
    db: Session = Depends(get_db),
    periodo: str = Query("semanal", description="Agrupación: diario | semanal | mensual"),
    cantidad_periodos: int = Query(8, ge=1, le=24),
):
    """
    Tendencias de ventas en los últimos N períodos agrupados por día, semana o mes.
    Docs Módulo 1 §3.1 — KPIs con comparación vs período anterior.
    """
    from fastapi import HTTPException
    try:
        return svc_dashboard.tendencias_ventas(
            db,
            periodo=periodo,
            cantidad_periodos=cantidad_periodos,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
