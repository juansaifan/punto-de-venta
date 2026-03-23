# Servicios del dominio Ventas (Punto de Venta)
from datetime import date
from decimal import Decimal
from typing import Any, List, Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models.persona import Persona, Cliente, CuentaCorrienteCliente
from backend.models.producto import Producto
from backend.models.venta import Venta, ItemVenta, EstadoVenta
from backend.services import cuentas_corrientes as svc_cuentas_corrientes
from backend.services import auditoria_eventos as svc_auditoria_eventos


def registrar_venta(
    sesion: Session,
    *,
    items: List[dict],
    descuento: Decimal | float = 0,
    metodo_pago: Optional[str] = None,
    cliente_id: int | None = None,
    modo_venta: str = "TEU_ON",
) -> Venta:
    """
    Registra una venta con ítems. Cada ítem debe tener producto_id, cantidad
    y opcionalmente precio_unitario (si no se envía se usa precio_venta del producto).
    cliente_id opcional: FK a Persona (cliente); si se envía, la persona debe existir.
    """
    if not items:
        raise ValueError("La venta debe tener al menos un ítem")
    if cliente_id is not None:
        if sesion.get(Persona, cliente_id) is None:
            raise ValueError(f"Cliente (persona) {cliente_id} no encontrado")

    modo_norm = (modo_venta or "TEU_ON").strip().upper()
    if modo_norm not in {"TEU_ON", "TEU_OFF"}:
        raise ValueError("modo_venta inválido; válidos: TEU_ON, TEU_OFF")

    # Normalizar método de pago solo si el modo lo requiere.
    metodo_norm: str = "PENDIENTE"
    if modo_norm == "TEU_ON":
        metodo_norm = (metodo_pago or "EFECTIVO").strip().upper()

    venta = Venta(
        subtotal=Decimal("0"),
        descuento=Decimal(str(descuento)),
        impuesto=Decimal("0"),
        total=Decimal("0"),
        metodo_pago=metodo_norm or "EFECTIVO",
        cliente_id=cliente_id,
        estado=EstadoVenta.PAGADA.value if modo_norm == "TEU_ON" else EstadoVenta.PENDIENTE.value,
    )
    sesion.add(venta)
    sesion.flush()

    for it in items:
        producto_id = it["producto_id"]
        cantidad = Decimal(str(it["cantidad"]))
        if cantidad <= 0:
            raise ValueError(f"Cantidad inválida para producto_id {producto_id}")

        producto = sesion.get(Producto, producto_id)
        if producto is None:
            raise ValueError(f"Producto {producto_id} no encontrado")

        precio = it.get("precio_unitario")
        if precio is not None:
            precio_unitario = Decimal(str(precio))
        else:
            precio_unitario = producto.precio_venta

        subtotal = cantidad * precio_unitario
        item = ItemVenta(
            venta_id=venta.id,
            producto_id=producto.id,
            nombre_producto=producto.nombre,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            subtotal=subtotal,
        )
        venta.items.append(item)

    venta.recalcular_totales()

    # Generar número de ticket (útil para TEU_OFF: cola en caja)
    # Se genera luego del flush para usar venta.id.
    if venta.numero_ticket is None:
        venta.numero_ticket = f"TCK-{venta.id:08d}"
    sesion.flush()
    sesion.refresh(venta)

    # Validación de crédito y registro en cuenta corriente solo en TEU_ON.
    if modo_norm == "TEU_ON" and cliente_id is not None and metodo_norm == "CUENTA_CORRIENTE":
        stmt_cliente = select(Cliente).where(Cliente.persona_id == cliente_id).limit(1)
        cliente_rol = sesion.scalars(stmt_cliente).first()
        if cliente_rol is None:
            raise ValueError("El cliente no tiene rol de Cliente configurado para operar a crédito")

        limite = cliente_rol.limite_credito
        if limite is not None:
            cuenta = (
                sesion.query(CuentaCorrienteCliente)
                .where(CuentaCorrienteCliente.cliente_id == cliente_rol.id)
                .one_or_none()
            )
            saldo_actual = cuenta.saldo if cuenta is not None else Decimal("0")
            nuevo_saldo = saldo_actual + venta.total
            if nuevo_saldo > limite:
                raise ValueError("Límite de crédito excedido para el cliente")

        # Registrar movimiento en cuenta corriente del cliente (identificado por rol Cliente)
        try:
            svc_cuentas_corrientes.registrar_movimiento_cuenta_corriente(
                sesion,
                cliente_id=cliente_rol.id,
                tipo="VENTA",
                monto=venta.total,
                descripcion=f"Venta #{venta.id} a crédito",
            )
        except ValueError:
            # No bloquear la venta si la cuenta corriente no puede actualizarse.
            pass

    return venta


def obtener_venta_por_id(sesion: Session, venta_id: int) -> Optional[Venta]:
    """Obtiene una venta por ID (con ítems cargados)."""
    return sesion.get(Venta, venta_id)


def listar_ventas(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
    estado: Optional[str] = None,
    cliente_id: Optional[int] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> Sequence[Venta]:
    """
    Lista ventas recientes con filtros opcionales.
    Docs Módulo 2 §13 — estados: PENDIENTE, PAGADA, FIADA, CANCELADA, SUSPENDIDA.
    """
    stmt = select(Venta)
    if estado:
        stmt = stmt.where(Venta.estado == estado.upper())
    if cliente_id is not None:
        stmt = stmt.where(Venta.cliente_id == cliente_id)
    if fecha_desde:
        stmt = stmt.where(func.date(Venta.creado_en) >= fecha_desde.isoformat())
    if fecha_hasta:
        stmt = stmt.where(func.date(Venta.creado_en) <= fecha_hasta.isoformat())
    stmt = stmt.order_by(Venta.creado_en.desc()).limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def buscar_ventas(
    sesion: Session,
    *,
    q: str,
    limite: int = 50,
) -> list[dict[str, Any]]:
    """
    Búsqueda de ventas por número de ticket, nombre de cliente, DNI o producto.
    Docs Módulo 2 §3 — Operaciones Comerciales / búsqueda de operaciones.
    """
    q_lower = q.strip().lower()
    if not q_lower:
        return []

    # Intentar búsqueda por número de ticket exacto
    stmt_ticket = (
        select(Venta)
        .where(func.lower(Venta.numero_ticket).contains(q_lower))
        .limit(limite)
    )
    # Búsqueda por persona (nombre/apellido/documento)
    stmt_persona = (
        select(Venta)
        .join(Persona, Venta.cliente_id == Persona.id, isouter=True)
        .where(
            or_(
                func.lower(Persona.nombre).contains(q_lower),
                func.lower(Persona.apellido).contains(q_lower),
                func.lower(Persona.documento).contains(q_lower),
            )
        )
        .limit(limite)
    )
    # Búsqueda por item (nombre producto)
    stmt_item = (
        select(Venta)
        .join(ItemVenta, ItemVenta.venta_id == Venta.id)
        .where(func.lower(ItemVenta.nombre_producto).contains(q_lower))
        .limit(limite)
    )

    ids_vistos: set[int] = set()
    resultado: list[dict[str, Any]] = []

    for stmt in (stmt_ticket, stmt_persona, stmt_item):
        ventas = sesion.scalars(stmt).all()
        for v in ventas:
            if v.id in ids_vistos:
                continue
            ids_vistos.add(v.id)
            persona = sesion.get(Persona, v.cliente_id) if v.cliente_id else None
            resultado.append({
                "venta_id": v.id,
                "numero_ticket": v.numero_ticket,
                "estado": v.estado,
                "cliente_id": v.cliente_id,
                "cliente_nombre": f"{persona.nombre} {persona.apellido}".strip() if persona else None,
                "cliente_documento": persona.documento if persona else None,
                "total": float(v.total),
                "creado_en": v.creado_en.isoformat() if v.creado_en else None,
                "metodo_pago": v.metodo_pago,
            })
            if len(resultado) >= limite:
                break
        if len(resultado) >= limite:
            break

    return resultado


def cancelar_venta(
    sesion: Session,
    *,
    venta_id: int,
    motivo: Optional[str] = None,
) -> Venta:
    """
    Cancela una venta que esté en estado PENDIENTE o SUSPENDIDA.
    Docs Módulo 2 §13 — estados de la venta (CANCELADA).
    """
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    if venta.estado not in {EstadoVenta.PENDIENTE.value, EstadoVenta.SUSPENDIDA.value}:
        raise ValueError(
            f"Solo se pueden cancelar ventas en estado PENDIENTE o SUSPENDIDA; estado actual: {venta.estado}"
        )

    venta.estado = EstadoVenta.CANCELADA.value
    sesion.add(venta)
    sesion.flush()

    svc_auditoria_eventos.registrar_evento(
        sesion,
        nombre="VentaCancelada",
        payload={"venta_id": venta.id, "motivo": motivo},
        modulo="ventas",
        entidad_tipo="venta",
        entidad_id=venta.id,
    )

    sesion.refresh(venta)
    return venta


def agregar_item_a_venta(
    sesion: Session,
    *,
    venta_id: int,
    producto_id: int,
    cantidad: Decimal | float,
    precio_unitario: Optional[Decimal | float] = None,
) -> Venta:
    """
    Agrega un producto al carrito de una venta PENDIENTE.
    Si el producto ya existe en el carrito, incrementa la cantidad.
    Docs Módulo 2 §8 — carrito de venta.
    """
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    if venta.estado != EstadoVenta.PENDIENTE.value:
        raise ValueError("Solo se pueden agregar ítems a ventas en estado PENDIENTE")

    producto = sesion.get(Producto, producto_id)
    if producto is None:
        raise ValueError(f"Producto {producto_id} no encontrado")

    cantidad_dec = Decimal(str(cantidad))
    if cantidad_dec <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")

    precio = Decimal(str(precio_unitario)) if precio_unitario is not None else producto.precio_venta

    # Si ya existe el ítem, suma cantidad
    stmt_item = select(ItemVenta).where(
        ItemVenta.venta_id == venta_id,
        ItemVenta.producto_id == producto_id,
    )
    item_existente = sesion.scalars(stmt_item).first()
    if item_existente:
        item_existente.cantidad += cantidad_dec
        item_existente.subtotal = item_existente.cantidad * item_existente.precio_unitario
        sesion.add(item_existente)
    else:
        nuevo = ItemVenta(
            venta_id=venta.id,
            producto_id=producto.id,
            nombre_producto=producto.nombre,
            cantidad=cantidad_dec,
            precio_unitario=precio,
            subtotal=cantidad_dec * precio,
        )
        sesion.add(nuevo)
        venta.items.append(nuevo)

    sesion.flush()
    venta.recalcular_totales()
    sesion.flush()
    sesion.refresh(venta)
    return venta


def eliminar_item_de_venta(
    sesion: Session,
    *,
    venta_id: int,
    item_id: int,
) -> Venta:
    """
    Elimina un ítem del carrito de una venta PENDIENTE.
    Docs Módulo 2 §8 — carrito de venta (eliminar producto).
    """
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    if venta.estado != EstadoVenta.PENDIENTE.value:
        raise ValueError("Solo se pueden modificar ventas en estado PENDIENTE")

    item = sesion.get(ItemVenta, item_id)
    if item is None or item.venta_id != venta_id:
        raise ValueError(f"Ítem {item_id} no encontrado en la venta {venta_id}")

    if len(venta.items) <= 1:
        raise ValueError("No se puede eliminar el único ítem de la venta; cancela la venta si deseas anularla")

    sesion.delete(item)
    sesion.flush()
    sesion.refresh(venta)
    venta.recalcular_totales()
    sesion.flush()
    sesion.refresh(venta)
    return venta


def actualizar_item_de_venta(
    sesion: Session,
    *,
    venta_id: int,
    item_id: int,
    cantidad: Optional[Decimal | float] = None,
    precio_unitario: Optional[Decimal | float] = None,
) -> Venta:
    """
    Modifica la cantidad y/o precio de un ítem en una venta PENDIENTE.
    Docs Módulo 2 §8 — carrito (modificar cantidad).
    """
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    if venta.estado != EstadoVenta.PENDIENTE.value:
        raise ValueError("Solo se pueden modificar ventas en estado PENDIENTE")

    item = sesion.get(ItemVenta, item_id)
    if item is None or item.venta_id != venta_id:
        raise ValueError(f"Ítem {item_id} no encontrado en la venta {venta_id}")

    if cantidad is not None:
        cant = Decimal(str(cantidad))
        if cant <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        item.cantidad = cant

    if precio_unitario is not None:
        item.precio_unitario = Decimal(str(precio_unitario))

    item.subtotal = item.cantidad * item.precio_unitario
    sesion.add(item)
    sesion.flush()
    venta.recalcular_totales()
    sesion.flush()
    sesion.refresh(venta)
    return venta


def aplicar_descuento_a_venta(
    sesion: Session,
    *,
    venta_id: int,
    descuento: Decimal | float,
) -> Venta:
    """
    Aplica un descuento global a una venta PENDIENTE.
    Docs Módulo 2 §8 — carrito (aplicar descuento).
    """
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    if venta.estado != EstadoVenta.PENDIENTE.value:
        raise ValueError("Solo se pueden aplicar descuentos a ventas en estado PENDIENTE")

    descuento_dec = Decimal(str(descuento))
    if descuento_dec < 0:
        raise ValueError("El descuento no puede ser negativo")

    venta.descuento = descuento_dec
    venta.recalcular_totales()
    sesion.add(venta)
    sesion.flush()
    sesion.refresh(venta)
    return venta


def agregar_pesable_por_barcode(
    sesion: Session,
    *,
    venta_id: int,
    barcode: str,
) -> Venta:
    """
    Integración POS↔Pesables (docs Módulo 2 §8 + submodulo_pesables.md §13).

    Al escanear el EAN-13 de un ítem pesable en el POS:
    - Busca el PesableItem por barcode.
    - Valida que esté en estado 'printed' (ya impreso, no usado).
    - Agrega un ItemVenta usando el precio_total codificado en la etiqueta (NO recalcula).
    - La cantidad representa el peso (en kg) del ítem.
    - Marca el PesableItem como 'used' para evitar reutilización.
    - Recalcula los totales de la venta.

    Regla crítica: el precio viaja codificado en el barcode → el POS nunca recalcula.
    """
    from backend.models.pesables import PesableItem, EstadoPesableItem

    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    if venta.estado != EstadoVenta.PENDIENTE.value:
        raise ValueError("Solo se pueden agregar ítems a ventas en estado PENDIENTE")

    # Buscar el ítem pesable por barcode
    pesable_item = sesion.scalars(
        select(PesableItem).where(PesableItem.barcode == barcode.strip())
    ).first()
    if pesable_item is None:
        raise ValueError(f"No se encontró ningún ítem pesable con barcode '{barcode}'")

    if pesable_item.estado == EstadoPesableItem.USED.value:
        raise ValueError(
            f"El ítem pesable (id={pesable_item.id}) ya fue utilizado. No se puede reutilizar una etiqueta."
        )

    # Crear ItemVenta con precio codificado en etiqueta (sin recalcular).
    # Formato ticket (§8 docs): "Pan 1.500kg x $2000/kg → $3000"
    #   - cantidad       = peso en kg (ej. 1.500)
    #   - precio_unitario = precio por kg del producto (ej. $2000/kg)
    #   - subtotal       = precio_total codificado en barcode (ej. $3000) → NO se recalcula
    nuevo_item = ItemVenta(
        venta_id=venta.id,
        producto_id=pesable_item.producto_id,
        nombre_producto=f"{pesable_item.nombre_producto} {pesable_item.peso}kg",
        cantidad=pesable_item.peso,
        precio_unitario=pesable_item.precio_unitario,  # precio/kg del producto
        subtotal=pesable_item.precio_total,            # precio fijo del barcode
    )
    sesion.add(nuevo_item)
    venta.items.append(nuevo_item)

    # Marcar ítem pesable como usado
    pesable_item.estado = EstadoPesableItem.USED.value
    sesion.add(pesable_item)

    sesion.flush()
    venta.recalcular_totales()
    sesion.flush()
    sesion.refresh(venta)
    return venta


def resolver_barcode_pesable(sesion: Session, *, barcode: str) -> dict:
    """
    Resuelve un barcode EAN-13 de pesable y devuelve la información del ítem
    sin añadirlo a ninguna venta. Útil para que el POS muestre una previsualización
    antes de confirmar el escaneo.

    Retorna dict con: item_id, producto_id, nombre_producto, peso, precio_unitario,
    precio_total, estado, barcode.

    Lanza ValueError si no existe o ya fue usado.
    """
    from backend.models.pesables import PesableItem

    item = sesion.scalars(
        select(PesableItem).where(PesableItem.barcode == barcode.strip())
    ).first()
    if item is None:
        raise ValueError(f"No se encontró ningún ítem pesable con barcode '{barcode}'")

    return {
        "item_id": item.id,
        "producto_id": item.producto_id,
        "nombre_producto": item.nombre_producto,
        "plu": item.plu,
        "peso": float(item.peso),
        "precio_unitario": float(item.precio_unitario),
        "precio_total": float(item.precio_total),
        "barcode": item.barcode,
        "estado": item.estado,
        "creado_en": item.creado_en.isoformat() if item.creado_en else None,
    }


def suspender_venta_pendiente(
    sesion: Session,
    *,
    venta_id: int,
) -> Venta:
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    if venta.estado != EstadoVenta.PENDIENTE.value:
        raise ValueError("Solo se pueden suspender ventas en estado PENDIENTE")

    venta.estado = EstadoVenta.SUSPENDIDA.value
    sesion.add(venta)
    sesion.flush()

    svc_auditoria_eventos.registrar_evento(
        sesion,
        nombre="VentaSuspendida",
        payload={"venta_id": venta.id, "estado": venta.estado},
        modulo="ventas",
        entidad_tipo="venta",
        entidad_id=venta.id,
    )

    sesion.refresh(venta)
    return venta


def reanudar_venta_suspensada(
    sesion: Session,
    *,
    venta_id: int,
) -> Venta:
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        raise ValueError("Venta no encontrada")
    if venta.estado != EstadoVenta.SUSPENDIDA.value:
        raise ValueError("Solo se pueden reanudar ventas en estado SUSPENDIDA")

    venta.estado = EstadoVenta.PENDIENTE.value
    sesion.add(venta)
    sesion.flush()

    svc_auditoria_eventos.registrar_evento(
        sesion,
        nombre="VentaReanudada",
        payload={"venta_id": venta.id, "estado": venta.estado},
        modulo="ventas",
        entidad_tipo="venta",
        entidad_id=venta.id,
    )

    sesion.refresh(venta)
    return venta
