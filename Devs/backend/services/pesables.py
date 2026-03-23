"""Servicio del submódulo Pesables (Módulo 2 – Punto de Venta).

Responsabilidades:
- Cálculo bidireccional peso ↔ precio
- Generación de código de barras EAN-13  (formato: 20 + PLU(5) + PRECIO_CENTAVOS(5) + CHECKSUM)
- Preparación de ítems pesables (uno o batch)
- Gestión de estados: pending → printed → used
- Generación de datos para etiquetas (batch)
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.pesables import EstadoPesableItem, PesableItem
from backend.models.producto import Producto


# ---------------------------------------------------------------------------
# Cálculo bidireccional
# ---------------------------------------------------------------------------

def calcular_precio_por_peso(peso: Decimal, precio_unitario: Decimal) -> Decimal:
    """Retorna precio_total = peso × precio_unitario, redondeado a 2 decimales."""
    return (Decimal(str(peso)) * Decimal(str(precio_unitario))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def calcular_peso_por_precio(precio: Decimal, precio_unitario: Decimal) -> Decimal:
    """Retorna peso = precio / precio_unitario, redondeado a 3 decimales."""
    precio_u = Decimal(str(precio_unitario))
    if precio_u == 0:
        raise ValueError("precio_unitario no puede ser 0")
    return (Decimal(str(precio)) / precio_u).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )


# ---------------------------------------------------------------------------
# Generación EAN-13
# ---------------------------------------------------------------------------

def _ean13_checksum(doce_digitos: str) -> int:
    """Calcula el dígito verificador EAN-13 a partir de los primeros 12 dígitos."""
    total = 0
    for i, ch in enumerate(doce_digitos):
        factor = 1 if i % 2 == 0 else 3
        total += int(ch) * factor
    return (10 - (total % 10)) % 10


def generar_ean13(plu: int, precio_total: Decimal) -> str:
    """Genera el código EAN-13 para un pesable.

    Formato: [20][PLU(5 dígitos)][PRECIO_CENTAVOS(5 dígitos)][CHECKSUM]
    El precio se expresa en centavos enteros (máx. 99999 centavos = $999.99).
    Si el precio supera el rango, se trunca a los 5 dígitos menos significativos.
    """
    precio_centavos = int((Decimal(str(precio_total)) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    plu_str = str(int(plu) % 100000).zfill(5)
    precio_str = str(precio_centavos % 100000).zfill(5)
    doce = f"20{plu_str}{precio_str}"
    checksum = _ean13_checksum(doce)
    return f"{doce}{checksum}"


# ---------------------------------------------------------------------------
# Obtener producto pesable con validación
# ---------------------------------------------------------------------------

def _obtener_producto_pesable(sesion: Session, producto_id: int) -> Producto:
    producto = sesion.get(Producto, producto_id)
    if producto is None:
        raise ValueError(f"Producto {producto_id} no encontrado")
    if not producto.pesable:
        raise ValueError(
            f"Producto {producto_id} no es pesable. "
            "Actualiza el producto con pesable=true y plu para habilitarlo."
        )
    if producto.plu is None:
        raise ValueError(
            f"Producto {producto_id} no tiene PLU asignado. "
            "Asigna un PLU (5 dígitos) antes de preparar ítems pesables."
        )
    return producto


# ---------------------------------------------------------------------------
# Operaciones CRUD de PesableItem
# ---------------------------------------------------------------------------

def preparar_item(
    sesion: Session,
    *,
    producto_id: int,
    peso: Optional[Decimal] = None,
    precio: Optional[Decimal] = None,
) -> PesableItem:
    """Prepara un ítem pesable.

    Se debe proporcionar exactamente uno de: peso o precio.
    El valor faltante se calcula automáticamente.
    """
    if peso is None and precio is None:
        raise ValueError("Debe proporcionar 'peso' o 'precio'")
    if peso is not None and precio is not None:
        raise ValueError("Proporcione solo 'peso' o solo 'precio', no ambos")

    producto = _obtener_producto_pesable(sesion, producto_id)
    precio_unitario = Decimal(str(producto.precio_venta))

    if peso is not None:
        peso_dec = Decimal(str(peso))
        if peso_dec <= 0:
            raise ValueError("El peso debe ser mayor que 0")
        precio_total = calcular_precio_por_peso(peso_dec, precio_unitario)
        peso_final = peso_dec
    else:
        precio_dec = Decimal(str(precio))
        if precio_dec <= 0:
            raise ValueError("El precio debe ser mayor que 0")
        peso_final = calcular_peso_por_precio(precio_dec, precio_unitario)
        precio_total = calcular_precio_por_peso(peso_final, precio_unitario)

    barcode = generar_ean13(producto.plu, precio_total)  # type: ignore[arg-type]

    item = PesableItem(
        producto_id=producto_id,
        nombre_producto=producto.nombre,
        plu=producto.plu,
        peso=peso_final,
        precio_unitario=precio_unitario,
        precio_total=precio_total,
        barcode=barcode,
        estado=EstadoPesableItem.PENDING.value,
    )
    sesion.add(item)
    sesion.flush()
    sesion.refresh(item)
    return item


def preparar_items_batch(
    sesion: Session,
    items: Sequence[dict],
) -> list[PesableItem]:
    """Prepara múltiples ítems pesables en una sola operación."""
    resultado: list[PesableItem] = []
    for it in items:
        resultado.append(
            preparar_item(
                sesion,
                producto_id=int(it["producto_id"]),
                peso=Decimal(str(it["peso"])) if it.get("peso") is not None else None,
                precio=Decimal(str(it["precio"])) if it.get("precio") is not None else None,
            )
        )
    return resultado


def marcar_item_impreso(sesion: Session, item_id: int) -> PesableItem:
    """Cambia estado del ítem de pending → printed."""
    item = sesion.get(PesableItem, item_id)
    if item is None:
        raise ValueError(f"PesableItem {item_id} no encontrado")
    if item.estado == EstadoPesableItem.USED.value:
        raise ValueError("No se puede marcar como impreso un ítem ya usado")
    item.estado = EstadoPesableItem.PRINTED.value
    sesion.add(item)
    sesion.flush()
    sesion.refresh(item)
    return item


def marcar_item_usado(sesion: Session, item_id: int) -> PesableItem:
    """Cambia estado del ítem a used (vendido/escaneado)."""
    item = sesion.get(PesableItem, item_id)
    if item is None:
        raise ValueError(f"PesableItem {item_id} no encontrado")
    if item.estado == EstadoPesableItem.USED.value:
        raise ValueError("El ítem ya fue marcado como usado")
    item.estado = EstadoPesableItem.USED.value
    sesion.add(item)
    sesion.flush()
    sesion.refresh(item)
    return item


def listar_items(
    sesion: Session,
    *,
    estado: Optional[str] = None,
    producto_id: Optional[int] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[PesableItem]:
    """Lista ítems pesables con filtros opcionales por estado y/o producto."""
    stmt = select(PesableItem)
    if estado is not None:
        stmt = stmt.where(PesableItem.estado == estado.strip().lower())
    if producto_id is not None:
        stmt = stmt.where(PesableItem.producto_id == producto_id)
    stmt = stmt.order_by(PesableItem.creado_en.desc(), PesableItem.id.desc()).limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def obtener_item(sesion: Session, item_id: int) -> Optional[PesableItem]:
    return sesion.get(PesableItem, item_id)


def eliminar_item_pendiente(sesion: Session, item_id: int) -> None:
    """Elimina un PesableItem en estado 'pending'.

    Solo se pueden eliminar ítems no impresos. Una vez impresa la etiqueta
    (estado printed) o ya vendida (used), el ítem no puede eliminarse para
    mantener trazabilidad.
    """
    item = sesion.get(PesableItem, item_id)
    if item is None:
        raise ValueError(f"PesableItem {item_id} no encontrado")
    if item.estado != EstadoPesableItem.PENDING.value:
        raise ValueError(
            f"Solo se pueden eliminar ítems en estado 'pending'. "
            f"Estado actual: '{item.estado}'"
        )
    sesion.delete(item)
    sesion.flush()


def listar_productos_pesables(
    sesion: Session,
    *,
    activo_only: bool = True,
    limite: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Lista todos los productos habilitados como pesables (con PLU asignado).

    Necesario para el flujo §3 del submódulo: el operador selecciona
    el producto pesable antes de ingresar peso/precio.
    Devuelve: id, sku, nombre, precio_venta, plu, activo.
    """
    stmt = (
        select(Producto)
        .where(Producto.pesable.is_(True))
        .where(Producto.plu.isnot(None))
    )
    if activo_only:
        stmt = stmt.where(Producto.activo.is_(True))
    stmt = stmt.order_by(Producto.nombre.asc()).limit(limite).offset(offset)
    productos = sesion.scalars(stmt).all()
    return [
        {
            "id": p.id,
            "sku": p.sku,
            "nombre": p.nombre,
            "precio_venta": float(p.precio_venta),
            "plu": p.plu,
            "activo": p.activo,
        }
        for p in productos
    ]


def generar_datos_etiquetas(
    sesion: Session,
    item_ids: list[int],
) -> list[dict]:
    """Genera la data para imprimir etiquetas de los ítems dados.

    Retorna lista de dicts con los campos necesarios para la etiqueta:
    nombre, peso, precio, barcode, plu, precio_unitario.
    También cambia el estado de pending → printed automáticamente.
    """
    etiquetas = []
    for item_id in item_ids:
        item = sesion.get(PesableItem, item_id)
        if item is None:
            raise ValueError(f"PesableItem {item_id} no encontrado")
        if item.estado == EstadoPesableItem.PENDING.value:
            item.estado = EstadoPesableItem.PRINTED.value
            sesion.add(item)
        etiquetas.append({
            "item_id": item.id,
            "producto_id": item.producto_id,
            "nombre_producto": item.nombre_producto,
            "plu": item.plu,
            "peso": float(item.peso),
            "precio_unitario": float(item.precio_unitario),
            "precio_total": float(item.precio_total),
            "barcode": item.barcode,
            "estado": item.estado,
        })
    sesion.flush()
    return etiquetas
