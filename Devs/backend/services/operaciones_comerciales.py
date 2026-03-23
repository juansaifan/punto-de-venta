"""Servicios de Operaciones Comerciales (Módulo 2 - POS).

Implementación mínima end-to-end de:
- Devolución: reingreso de stock + reintegro (caja o cuenta corriente)
- Nota de crédito: reintegro (caja o cuenta corriente)
- Anulación de venta pendiente: restaura stock y marca venta CANCELADA
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from backend.events import emit as emit_event
from backend.models.caja import TipoMovimientoCaja
from backend.models.inventario import TipoMovimiento
from backend.models.operaciones_comerciales import (
    EstadoOperacionComercial,
    OperacionComercial,
    OperacionComercialDetalle,
    TipoOperacionComercial,
)
from backend.models.persona import Cliente, CuentaCorrienteCliente
from backend.models.producto import Producto
from backend.models.venta import EstadoVenta, ItemVenta, Venta
from backend.services import cuentas_corrientes as svc_cc
from backend.services import inventario as svc_inventario
from backend.services import tesoreria as svc_tesoreria


def _obtener_venta_con_items(sesion: Session, venta_id: int) -> Venta:
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    # Acceder a la relación fuerza carga lazy dentro de la sesión.
    _ = venta.items
    return venta


def _validar_reintegro_tipo(reintegro_tipo: str) -> str:
    tipo = (reintegro_tipo or "").strip().upper()
    if tipo not in {"EFECTIVO", "MEDIO_PAGO_ORIGINAL", "CUENTA_CORRIENTE"}:
        raise ValueError(
            "reintegro_tipo inválido; válidos: EFECTIVO, MEDIO_PAGO_ORIGINAL, CUENTA_CORRIENTE"
        )
    return tipo


def _obtener_cliente_rol(sesion: Session, *, persona_id: int) -> Cliente:
    stmt_cliente = (
        sesion.query(Cliente).filter(Cliente.persona_id == persona_id).limit(1)
    )
    cliente = stmt_cliente.one_or_none()
    if cliente is None:
        raise ValueError(
            "El cliente no tiene rol de Cliente configurado para operar"
        )
    return cliente


def _reingresar_items(
    sesion: Session,
    *,
    detalles: list[OperacionComercialDetalle],
) -> None:
    for d in detalles:
        svc_inventario.ingresar_stock(
            sesion,
            producto_id=d.producto_id,
            cantidad=d.cantidad,
            tipo=TipoMovimiento.DEVOLUCION.value,
            referencia=f"Devolucion op#{d.operacion_id}",
        )


def registrar_devolucion(
    sesion: Session,
    *,
    venta_id: int,
    reintegro_tipo: str,
    reintegro_metodo_pago: Optional[str],
    motivo: Optional[str],
    items: list[dict[str, Any]],
) -> OperacionComercial:
    venta = _obtener_venta_con_items(sesion, venta_id)

    reintegro_tipo_norm = _validar_reintegro_tipo(reintegro_tipo)

    # Devoluciones solo sobre ventas pagadas (PAGADA/FIADA), no sobre pendientes.
    if venta.estado not in {EstadoVenta.PAGADA.value, EstadoVenta.FIADA.value}:
        raise ValueError("La devolución solo se permite sobre ventas pagadas")

    if not items:
        raise ValueError("Debe especificar al menos un item")

    # Construir detalles (validar item_venta y cantidad).
    detalles: list[OperacionComercialDetalle] = []
    total = Decimal("0")

    items_por_id = {it.id: it for it in venta.items}
    for it_payload in items:
        item_venta_id = int(it_payload["item_venta_id"])
        cantidad = Decimal(str(it_payload["cantidad"]))
        if cantidad <= 0:
            raise ValueError("cantidad debe ser > 0")
        item_original = items_por_id.get(item_venta_id)
        if item_original is None:
            raise ValueError(f"item_venta_id {item_venta_id} no pertenece a la venta")
        if cantidad > Decimal(str(item_original.cantidad)):
            raise ValueError(
                f"Cantidad excede la disponible del item (max={item_original.cantidad})"
            )

        subtotal = cantidad * Decimal(str(item_original.precio_unitario))
        total += subtotal

        detalle = OperacionComercialDetalle(
            item_venta_id=item_original.id,
            producto_id=item_original.producto_id,
            nombre_producto=item_original.nombre_producto,
            cantidad=cantidad,
            precio_unitario=Decimal(str(item_original.precio_unitario)),
            subtotal=subtotal,
        )
        detalles.append(detalle)

    if total <= 0:
        raise ValueError("El importe de devolución debe ser > 0")

    # Crear operación (flush para tener id y poder referenciar).
    cliente_id = venta.cliente_id
    operacion = OperacionComercial(
        venta_id=venta.id,
        cliente_id=cliente_id,
        tipo=TipoOperacionComercial.DEVOLUCION,
        estado=EstadoOperacionComercial.EJECUTADA,
        motivo=motivo,
        importe_total=total,
        detalle_json=json.dumps(
            {"items": items, "reintegro_tipo": reintegro_tipo_norm},
            ensure_ascii=False,
            default=str,
        ),
    )
    sesion.add(operacion)
    sesion.flush()
    for d in detalles:
        d.operacion_id = operacion.id
        sesion.add(d)

    # Impacto inventario.
    _reingresar_items(sesion, detalles=detalles)

    # Impacto caja / cuenta corriente.
    if reintegro_tipo_norm == "CUENTA_CORRIENTE":
        if venta.cliente_id is None:
            raise ValueError("La devolución a cuenta corriente requiere cliente en la venta")
        cliente_rol = _obtener_cliente_rol(sesion, persona_id=venta.cliente_id)
        svc_cc.registrar_movimiento_cuenta_corriente(
            sesion,
            cliente_id=cliente_rol.id,
            tipo="PAGO",
            monto=total,
            descripcion=f"Devolucion op#{operacion.id} (venta #{venta.id})",
        )
    else:
        caja_abierta = svc_tesoreria.obtener_caja_abierta(sesion)
        if caja_abierta is None:
            raise ValueError("No hay caja abierta")

        if reintegro_tipo_norm == "MEDIO_PAGO_ORIGINAL":
            medio_pago = venta.metodo_pago
        else:
            medio_pago = (reintegro_metodo_pago or "EFECTIVO").strip().upper()

        svc_tesoreria.registrar_movimiento_caja(
            sesion,
            caja_abierta.id,
            tipo=TipoMovimientoCaja.DEVOLUCION.value,
            monto=total,
            referencia=f"Devolucion op#{operacion.id}",
            medio_pago=medio_pago,
        )

    sesion.flush()
    sesion.refresh(operacion)

    emit_event(
        "OperacionComercialRegistrada",
        {
            "operacion_id": operacion.id,
            "venta_id": operacion.venta_id,
            "cliente_id": operacion.cliente_id,
            "tipo": operacion.tipo.value,
            "estado": operacion.estado.value,
            "motivo": operacion.motivo,
            "importe_total": float(operacion.importe_total),
            "__sesion": sesion,
        },
    )
    return operacion


def registrar_nota_credito(
    sesion: Session,
    *,
    venta_id: int,
    reintegro_tipo: str,
    reintegro_metodo_pago: Optional[str],
    importe: Decimal,
    motivo: Optional[str],
) -> OperacionComercial:
    venta = _obtener_venta_con_items(sesion, venta_id)

    reintegro_tipo_norm = _validar_reintegro_tipo(reintegro_tipo)
    if importe <= 0:
        raise ValueError("importe debe ser > 0")

    operacion = OperacionComercial(
        venta_id=venta.id,
        cliente_id=venta.cliente_id,
        tipo=TipoOperacionComercial.NOTA_CREDITO,
        estado=EstadoOperacionComercial.EJECUTADA,
        motivo=motivo,
        importe_total=Decimal(str(importe)),
        detalle_json=json.dumps(
            {"reintegro_tipo": reintegro_tipo_norm, "importe": str(importe)},
            ensure_ascii=False,
        ),
    )
    sesion.add(operacion)
    sesion.flush()

    if reintegro_tipo_norm == "CUENTA_CORRIENTE":
        if venta.cliente_id is None:
            raise ValueError("La nota de crédito a cuenta corriente requiere cliente en la venta")
        cliente_rol = _obtener_cliente_rol(sesion, persona_id=venta.cliente_id)
        svc_cc.registrar_movimiento_cuenta_corriente(
            sesion,
            cliente_id=cliente_rol.id,
            tipo="PAGO",
            monto=importe,
            descripcion=f"Nota de crédito op#{operacion.id} (venta #{venta.id})",
        )
    else:
        caja_abierta = svc_tesoreria.obtener_caja_abierta(sesion)
        if caja_abierta is None:
            raise ValueError("No hay caja abierta")
        medio_pago = (
            venta.metodo_pago
            if reintegro_tipo_norm == "MEDIO_PAGO_ORIGINAL"
            else (reintegro_metodo_pago or "EFECTIVO").strip().upper()
        )
        svc_tesoreria.registrar_movimiento_caja(
            sesion,
            caja_abierta.id,
            tipo=TipoMovimientoCaja.DEVOLUCION.value,
            monto=importe,
            referencia=f"Nota crédito op#{operacion.id}",
            medio_pago=medio_pago,
        )

    sesion.flush()
    sesion.refresh(operacion)

    emit_event(
        "OperacionComercialRegistrada",
        {
            "operacion_id": operacion.id,
            "venta_id": operacion.venta_id,
            "cliente_id": operacion.cliente_id,
            "tipo": operacion.tipo.value,
            "estado": operacion.estado.value,
            "motivo": operacion.motivo,
            "importe_total": float(operacion.importe_total),
            "__sesion": sesion,
        },
    )
    return operacion


def anular_venta_pendiente(
    sesion: Session,
    *,
    venta_id: int,
    motivo: Optional[str],
) -> OperacionComercial:
    venta = _obtener_venta_con_items(sesion, venta_id)

    if venta.estado not in {
        EstadoVenta.PENDIENTE.value,
        EstadoVenta.PAGADA.value,
        EstadoVenta.FIADA.value,
    }:
        raise ValueError("No se puede anular el estado de la venta")

    # Restaurar stock: TEU_OFF descuenta stock al crear ticket.
    detalles: list[OperacionComercialDetalle] = []
    total_items = Decimal("0")
    for it in venta.items:
        cantidad = Decimal(str(it.cantidad))
        subtotal = Decimal(str(it.precio_unitario)) * cantidad
        total_items += subtotal
        detalles.append(
            OperacionComercialDetalle(
                item_venta_id=it.id,
                producto_id=it.producto_id,
                nombre_producto=it.nombre_producto,
                cantidad=cantidad,
                precio_unitario=Decimal(str(it.precio_unitario)),
                subtotal=subtotal,
            )
        )

    operacion = OperacionComercial(
        venta_id=venta.id,
        cliente_id=venta.cliente_id,
        tipo=TipoOperacionComercial.ANULACION,
        estado=EstadoOperacionComercial.EJECUTADA,
        motivo=motivo,
        importe_total=Decimal(str(venta.total)),
        detalle_json=json.dumps(
            {"venta_estado": venta.estado, "total_items": str(total_items)},
            ensure_ascii=False,
            default=str,
        ),
    )
    sesion.add(operacion)
    sesion.flush()

    for d in detalles:
        d.operacion_id = operacion.id
        sesion.add(d)

    _reingresar_items(sesion, detalles=detalles)

    # Revertir impactos monetarios solo para ventas pagadas/fiadas.
    if venta.estado == EstadoVenta.PAGADA.value:
        if venta.metodo_pago == "CUENTA_CORRIENTE":
            if venta.cliente_id is not None:
                cliente_rol = _obtener_cliente_rol(sesion, persona_id=venta.cliente_id)
                svc_cc.registrar_movimiento_cuenta_corriente(
                    sesion,
                    cliente_id=cliente_rol.id,
                    tipo="PAGO",
                    monto=Decimal(str(venta.total)),
                    descripcion=f"Anulación venta #{venta.id}",
                )

            # TEU_ON con cuenta corriente puede haber generado movimiento de caja
            # (si había caja abierta al registrar la venta). Revertimos usando
            # venta.caja_id y no dependemos de una caja abierta "actual".
            if venta.caja_id is not None:
                try:
                    svc_tesoreria.registrar_movimiento_caja(
                        sesion,
                        venta.caja_id,
                        tipo=TipoMovimientoCaja.DEVOLUCION.value,
                        monto=Decimal(str(venta.total)),
                        referencia=f"Anulación venta #{venta.id}",
                        medio_pago=venta.metodo_pago,
                    )
                except ValueError:
                    # Si la caja no permite movimientos (p.ej. cerrada) o no está abierta,
                    # la anulación igualmente debe completarse por consistencia operativa.
                    pass
        else:
            # Revertir movimiento de caja solo si la venta lo registró (venta.caja_id).
            if venta.caja_id is not None:
                try:
                    svc_tesoreria.registrar_movimiento_caja(
                        sesion,
                        venta.caja_id,
                        tipo=TipoMovimientoCaja.DEVOLUCION.value,
                        monto=Decimal(str(venta.total)),
                        referencia=f"Anulación venta #{venta.id}",
                        medio_pago=venta.metodo_pago,
                    )
                except ValueError:
                    # Si la caja no admite movimientos (p.ej. cerrada), se omite el movimiento.
                    pass

    if venta.estado == EstadoVenta.FIADA.value:
        # FIADA implica pago a cuenta corriente; no se reingresa caja.
        if venta.cliente_id is None:
            raise ValueError("Venta FIADA requiere cliente")
        cliente_rol = _obtener_cliente_rol(sesion, persona_id=venta.cliente_id)
        svc_cc.registrar_movimiento_cuenta_corriente(
            sesion,
            cliente_id=cliente_rol.id,
            tipo="PAGO",
            monto=Decimal(str(venta.total)),
            descripcion=f"Anulación venta FIADA #{venta.id}",
        )

    venta.estado = EstadoVenta.CANCELADA.value
    sesion.add(venta)

    sesion.flush()
    sesion.refresh(operacion)

    emit_event(
        "OperacionComercialRegistrada",
        {
            "operacion_id": operacion.id,
            "venta_id": operacion.venta_id,
            "cliente_id": operacion.cliente_id,
            "tipo": operacion.tipo.value,
            "estado": operacion.estado.value,
            "motivo": operacion.motivo,
            "importe_total": float(operacion.importe_total),
            "__sesion": sesion,
        },
    )
    return operacion


def registrar_cambio_producto(
    sesion: Session,
    *,
    venta_id: int,
    items_devueltos: list[dict[str, Any]],
    items_nuevos: list[dict[str, Any]],
    reintegro_tipo_diferencia: str,
    reintegro_metodo_pago: Optional[str],
    motivo: Optional[str],
) -> OperacionComercial:
    """
    Cambio de producto (versión mínima):
    - permite reemplazar items completos indicados por item_venta_id
    - soporta cantidades parciales por item_venta_id
    - requiere que la venta no tenga descuento ni impuesto
    """
    venta = _obtener_venta_con_items(sesion, venta_id)
    reintegro_tipo_norm = _validar_reintegro_tipo(reintegro_tipo_diferencia)

    if venta.descuento != 0 or venta.impuesto != 0:
        raise ValueError(
            "Cambio de producto soporta solo ventas sin descuento/impuesto en esta versión"
        )

    if not items_devueltos or not items_nuevos:
        raise ValueError("Debe indicar items_devueltos e items_nuevos")

    items_por_id = {it.id: it for it in venta.items}

    # Validar items devueltos (reemplazo total de cada item).
    detalles_devueltos: list[OperacionComercialDetalle] = []
    importe_devuelto = Decimal("0")
    for it_payload in items_devueltos:
        item_venta_id = int(it_payload["item_venta_id"])
        cantidad = Decimal(str(it_payload["cantidad"]))
        if cantidad <= 0:
            raise ValueError("cantidad debe ser > 0")

        item_original = items_por_id.get(item_venta_id)
        if item_original is None:
            raise ValueError(
                f"item_venta_id {item_venta_id} no pertenece a la venta"
            )
        if cantidad > Decimal(str(item_original.cantidad)):
            raise ValueError(
                f"Cantidad devuelta excede la disponible del item (max={item_original.cantidad})"
            )

        subtotal = cantidad * Decimal(str(item_original.precio_unitario))
        importe_devuelto += subtotal
        detalles_devueltos.append(
            OperacionComercialDetalle(
                item_venta_id=item_original.id,
                producto_id=item_original.producto_id,
                nombre_producto=item_original.nombre_producto,
                cantidad=cantidad,
                precio_unitario=Decimal(str(item_original.precio_unitario)),
                subtotal=subtotal,
            )
        )

    # Validar items nuevos.
    detalles_nuevos: list[OperacionComercialDetalle] = []
    importe_nuevo = Decimal("0")
    for payload in items_nuevos:
        producto_id = int(payload["producto_id"])
        cantidad = Decimal(str(payload["cantidad"]))
        if cantidad <= 0:
            raise ValueError("cantidad debe ser > 0")

        producto = sesion.get(Producto, producto_id)
        if producto is None:
            raise ValueError(f"Producto {producto_id} no encontrado")

        precio_unitario_payload = payload.get("precio_unitario")
        precio_unitario = (
            Decimal(str(precio_unitario_payload))
            if precio_unitario_payload is not None
            else Decimal(str(producto.precio_venta))
        )
        subtotal = cantidad * precio_unitario
        importe_nuevo += subtotal
        detalles_nuevos.append(
            OperacionComercialDetalle(
                item_venta_id=None,
                producto_id=producto.id,
                nombre_producto=producto.nombre,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=subtotal,
            )
        )

    diferencia = importe_nuevo - importe_devuelto

    # Impacto inventario: reingresar devueltos + descontar nuevos.
    for d in detalles_devueltos:
        svc_inventario.ingresar_stock(
            sesion,
            producto_id=d.producto_id,
            cantidad=d.cantidad,
            tipo=TipoMovimiento.DEVOLUCION.value,
            referencia=f"Cambio producto op (venta #{venta.id})",
        )
    for d in detalles_nuevos:
        svc_inventario.descontar_stock_por_venta(
            sesion,
            producto_id=d.producto_id,
            cantidad=d.cantidad,
            referencia=f"Cambio producto op (venta #{venta.id})",
        )

    # Actualizar items de venta:
    # - Reducir cantidad del item original por la cantidad devuelta parcial
    # - Agregar items nuevos como líneas adicionales
    for d in detalles_devueltos:
        item_original = next(
            (it for it in venta.items if it.id == d.item_venta_id), None
        )
        if item_original is not None:
            item_original.cantidad = Decimal(str(item_original.cantidad)) - Decimal(
                str(d.cantidad)
            )
            item_original.subtotal = (
                item_original.cantidad * Decimal(str(item_original.precio_unitario))
            )
            if item_original.cantidad <= 0:
                venta.items.remove(item_original)
            sesion.flush()

    for d in detalles_nuevos:
        venta.items.append(
            ItemVenta(
                venta_id=venta.id,
                producto_id=d.producto_id,
                nombre_producto=d.nombre_producto,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
                subtotal=d.subtotal,
            )
        )

    venta.recalcular_totales()
    sesion.add(venta)

    operacion = OperacionComercial(
        venta_id=venta.id,
        cliente_id=venta.cliente_id,
        tipo=TipoOperacionComercial.CAMBIO_PRODUCTO,
        estado=EstadoOperacionComercial.EJECUTADA,
        motivo=motivo,
        importe_total=abs(diferencia),
        detalle_json=json.dumps(
            {
                "items_devueltos": items_devueltos,
                "items_nuevos": items_nuevos,
                "diferencia": str(diferencia),
                "reintegro_tipo_diferencia": reintegro_tipo_norm,
            },
            ensure_ascii=False,
            default=str,
        ),
    )
    sesion.add(operacion)
    sesion.flush()

    for d in detalles_devueltos + detalles_nuevos:
        d.operacion_id = operacion.id
        sesion.add(d)

    # Impacto caja / cuenta corriente por la diferencia.
    if diferencia != 0:
        if reintegro_tipo_norm == "CUENTA_CORRIENTE":
            if venta.cliente_id is None:
                raise ValueError(
                    "Cambio de producto a CUENTA_CORRIENTE requiere cliente"
                )
            cliente_rol = _obtener_cliente_rol(
                sesion, persona_id=venta.cliente_id
            )
            # Cuenta corriente modela deuda/saldo:
            # - diferencia > 0: el cliente paga la diferencia (VENTA)
            # - diferencia < 0: el comercio devuelve (PAGO)
            if diferencia > 0:
                svc_cc.registrar_movimiento_cuenta_corriente(
                    sesion,
                    cliente_id=cliente_rol.id,
                    tipo="VENTA",
                    monto=Decimal(str(diferencia)),
                    descripcion=f"Cambio de producto op#{operacion.id}",
                )
            else:
                svc_cc.registrar_movimiento_cuenta_corriente(
                    sesion,
                    cliente_id=cliente_rol.id,
                    tipo="PAGO",
                    monto=Decimal(str(abs(diferencia))),
                    descripcion=f"Cambio de producto op#{operacion.id}",
                )
        else:
            caja_abierta = svc_tesoreria.obtener_caja_abierta(sesion)
            if caja_abierta is None:
                raise ValueError("No hay caja abierta")

            if reintegro_tipo_norm == "MEDIO_PAGO_ORIGINAL":
                medio_pago = venta.metodo_pago
            else:
                medio_pago = (reintegro_metodo_pago or "EFECTIVO").strip().upper()

            tipo_mov = (
                TipoMovimientoCaja.VENTA.value
                if diferencia > 0
                else TipoMovimientoCaja.DEVOLUCION.value
            )

            svc_tesoreria.registrar_movimiento_caja(
                sesion,
                caja_abierta.id,
                tipo=tipo_mov,
                monto=abs(diferencia),
                referencia=f"Cambio producto op#{operacion.id}",
                medio_pago=medio_pago,
            )

    sesion.flush()
    sesion.refresh(operacion)

    emit_event(
        "OperacionComercialRegistrada",
        {
            "operacion_id": operacion.id,
            "venta_id": operacion.venta_id,
            "cliente_id": operacion.cliente_id,
            "tipo": operacion.tipo.value,
            "estado": operacion.estado.value,
            "motivo": operacion.motivo,
            "importe_total": float(operacion.importe_total),
            "__sesion": sesion,
        },
    )
    return operacion


def registrar_nota_debito(
    sesion: Session,
    *,
    venta_id: int,
    reintegro_tipo: str,
    reintegro_metodo_pago: Optional[str],
    importe: Decimal,
    motivo: Optional[str],
) -> OperacionComercial:
    venta = _obtener_venta_con_items(sesion, venta_id)
    reintegro_tipo_norm = _validar_reintegro_tipo(reintegro_tipo)

    if importe <= 0:
        raise ValueError("importe debe ser > 0")

    operacion = OperacionComercial(
        venta_id=venta.id,
        cliente_id=venta.cliente_id,
        tipo=TipoOperacionComercial.NOTA_DEBITO,
        estado=EstadoOperacionComercial.EJECUTADA,
        motivo=motivo,
        importe_total=Decimal(str(importe)),
        detalle_json=json.dumps(
            {
                "reintegro_tipo": reintegro_tipo_norm,
                "importe": str(importe),
            },
            ensure_ascii=False,
            default=str,
        ),
    )
    sesion.add(operacion)
    sesion.flush()

    if reintegro_tipo_norm == "CUENTA_CORRIENTE":
        if venta.cliente_id is None:
            raise ValueError(
                "Nota de débito a CUENTA_CORRIENTE requiere cliente"
            )
        cliente_rol = _obtener_cliente_rol(
            sesion, persona_id=venta.cliente_id
        )
        # Nota de débito incrementa deuda (saldo): tipo="VENTA".
        svc_cc.registrar_movimiento_cuenta_corriente(
            sesion,
            cliente_id=cliente_rol.id,
            tipo="VENTA",
            monto=Decimal(str(importe)),
            descripcion=f"Nota de débito op#{operacion.id}",
        )
    else:
        caja_abierta = svc_tesoreria.obtener_caja_abierta(sesion)
        if caja_abierta is None:
            raise ValueError("No hay caja abierta")

        if reintegro_tipo_norm == "MEDIO_PAGO_ORIGINAL":
            medio_pago = venta.metodo_pago
        else:
            medio_pago = (reintegro_metodo_pago or "EFECTIVO").strip().upper()

        svc_tesoreria.registrar_movimiento_caja(
            sesion,
            caja_abierta.id,
            tipo=TipoMovimientoCaja.INGRESO.value,
            monto=Decimal(str(importe)),
            referencia=f"Nota débito op#{operacion.id}",
            medio_pago=medio_pago,
        )

    sesion.flush()
    sesion.refresh(operacion)

    emit_event(
        "OperacionComercialRegistrada",
        {
            "operacion_id": operacion.id,
            "venta_id": operacion.venta_id,
            "cliente_id": operacion.cliente_id,
            "tipo": operacion.tipo.value,
            "estado": operacion.estado.value,
            "motivo": operacion.motivo,
            "importe_total": float(operacion.importe_total),
            "__sesion": sesion,
        },
    )
    return operacion


def registrar_credito_cuenta_corriente(
    sesion: Session,
    *,
    venta_id: int,
    importe: Decimal,
    motivo: Optional[str],
) -> OperacionComercial:
    venta = _obtener_venta_con_items(sesion, venta_id)

    if importe <= 0:
        raise ValueError("importe debe ser > 0")

    if venta.cliente_id is None:
        raise ValueError("Crédito en cuenta requiere cliente en la venta")

    cliente_rol = _obtener_cliente_rol(sesion, persona_id=venta.cliente_id)

    operacion = OperacionComercial(
        venta_id=venta.id,
        cliente_id=venta.cliente_id,
        tipo=TipoOperacionComercial.CREDITO_CUENTA_CORRIENTE,
        estado=EstadoOperacionComercial.EJECUTADA,
        motivo=motivo,
        importe_total=Decimal(str(importe)),
        detalle_json=json.dumps(
            {"importe": str(importe), "origen": "credito_cuenta_corriente"},
            ensure_ascii=False,
            default=str,
        ),
    )
    sesion.add(operacion)
    sesion.flush()

    # Crédito reduce deuda: tipo="PAGO".
    svc_cc.registrar_movimiento_cuenta_corriente(
        sesion,
        cliente_id=cliente_rol.id,
        tipo="PAGO",
        monto=Decimal(str(importe)),
        descripcion=f"Crédito en cuenta corriente op#{operacion.id}",
    )

    sesion.flush()
    sesion.refresh(operacion)

    emit_event(
        "OperacionComercialRegistrada",
        {
            "operacion_id": operacion.id,
            "venta_id": operacion.venta_id,
            "cliente_id": operacion.cliente_id,
            "tipo": operacion.tipo.value,
            "estado": operacion.estado.value,
            "motivo": operacion.motivo,
            "importe_total": float(operacion.importe_total),
            "__sesion": sesion,
        },
    )
    return operacion


def listar_operaciones_por_venta(
    sesion: Session, *, venta_id: int, limite: int = 100, offset: int = 0
) -> list[OperacionComercial]:
    stmt = (
        sesion.query(OperacionComercial)
        .filter(OperacionComercial.venta_id == venta_id)
        .order_by(OperacionComercial.creado_en.desc(), OperacionComercial.id.desc())
        .limit(limite)
        .offset(offset)
    )
    return list(stmt.all())

