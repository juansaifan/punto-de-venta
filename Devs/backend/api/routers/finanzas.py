"""Endpoints REST para Finanzas."""
from datetime import date, datetime
from typing import Iterable, Mapping

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import reportes as svc_reportes
from backend.api.schemas.finanzas import (
    ActualizarCuentaRequest,
    CrearCuentaRequest,
    CuentaFinancieraResponse,
    TransaccionFinancieraResponse,
    TransferirEntreCuentasRequest,
    TransferirEntreCuentasResponse,
)
from backend.services import finanzas as svc_finanzas
from backend.services import cuentas_corrientes as svc_cuentas_corrientes

router = APIRouter(prefix="/finanzas", tags=["finanzas"])


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


@router.get("/resumen-global")
def obtener_resumen_financiero_global(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(
        default=None,
        description="Incluir transacciones desde esta fecha (inclusive) para total_ingresos/total_gastos",
    ),
    hasta: datetime | None = Query(
        default=None,
        description="Incluir transacciones hasta esta fecha (inclusive) para total_ingresos/total_gastos",
    ),
):
    """Resumen financiero consolidado: saldo total de todas las cuentas, total ingresos/gastos en rango opcional (docs Módulo 4 §5)."""
    resumen = svc_finanzas.resumen_financiero_global(db, desde=desde, hasta=hasta)
    return {
        "saldo_total": float(resumen["saldo_total"]),
        "total_ingresos": float(resumen["total_ingresos"]),
        "total_gastos": float(resumen["total_gastos"]),
        "cantidad_cuentas": resumen["cantidad_cuentas"],
        "desde": resumen["desde"],
        "hasta": resumen["hasta"],
    }


@router.get("/flujo-caja")
def obtener_flujo_caja(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(
        default=None,
        description="Incluir transacciones desde esta fecha (inclusive)",
    ),
    hasta: datetime | None = Query(
        default=None,
        description="Incluir transacciones hasta esta fecha (inclusive)",
    ),
):
    """
    Devuelve el flujo de caja agregado por día:
    - ingresos
    - egresos
    - saldo_dia (ingresos - egresos)
    - saldo_acumulado (suma acumulada en el tiempo)
    """
    puntos = svc_finanzas.obtener_flujo_caja(
        db,
        desde=desde,
        hasta=hasta,
    )
    return [
        {
            "fecha": p["fecha"] if isinstance(p["fecha"], str) else p["fecha"].isoformat(),
            "ingresos": float(p["ingresos"]),
            "egresos": float(p["egresos"]),
            "saldo_dia": float(p["saldo_dia"]),
            "saldo_acumulado": float(p["saldo_acumulado"]),
        }
        for p in puntos
    ]


@router.get("/balances-mensuales")
def obtener_balances_mensuales(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(
        default=None,
        description="Incluir transacciones desde esta fecha (inclusive)",
    ),
    hasta: datetime | None = Query(
        default=None,
        description="Incluir transacciones hasta esta fecha (inclusive)",
    ),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Devuelve balances financieros mensuales:
    - periodo: YYYY-MM
    - ingresos: suma de montos de tipo ingreso del mes
    - egresos: suma de montos de tipo gasto del mes
    - resultado_neto: ingresos - egresos
    """
    puntos = svc_finanzas.obtener_balances_mensuales(
        db,
        desde=desde,
        hasta=hasta,
    )
    filas = [
        {
            "periodo": p["periodo"],
            "ingresos": float(p["ingresos"]),
            "egresos": float(p["egresos"]),
            "resultado_neto": float(p["resultado_neto"]),
        }
        for p in puntos
    ]
    if formato == "csv":
        csv = _to_csv(
            filas,
            columnas=["periodo", "ingresos", "egresos", "resultado_neto"],
        )
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/indicadores")
def obtener_indicadores_financieros(
    db: Session = Depends(get_db),
    periodo: str = Query(
        default="dia",
        description="Periodo de cálculo: 'dia' o 'mes'. Si no se indican fechas, usa el día/mes actual.",
    ),
    desde: datetime | None = Query(
        default=None,
        description="Rango opcional: desde esta fecha (inclusive)",
    ),
    hasta: datetime | None = Query(
        default=None,
        description="Rango opcional: hasta esta fecha (inclusive)",
    ),
):
    """
    Indicadores financieros globales básicos:
    - total_ingresos
    - total_gastos
    - resultado_neto
    - promedio_diario (resultado_neto / días del rango)
    - cantidad_movimientos

    Corresponde al submódulo Indicadores financieros (docs Módulo 4 §11).
    """
    if periodo not in {"dia", "mes"}:
        raise HTTPException(status_code=400, detail="Periodo inválido; debe ser 'dia' o 'mes'")

    indicadores = svc_finanzas.obtener_indicadores_financieros(
        db,
        periodo=periodo,  # type: ignore[arg-type]
        desde=desde,
        hasta=hasta,
    )

    return {
        "periodo": indicadores["periodo"],
        "desde": indicadores["desde"].isoformat() if indicadores["desde"] else None,
        "hasta": indicadores["hasta"].isoformat() if indicadores["hasta"] else None,
        "total_ingresos": float(indicadores["total_ingresos"]),
        "total_gastos": float(indicadores["total_gastos"]),
        "resultado_neto": float(indicadores["resultado_neto"]),
        "promedio_diario": float(indicadores["promedio_diario"]),
        "dias": indicadores["dias"],
        "cantidad_movimientos": indicadores["cantidad_movimientos"],
    }


@router.get("/rentabilidad/margen-producto")
def get_margen_producto_finanzas(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    orden_por: str = Query(
        "margen_bruto",
        description="Orden: 'margen_bruto', 'margen_pct' o 'total_vendido'",
    ),
):
    """Rentabilidad (docs Módulo 4 §9): margen por producto."""
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


@router.get("/rentabilidad/margen-categoria")
def get_margen_categoria_finanzas(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    limite: int = Query(50, ge=1, le=200),
    orden_por: str = Query(
        "margen_bruto",
        description="Orden: 'margen_bruto', 'margen_pct' o 'total_vendido'",
    ),
):
    """Rentabilidad (docs Módulo 4 §9): margen por categoría."""
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


@router.get("/transacciones")
def listar_transacciones_global(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(default=None, description="Filtrar desde esta fecha (inclusive)"),
    hasta: datetime | None = Query(default=None, description="Filtrar hasta esta fecha (inclusive)"),
    tipo: str | None = Query(default=None, description="Filtrar por tipo: ingreso o gasto"),
    cuenta_id: int | None = Query(default=None, description="Filtrar por cuenta financiera"),
    conciliada: bool | None = Query(default=None, description="Filtrar por estado de conciliación"),
    limite: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Lista transacciones de todas las cuentas (historial financiero) con filtros opcionales.
    Sirve para consulta y exportación (docs Módulo 4 §7 Ingresos, §8 Egresos, §12 Historial).
    """
    try:
        items = svc_finanzas.listar_transacciones_global(
            db,
            desde=desde,
            hasta=hasta,
            tipo=tipo,
            cuenta_id=cuenta_id,
            conciliada=conciliada,
            limite=limite,
            offset=offset,
        )
    except ValueError as e:
        msg = str(e)
        if "inválido" in msg.lower():
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    if formato == "csv":
        csv = _to_csv(
            items,
            columnas=[
                "id",
                "cuenta_id",
                "nombre_cuenta",
                "tipo",
                "monto",
                "fecha",
                "descripcion",
                "conciliada",
            ],
        )
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(content=csv, media_type="text/csv")
    return items


@router.get("/ingresos")
def listar_ingresos(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(default=None, description="Filtrar desde esta fecha (inclusive)"),
    hasta: datetime | None = Query(default=None, description="Filtrar hasta esta fecha (inclusive)"),
    cuenta_id: int | None = Query(default=None, description="Filtrar por cuenta financiera"),
    conciliada: bool | None = Query(default=None, description="Filtrar por estado de conciliación"),
    limite: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Submódulo Ingresos (docs Módulo 4 §7): lista ingresos históricos (tipo='ingreso')
    con filtros opcionales y exportación CSV.
    """
    items = svc_finanzas.listar_transacciones_global(
        db,
        desde=desde,
        hasta=hasta,
        tipo="ingreso",
        cuenta_id=cuenta_id,
        conciliada=conciliada,
        limite=limite,
        offset=offset,
    )
    if formato == "csv":
        csv = _to_csv(
            items,
            columnas=[
                "id",
                "cuenta_id",
                "nombre_cuenta",
                "tipo",
                "monto",
                "fecha",
                "descripcion",
                "conciliada",
            ],
        )
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(content=csv, media_type="text/csv")
    return items


@router.get("/egresos")
def listar_egresos(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(default=None, description="Filtrar desde esta fecha (inclusive)"),
    hasta: datetime | None = Query(default=None, description="Filtrar hasta esta fecha (inclusive)"),
    cuenta_id: int | None = Query(default=None, description="Filtrar por cuenta financiera"),
    conciliada: bool | None = Query(default=None, description="Filtrar por estado de conciliación"),
    limite: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    formato: str = Query(
        "json",
        description="Formato de salida: 'json' (por defecto) o 'csv' para exportar.",
    ),
):
    """
    Submódulo Egresos (docs Módulo 4 §8): lista egresos históricos (tipo='gasto')
    con filtros opcionales y exportación CSV.
    """
    items = svc_finanzas.listar_transacciones_global(
        db,
        desde=desde,
        hasta=hasta,
        tipo="gasto",
        cuenta_id=cuenta_id,
        conciliada=conciliada,
        limite=limite,
        offset=offset,
    )
    if formato == "csv":
        csv = _to_csv(
            items,
            columnas=[
                "id",
                "cuenta_id",
                "nombre_cuenta",
                "tipo",
                "monto",
                "fecha",
                "descripcion",
                "conciliada",
            ],
        )
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(content=csv, media_type="text/csv")
    return items


@router.get("/cuentas", response_model=list[CuentaFinancieraResponse])
def listar_cuentas(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    estado: str | None = Query(None, description="Filtrar por estado: activa / inactiva"),
):
    """Lista cuentas financieras (activas/inactivas)."""
    cuentas = svc_finanzas.listar_cuentas(db, limite=limite, offset=offset)
    if estado is not None:
        cuentas = [c for c in cuentas if c.estado == estado.strip().lower()]
    return cuentas


# Ruta específica ANTES de la parametrizada para evitar conflicto 422
@router.post("/cuentas/transferir", status_code=201, response_model=TransferirEntreCuentasResponse)
def transferir_entre_cuentas(body: TransferirEntreCuentasRequest, db: Session = Depends(get_db)):
    """
    Transfiere fondos entre dos cuentas financieras (§8 Tesorería).

    - Registra un GASTO en cuenta origen y un INGRESO en cuenta destino.
    - Actualiza saldos de ambas cuentas automáticamente.
    - Falla si saldo en origen es insuficiente o alguna cuenta está inactiva.
    """
    try:
        return svc_finanzas.transferir_entre_cuentas(
            db,
            cuenta_origen_id=body.cuenta_origen_id,
            cuenta_destino_id=body.cuenta_destino_id,
            importe=body.importe,
            motivo=body.motivo,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.get("/cuentas/{cuenta_id}", response_model=CuentaFinancieraResponse)
def obtener_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    """Obtiene una cuenta por ID."""
    c = svc_finanzas.obtener_cuenta_por_id(db, cuenta_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return c


@router.post("/cuentas", status_code=201, response_model=CuentaFinancieraResponse)
def crear_cuenta(body: CrearCuentaRequest, db: Session = Depends(get_db)):
    """Crea una cuenta financiera (§9 Tesorería).

    Tipos admitidos: caja_fisica, cuenta_bancaria, billetera_virtual,
    fondo_operativo, fondo_cambio, GENERAL.
    """
    try:
        return svc_finanzas.crear_cuenta(
            db,
            nombre=body.nombre,
            tipo=body.tipo,
            saldo_inicial=body.saldo_inicial,
            observaciones=body.observaciones,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/cuentas/{cuenta_id}", response_model=CuentaFinancieraResponse)
def actualizar_cuenta(
    cuenta_id: int,
    body: ActualizarCuentaRequest,
    db: Session = Depends(get_db),
):
    """Actualiza parcialmente una cuenta financiera (nombre, tipo, estado, observaciones)."""
    try:
        return svc_finanzas.actualizar_cuenta(
            db,
            cuenta_id,
            nombre=body.nombre,
            tipo=body.tipo,
            estado=body.estado,
            observaciones=body.observaciones,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.post(
    "/cuentas/{cuenta_id}/transacciones",
    status_code=201,
    response_model=TransaccionFinancieraResponse,
)
def registrar_transaccion(
    cuenta_id: int,
    body: dict,
    db: Session = Depends(get_db),
):
    """Registra una transacción financiera (ingreso/gasto) para una cuenta."""
    tipo = body.get("tipo", "")
    monto = body.get("monto")
    descripcion = body.get("descripcion")
    if monto is None:
        raise HTTPException(status_code=422, detail="El monto es obligatorio")
    try:
        transaccion = svc_finanzas.registrar_transaccion(
            db,
            cuenta_id=cuenta_id,
            tipo=tipo,
            monto=monto,
            descripcion=descripcion,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return transaccion


@router.post("/pagos-cliente", status_code=201)
def registrar_pago_cliente(body: dict, db: Session = Depends(get_db)):
    """
    Registra un pago de cliente:

    - Crea una transacción financiera de tipo 'ingreso' en la cuenta indicada.
    - Registra un movimiento PAGO en la cuenta corriente del cliente asociado.

    Body esperado:
    - cuenta_id: int (cuenta financiera donde se acredita el pago)
    - cliente_id: int
    - monto: numérico > 0
    - descripcion: opcional
    """
    cuenta_id = body.get("cuenta_id")
    cliente_id = body.get("cliente_id")
    monto = body.get("monto")
    descripcion = body.get("descripcion")

    if cuenta_id is None or cliente_id is None or monto is None:
        raise HTTPException(
            status_code=422,
            detail="cuenta_id, cliente_id y monto son obligatorios",
        )

    # Registrar transacción financiera (ingreso)
    try:
        tx = svc_finanzas.registrar_transaccion(
            db,
            cuenta_id=int(cuenta_id),
            tipo="ingreso",
            monto=monto,
            descripcion=descripcion or f"Pago cliente {cliente_id}",
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # Registrar movimiento de cuenta corriente del cliente (PAGO)
    try:
        svc_cuentas_corrientes.registrar_movimiento_cuenta_corriente(
            db,
            cliente_id=int(cliente_id),
            tipo="PAGO",
            monto=monto,
            descripcion=descripcion or f"Pago aplicado a tx {tx.id}",
        )
    except ValueError:
        # No revertimos la transacción financiera; solo dejamos constancia implícita.
        pass

    return {
        "transaccion_id": tx.id,
        "cuenta_id": tx.cuenta_id,
        "cliente_id": int(cliente_id),
        "monto": float(tx.monto),
        "descripcion": tx.descripcion,
    }


@router.get(
    "/cuentas/{cuenta_id}/transacciones",
    response_model=list[TransaccionFinancieraResponse],
)
def listar_transacciones(
    cuenta_id: int,
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tipo: str | None = Query(
        default=None,
        description="Filtrar por tipo de transacción (ingreso/gasto)",
    ),
    desde: datetime | None = Query(
        default=None,
        description="Filtrar transacciones desde esta fecha (inclusive)",
    ),
    hasta: datetime | None = Query(
        default=None,
        description="Filtrar transacciones hasta esta fecha (inclusive)",
    ),
    conciliada: bool | None = Query(
        default=None,
        description="Filtrar por estado de conciliación (true/false)",
    ),
):
    """
    Lista transacciones de una cuenta financiera, con filtros opcionales por tipo, rango de fechas y conciliación.
    """
    try:
        transacciones = svc_finanzas.listar_transacciones_por_cuenta(
            db,
            cuenta_id=cuenta_id,
            limite=limite,
            offset=offset,
            tipo=tipo,
            desde=desde,
            hasta=hasta,
            conciliada=conciliada,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return list(transacciones)


@router.get("/cuentas/{cuenta_id}/resumen")
def obtener_resumen_cuenta(
    cuenta_id: int,
    db: Session = Depends(get_db),
    desde: datetime | None = Query(
        default=None,
        description="Filtrar movimientos desde esta fecha (inclusive) para el resumen",
    ),
    hasta: datetime | None = Query(
        default=None,
        description="Filtrar movimientos hasta esta fecha (inclusive) para el resumen",
    ),
):
    """
    Devuelve un resumen financiero de la cuenta:
    - saldo_actual
    - total_ingresos
    - total_gastos
    - balance_movimientos (ingresos - gastos) en el rango opcional.
    """
    try:
        resumen = svc_finanzas.obtener_resumen_cuenta(
            db,
            cuenta_id=cuenta_id,
            desde=desde,
            hasta=hasta,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return {
        "cuenta_id": resumen["cuenta_id"],
        "nombre": resumen["nombre"],
        "tipo": resumen["tipo"],
        "saldo_actual": float(resumen["saldo_actual"]),
        "total_ingresos": float(resumen["total_ingresos"]),
        "total_gastos": float(resumen["total_gastos"]),
        "balance_movimientos": float(resumen["balance_movimientos"]),
    }


@router.get("/cuentas/{cuenta_id}/evolucion-saldo")
def obtener_evolucion_saldo_cuenta(
    cuenta_id: int,
    db: Session = Depends(get_db),
    desde: datetime | None = Query(
        default=None,
        description="Incluir movimientos desde esta fecha (inclusive)",
    ),
    hasta: datetime | None = Query(
        default=None,
        description="Incluir movimientos hasta esta fecha (inclusive)",
    ),
):
    """
    Devuelve la evolución del saldo de la cuenta en el tiempo,
    como una lista ordenada cronológicamente con saldo después de cada movimiento.
    """
    try:
        puntos = svc_finanzas.obtener_evolucion_saldo_cuenta(
            db,
            cuenta_id=cuenta_id,
            desde=desde,
            hasta=hasta,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return [
        {
            "fecha": p["fecha"].isoformat(),
            "saldo_despues": float(p["saldo_despues"]),
            "tipo": p["tipo"],
            "monto": float(p["monto"]),
            "descripcion": p["descripcion"],
        }
        for p in puntos
    ]


@router.patch(
    "/cuentas/{cuenta_id}/transacciones/{transaccion_id}/conciliar",
    response_model=TransaccionFinancieraResponse,
)
def conciliar_transaccion(
    cuenta_id: int,
    transaccion_id: int,
    db: Session = Depends(get_db),
):
    """Marca una transacción como conciliada (control financiero / ROADMAP Fase 4)."""
    try:
        tx = svc_finanzas.marcar_transaccion_conciliada(
            db,
            cuenta_id=cuenta_id,
            transaccion_id=transaccion_id,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower() or "no pertenece" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return tx


@router.get("/balances-diarios")
def obtener_balances_diarios(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(default=None, description="Desde esta fecha (inclusive)"),
    hasta: datetime | None = Query(default=None, description="Hasta esta fecha (inclusive)"),
    formato: str = Query("json", description="Formato: 'json' o 'csv'"),
):
    """
    Balance financiero diario (docs Módulo 4 §10):
    Para cada día devuelve periodo (YYYY-MM-DD), ingresos, egresos, resultado_neto.
    """
    filas = svc_finanzas.obtener_balances_diarios(db, desde=desde, hasta=hasta)
    if formato == "csv":
        csv = _to_csv(filas, columnas=["periodo", "ingresos", "egresos", "resultado_neto"])
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/balances-anuales")
def obtener_balances_anuales(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(default=None, description="Desde esta fecha (inclusive)"),
    hasta: datetime | None = Query(default=None, description="Hasta esta fecha (inclusive)"),
    formato: str = Query("json", description="Formato: 'json' o 'csv'"),
):
    """
    Balance financiero anual (docs Módulo 4 §10):
    Para cada año devuelve periodo (YYYY), ingresos, egresos, resultado_neto.
    """
    filas = svc_finanzas.obtener_balances_anuales(db, desde=desde, hasta=hasta)
    if formato == "csv":
        csv = _to_csv(filas, columnas=["periodo", "ingresos", "egresos", "resultado_neto"])
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/flujo-caja-agrupado")
def obtener_flujo_caja_agrupado(
    db: Session = Depends(get_db),
    agrupacion: str = Query(
        "dia",
        description="Nivel de agrupación: 'dia', 'semana' o 'mes'",
    ),
    desde: datetime | None = Query(default=None, description="Desde esta fecha (inclusive)"),
    hasta: datetime | None = Query(default=None, description="Hasta esta fecha (inclusive)"),
    formato: str = Query("json", description="Formato: 'json' o 'csv'"),
):
    """
    Flujo de caja agrupado (docs Módulo 4 §6):
    día/semana/mes con ingresos, egresos, saldo_dia, saldo_acumulado.
    """
    if agrupacion not in {"dia", "semana", "mes"}:
        raise HTTPException(status_code=400, detail="agrupacion debe ser 'dia', 'semana' o 'mes'")
    try:
        filas = svc_finanzas.obtener_flujo_caja_agrupado(db, agrupacion=agrupacion, desde=desde, hasta=hasta)  # type: ignore[arg-type]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if formato == "csv":
        csv = _to_csv(filas, columnas=["periodo", "ingresos", "egresos", "saldo_dia", "saldo_acumulado"])
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=csv, media_type="text/csv")
    return filas


@router.get("/rentabilidad/periodo")
def get_rentabilidad_periodo(
    db: Session = Depends(get_db),
    fecha_desde: date = Query(..., description="Desde (YYYY-MM-DD)"),
    fecha_hasta: date = Query(..., description="Hasta (YYYY-MM-DD)"),
    agrupacion: str = Query("mes", description="Agrupación: 'dia' o 'mes'"),
    formato: str = Query("json", description="Formato: 'json' o 'csv'"),
):
    """
    Rentabilidad por período (docs Módulo 4 §9):
    Margen bruto y neto cruzando ventas con costos de producto y gastos financieros.
    Devuelve resumen global + tabla de filas por período.
    """
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    if agrupacion not in {"dia", "mes"}:
        raise HTTPException(status_code=400, detail="agrupacion debe ser 'dia' o 'mes'")
    try:
        data = svc_finanzas.rentabilidad_por_periodo(
            db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            agrupacion=agrupacion,  # type: ignore[arg-type]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if formato == "csv":
        csv = _to_csv(
            data.get("filas", []),
            columnas=[
                "periodo",
                "total_ventas",
                "total_costo",
                "gastos_operativos",
                "margen_bruto",
                "margen_bruto_pct",
                "margen_neto",
                "margen_neto_pct",
            ],
        )
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/tendencias")
def obtener_tendencias_financieras(
    db: Session = Depends(get_db),
    agrupacion: str = Query(
        "mes",
        description="Nivel de agrupación: 'dia', 'semana' o 'mes'",
    ),
    n_periodos: int = Query(12, ge=1, le=120, description="Número de períodos a mostrar"),
    hasta: datetime | None = Query(default=None, description="Hasta esta fecha (inclusive)"),
    formato: str = Query("json", description="Formato: 'json' o 'csv'"),
):
    """
    Tendencias financieras (docs Módulo 4 §12):
    Compara ingresos vs. egresos en los últimos N períodos (día/semana/mes),
    mostrando variación porcentual entre períodos consecutivos para detectar tendencias.
    """
    if agrupacion not in {"dia", "semana", "mes"}:
        raise HTTPException(status_code=400, detail="agrupacion debe ser 'dia', 'semana' o 'mes'")
    data = svc_finanzas.tendencias_financieras(
        db,
        agrupacion=agrupacion,  # type: ignore[arg-type]
        n_periodos=n_periodos,
        hasta=hasta,
    )
    if formato == "csv":
        from fastapi.responses import PlainTextResponse
        csv = _to_csv(
            data.get("filas", []),
            columnas=[
                "periodo",
                "ingresos",
                "egresos",
                "resultado_neto",
                "variacion_ingresos_pct",
                "variacion_egresos_pct",
            ],
        )
        return PlainTextResponse(content=csv, media_type="text/csv")
    return data


@router.get("/indicadores-avanzados")
def get_indicadores_avanzados(
    db: Session = Depends(get_db),
    desde: datetime | None = Query(default=None, description="Desde esta fecha (inclusive)"),
    hasta: datetime | None = Query(default=None, description="Hasta esta fecha (inclusive)"),
):
    """
    Indicadores financieros avanzados (docs Módulo 4 §11):
    liquidez, margen_ganancia_pct, ticket_promedio, resultado_neto,
    saldo_total_cuentas, total_ingresos, total_gastos.
    """
    return svc_finanzas.obtener_indicadores_avanzados(db, desde=desde, hasta=hasta)


@router.patch(
    "/cuentas/{cuenta_id}/transacciones/{transaccion_id}/desconciliar",
    response_model=TransaccionFinancieraResponse,
)
def desconciliar_transaccion(
    cuenta_id: int,
    transaccion_id: int,
    db: Session = Depends(get_db),
):
    """Quita el estado de conciliada de una transacción."""
    try:
        tx = svc_finanzas.desmarcar_transaccion_conciliada(
            db,
            cuenta_id=cuenta_id,
            transaccion_id=transaccion_id,
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower() or "no pertenece" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return tx
