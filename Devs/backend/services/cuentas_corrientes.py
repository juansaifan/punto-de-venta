"""Servicios del submódulo Tesorería / Cuentas Corrientes de Clientes.

Responsabilidades:
- Mantener cuentas corrientes de clientes (saldo de deuda).
- Registrar movimientos de tipo VENTA, PAGO, AJUSTE.
- Exponer resúmenes y listados de movimientos.

Nota: Los modelos `CuentaCorrienteCliente` y `MovimientoCuentaCorriente` viven en
`backend.models.persona`, pero conceptualmente este servicio pertenece a Tesorería.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.events import emit as emit_event
from backend.models.persona import (
    Cliente,
    CuentaCorrienteCliente,
    MovimientoCuentaCorriente,
)


def _obtener_o_crear_cuenta_corriente(
    sesion: Session,
    cliente_id: int,
) -> CuentaCorrienteCliente:
    cuenta = (
        sesion.query(CuentaCorrienteCliente)
        .where(CuentaCorrienteCliente.cliente_id == cliente_id)
        .one_or_none()
    )
    if cuenta is None:
        cliente = sesion.get(Cliente, cliente_id)
        if cliente is None:
            raise ValueError(f"Cliente {cliente_id} no encontrado")
        cuenta = CuentaCorrienteCliente(cliente_id=cliente_id)
        sesion.add(cuenta)
        sesion.flush()
        sesion.refresh(cuenta)
    return cuenta


_TIPOS_CC_VALIDOS = {"VENTA", "PAGO", "AJUSTE", "NOTA_CREDITO", "NOTA_DEBITO"}
_TIPOS_CC_AUMENTAN_SALDO = {"VENTA", "NOTA_DEBITO"}
_TIPOS_CC_REDUCEN_SALDO = {"PAGO", "NOTA_CREDITO"}


def registrar_movimiento_cuenta_corriente(
    sesion: Session,
    *,
    cliente_id: int,
    tipo: str,
    monto: float | Decimal,
    descripcion: Optional[str] = None,
) -> MovimientoCuentaCorriente:
    """
    Registra un movimiento de cuenta corriente para un cliente.

    Reglas de signo sobre el saldo (saldo = deuda del cliente):
    - VENTA / NOTA_DEBITO: saldo += monto (aumenta deuda)
    - PAGO / NOTA_CREDITO: saldo -= monto (reduce deuda)
    - AJUSTE: saldo += monto (monto puede ser positivo o negativo)
    """
    tipo_norm = tipo.upper().strip()
    if tipo_norm not in _TIPOS_CC_VALIDOS:
        raise ValueError(
            f"Tipo de movimiento inválido; debe ser uno de: {', '.join(sorted(_TIPOS_CC_VALIDOS))}"
        )

    monto_dec = Decimal(str(monto))
    if monto_dec <= 0 and tipo_norm != "AJUSTE":
        raise ValueError("El monto debe ser mayor que cero")

    cuenta = _obtener_o_crear_cuenta_corriente(sesion, cliente_id)

    if tipo_norm in _TIPOS_CC_AUMENTAN_SALDO:
        cuenta.saldo += monto_dec
    elif tipo_norm in _TIPOS_CC_REDUCEN_SALDO:
        cuenta.saldo -= monto_dec
    else:  # AJUSTE
        cuenta.saldo += monto_dec

    sesion.add(cuenta)  # marcar explícitamente como dirty para asegurar flush del saldo

    movimiento = MovimientoCuentaCorriente(
        cuenta_id=cuenta.id,
        tipo=tipo_norm,
        monto=monto_dec,
        descripcion=descripcion,
    )
    sesion.add(movimiento)
    sesion.flush()
    sesion.refresh(movimiento)
    sesion.refresh(cuenta)

    # Evento (submódulo Tesorería / cuentas corrientes)
    emit_event(
        "MovimientoCuentaCorrienteRegistrado",
        {
            "movimiento_id": movimiento.id,
            "cuenta_id": movimiento.cuenta_id,
            "cliente_id": cliente_id,
            "tipo": movimiento.tipo,
            "monto": float(movimiento.monto),
            "descripcion": movimiento.descripcion,
            "fecha": movimiento.fecha.isoformat() if movimiento.fecha else None,
            "saldo_despues": float(cuenta.saldo),
            "__sesion": sesion,
        },
    )
    return movimiento


def obtener_resumen_cuenta_corriente(
    sesion: Session,
    cliente_id: int,
) -> dict:
    """
    Devuelve un resumen de la cuenta corriente del cliente:
    - saldo
    - limite_credito (desde Cliente.limite_credito)
    - disponible (limite_credito - saldo, si hay límite)
    """
    cliente = sesion.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} no encontrado")

    cuenta = (
        sesion.query(CuentaCorrienteCliente)
        .where(CuentaCorrienteCliente.cliente_id == cliente_id)
        .one_or_none()
    )
    saldo = cuenta.saldo if cuenta is not None else Decimal("0")

    limite = cliente.limite_credito
    if limite is not None:
        disponible: Optional[Decimal] = limite - saldo
    else:
        disponible = None

    return {
        "cliente_id": cliente_id,
        "saldo": saldo,
        "limite_credito": limite,
        "disponible": disponible,
    }


def listar_cuentas_corrientes(
    sesion: Session,
    *,
    solo_con_saldo: bool = False,
    limite: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    Lista todas las cuentas corrientes de clientes con datos básicos del cliente.
    Si solo_con_saldo=True solo devuelve cuentas con saldo > 0 (deuda activa).
    """
    stmt = select(CuentaCorrienteCliente)
    if solo_con_saldo:
        stmt = stmt.where(CuentaCorrienteCliente.saldo > 0)
    stmt = stmt.order_by(CuentaCorrienteCliente.saldo.desc()).limit(limite).offset(offset)
    cuentas = sesion.scalars(stmt).all()

    resultado = []
    for cuenta in cuentas:
        cliente = sesion.get(Cliente, cuenta.cliente_id)
        resultado.append(
            {
                "cuenta_id": cuenta.id,
                "cliente_id": cuenta.cliente_id,
                "saldo": cuenta.saldo,
                "limite_credito": cliente.limite_credito if cliente else None,
                "disponible": (
                    (cliente.limite_credito - cuenta.saldo)
                    if cliente and cliente.limite_credito is not None
                    else None
                ),
            }
        )
    return resultado


def listar_movimientos_cuenta_corriente(
    sesion: Session,
    *,
    cliente_id: int,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[MovimientoCuentaCorriente]:
    """Lista movimientos de cuenta corriente para un cliente, ordenados por fecha descendente."""
    cliente = sesion.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} no encontrado")

    cuenta = (
        sesion.query(CuentaCorrienteCliente)
        .where(CuentaCorrienteCliente.cliente_id == cliente_id)
        .one_or_none()
    )
    if cuenta is None:
        return []

    stmt = (
        select(MovimientoCuentaCorriente)
        .where(MovimientoCuentaCorriente.cuenta_id == cuenta.id)
        .order_by(
            MovimientoCuentaCorriente.fecha.desc(),
            MovimientoCuentaCorriente.id.desc(),
        )
        .limit(limite)
        .offset(offset)
    )
    return sesion.scalars(stmt).all()


# ---------------------------------------------------------------------------
# Aging de cuentas corrientes (docs Módulo 3 §5 / Tesorería)
# ---------------------------------------------------------------------------

_TRAMOS_AGING = [
    ("0_30", 0, 30),
    ("31_60", 31, 60),
    ("61_90", 61, 90),
    ("mas_90", 91, None),
]


def aging_cuentas_corrientes(sesion: Session) -> dict[str, Any]:
    """
    Reporte de aging (antigüedad de deuda) de cuentas corrientes.

    Para cada cliente con saldo > 0 determina los días transcurridos desde
    el último movimiento de tipo VENTA (deuda más reciente) o desde el
    `actualizado_en` de la cuenta.

    Agrupa los saldos en tramos: 0-30, 31-60, 61-90 y +90 días.
    Docs Módulo 3 §5 — Historial de movimientos / control de deuda.
    """
    # Usar fecha UTC para ser consistente con los timestamps almacenados en UTC
    hoy = datetime.now(timezone.utc).date()

    cuentas = sesion.scalars(
        select(CuentaCorrienteCliente).where(CuentaCorrienteCliente.saldo > 0)
    ).all()

    tramos: dict[str, list[dict[str, Any]]] = {t[0]: [] for t in _TRAMOS_AGING}
    resumen: dict[str, float] = {t[0]: 0.0 for t in _TRAMOS_AGING}

    for cuenta in cuentas:
        # Última VENTA (deuda más antigua sin pagar aún)
        ultimo_venta = sesion.scalar(
            select(func.max(MovimientoCuentaCorriente.fecha))
            .where(
                MovimientoCuentaCorriente.cuenta_id == cuenta.id,
                MovimientoCuentaCorriente.tipo == "VENTA",
            )
        )
        if ultimo_venta:
            if isinstance(ultimo_venta, str):
                ref_date = date.fromisoformat(ultimo_venta[:10])
            elif isinstance(ultimo_venta, datetime):
                ref_date = ultimo_venta.date()
            else:
                ref_date = ultimo_venta
        else:
            ref_date = cuenta.actualizado_en.date() if isinstance(cuenta.actualizado_en, datetime) else hoy

        dias = max(0, (hoy - ref_date).days)
        cliente = sesion.get(Cliente, cuenta.cliente_id)

        from backend.models.persona import Persona
        persona = sesion.get(Persona, cliente.persona_id) if cliente else None
        nombre = f"{persona.nombre} {persona.apellido}" if persona else f"Cliente {cuenta.cliente_id}"

        item = {
            "cuenta_id": cuenta.id,
            "cliente_id": cuenta.cliente_id,
            "nombre": nombre,
            "saldo": float(cuenta.saldo),
            "dias_sin_pago": dias,
            "ultima_venta": ultimo_venta.isoformat()[:10] if ultimo_venta else None,
        }

        for tramo, desde, hasta in _TRAMOS_AGING:
            if desde <= dias and (hasta is None or dias <= hasta):
                tramos[tramo].append(item)
                resumen[tramo] += float(cuenta.saldo)
                break

    total_deuda = sum(resumen.values())
    return {
        "fecha_corte": hoy.isoformat(),
        "total_deuda": round(total_deuda, 2),
        "resumen_por_tramo": {
            t[0]: {"cantidad_clientes": len(tramos[t[0]]), "total": round(resumen[t[0]], 2)}
            for t in _TRAMOS_AGING
        },
        "detalle": {t[0]: tramos[t[0]] for t in _TRAMOS_AGING},
    }


def reporte_deudores(
    sesion: Session,
    *,
    saldo_minimo: float = 0.01,
    limite: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Lista de clientes con deuda activa ordenados por saldo descendente.
    Incluye días desde el último movimiento VENTA y estado del cliente.
    Docs Módulo 3 §5 — Gestión de deuda / morosidad.
    """
    from backend.models.persona import Persona

    hoy = datetime.now(timezone.utc).date()
    stmt = (
        select(CuentaCorrienteCliente)
        .where(CuentaCorrienteCliente.saldo >= Decimal(str(saldo_minimo)))
        .order_by(CuentaCorrienteCliente.saldo.desc())
        .limit(limite)
        .offset(offset)
    )
    cuentas = sesion.scalars(stmt).all()

    resultado = []
    for cuenta in cuentas:
        cliente = sesion.get(Cliente, cuenta.cliente_id)
        persona = sesion.get(Persona, cliente.persona_id) if cliente else None

        ultimo_pago = sesion.scalar(
            select(func.max(MovimientoCuentaCorriente.fecha))
            .where(
                MovimientoCuentaCorriente.cuenta_id == cuenta.id,
                MovimientoCuentaCorriente.tipo == "PAGO",
            )
        )
        ultima_venta = sesion.scalar(
            select(func.max(MovimientoCuentaCorriente.fecha))
            .where(
                MovimientoCuentaCorriente.cuenta_id == cuenta.id,
                MovimientoCuentaCorriente.tipo == "VENTA",
            )
        )

        def _dias(dt_val) -> int | None:
            if dt_val is None:
                return None
            if isinstance(dt_val, str):
                ref = date.fromisoformat(dt_val[:10])
            elif isinstance(dt_val, datetime):
                ref = dt_val.date()
            else:
                ref = dt_val
            return (hoy - ref).days

        limite_credito = float(cliente.limite_credito) if cliente and cliente.limite_credito else None
        disponible = None
        if limite_credito is not None:
            disponible = round(limite_credito - float(cuenta.saldo), 2)

        resultado.append({
            "cuenta_id": cuenta.id,
            "cliente_id": cuenta.cliente_id,
            "nombre": f"{persona.nombre} {persona.apellido}" if persona else f"Cliente {cuenta.cliente_id}",
            "saldo": float(cuenta.saldo),
            "limite_credito": limite_credito,
            "disponible": disponible,
            "dias_desde_ultima_venta": _dias(ultima_venta),
            "dias_desde_ultimo_pago": _dias(ultimo_pago),
            "estado_cliente": cliente.estado if cliente else None,
        })
    return resultado


def estadisticas_pagos_cliente(
    sesion: Session,
    *,
    cliente_id: int,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> dict[str, Any]:
    """
    Estadísticas de pagos de un cliente: cuánto y cuándo paga.
    Docs Módulo 3 §10 — Historial de movimientos.
    """
    from sqlalchemy import Date as SADate, cast as sa_cast

    cliente = sesion.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} no encontrado")

    cuenta = sesion.scalars(
        select(CuentaCorrienteCliente).where(CuentaCorrienteCliente.cliente_id == cliente_id)
    ).first()

    if cuenta is None:
        return {
            "cliente_id": cliente_id,
            "saldo_actual": 0.0,
            "total_ventas_cc": 0.0,
            "total_pagos_cc": 0.0,
            "cantidad_ventas": 0,
            "cantidad_pagos": 0,
            "promedio_pago": 0.0,
            "ultimo_pago": None,
            "ultima_venta": None,
        }

    base_stmt = select(
        MovimientoCuentaCorriente
    ).where(MovimientoCuentaCorriente.cuenta_id == cuenta.id)

    if fecha_desde:
        base_stmt = base_stmt.where(sa_cast(MovimientoCuentaCorriente.fecha, SADate) >= fecha_desde)
    if fecha_hasta:
        base_stmt = base_stmt.where(sa_cast(MovimientoCuentaCorriente.fecha, SADate) <= fecha_hasta)

    movimientos = sesion.scalars(base_stmt).all()

    total_ventas = sum(float(m.monto) for m in movimientos if m.tipo == "VENTA")
    total_pagos = sum(float(m.monto) for m in movimientos if m.tipo == "PAGO")
    cant_ventas = sum(1 for m in movimientos if m.tipo == "VENTA")
    cant_pagos = sum(1 for m in movimientos if m.tipo == "PAGO")
    promedio_pago = round(total_pagos / cant_pagos, 2) if cant_pagos else 0.0

    fechas_pagos = [m.fecha for m in movimientos if m.tipo == "PAGO"]
    fechas_ventas = [m.fecha for m in movimientos if m.tipo == "VENTA"]

    return {
        "cliente_id": cliente_id,
        "saldo_actual": float(cuenta.saldo),
        "total_ventas_cc": round(total_ventas, 2),
        "total_pagos_cc": round(total_pagos, 2),
        "cantidad_ventas": cant_ventas,
        "cantidad_pagos": cant_pagos,
        "promedio_pago": promedio_pago,
        "ultimo_pago": max(fechas_pagos).isoformat() if fechas_pagos else None,
        "ultima_venta": max(fechas_ventas).isoformat() if fechas_ventas else None,
    }

