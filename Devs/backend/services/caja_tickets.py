"""Lógica de tickets POS en cola y cobro desde Caja.

Para TEU_OFF:
- el vendedor registra la venta con estado PENDIENTE y genera numero_ticket
- Caja lista tickets pendientes y ejecuta el cobro (transición a PAGADA/FIADA)
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.events import emit as emit_event
from backend.models.caja import Caja
from backend.models.pagos import PaymentTransaction
from backend.models.persona import Cliente, Persona, CuentaCorrienteCliente
from backend.models.venta import EstadoVenta, Venta
from backend.services import cuentas_corrientes as svc_cc
from backend.services import tesoreria as svc_tesoreria


def listar_tickets_pendientes(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[dict[str, Any]]:
    stmt = (
        select(Venta, Persona)
        .join(Persona, Venta.cliente_id == Persona.id, isouter=True)
        .where(Venta.estado == EstadoVenta.PENDIENTE.value)
        .order_by(Venta.creado_en.asc(), Venta.id.asc())
        .limit(limite)
        .offset(offset)
    )
    filas = sesion.execute(stmt).all()

    out: list[dict[str, Any]] = []
    for venta, persona in filas:
        out.append(
            {
                "venta_id": venta.id,
                "numero_ticket": venta.numero_ticket,
                "cliente_id": venta.cliente_id,
                "cliente_nombre": (f"{persona.apellido} {persona.nombre}").strip()
                if persona is not None
                else None,
                "cliente_documento": persona.documento if persona is not None else None,
                "total": Decimal(str(venta.total)),
                "creado_en": venta.creado_en,
                "estado": venta.estado,
            }
        )
    return out


def obtener_ticket_por_id(sesion: Session, venta_id: int) -> Optional[Venta]:
    return sesion.get(Venta, venta_id)


def _obtener_cliente_rol_por_persona_id(
    sesion: Session, *, persona_id: int
) -> Cliente:
    stmt_cliente = select(Cliente).where(Cliente.persona_id == persona_id).limit(1)
    cliente_rol = sesion.scalars(stmt_cliente).first()
    if cliente_rol is None:
        raise ValueError(
            "El cliente no tiene rol de Cliente configurado para operar a crédito"
        )
    return cliente_rol


def _saldo_actual_cuenta_corriente(
    sesion: Session, *, cliente_rol_id: int
) -> Decimal:
    cuenta = (
        sesion.query(CuentaCorrienteCliente)
        .where(CuentaCorrienteCliente.cliente_id == cliente_rol_id)
        .one_or_none()
    )
    return Decimal(str(cuenta.saldo)) if cuenta is not None else Decimal("0")


def cobro_ticket(
    sesion: Session,
    *,
    venta_id: int,
    pagos: Sequence[dict[str, Any]],
    observaciones: Optional[str] = None,
) -> Venta:
    """
    Ejecuta el cobro de un ticket pendiente.

    pagos: lista de dict con:
      - metodo_pago (str)
      - importe (Decimal)
      - medio_pago (opcional)
      - cobrador (opcional)
    """

    caja_abierta: Optional[Caja] = svc_tesoreria.obtener_caja_abierta(sesion)
    if caja_abierta is None:
        raise ValueError("No hay caja abierta")

    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError(f"Venta {venta_id} no encontrada")

    if venta.estado != EstadoVenta.PENDIENTE.value:
        raise ValueError("El ticket no está pendiente")

    if not pagos:
        raise ValueError("Debe enviar al menos un pago")

    pagos_norm: list[dict[str, Any]] = []
    for p in pagos:
        metodo = (p.get("metodo_pago") or "").strip().upper()
        if not metodo:
            raise ValueError("metodo_pago es requerido por cada pago")
        importe = Decimal(str(p.get("importe")))
        if importe <= 0:
            raise ValueError("importe debe ser mayor que cero")

        pagos_norm.append(
            {
                "metodo_pago": metodo,
                "importe": importe,
                "medio_pago": p.get("medio_pago"),
                "cobrador": p.get("cobrador"),
            }
        )

    total_pagos = sum(p["importe"] for p in pagos_norm)
    if total_pagos != Decimal(str(venta.total)):
        # Tolerancia por redondeos decimales simples
        if abs(total_pagos - Decimal(str(venta.total))) > Decimal("0.01"):
            raise ValueError("La suma de pagos no coincide con el total de la venta")

    importe_credito = sum(
        p["importe"] for p in pagos_norm if p["metodo_pago"] == "CUENTA_CORRIENTE"
    )

    # Validación de crédito y registro de deuda SOLO si hay CUENTA_CORRIENTE.
    if importe_credito > 0:
        if venta.cliente_id is None:
            raise ValueError("Ticket requiere cliente para cuenta corriente")
        cliente_rol = _obtener_cliente_rol_por_persona_id(
            sesion, persona_id=venta.cliente_id
        )

        limite = cliente_rol.limite_credito
        if limite is not None:
            saldo_actual = _saldo_actual_cuenta_corriente(
                sesion, cliente_rol_id=cliente_rol.id
            )
            nuevo_saldo = saldo_actual + importe_credito
            if nuevo_saldo > limite:
                raise ValueError("Límite de crédito excedido para el cliente")

        # Registrar la deuda (tipo VENTA) en cuenta corriente del cliente
        svc_cc.registrar_movimiento_cuenta_corriente(
            sesion,
            cliente_id=cliente_rol.id,
            tipo="VENTA",
            monto=importe_credito,
            descripcion=f"Venta #{venta.id} a crédito (TEU_OFF)",
        )

    # Crear PaymentTransaction y registrar movimientos de caja para pagos no crédito
    detalle_pagos = []
    for p in pagos_norm:
        if p["metodo_pago"] != "CUENTA_CORRIENTE":
            # Movimiento de caja: cada pago no crédito se audita por separado.
            svc_tesoreria.registrar_movimiento_caja(
                sesion,
                caja_abierta.id,
                tipo="VENTA",
                monto=p["importe"],
                referencia=f"Venta #{venta.id}",
                medio_pago=p["metodo_pago"],
            )

        pt = PaymentTransaction(
            venta_id=venta.id,
            caja_id=caja_abierta.id,
            metodo_pago=p["metodo_pago"],
            importe=p["importe"],
            medio_pago=p.get("medio_pago"),
            cobrador=p.get("cobrador"),
            observaciones=observaciones,
        )
        sesion.add(pt)
        sesion.flush()  # para tener pt.id al emitir evento

        detalle_pagos.append(
            {
                "pago_id": pt.id,
                "metodo_pago": p["metodo_pago"],
                "importe": float(pt.importe),
            }
        )

        emit_event(
            "PagoRegistrado",
            {
                "pago_id": pt.id,
                "venta_id": venta.id,
                "metodo_pago": pt.metodo_pago,
                "monto": float(pt.importe),
                "__sesion": sesion,
            },
        )

    # Actualizar estado y datos de venta
    venta.caja_id = caja_abierta.id
    venta.detalle_pagos = json.dumps(detalle_pagos, ensure_ascii=False)

    if importe_credito == Decimal(str(venta.total)):
        venta.estado = EstadoVenta.FIADA.value
        # En FIADA puede mantenerse CUENTA_CORRIENTE como método principal
        venta.metodo_pago = "CUENTA_CORRIENTE"
    else:
        venta.estado = EstadoVenta.PAGADA.value
        if len(pagos_norm) == 1:
            venta.metodo_pago = pagos_norm[0]["metodo_pago"]
        else:
            venta.metodo_pago = "PAGO_COMBINADO"

    sesion.add(venta)
    sesion.flush()
    sesion.refresh(venta)
    return venta

