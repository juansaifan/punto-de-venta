# Servicios del dominio Finanzas
from datetime import datetime, timezone, date as date_type
from decimal import Decimal
from typing import Any, Optional, Sequence, Literal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.events import emit as emit_event
from backend.models.finanzas import CuentaFinanciera, TransaccionFinanciera


def listar_cuentas(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[CuentaFinanciera]:
    """Lista cuentas financieras."""
    stmt = (
        select(CuentaFinanciera)
        .order_by(CuentaFinanciera.id)
        .limit(limite)
        .offset(offset)
    )
    return sesion.scalars(stmt).all()


def obtener_cuenta_por_id(sesion: Session, cuenta_id: int) -> Optional[CuentaFinanciera]:
    """Obtiene una cuenta por ID."""
    return sesion.get(CuentaFinanciera, cuenta_id)


_TIPOS_CUENTA_VALIDOS = {
    "caja_fisica",
    "cuenta_bancaria",
    "billetera_virtual",
    "fondo_operativo",
    "fondo_cambio",
    "GENERAL",
}


def crear_cuenta(
    sesion: Session,
    *,
    nombre: str,
    tipo: str = "GENERAL",
    saldo_inicial: Decimal | float = 0,
    observaciones: str | None = None,
) -> CuentaFinanciera:
    """Crea una nueva cuenta financiera con saldo inicial opcional.

    Tipos admitidos (§9 Tesorería): caja_fisica, cuenta_bancaria,
    billetera_virtual, fondo_operativo, fondo_cambio, GENERAL.
    """
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la cuenta no puede estar vacío")
    tipo_norm = tipo.strip() or "GENERAL"
    cuenta = CuentaFinanciera(
        nombre=nombre,
        tipo=tipo_norm,
        saldo=Decimal(str(saldo_inicial)),
        estado="activa",
        observaciones=observaciones.strip() if observaciones else None,
    )
    sesion.add(cuenta)
    sesion.flush()
    sesion.refresh(cuenta)
    return cuenta


def actualizar_cuenta(
    sesion: Session,
    cuenta_id: int,
    *,
    nombre: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    observaciones: str | None = None,
) -> CuentaFinanciera:
    """Actualiza parcialmente una cuenta financiera.

    estado admite: activa / inactiva.
    """
    cuenta = sesion.get(CuentaFinanciera, cuenta_id)
    if cuenta is None:
        raise ValueError(f"Cuenta financiera {cuenta_id} no encontrada")
    if nombre is None and tipo is None and estado is None and observaciones is None:
        raise ValueError("Se debe enviar al menos un campo a actualizar")
    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre no puede estar vacío")
        cuenta.nombre = nombre
    if tipo is not None:
        cuenta.tipo = tipo.strip() or "GENERAL"
    if estado is not None:
        estado_norm = estado.strip().lower()
        if estado_norm not in {"activa", "inactiva"}:
            raise ValueError("estado debe ser 'activa' o 'inactiva'")
        cuenta.estado = estado_norm
    if observaciones is not None:
        cuenta.observaciones = observaciones.strip() or None
    sesion.add(cuenta)
    sesion.flush()
    sesion.refresh(cuenta)
    return cuenta


def transferir_entre_cuentas(
    sesion: Session,
    *,
    cuenta_origen_id: int,
    cuenta_destino_id: int,
    importe: Decimal | float,
    motivo: str | None = None,
    usuario_id: int | None = None,
) -> dict:
    """Transfiere fondos entre dos cuentas financieras (§8 Tesorería).

    Crea un GASTO en la cuenta origen y un INGRESO en la cuenta destino.
    El saldo de ambas cuentas se actualiza automáticamente.
    Lanza ValueError si: misma cuenta, importe <= 0, saldo insuficiente en origen.
    """
    if cuenta_origen_id == cuenta_destino_id:
        raise ValueError("La cuenta origen y destino deben ser distintas")

    cuenta_origen = sesion.get(CuentaFinanciera, cuenta_origen_id)
    if cuenta_origen is None:
        raise ValueError(f"Cuenta origen {cuenta_origen_id} no encontrada")
    if cuenta_origen.estado == "inactiva":
        raise ValueError(f"La cuenta origen '{cuenta_origen.nombre}' está inactiva")

    cuenta_destino = sesion.get(CuentaFinanciera, cuenta_destino_id)
    if cuenta_destino is None:
        raise ValueError(f"Cuenta destino {cuenta_destino_id} no encontrada")
    if cuenta_destino.estado == "inactiva":
        raise ValueError(f"La cuenta destino '{cuenta_destino.nombre}' está inactiva")

    importe_dec = Decimal(str(importe))
    if importe_dec <= 0:
        raise ValueError("El importe debe ser mayor que cero")
    if cuenta_origen.saldo < importe_dec:
        raise ValueError(
            f"Saldo insuficiente en cuenta origen "
            f"(disponible: {cuenta_origen.saldo}, solicitado: {importe_dec})"
        )

    motivo_str = (motivo or "").strip() or None
    ref_egreso = f"[TRANSF→{cuenta_destino_id}] {motivo_str or cuenta_destino.nombre}"
    ref_ingreso = f"[TRANSF←{cuenta_origen_id}] {motivo_str or cuenta_origen.nombre}"

    tx_egreso = registrar_transaccion(
        sesion,
        cuenta_id=cuenta_origen_id,
        tipo="gasto",
        monto=importe_dec,
        descripcion=ref_egreso,
    )
    tx_ingreso = registrar_transaccion(
        sesion,
        cuenta_id=cuenta_destino_id,
        tipo="ingreso",
        monto=importe_dec,
        descripcion=ref_ingreso,
    )

    emit_event(
        "TransferenciaEntreCuentas",
        {
            "cuenta_origen_id": cuenta_origen_id,
            "cuenta_destino_id": cuenta_destino_id,
            "importe": float(importe_dec),
            "motivo": motivo_str,
            "transaccion_egreso_id": tx_egreso.id,
            "transaccion_ingreso_id": tx_ingreso.id,
            "__sesion": sesion,
        },
    )

    return {
        "cuenta_origen_id": cuenta_origen_id,
        "cuenta_destino_id": cuenta_destino_id,
        "importe": float(importe_dec),
        "motivo": motivo_str,
        "transaccion_egreso_id": tx_egreso.id,
        "transaccion_ingreso_id": tx_ingreso.id,
    }


def registrar_transaccion(
    sesion: Session,
    *,
    cuenta_id: int,
    tipo: str,
    monto: Decimal | float,
    descripcion: str | None = None,
) -> TransaccionFinanciera:
    """Registra una transacción financiera (ingreso/gasto) y actualiza el saldo de la cuenta."""
    cuenta = sesion.get(CuentaFinanciera, cuenta_id)
    if cuenta is None:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    tipo_normalizado = tipo.lower().strip()
    if tipo_normalizado not in {"ingreso", "gasto"}:
        raise ValueError("Tipo de transacción inválido; debe ser 'ingreso' o 'gasto'")

    monto_dec = Decimal(str(monto))
    if monto_dec <= 0:
        raise ValueError("El monto debe ser mayor que cero")

    # Actualizar saldo según tipo
    if tipo_normalizado == "ingreso":
        cuenta.saldo += monto_dec
    else:  # gasto
        cuenta.saldo -= monto_dec

    transaccion = TransaccionFinanciera(
        cuenta_id=cuenta.id,
        tipo=tipo_normalizado,
        monto=monto_dec,
        descripcion=descripcion,
    )
    sesion.add(transaccion)
    sesion.flush()
    sesion.refresh(transaccion)

    # Eventos (EVENTOS.md §5): IngresoRegistrado / GastoRegistrado
    payload = {
        "transaccion_id": transaccion.id,
        "cuenta_id": cuenta.id,
        "tipo": tipo_normalizado,
        "monto": float(monto_dec),
        "descripcion": descripcion,
        "fecha": transaccion.fecha.isoformat() if transaccion.fecha else None,
        "__sesion": sesion,
    }
    if tipo_normalizado == "ingreso":
        emit_event("IngresoRegistrado", payload)
    else:
        emit_event("GastoRegistrado", payload)

    return transaccion


def listar_transacciones_por_cuenta(
    sesion: Session,
    cuenta_id: int,
    *,
    limite: int = 100,
    offset: int = 0,
    tipo: Optional[str] = None,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    conciliada: Optional[bool] = None,
) -> Sequence[TransaccionFinanciera]:
    """
    Lista transacciones de una cuenta financiera, con filtros opcionales por tipo, rango de fechas y estado de conciliación.
    """
    cuenta = sesion.get(CuentaFinanciera, cuenta_id)
    if cuenta is None:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    stmt = select(TransaccionFinanciera).where(
        TransaccionFinanciera.cuenta_id == cuenta_id
    )

    if tipo:
        tipo_normalizado = tipo.lower().strip()
        if tipo_normalizado not in {"ingreso", "gasto"}:
            raise ValueError("Tipo de transacción inválido; debe ser 'ingreso' o 'gasto'")
        stmt = stmt.where(TransaccionFinanciera.tipo == tipo_normalizado)

    if desde is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)

    if conciliada is not None:
        stmt = stmt.where(TransaccionFinanciera.conciliada == conciliada)

    stmt = stmt.order_by(TransaccionFinanciera.fecha.desc()).limit(limite).offset(offset)

    return sesion.scalars(stmt).all()


def listar_transacciones_global(
    sesion: Session,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    tipo: Optional[str] = None,
    cuenta_id: Optional[int] = None,
    conciliada: Optional[bool] = None,
    limite: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    Lista transacciones de todas las cuentas (o de una cuenta si cuenta_id está indicado),
    con filtros opcionales. Para historial financiero y exportación (docs Módulo 4 §7, §8, §12).
    Cada ítem incluye: id, cuenta_id, nombre_cuenta, tipo, monto, fecha, descripcion, conciliada.
    """
    stmt = (
        select(TransaccionFinanciera, CuentaFinanciera.nombre)
        .join(CuentaFinanciera, TransaccionFinanciera.cuenta_id == CuentaFinanciera.id)
    )
    if cuenta_id is not None:
        stmt = stmt.where(TransaccionFinanciera.cuenta_id == cuenta_id)
    if tipo:
        tipo_n = tipo.lower().strip()
        if tipo_n not in {"ingreso", "gasto"}:
            raise ValueError("Tipo de transacción inválido; debe ser 'ingreso' o 'gasto'")
        stmt = stmt.where(TransaccionFinanciera.tipo == tipo_n)
    if desde is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)
    if conciliada is not None:
        stmt = stmt.where(TransaccionFinanciera.conciliada == conciliada)

    stmt = stmt.order_by(TransaccionFinanciera.fecha.desc(), TransaccionFinanciera.id.desc())
    stmt = stmt.limit(limite).offset(offset)

    filas = sesion.execute(stmt).all()
    return [
        {
            "id": tx.id,
            "cuenta_id": tx.cuenta_id,
            "nombre_cuenta": nombre_cuenta,
            "tipo": tx.tipo,
            "monto": float(tx.monto),
            "fecha": tx.fecha.isoformat() if tx.fecha else None,
            "descripcion": tx.descripcion,
            "conciliada": tx.conciliada,
        }
        for tx, nombre_cuenta in filas
    ]


def obtener_resumen_cuenta(
    sesion: Session,
    cuenta_id: int,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> dict:
    """
    Devuelve un resumen financiero de la cuenta:
    - saldo_actual
    - total_ingresos
    - total_gastos
    - balance_movimientos = ingresos - gastos (en el rango opcional).
    """
    cuenta = sesion.get(CuentaFinanciera, cuenta_id)
    if cuenta is None:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    stmt = select(TransaccionFinanciera).where(
        TransaccionFinanciera.cuenta_id == cuenta_id
    )
    if desde is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)

    ingresos = Decimal("0")
    gastos = Decimal("0")
    for tx in sesion.scalars(stmt):
        if tx.tipo == "ingreso":
            ingresos += tx.monto
        elif tx.tipo == "gasto":
            gastos += tx.monto

    balance_movimientos = ingresos - gastos

    return {
        "cuenta_id": cuenta.id,
        "nombre": cuenta.nombre,
        "tipo": cuenta.tipo,
        "saldo_actual": cuenta.saldo,
        "total_ingresos": ingresos,
        "total_gastos": gastos,
        "balance_movimientos": balance_movimientos,
    }


def obtener_evolucion_saldo_cuenta(
    sesion: Session,
    cuenta_id: int,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> list[dict]:
    """
    Devuelve la evolución del saldo de una cuenta en el tiempo,
    como una lista ordenada cronológicamente con:
    - fecha
    - saldo_despues (saldo acumulado luego de cada movimiento)
    """
    cuenta = sesion.get(CuentaFinanciera, cuenta_id)
    if cuenta is None:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    stmt = select(TransaccionFinanciera).where(
        TransaccionFinanciera.cuenta_id == cuenta_id
    )
    if desde is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)

    # Orden cronológico ascendente
    stmt = stmt.order_by(TransaccionFinanciera.fecha.asc(), TransaccionFinanciera.id.asc())

    saldo = Decimal("0")
    puntos: list[dict] = []
    for tx in sesion.scalars(stmt):
        if tx.tipo == "ingreso":
            saldo += tx.monto
        elif tx.tipo == "gasto":
            saldo -= tx.monto
        puntos.append(
            {
                "fecha": tx.fecha,
                "saldo_despues": saldo,
                "tipo": tx.tipo,
                "monto": tx.monto,
                "descripcion": tx.descripcion,
            }
        )

    return puntos


def marcar_transaccion_conciliada(
    sesion: Session,
    cuenta_id: int,
    transaccion_id: int,
) -> TransaccionFinanciera:
    """
    Marca una transacción como conciliada. La transacción debe pertenecer a la cuenta indicada.
    """
    cuenta = sesion.get(CuentaFinanciera, cuenta_id)
    if cuenta is None:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    tx = sesion.get(TransaccionFinanciera, transaccion_id)
    if tx is None:
        raise ValueError(f"Transacción {transaccion_id} no encontrada")
    if tx.cuenta_id != cuenta_id:
        raise ValueError(f"La transacción {transaccion_id} no pertenece a la cuenta {cuenta_id}")

    tx.conciliada = True
    tx.fecha_conciliacion = datetime.now(timezone.utc)
    sesion.add(tx)
    sesion.flush()
    sesion.refresh(tx)
    return tx


def desmarcar_transaccion_conciliada(
    sesion: Session,
    cuenta_id: int,
    transaccion_id: int,
) -> TransaccionFinanciera:
    """
    Quita el estado de conciliada de una transacción. La transacción debe pertenecer a la cuenta indicada.
    """
    cuenta = sesion.get(CuentaFinanciera, cuenta_id)
    if cuenta is None:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    tx = sesion.get(TransaccionFinanciera, transaccion_id)
    if tx is None:
        raise ValueError(f"Transacción {transaccion_id} no encontrada")
    if tx.cuenta_id != cuenta_id:
        raise ValueError(f"La transacción {transaccion_id} no pertenece a la cuenta {cuenta_id}")

    tx.conciliada = False
    tx.fecha_conciliacion = None
    sesion.add(tx)
    sesion.flush()
    sesion.refresh(tx)
    return tx


def resumen_financiero_global(
    sesion: Session,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> dict:
    """
    Resumen financiero consolidado de todas las cuentas (docs Módulo 4 §5 Resumen financiero).
    - saldo_total: suma de saldos actuales de todas las cuentas.
    - total_ingresos / total_gastos: suma de transacciones en el rango [desde, hasta] si se indican; si no, 0.
    - cantidad_cuentas.
    """
    # Saldo total actual (suma de saldos de todas las cuentas)
    stmt_saldo = select(func.coalesce(func.sum(CuentaFinanciera.saldo), 0))
    saldo_total = sesion.execute(stmt_saldo).scalar() or Decimal("0")

    # Cantidad de cuentas
    stmt_count = select(func.count(CuentaFinanciera.id))
    cantidad_cuentas = sesion.execute(stmt_count).scalar() or 0

    total_ingresos = Decimal("0")
    total_gastos = Decimal("0")
    if desde is not None or hasta is not None:
        stmt = select(
            func.coalesce(
                func.sum(case((TransaccionFinanciera.tipo == "ingreso", TransaccionFinanciera.monto), else_=0)),
                0,
            ).label("ingresos"),
            func.coalesce(
                func.sum(case((TransaccionFinanciera.tipo == "gasto", TransaccionFinanciera.monto), else_=0)),
                0,
            ).label("gastos"),
        ).select_from(TransaccionFinanciera)
        if desde is not None:
            stmt = stmt.where(TransaccionFinanciera.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)
        row = sesion.execute(stmt).one()
        total_ingresos = row.ingresos or Decimal("0")
        total_gastos = row.gastos or Decimal("0")

    return {
        "saldo_total": saldo_total,
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "cantidad_cuentas": cantidad_cuentas,
        "desde": desde.isoformat() if desde else None,
        "hasta": hasta.isoformat() if hasta else None,
    }


def obtener_flujo_caja(
    sesion: Session,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> list[dict]:
    """
    Devuelve el flujo de caja agregado por día (docs Módulo 4 §6 Flujo de caja).
    Para cada fecha incluye:
    - ingresos: suma de transacciones tipo "ingreso" del día
    - egresos: suma de transacciones tipo "gasto" del día
    - saldo_dia: ingresos - egresos
    - saldo_acumulado: suma acumulada de saldo_dia ordenado cronológicamente
    """
    # Agrupamos por fecha (DATE) para que funcione correctamente en SQLite.
    fecha_expr = func.date(TransaccionFinanciera.fecha).label("fecha")

    stmt = select(
        fecha_expr,
        func.coalesce(
            func.sum(
                case(
                    (TransaccionFinanciera.tipo == "ingreso", TransaccionFinanciera.monto),
                    else_=0,
                )
            ),
            0,
        ).label("ingresos"),
        func.coalesce(
            func.sum(
                case(
                    (TransaccionFinanciera.tipo == "gasto", TransaccionFinanciera.monto),
                    else_=0,
                )
            ),
            0,
        ).label("egresos"),
    ).select_from(TransaccionFinanciera)

    if desde is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)

    stmt = stmt.group_by(fecha_expr).order_by(fecha_expr.asc())

    filas = sesion.execute(stmt).all()

    resultado: list[dict] = []
    saldo_acumulado = Decimal("0")
    for fila in filas:
        fecha, ingresos, egresos = fila.fecha, fila.ingresos, fila.egresos
        ingresos_dec = ingresos if isinstance(ingresos, Decimal) else Decimal(str(ingresos or 0))
        egresos_dec = egresos if isinstance(egresos, Decimal) else Decimal(str(egresos or 0))
        saldo_dia = ingresos_dec - egresos_dec
        saldo_acumulado += saldo_dia
        resultado.append(
            {
                "fecha": fecha,
                "ingresos": ingresos_dec,
                "egresos": egresos_dec,
                "saldo_dia": saldo_dia,
                "saldo_acumulado": saldo_acumulado,
            }
        )

    return resultado


def obtener_balances_mensuales(
    sesion: Session,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> list[dict]:
    """
    Genera balances financieros mensuales a partir de las transacciones:
    - periodo (YYYY-MM)
    - ingresos: suma de montos tipo "ingreso" del mes
    - egresos: suma de montos tipo "gasto" del mes
    - resultado_neto: ingresos - egresos

    Corresponde al submódulo Balances (docs Módulo 4 §10).
    """
    # Usamos strftime para obtener año-mes de la fecha de la transacción.
    periodo_expr = func.strftime("%Y-%m", TransaccionFinanciera.fecha).label("periodo")

    stmt = select(
        periodo_expr,
        func.coalesce(
            func.sum(
                case(
                    (TransaccionFinanciera.tipo == "ingreso", TransaccionFinanciera.monto),
                    else_=0,
                )
            ),
            0,
        ).label("ingresos"),
        func.coalesce(
            func.sum(
                case(
                    (TransaccionFinanciera.tipo == "gasto", TransaccionFinanciera.monto),
                    else_=0,
                )
            ),
            0,
        ).label("egresos"),
    ).select_from(TransaccionFinanciera)

    if desde is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)

    stmt = stmt.group_by(periodo_expr).order_by(periodo_expr.asc())

    filas = sesion.execute(stmt).all()

    resultado: list[dict] = []
    for fila in filas:
        periodo, ingresos, egresos = fila.periodo, fila.ingresos, fila.egresos
        ingresos_dec = ingresos if isinstance(ingresos, Decimal) else Decimal(str(ingresos or 0))
        egresos_dec = egresos if isinstance(egresos, Decimal) else Decimal(str(egresos or 0))
        resultado_neto = ingresos_dec - egresos_dec
        resultado.append(
            {
                "periodo": periodo,
                "ingresos": ingresos_dec,
                "egresos": egresos_dec,
                "resultado_neto": resultado_neto,
            }
        )

    return resultado


def obtener_indicadores_financieros(
    sesion: Session,
    *,
    periodo: Literal["dia", "mes"] = "dia",
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> dict:
    """
    Calcula indicadores financieros globales básicos:
    - total_ingresos
    - total_gastos
    - resultado_neto
    - promedio_diario (resultado_neto / número de días en el rango)

    Si no se indican desde/hasta:
    - periodo="dia": usa el día actual.
    - periodo="mes": usa el mes actual.

    Diseñado para alimentar el submódulo Indicadores financieros (docs Módulo 4 §11).
    """
    ahora = datetime.now(timezone.utc)

    if desde is None or hasta is None:
        if periodo == "mes":
            # Primer día del mes actual (00:00) hasta fin de mes (aprox 31 días vista, suficiente para SQLite)
            desde_calc = datetime(ahora.year, ahora.month, 1, tzinfo=timezone.utc)
            # Sumamos 32 días y retrocedemos a 00:00 del día 1 del siguiente mes como límite abierto
            if ahora.month == 12:
                hasta_calc = datetime(ahora.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                hasta_calc = datetime(ahora.year, ahora.month + 1, 1, tzinfo=timezone.utc)
        else:
            # periodo "dia": rango del día actual
            desde_calc = datetime(ahora.year, ahora.month, ahora.day, tzinfo=timezone.utc)
            hasta_calc = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59, tzinfo=timezone.utc)
        if desde is None:
            desde = desde_calc
        if hasta is None:
            hasta = hasta_calc

    # Agregamos sobre todas las transacciones en el rango
    stmt = select(
        func.coalesce(
            func.sum(
                case(
                    (TransaccionFinanciera.tipo == "ingreso", TransaccionFinanciera.monto),
                    else_=0,
                )
            ),
            0,
        ).label("ingresos"),
        func.coalesce(
            func.sum(
                case(
                    (TransaccionFinanciera.tipo == "gasto", TransaccionFinanciera.monto),
                    else_=0,
                )
            ),
            0,
        ).label("gastos"),
        func.count().label("cantidad_movimientos"),
    ).select_from(TransaccionFinanciera)

    stmt = stmt.where(TransaccionFinanciera.fecha >= desde).where(
        TransaccionFinanciera.fecha <= hasta
    )

    row = sesion.execute(stmt).one()
    total_ingresos = row.ingresos or Decimal("0")
    total_gastos = row.gastos or Decimal("0")
    resultado_neto = total_ingresos - total_gastos

    # Número de días en el rango (al menos 1)
    dias = max((hasta.date() - desde.date()).days + 1, 1)
    promedio_diario = resultado_neto / Decimal(dias)

    return {
        "periodo": periodo,
        "desde": desde,
        "hasta": hasta,
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "resultado_neto": resultado_neto,
        "promedio_diario": promedio_diario,
        "dias": dias,
        "cantidad_movimientos": int(row.cantidad_movimientos or 0),
    }


# ---------------------------------------------------------------------------
# Nuevas funciones — brechas funcionales Módulo 4 (Finanzas)
# ---------------------------------------------------------------------------


def _agg_transacciones_por_expr(
    sesion: Session,
    periodo_expr: Any,
    desde: Optional[datetime],
    hasta: Optional[datetime],
) -> list[dict[str, Any]]:
    """Helper: agrupa TransaccionFinanciera por periodo_expr e incluye ingresos/egresos/resultado."""
    stmt = select(
        periodo_expr,
        func.coalesce(
            func.sum(
                case(
                    (TransaccionFinanciera.tipo == "ingreso", TransaccionFinanciera.monto),
                    else_=0,
                )
            ),
            0,
        ).label("ingresos"),
        func.coalesce(
            func.sum(
                case(
                    (TransaccionFinanciera.tipo == "gasto", TransaccionFinanciera.monto),
                    else_=0,
                )
            ),
            0,
        ).label("egresos"),
    ).select_from(TransaccionFinanciera)

    if desde is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)

    stmt = stmt.group_by(periodo_expr).order_by(periodo_expr.asc())
    filas = sesion.execute(stmt).all()

    resultado: list[dict[str, Any]] = []
    for fila in filas:
        ing = fila.ingresos if isinstance(fila.ingresos, Decimal) else Decimal(str(fila.ingresos or 0))
        eg = fila.egresos if isinstance(fila.egresos, Decimal) else Decimal(str(fila.egresos or 0))
        resultado.append(
            {
                "periodo": str(fila[0]),
                "ingresos": float(ing),
                "egresos": float(eg),
                "resultado_neto": float(ing - eg),
            }
        )
    return resultado


def obtener_balances_diarios(
    sesion: Session,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """
    Balance financiero diario (docs Módulo 4 §10).
    Para cada día devuelve: periodo (YYYY-MM-DD), ingresos, egresos, resultado_neto.
    """
    expr = func.date(TransaccionFinanciera.fecha).label("periodo")
    return _agg_transacciones_por_expr(sesion, expr, desde, hasta)


def obtener_balances_anuales(
    sesion: Session,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """
    Balance financiero anual (docs Módulo 4 §10).
    Para cada año devuelve: periodo (YYYY), ingresos, egresos, resultado_neto.
    """
    expr = func.strftime("%Y", TransaccionFinanciera.fecha).label("periodo")
    return _agg_transacciones_por_expr(sesion, expr, desde, hasta)


def obtener_flujo_caja_agrupado(
    sesion: Session,
    *,
    agrupacion: Literal["dia", "semana", "mes"] = "dia",
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """
    Flujo de caja agrupado por día/semana/mes (docs Módulo 4 §6).
    Devuelve: periodo, ingresos, egresos, saldo_dia, saldo_acumulado.
    """
    if agrupacion not in {"dia", "semana", "mes"}:
        raise ValueError("agrupacion debe ser 'dia', 'semana' o 'mes'")

    if agrupacion == "dia":
        expr = func.date(TransaccionFinanciera.fecha).label("periodo")
    elif agrupacion == "mes":
        expr = func.strftime("%Y-%m", TransaccionFinanciera.fecha).label("periodo")
    else:  # semana
        expr = func.strftime("%Y-W%W", TransaccionFinanciera.fecha).label("periodo")

    base = _agg_transacciones_por_expr(sesion, expr, desde, hasta)
    saldo_acumulado = Decimal("0")
    for fila in base:
        saldo_dia = Decimal(str(fila["ingresos"])) - Decimal(str(fila["egresos"]))
        saldo_acumulado += saldo_dia
        fila["saldo_dia"] = float(saldo_dia)
        fila["saldo_acumulado"] = float(saldo_acumulado)
    return base


def rentabilidad_por_periodo(
    sesion: Session,
    *,
    fecha_desde: date_type,
    fecha_hasta: date_type,
    agrupacion: Literal["dia", "mes"] = "mes",
) -> dict[str, Any]:
    """
    Rentabilidad por período (docs Módulo 4 §9).
    Cruza ventas (ItemVenta) con costos (Producto.costo_actual) y gastos financieros
    (TransaccionFinanciera.tipo='gasto') para calcular margen bruto y neto por período.

    Devuelve resumen global y tabla de filas agrupadas.
    """
    from backend.models.venta import Venta, ItemVenta, EstadoVenta
    from backend.models.producto import Producto

    desde_str = fecha_desde.isoformat()
    hasta_str = fecha_hasta.isoformat()

    # Ventas brutas y costo total por período
    if agrupacion == "dia":
        venta_periodo_expr = func.date(Venta.creado_en).label("periodo")
    else:
        venta_periodo_expr = func.strftime("%Y-%m", Venta.creado_en).label("periodo")

    ventas_stmt = (
        select(
            venta_periodo_expr,
            func.coalesce(func.sum(ItemVenta.subtotal), 0).label("total_ventas"),
            func.coalesce(
                func.sum(ItemVenta.cantidad * Producto.costo_actual), 0
            ).label("total_costo"),
        )
        .select_from(ItemVenta)
        .join(Venta, Venta.id == ItemVenta.venta_id)
        .join(Producto, Producto.id == ItemVenta.producto_id)
        .where(func.date(Venta.creado_en) >= desde_str)
        .where(func.date(Venta.creado_en) <= hasta_str)
        .where(Venta.estado != EstadoVenta.CANCELADA.value)
        .group_by(venta_periodo_expr)
    )
    ventas_rows = sesion.execute(ventas_stmt).all()
    ventas_map: dict[str, dict] = {}
    for r in ventas_rows:
        ventas_map[str(r.periodo)] = {
            "total_ventas": float(r.total_ventas or 0),
            "total_costo": float(r.total_costo or 0),
        }

    # Gastos financieros por período
    from datetime import datetime as dt_type
    desde_dt = dt_type.combine(fecha_desde, dt_type.min.time()).replace(tzinfo=timezone.utc)
    hasta_dt = dt_type.combine(fecha_hasta, dt_type.max.time()).replace(tzinfo=timezone.utc)

    if agrupacion == "dia":
        gasto_periodo_expr = func.date(TransaccionFinanciera.fecha).label("periodo")
    else:
        gasto_periodo_expr = func.strftime("%Y-%m", TransaccionFinanciera.fecha).label("periodo")

    gastos_stmt = (
        select(
            gasto_periodo_expr,
            func.coalesce(func.sum(TransaccionFinanciera.monto), 0).label("total_gastos"),
        )
        .where(TransaccionFinanciera.tipo == "gasto")
        .where(TransaccionFinanciera.fecha >= desde_dt)
        .where(TransaccionFinanciera.fecha <= hasta_dt)
        .group_by(gasto_periodo_expr)
    )
    gastos_rows = sesion.execute(gastos_stmt).all()
    gastos_map: dict[str, float] = {str(r.periodo): float(r.total_gastos or 0) for r in gastos_rows}

    # Combinar por período
    periodos = sorted(set(ventas_map.keys()) | set(gastos_map.keys()))
    filas: list[dict[str, Any]] = []
    total_ventas_global = Decimal("0")
    total_costo_global = Decimal("0")
    total_gastos_global = Decimal("0")

    for p in periodos:
        vd = ventas_map.get(p, {"total_ventas": 0.0, "total_costo": 0.0})
        tv = Decimal(str(vd["total_ventas"]))
        tc = Decimal(str(vd["total_costo"]))
        tg = Decimal(str(gastos_map.get(p, 0.0)))
        margen_bruto = tv - tc
        margen_neto = margen_bruto - tg
        margen_bruto_pct = float(round(margen_bruto / tv * 100, 2)) if tv else 0.0
        margen_neto_pct = float(round(margen_neto / tv * 100, 2)) if tv else 0.0

        total_ventas_global += tv
        total_costo_global += tc
        total_gastos_global += tg

        filas.append(
            {
                "periodo": p,
                "total_ventas": float(tv),
                "total_costo": float(tc),
                "gastos_operativos": float(tg),
                "margen_bruto": float(round(margen_bruto, 2)),
                "margen_bruto_pct": margen_bruto_pct,
                "margen_neto": float(round(margen_neto, 2)),
                "margen_neto_pct": margen_neto_pct,
            }
        )

    # Resumen global
    mg_bruto_global = total_ventas_global - total_costo_global
    mg_neto_global = mg_bruto_global - total_gastos_global
    return {
        "resumen": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "agrupacion": agrupacion,
            "total_ventas": float(total_ventas_global),
            "total_costo": float(total_costo_global),
            "gastos_operativos": float(total_gastos_global),
            "margen_bruto": float(round(mg_bruto_global, 2)),
            "margen_bruto_pct": float(round(mg_bruto_global / total_ventas_global * 100, 2)) if total_ventas_global else 0.0,
            "margen_neto": float(round(mg_neto_global, 2)),
            "margen_neto_pct": float(round(mg_neto_global / total_ventas_global * 100, 2)) if total_ventas_global else 0.0,
        },
        "filas": filas,
    }


def tendencias_financieras(
    sesion: Session,
    *,
    agrupacion: Literal["dia", "semana", "mes"] = "mes",
    n_periodos: int = 12,
    hasta: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Tendencias financieras (docs Módulo 4 §12): compara ingresos vs. egresos a lo largo
    del tiempo, calculando variaciones porcentuales entre períodos consecutivos.

    Devuelve los últimos `n_periodos` agrupados según `agrupacion` ('dia', 'semana', 'mes').
    Cada entrada incluye:
      - periodo: etiqueta del período
      - ingresos: total ingresos del período
      - egresos: total egresos del período
      - resultado_neto: ingresos - egresos
      - variacion_ingresos_pct: variación % respecto al período anterior (None para el 1er período)
      - variacion_egresos_pct: variación % respecto al período anterior (None para el 1er período)
    """
    if agrupacion == "dia":
        periodo_expr = func.strftime("%Y-%m-%d", TransaccionFinanciera.fecha).label("periodo")
    elif agrupacion == "semana":
        periodo_expr = func.strftime("%Y-W%W", TransaccionFinanciera.fecha).label("periodo")
    else:
        periodo_expr = func.strftime("%Y-%m", TransaccionFinanciera.fecha).label("periodo")

    stmt = (
        select(
            periodo_expr,
            func.coalesce(
                func.sum(case((TransaccionFinanciera.tipo == "ingreso", TransaccionFinanciera.monto), else_=0)), 0
            ).label("ingresos"),
            func.coalesce(
                func.sum(case((TransaccionFinanciera.tipo == "gasto", TransaccionFinanciera.monto), else_=0)), 0
            ).label("egresos"),
        )
        .select_from(TransaccionFinanciera)
        .group_by(periodo_expr)
        .order_by(periodo_expr.asc())
    )
    if hasta is not None:
        stmt = stmt.where(TransaccionFinanciera.fecha <= hasta)

    filas_db = sesion.execute(stmt).all()

    # Tomar los últimos n_periodos
    filas_db = filas_db[-n_periodos:] if len(filas_db) > n_periodos else filas_db

    filas: list[dict[str, Any]] = []
    prev_ingresos: Optional[Decimal] = None
    prev_egresos: Optional[Decimal] = None

    for row in filas_db:
        ingresos = row.ingresos if isinstance(row.ingresos, Decimal) else Decimal(str(row.ingresos or 0))
        egresos = row.egresos if isinstance(row.egresos, Decimal) else Decimal(str(row.egresos or 0))
        resultado_neto = ingresos - egresos

        if prev_ingresos is not None and prev_ingresos > 0:
            variacion_ingresos_pct: Optional[float] = float(
                round((ingresos - prev_ingresos) / prev_ingresos * 100, 2)
            )
        else:
            variacion_ingresos_pct = None

        if prev_egresos is not None and prev_egresos > 0:
            variacion_egresos_pct: Optional[float] = float(
                round((egresos - prev_egresos) / prev_egresos * 100, 2)
            )
        else:
            variacion_egresos_pct = None

        filas.append(
            {
                "periodo": str(row.periodo),
                "ingresos": float(ingresos),
                "egresos": float(egresos),
                "resultado_neto": float(resultado_neto),
                "variacion_ingresos_pct": variacion_ingresos_pct,
                "variacion_egresos_pct": variacion_egresos_pct,
            }
        )
        prev_ingresos = ingresos
        prev_egresos = egresos

    return {
        "agrupacion": agrupacion,
        "n_periodos": n_periodos,
        "filas": filas,
    }


def obtener_indicadores_avanzados(
    sesion: Session,
    *,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Indicadores financieros avanzados (docs Módulo 4 §11):
    - liquidez: saldo_total_cuentas / promedio_egresos_diarios (o None si sin egresos)
    - margen_ganancia_pct: (total_ingresos - total_gastos) / total_ingresos * 100
    - ticket_promedio: total_ventas / cantidad_ventas (desde ventas, no desde TX financieras)
    - total_ingresos, total_gastos, resultado_neto (del rango)
    - saldo_total_cuentas
    """
    from backend.models.venta import Venta, EstadoVenta

    # Saldo total de cuentas (liquidez base)
    saldo_total = sesion.execute(
        select(func.coalesce(func.sum(CuentaFinanciera.saldo), 0))
    ).scalar() or Decimal("0")

    # Totales financieros en el rango
    base_stmt = select(
        func.coalesce(
            func.sum(case((TransaccionFinanciera.tipo == "ingreso", TransaccionFinanciera.monto), else_=0)), 0
        ).label("ingresos"),
        func.coalesce(
            func.sum(case((TransaccionFinanciera.tipo == "gasto", TransaccionFinanciera.monto), else_=0)), 0
        ).label("gastos"),
        func.count(func.distinct(func.date(TransaccionFinanciera.fecha))).label("dias_con_actividad"),
    ).select_from(TransaccionFinanciera)
    if desde is not None:
        base_stmt = base_stmt.where(TransaccionFinanciera.fecha >= desde)
    if hasta is not None:
        base_stmt = base_stmt.where(TransaccionFinanciera.fecha <= hasta)
    row = sesion.execute(base_stmt).one()
    total_ingresos = row.ingresos if isinstance(row.ingresos, Decimal) else Decimal(str(row.ingresos or 0))
    total_gastos = row.gastos if isinstance(row.gastos, Decimal) else Decimal(str(row.gastos or 0))
    dias_activos = max(int(row.dias_con_actividad or 1), 1)
    resultado_neto = total_ingresos - total_gastos

    # Liquidez = saldo_total / promedio_egresos_diarios
    promedio_egresos_diarios = total_gastos / Decimal(dias_activos) if total_gastos > 0 else Decimal("0")
    liquidez = float(round(Decimal(str(saldo_total)) / promedio_egresos_diarios, 2)) if promedio_egresos_diarios > 0 else None

    # Margen de ganancia %
    margen_ganancia_pct = float(round(resultado_neto / total_ingresos * 100, 2)) if total_ingresos > 0 else 0.0

    # Ticket promedio desde ventas
    ventas_stmt = select(
        func.count(Venta.id).label("cantidad_ventas"),
        func.coalesce(func.sum(Venta.total), 0).label("total_ventas"),
    ).where(Venta.estado != EstadoVenta.CANCELADA.value)
    if desde is not None:
        ventas_stmt = ventas_stmt.where(Venta.creado_en >= desde)
    if hasta is not None:
        ventas_stmt = ventas_stmt.where(Venta.creado_en <= hasta)
    vrow = sesion.execute(ventas_stmt).one()
    cantidad_ventas = int(vrow.cantidad_ventas or 0)
    total_ventas = float(vrow.total_ventas or 0)
    ticket_promedio = round(total_ventas / cantidad_ventas, 2) if cantidad_ventas > 0 else 0.0

    return {
        "saldo_total_cuentas": float(saldo_total),
        "total_ingresos": float(total_ingresos),
        "total_gastos": float(total_gastos),
        "resultado_neto": float(resultado_neto),
        "margen_ganancia_pct": margen_ganancia_pct,
        "liquidez": liquidez,
        "promedio_egresos_diarios": float(promedio_egresos_diarios),
        "ticket_promedio": ticket_promedio,
        "cantidad_ventas": cantidad_ventas,
        "total_ventas": total_ventas,
        "desde": desde.isoformat() if desde else None,
        "hasta": hasta.isoformat() if hasta else None,
    }
