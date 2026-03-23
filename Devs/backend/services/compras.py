"""Servicios del dominio Compras/Proveedores."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.compra import Compra, ItemCompra
from backend.models.persona import Persona
from backend.models.producto import Producto


def crear_compra(
    sesion: Session,
    *,
    proveedor_id: int,
    items: list[dict[str, Any]],
    fecha: datetime | None = None,
) -> Compra:
    """
    Crea una compra confirmada con sus ítems.

    Cada item debe contener:
    - producto_id
    - cantidad
    - costo_unitario
    """
    proveedor = sesion.get(Persona, proveedor_id)
    if proveedor is None:
        raise ValueError(f"Proveedor {proveedor_id} no encontrado")

    if not items:
        raise ValueError("La compra debe tener al menos un ítem")

    compra = Compra(
        proveedor_id=proveedor_id,
        fecha=fecha or datetime.now(timezone.utc),
        estado="CONFIRMADA",
    )
    sesion.add(compra)
    sesion.flush()

    total = Decimal("0")
    for item in items:
        producto_id = int(item["producto_id"])
        cantidad = Decimal(str(item["cantidad"]))
        costo_unitario = Decimal(str(item["costo_unitario"]))

        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        if costo_unitario < 0:
            raise ValueError("El costo_unitario no puede ser negativo")

        producto = sesion.get(Producto, producto_id)
        if producto is None:
            raise ValueError(f"Producto {producto_id} no encontrado")

        subtotal = cantidad * costo_unitario
        total += subtotal

        sesion.add(
            ItemCompra(
                compra_id=compra.id,
                producto_id=producto_id,
                nombre_producto=producto.nombre,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
                subtotal=subtotal,
            )
        )

    compra.total = total
    sesion.add(compra)
    sesion.flush()
    sesion.refresh(compra)
    return compra


def listar_compras(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Compra]:
    """Lista compras ordenadas por fecha descendente."""
    stmt = (
        select(Compra)
        .order_by(Compra.fecha.desc(), Compra.id.desc())
        .limit(limite)
        .offset(offset)
    )
    return sesion.scalars(stmt).all()

