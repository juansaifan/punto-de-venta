# Servicios del dominio Tesorería (caja)
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.events import emit as emit_event
from backend.models.caja import Caja, MovimientoCaja, TipoMovimientoCaja


def abrir_caja(
    sesion: Session,
    *,
    saldo_inicial: Decimal | float = 0,
    usuario_id: Optional[int] = None,
) -> Caja:
    """
    Abre una nueva caja. Solo puede haber una caja abierta a la vez.
    Lanza ValueError si ya existe una caja abierta.
    """
    existente = obtener_caja_abierta(sesion)
    if existente is not None:
        raise ValueError(
            f"Ya existe una caja abierta (id={existente.id}). "
            "Cierre la caja actual antes de abrir otra."
        )
    saldo_inicial = Decimal(str(saldo_inicial))
    caja = Caja(
        saldo_inicial=saldo_inicial,
        usuario_id=usuario_id,
    )
    sesion.add(caja)
    sesion.flush()
    sesion.refresh(caja)
    # Evento (EVENTOS.md §4)
    emit_event(
        "CajaAbierta",
        {
            "caja_id": caja.id,
            "fecha_apertura": caja.fecha_apertura.isoformat() if caja.fecha_apertura else None,
            "saldo_inicial": float(caja.saldo_inicial),
            "usuario_id": caja.usuario_id,
            "__sesion": sesion,
        },
    )
    return caja


def cerrar_caja(
    sesion: Session,
    caja_id: int,
    *,
    saldo_final: Optional[Decimal | float] = None,
    supervisor_autorizado: bool = False,
) -> Caja:
    """
    Cierra la caja indicada (registra fecha_cierre y opcionalmente saldo_final).
    Lanza ValueError si la caja no existe o ya está cerrada.
    """
    from datetime import datetime, timezone

    caja = sesion.get(Caja, caja_id)
    if caja is None:
        raise ValueError(f"Caja {caja_id} no encontrada")
    if caja.fecha_cierre is not None:
        raise ValueError(f"La caja {caja_id} ya está cerrada")
    from backend.services import configuracion as svc_configuracion

    config = svc_configuracion.get_configuracion_caja(sesion)

    # Si el arqueo es obligatorio, saldo_final debe estar informado.
    if config.get("obligar_arqueo", False) and saldo_final is None:
        raise ValueError("Arqueo requerido: saldo_final es obligatorio para cerrar la caja")

    caja.fecha_cierre = datetime.now(timezone.utc)
    if saldo_final is not None:
        caja.saldo_final = Decimal(str(saldo_final))

    # Validación de diferencia según configuración.
    if saldo_final is not None:
        # saldo_teorico se calcula con saldo_inicial y movimientos existentes.
        resumen_teorico = obtener_resumen_caja(sesion, caja_id)
        saldo_teorico = Decimal(str(resumen_teorico["saldo_teorico"]))
        saldo_final_dec = Decimal(str(saldo_final))

        # Normalizamos a 2 decimales para evitar diferencias por representación.
        saldo_teorico = saldo_teorico.quantize(Decimal("0.01"))
        saldo_final_dec = saldo_final_dec.quantize(Decimal("0.01"))
        diferencia = saldo_final_dec - saldo_teorico

        # Comparación con 2 decimales.
        if diferencia != 0 and not config.get(
            "permitir_cierre_con_diferencia", False
        ):
            if config.get("requerir_autorizacion_supervisor_cierre", False):
                if not supervisor_autorizado:
                    raise ValueError(
                        "Se requiere autorización de supervisor para cerrar con diferencia"
                    )
            else:
                raise ValueError("No se permite cerrar caja con diferencia de arqueo")

    sesion.add(caja)
    sesion.flush()
    sesion.refresh(caja)
    # Evento (EVENTOS.md §4)
    emit_event(
        "CajaCerrada",
        {
            "caja_id": caja.id,
            "fecha_apertura": caja.fecha_apertura.isoformat() if caja.fecha_apertura else None,
            "fecha_cierre": caja.fecha_cierre.isoformat() if caja.fecha_cierre else None,
            "saldo_inicial": float(caja.saldo_inicial),
            "saldo_final": float(caja.saldo_final) if caja.saldo_final is not None else None,
            "__sesion": sesion,
        },
    )
    return caja


def obtener_caja_abierta(sesion: Session) -> Optional[Caja]:
    """Devuelve la caja abierta (fecha_cierre is None), si existe."""
    stmt = select(Caja).where(Caja.fecha_cierre.is_(None)).limit(1)
    return sesion.execute(stmt).scalars().first()


def obtener_caja_por_id(sesion: Session, caja_id: int) -> Optional[Caja]:
    """Obtiene una caja por ID."""
    return sesion.get(Caja, caja_id)


def listar_cajas(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Caja]:
    """Lista cajas (más recientes primero por fecha_apertura)."""
    stmt = (
        select(Caja)
        .order_by(Caja.fecha_apertura.desc())
        .limit(limite)
        .offset(offset)
    )
    return sesion.scalars(stmt).all()


def registrar_movimiento_caja(
    sesion: Session,
    caja_id: int,
    *,
    tipo: str,
    monto: Decimal | float,
    referencia: Optional[str] = None,
    medio_pago: str = "EFECTIVO",
) -> MovimientoCaja:
    """
    Registra un movimiento de caja (INGRESO, GASTO, RETIRO, etc.).
    La caja debe estar abierta. Monto siempre positivo; el tipo indica la naturaleza.
    """
    caja = sesion.get(Caja, caja_id)
    if caja is None:
        raise ValueError(f"Caja {caja_id} no encontrada")
    if caja.fecha_cierre is not None:
        raise ValueError(f"La caja {caja_id} está cerrada; no se pueden registrar movimientos")
    monto_val = Decimal(str(monto))
    if monto_val <= 0:
        raise ValueError("El monto debe ser mayor que cero")
    tipos_validos = {e.value for e in TipoMovimientoCaja}
    if tipo not in tipos_validos:
        raise ValueError(f"Tipo de movimiento inválido: {tipo}. Válidos: {sorted(tipos_validos)}")
    mov = MovimientoCaja(
        caja_id=caja_id,
        tipo=tipo,
        monto=monto_val,
        medio_pago=(medio_pago or "EFECTIVO").strip()[:32],
        referencia=referencia[:256] if referencia else None,
    )
    sesion.add(mov)
    sesion.flush()
    sesion.refresh(mov)

    # Evento (EVENTOS.md §4)
    emit_event(
        "MovimientoCajaRegistrado",
        {
            "movimiento_id": mov.id,
            "caja_id": mov.caja_id,
            "tipo": mov.tipo,
            "monto": float(mov.monto),
            "medio_pago": mov.medio_pago,
            "referencia": mov.referencia,
            "fecha": mov.fecha.isoformat() if mov.fecha else None,
            "__sesion": sesion,
        },
    )
    return mov


def listar_movimientos_caja(
    sesion: Session,
    caja_id: int,
    *,
    tipo: Optional[str] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[MovimientoCaja]:
    """Lista movimientos de una caja (ordenados por fecha). Filtra por tipo si se indica."""
    stmt = select(MovimientoCaja).where(MovimientoCaja.caja_id == caja_id)
    if tipo is not None:
        stmt = stmt.where(MovimientoCaja.tipo == tipo.upper())
    stmt = stmt.order_by(MovimientoCaja.fecha.desc()).limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def listar_movimientos_global(
    sesion: Session,
    *,
    tipo: Optional[str] = None,
    caja_id: Optional[int] = None,
    desde: Optional[object] = None,
    hasta: Optional[object] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[MovimientoCaja]:
    """
    Lista movimientos de caja de forma global, con filtros opcionales.

    Permite auditar movimientos de todas las cajas (§5 Movimientos).
    """
    from datetime import datetime

    stmt = select(MovimientoCaja)
    if tipo is not None:
        stmt = stmt.where(MovimientoCaja.tipo == tipo.upper())
    if caja_id is not None:
        stmt = stmt.where(MovimientoCaja.caja_id == caja_id)
    if desde is not None:
        stmt = stmt.where(MovimientoCaja.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(MovimientoCaja.fecha <= hasta)
    stmt = stmt.order_by(MovimientoCaja.fecha.desc()).limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def resumen_global_cajas(sesion: Session) -> dict:
    """
    Devuelve estadísticas consolidadas de todas las cajas históricas:
    - cantidad_cajas_total
    - cantidad_cajas_abiertas
    - cantidad_cajas_cerradas
    - total_ingresos_historico
    - total_egresos_historico
    - saldo_neto_historico
    """
    from sqlalchemy import func as sa_func

    total_cajas = sesion.execute(select(sa_func.count(Caja.id))).scalar() or 0
    abiertas = (
        sesion.execute(
            select(sa_func.count(Caja.id)).where(Caja.fecha_cierre.is_(None))
        ).scalar()
        or 0
    )

    ingresos_tipos = {
        TipoMovimientoCaja.INGRESO.value,
        TipoMovimientoCaja.VENTA.value,
    }
    egresos_tipos = {
        TipoMovimientoCaja.GASTO.value,
        TipoMovimientoCaja.RETIRO.value,
    }

    stmt_movs = select(MovimientoCaja.tipo, sa_func.sum(MovimientoCaja.monto)).group_by(
        MovimientoCaja.tipo
    )
    totales_por_tipo: dict[str, Decimal] = {}
    for tipo_val, total in sesion.execute(stmt_movs):
        totales_por_tipo[str(tipo_val)] = Decimal(str(total or 0))

    total_ingresos = sum(
        (totales_por_tipo.get(t, Decimal("0")) for t in ingresos_tipos),
        start=Decimal("0"),
    )
    total_egresos = sum(
        (totales_por_tipo.get(t, Decimal("0")) for t in egresos_tipos),
        start=Decimal("0"),
    )

    return {
        "cantidad_cajas_total": int(total_cajas),
        "cantidad_cajas_abiertas": int(abiertas),
        "cantidad_cajas_cerradas": int(total_cajas) - int(abiertas),
        "total_ingresos_historico": total_ingresos,
        "total_egresos_historico": total_egresos,
        "saldo_neto_historico": total_ingresos - total_egresos,
    }


def exportar_movimientos_caja_csv(sesion: Session, caja_id: int) -> str:
    """
    Genera un CSV con todos los movimientos de la caja indicada.
    Columnas: id, fecha, tipo, monto, medio_pago, referencia
    """
    caja = sesion.get(Caja, caja_id)
    if caja is None:
        raise ValueError(f"Caja {caja_id} no encontrada")

    movimientos = listar_movimientos_caja(sesion, caja_id, limite=5000)
    lineas = ["id,fecha,tipo,monto,medio_pago,referencia"]
    for m in movimientos:
        fecha_str = m.fecha.isoformat() if m.fecha else ""
        referencia_str = (m.referencia or "").replace(",", ";")
        lineas.append(
            f"{m.id},{fecha_str},{m.tipo},{m.monto},{m.medio_pago},{referencia_str}"
        )
    return "\n".join(lineas)


def obtener_resumen_caja(
    sesion: Session,
    caja_id: int,
) -> dict:
    """
    Devuelve un resumen (arqueo teórico) de la caja:
    - saldo_inicial
    - total_ingresos
    - total_egresos
    - saldo_teorico = saldo_inicial + ingresos - egresos
    """
    caja = sesion.get(Caja, caja_id)
    if caja is None:
        raise ValueError(f"Caja {caja_id} no encontrada")

    stmt = (
        select(
            MovimientoCaja.tipo,
            func.coalesce(func.sum(MovimientoCaja.monto), 0),
        )
        .where(MovimientoCaja.caja_id == caja_id)
        .group_by(MovimientoCaja.tipo)
    )

    totales_por_tipo: dict[str, Decimal] = {}
    for tipo, total in sesion.execute(stmt):
        totales_por_tipo[str(tipo)] = Decimal(str(total))

    ingresos_tipos = {
        TipoMovimientoCaja.INGRESO.value,
        TipoMovimientoCaja.VENTA.value,
    }
    egresos_tipos = {
        TipoMovimientoCaja.GASTO.value,
        TipoMovimientoCaja.RETIRO.value,
    }

    total_ingresos = sum(
        (totales_por_tipo.get(tipo, Decimal("0")) for tipo in ingresos_tipos),
        start=Decimal("0"),
    )
    total_egresos = sum(
        (totales_por_tipo.get(tipo, Decimal("0")) for tipo in egresos_tipos),
        start=Decimal("0"),
    )

    saldo_inicial = caja.saldo_inicial or Decimal("0")
    saldo_teorico = saldo_inicial + total_ingresos - total_egresos

    resumen: dict = {
        "caja_id": caja.id,
        "saldo_inicial": saldo_inicial,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "saldo_teorico": saldo_teorico,
    }

    # Si la caja está cerrada y hay saldo_final informado, devolvemos diferencia
    # para análisis/arqueo (saldo_final - saldo_teorico).
    if caja.fecha_cierre is not None and caja.saldo_final is not None:
        saldo_final = Decimal(str(caja.saldo_final))
        resumen["saldo_final"] = saldo_final
        resumen["diferencia"] = saldo_final - saldo_teorico

    return resumen
