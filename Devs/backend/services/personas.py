"""Servicios del dominio Personas (persona base + roles)."""
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Sequence

from sqlalchemy import cast as sa_cast, func, or_, select
from sqlalchemy.orm import Session

from backend.models.persona import Persona, Cliente, Proveedor, Empleado, Contacto


# Personas base -----------------------------------------------------------------


def listar_personas(
    sesion: Session,
    *,
    activo_only: bool = True,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Persona]:
    """Lista personas con paginación."""
    q = select(Persona).order_by(Persona.id)
    if activo_only:
        q = q.where(Persona.activo.is_(True))
    q = q.limit(limite).offset(offset)
    return sesion.scalars(q).all()


def obtener_persona_por_id(sesion: Session, persona_id: int) -> Optional[Persona]:
    """Obtiene una persona por su ID."""
    return sesion.get(Persona, persona_id)


def crear_persona(
    sesion: Session,
    *,
    nombre: str,
    apellido: str,
    documento: Optional[str] = None,
    telefono: Optional[str] = None,
    activo: bool = True,
) -> Persona:
    """Crea una nueva persona base."""
    persona = Persona(
        nombre=nombre.strip(),
        apellido=apellido.strip(),
        documento=documento.strip() if documento else None,
        telefono=telefono.strip() if telefono else None,
        activo=activo,
    )
    sesion.add(persona)
    sesion.flush()
    sesion.refresh(persona)
    return persona


def actualizar_persona(
    sesion: Session,
    persona_id: int,
    *,
    nombre: Optional[str] = None,
    apellido: Optional[str] = None,
    documento: Optional[str] = None,
    telefono: Optional[str] = None,
    activo: Optional[bool] = None,
) -> Optional[Persona]:
    """Actualiza una persona existente."""
    persona = sesion.get(Persona, persona_id)
    if persona is None:
        return None
    if nombre is not None:
        persona.nombre = nombre.strip()
    if apellido is not None:
        persona.apellido = apellido.strip()
    if documento is not None:
        persona.documento = documento.strip() if documento else None
    if telefono is not None:
        persona.telefono = telefono.strip() if telefono else None
    if activo is not None:
        persona.activo = activo
    sesion.flush()
    sesion.refresh(persona)
    return persona


# Clientes ----------------------------------------------------------------------


def crear_cliente(
    sesion: Session,
    *,
    persona_id: int,
    segmento: Optional[str] = None,
    condicion_pago: Optional[str] = None,
    limite_credito: Optional[float] = None,
    estado: str = "ACTIVO",
    observaciones: Optional[str] = None,
) -> Cliente:
    """Crea un rol de cliente asociado a una persona existente."""
    persona = sesion.get(Persona, persona_id)
    if persona is None:
        raise ValueError(f"Persona {persona_id} no encontrada")
    cliente = Cliente(
        persona_id=persona_id,
        segmento=segmento.strip() if segmento else None,
        condicion_pago=condicion_pago.strip() if condicion_pago else None,
        limite_credito=Decimal(str(limite_credito))
        if limite_credito is not None
        else None,
        estado=estado,
        observaciones=observaciones.strip() if observaciones else None,
    )
    sesion.add(cliente)
    sesion.flush()
    sesion.refresh(cliente)
    return cliente


def listar_clientes(
    sesion: Session,
    *,
    busqueda: Optional[str] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Cliente]:
    """Lista clientes con paginación."""
    stmt = select(Cliente).join(Persona, Cliente.persona_id == Persona.id).order_by(Cliente.id)
    if busqueda:
        q = f"%{busqueda.strip()}%"
        stmt = stmt.where(
            or_(
                Persona.nombre.ilike(q),
                Persona.apellido.ilike(q),
                Persona.documento.ilike(q),
                Persona.telefono.ilike(q),
            )
        )
    stmt = stmt.limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def buscar_clientes_lookup(
    sesion: Session,
    *,
    busqueda: str,
    limite: int = 20,
    offset: int = 0,
) -> Sequence[tuple[Cliente, Persona]]:
    """Búsqueda rápida de clientes para POS (devuelve (Cliente, Persona))."""
    q = (busqueda or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    stmt = (
        select(Cliente, Persona)
        .join(Persona, Cliente.persona_id == Persona.id)
        .where(
            or_(
                Persona.nombre.ilike(like),
                Persona.apellido.ilike(like),
                Persona.documento.ilike(like),
                Persona.telefono.ilike(like),
            )
        )
        .order_by(Persona.apellido, Persona.nombre, Cliente.id)
        .limit(limite)
        .offset(offset)
    )
    return list(sesion.execute(stmt).all())


def alta_rapida_cliente(
    sesion: Session,
    *,
    nombre: str,
    apellido: str,
    documento: Optional[str] = None,
    telefono: Optional[str] = None,
    segmento: Optional[str] = None,
    condicion_pago: Optional[str] = None,
    limite_credito: Optional[float] = None,
    estado: str = "ACTIVO",
    observaciones: Optional[str] = None,
) -> tuple[Cliente, Persona]:
    """Crea Persona + Cliente en una sola operación (pensado para POS)."""
    persona = crear_persona(
        sesion,
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        telefono=telefono,
        activo=True,
    )
    cliente = crear_cliente(
        sesion,
        persona_id=persona.id,
        segmento=segmento,
        condicion_pago=condicion_pago,
        limite_credito=limite_credito,
        estado=estado,
        observaciones=observaciones,
    )
    return cliente, persona


def obtener_cliente_por_id(sesion: Session, cliente_id: int) -> Optional[Cliente]:
    """Obtiene un cliente por id."""
    return sesion.get(Cliente, cliente_id)


def obtener_cliente_por_persona_id(sesion: Session, persona_id: int) -> Optional[Cliente]:
    """Obtiene el primer cliente asociado a una persona (relación 1:1 típica)."""
    return sesion.scalars(
        select(Cliente).where(Cliente.persona_id == persona_id).order_by(Cliente.id)
    ).first()


def actualizar_cliente(
    sesion: Session,
    cliente_id: int,
    *,
    segmento: Optional[str] = None,
    condicion_pago: Optional[str] = None,
    limite_credito: Optional[float] = None,
    estado: Optional[str] = None,
    observaciones: Optional[str] = None,
) -> Optional[Cliente]:
    """Actualiza los datos de configuración comercial de un cliente."""
    cliente = sesion.get(Cliente, cliente_id)
    if cliente is None:
        return None
    if segmento is not None:
        cliente.segmento = segmento.strip() or None
    if condicion_pago is not None:
        cliente.condicion_pago = condicion_pago.strip() or None
    if limite_credito is not None:
        cliente.limite_credito = Decimal(str(limite_credito))
    if estado is not None:
        cliente.estado = estado.strip()
    if observaciones is not None:
        cliente.observaciones = observaciones.strip() or None
    sesion.flush()
    sesion.refresh(cliente)
    return cliente


# Proveedores -------------------------------------------------------------------


def crear_proveedor(
    sesion: Session,
    *,
    persona_id: int,
    cuit: Optional[str] = None,
    condiciones_comerciales: Optional[str] = None,
    condiciones_pago: Optional[str] = None,
    lista_precios: Optional[str] = None,
    estado: str = "ACTIVO",
    frecuencia_entrega: Optional[str] = None,
    minimo_compra: Optional[float] = None,
    tiempo_estimado_entrega: Optional[str] = None,
    observaciones: Optional[str] = None,
) -> Proveedor:
    """Crea un rol de proveedor asociado a una persona existente."""
    persona = sesion.get(Persona, persona_id)
    if persona is None:
        raise ValueError(f"Persona {persona_id} no encontrada")
    proveedor = Proveedor(
        persona_id=persona_id,
        cuit=cuit.strip() if cuit else None,
        condiciones_comerciales=(
            condiciones_comerciales.strip() if condiciones_comerciales else None
        ),
        condiciones_pago=condiciones_pago.strip() if condiciones_pago else None,
        lista_precios=lista_precios.strip() if lista_precios else None,
        estado=estado,
        frecuencia_entrega=(
            frecuencia_entrega.strip() if frecuencia_entrega else None
        ),
        minimo_compra=minimo_compra,
        tiempo_estimado_entrega=(
            tiempo_estimado_entrega.strip() if tiempo_estimado_entrega else None
        ),
        observaciones=observaciones.strip() if observaciones else None,
    )
    sesion.add(proveedor)
    sesion.flush()
    sesion.refresh(proveedor)
    return proveedor


def listar_proveedores(
    sesion: Session,
    *,
    estado: Optional[str] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Proveedor]:
    """Lista proveedores con paginación y filtro opcional por estado."""
    stmt = select(Proveedor).order_by(Proveedor.id)
    if estado is not None:
        stmt = stmt.where(Proveedor.estado == estado.strip().upper())
    stmt = stmt.limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def obtener_proveedor_por_id(
    sesion: Session, proveedor_id: int
) -> Optional[Proveedor]:
    """Obtiene un proveedor por id."""
    return sesion.get(Proveedor, proveedor_id)


def actualizar_proveedor(
    sesion: Session,
    proveedor_id: int,
    *,
    cuit: Optional[str] = None,
    condiciones_comerciales: Optional[str] = None,
    condiciones_pago: Optional[str] = None,
    lista_precios: Optional[str] = None,
    estado: Optional[str] = None,
    frecuencia_entrega: Optional[str] = None,
    minimo_compra: Optional[float] = None,
    tiempo_estimado_entrega: Optional[str] = None,
    observaciones: Optional[str] = None,
) -> Optional[Proveedor]:
    """Actualiza los datos de un proveedor existente."""
    proveedor = sesion.get(Proveedor, proveedor_id)
    if proveedor is None:
        return None
    if cuit is not None:
        proveedor.cuit = cuit.strip() or None
    if condiciones_comerciales is not None:
        proveedor.condiciones_comerciales = condiciones_comerciales.strip() or None
    if condiciones_pago is not None:
        proveedor.condiciones_pago = condiciones_pago.strip() or None
    if lista_precios is not None:
        proveedor.lista_precios = lista_precios.strip() or None
    if estado is not None:
        proveedor.estado = estado.strip()
    if frecuencia_entrega is not None:
        proveedor.frecuencia_entrega = frecuencia_entrega.strip() or None
    if minimo_compra is not None:
        proveedor.minimo_compra = minimo_compra
    if tiempo_estimado_entrega is not None:
        proveedor.tiempo_estimado_entrega = tiempo_estimado_entrega.strip() or None
    if observaciones is not None:
        proveedor.observaciones = observaciones.strip() or None
    sesion.flush()
    sesion.refresh(proveedor)
    return proveedor


# Empleados ---------------------------------------------------------------------


def crear_empleado(
    sesion: Session,
    *,
    persona_id: int,
    documento: Optional[str] = None,
    cargo: Optional[str] = None,
    estado: str = "ACTIVO",
) -> Empleado:
    """Crea un rol de empleado asociado a una persona existente."""
    persona = sesion.get(Persona, persona_id)
    if persona is None:
        raise ValueError(f"Persona {persona_id} no encontrada")
    empleado = Empleado(
        persona_id=persona_id,
        documento=documento.strip() if documento else None,
        cargo=cargo.strip() if cargo else None,
        estado=estado,
    )
    sesion.add(empleado)
    sesion.flush()
    sesion.refresh(empleado)
    return empleado


def listar_empleados(
    sesion: Session,
    *,
    estado: Optional[str] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Empleado]:
    """Lista empleados con paginación y filtro opcional por estado."""
    stmt = select(Empleado).order_by(Empleado.id)
    if estado is not None:
        stmt = stmt.where(Empleado.estado == estado.strip().upper())
    stmt = stmt.limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def obtener_empleado_por_id(sesion: Session, empleado_id: int) -> Optional[Empleado]:
    """Obtiene un empleado por id."""
    return sesion.get(Empleado, empleado_id)


def obtener_empleado_por_persona_id(sesion: Session, persona_id: int) -> Optional[Empleado]:
    """Obtiene el primer empleado asociado a una persona."""
    return sesion.scalars(
        select(Empleado).where(Empleado.persona_id == persona_id).order_by(Empleado.id)
    ).first()


def actualizar_empleado(
    sesion: Session,
    empleado_id: int,
    *,
    documento: Optional[str] = None,
    cargo: Optional[str] = None,
    estado: Optional[str] = None,
) -> Optional[Empleado]:
    """Actualiza los datos de un empleado existente."""
    empleado = sesion.get(Empleado, empleado_id)
    if empleado is None:
        return None
    if documento is not None:
        empleado.documento = documento.strip() or None
    if cargo is not None:
        empleado.cargo = cargo.strip() or None
    if estado is not None:
        empleado.estado = estado.strip()
    sesion.flush()
    sesion.refresh(empleado)
    return empleado


# Contactos ---------------------------------------------------------------------


def crear_contacto(
    sesion: Session,
    *,
    persona_id: int,
    nombre: str,
    cargo: Optional[str] = None,
    telefono: Optional[str] = None,
    email: Optional[str] = None,
    observaciones: Optional[str] = None,
) -> Contacto:
    """Crea un contacto vinculado a una persona (proveedor, empresa, etc.)."""
    persona = sesion.get(Persona, persona_id)
    if persona is None:
        raise ValueError(f"Persona {persona_id} no encontrada")
    contacto = Contacto(
        persona_id=persona_id,
        nombre=nombre.strip(),
        cargo=cargo.strip() if cargo else None,
        telefono=telefono.strip() if telefono else None,
        email=email.strip() if email else None,
        observaciones=observaciones.strip() if observaciones else None,
    )
    sesion.add(contacto)
    sesion.flush()
    sesion.refresh(contacto)
    return contacto


def listar_contactos(
    sesion: Session,
    *,
    persona_id: Optional[int] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Contacto]:
    """Lista contactos, opcionalmente filtrando por persona."""
    stmt = select(Contacto).order_by(Contacto.id)
    if persona_id is not None:
        stmt = stmt.where(Contacto.persona_id == persona_id)
    stmt = stmt.limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def obtener_contacto_por_id(sesion: Session, contacto_id: int) -> Optional[Contacto]:
    """Obtiene un contacto por id."""
    return sesion.get(Contacto, contacto_id)


# Cuentas corrientes de clientes
#
# La lógica de cuentas corrientes se ha movido al submódulo Tesorería
# (`backend.services.cuentas_corrientes`). Este módulo permanece
# responsable únicamente del CRUD de personas y sus roles.


# ---------------------------------------------------------------------------
# Análisis comercial de clientes (docs Módulo 6 §5, §10)
# ---------------------------------------------------------------------------


def ventas_por_cliente(
    sesion: Session,
    *,
    cliente_id: int,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limite: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Historial de ventas de un cliente con estadísticas agregadas.
    Usa Venta.cliente_id = Cliente.persona_id.
    Docs Módulo 6 §5 — Clientes / §10 — Integración con Ventas.
    """
    from sqlalchemy import Date as SADate
    from backend.models.venta import Venta, EstadoVenta

    cliente = sesion.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} no encontrado")

    stmt = select(Venta).where(Venta.cliente_id == cliente.persona_id)
    if fecha_desde:
        stmt = stmt.where(sa_cast(Venta.creado_en, SADate) >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(sa_cast(Venta.creado_en, SADate) <= fecha_hasta)

    # Estadísticas globales (sin paginación)
    agg_stmt = select(
        func.count(Venta.id).label("total_ventas"),
        func.sum(Venta.total).label("total_facturado"),
        func.avg(Venta.total).label("ticket_promedio"),
        func.max(Venta.creado_en).label("ultima_compra"),
    ).where(Venta.cliente_id == cliente.persona_id)
    if fecha_desde:
        agg_stmt = agg_stmt.where(sa_cast(Venta.creado_en, SADate) >= fecha_desde)
    if fecha_hasta:
        agg_stmt = agg_stmt.where(sa_cast(Venta.creado_en, SADate) <= fecha_hasta)

    row = sesion.execute(agg_stmt).one()

    ventas_fiadas = sesion.scalar(
        select(func.count(Venta.id)).where(
            Venta.cliente_id == cliente.persona_id,
            Venta.estado == EstadoVenta.FIADA.value,
        )
    ) or 0

    # Ventas paginadas
    stmt_pag = stmt.order_by(Venta.creado_en.desc()).limit(limite).offset(offset)
    ventas = sesion.scalars(stmt_pag).all()

    persona = sesion.get(Persona, cliente.persona_id)

    return {
        "cliente_id": cliente_id,
        "persona_id": cliente.persona_id,
        "nombre": f"{persona.nombre} {persona.apellido}" if persona else "",
        "segmento": cliente.segmento,
        "limite_credito": float(cliente.limite_credito) if cliente.limite_credito else None,
        "estadisticas": {
            "total_ventas": int(row.total_ventas or 0),
            "total_facturado": float(row.total_facturado or 0),
            "ticket_promedio": round(float(row.ticket_promedio or 0), 2),
            "ultima_compra": row.ultima_compra.isoformat() if row.ultima_compra else None,
            "ventas_fiadas": int(ventas_fiadas),
        },
        "ventas": [
            {
                "id": v.id,
                "numero_ticket": v.numero_ticket,
                "total": float(v.total),
                "estado": v.estado,
                "metodo_pago": v.metodo_pago,
                "fecha": v.creado_en.isoformat(),
            }
            for v in ventas
        ],
    }


def ranking_clientes(
    sesion: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limite: int = 20,
    excluir_canceladas: bool = True,
) -> list[dict[str, Any]]:
    """
    Ranking de clientes ordenados por total facturado en el período.
    Docs Módulo 6 §5 — Segmentación de clientes.
    """
    from sqlalchemy import Date as SADate
    from backend.models.venta import Venta, EstadoVenta

    stmt = (
        select(
            Venta.cliente_id,
            func.count(Venta.id).label("total_ventas"),
            func.sum(Venta.total).label("total_facturado"),
            func.avg(Venta.total).label("ticket_promedio"),
        )
        .where(Venta.cliente_id.is_not(None))
        .group_by(Venta.cliente_id)
        .order_by(func.sum(Venta.total).desc())
        .limit(limite)
    )
    if excluir_canceladas:
        stmt = stmt.where(Venta.estado != EstadoVenta.CANCELADA.value)
    if fecha_desde:
        stmt = stmt.where(sa_cast(Venta.creado_en, SADate) >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(sa_cast(Venta.creado_en, SADate) <= fecha_hasta)

    rows = sesion.execute(stmt).all()

    resultado = []
    for pos, row in enumerate(rows, start=1):
        persona = sesion.get(Persona, row.cliente_id)
        # buscar el rol cliente asociado a esa persona
        cliente = sesion.scalars(
            select(Cliente).where(Cliente.persona_id == row.cliente_id)
        ).first()
        resultado.append({
            "posicion": pos,
            "persona_id": row.cliente_id,
            "cliente_id": cliente.id if cliente else None,
            "nombre": f"{persona.nombre} {persona.apellido}" if persona else f"Persona {row.cliente_id}",
            "segmento": cliente.segmento if cliente else None,
            "total_ventas": int(row.total_ventas or 0),
            "total_facturado": float(row.total_facturado or 0),
            "ticket_promedio": round(float(row.ticket_promedio or 0), 2),
        })
    return resultado


def resumen_cuenta_corriente_cliente(
    sesion: Session,
    *,
    cliente_id: int,
) -> dict[str, Any]:
    """
    Resumen de cuenta corriente de un cliente: saldo actual, límite de crédito y últimos movimientos.
    Docs Módulo 6 §5 / §10 — Integración con Tesorería.
    """
    from backend.models.persona import CuentaCorrienteCliente, MovimientoCuentaCorriente

    cliente = sesion.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} no encontrado")

    persona = sesion.get(Persona, cliente.persona_id)
    cc = cliente.cuenta_corriente

    movimientos = []
    saldo = Decimal("0")
    if cc:
        saldo = cc.saldo
        movs = sesion.scalars(
            select(MovimientoCuentaCorriente)
            .where(MovimientoCuentaCorriente.cuenta_id == cc.id)
            .order_by(MovimientoCuentaCorriente.fecha.desc())
            .limit(20)
        ).all()
        movimientos = [
            {
                "id": m.id,
                "tipo": m.tipo,
                "monto": float(m.monto),
                "descripcion": m.descripcion,
                "fecha": m.fecha.isoformat(),
            }
            for m in movs
        ]

    limite_credito = float(cliente.limite_credito) if cliente.limite_credito else None
    margen_disponible = None
    if limite_credito is not None:
        margen_disponible = round(limite_credito - float(saldo), 2)

    return {
        "cliente_id": cliente_id,
        "persona_id": cliente.persona_id,
        "nombre": f"{persona.nombre} {persona.apellido}" if persona else "",
        "segmento": cliente.segmento,
        "saldo_deuda": float(saldo),
        "limite_credito": limite_credito,
        "margen_disponible": margen_disponible,
        "estado": cliente.estado,
        "movimientos_recientes": movimientos,
    }


# ---------------------------------------------------------------------------
# Análisis comercial de proveedores (docs Módulo 6 §6, §10)
# ---------------------------------------------------------------------------


def compras_por_proveedor(
    sesion: Session,
    *,
    proveedor_id: int,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limite: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Historial de compras de un proveedor con estadísticas agregadas.
    Usa Compra.proveedor_id = Proveedor.persona_id.
    Docs Módulo 6 §6 — Proveedores / §10 — Integración con Inventario.
    """
    from sqlalchemy import Date as SADate
    from backend.models.compra import Compra

    proveedor = sesion.get(Proveedor, proveedor_id)
    if proveedor is None:
        raise ValueError(f"Proveedor {proveedor_id} no encontrado")

    stmt = select(Compra).where(Compra.proveedor_id == proveedor.persona_id)
    if fecha_desde:
        stmt = stmt.where(sa_cast(Compra.fecha, SADate) >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(sa_cast(Compra.fecha, SADate) <= fecha_hasta)

    # Estadísticas globales
    agg_stmt = select(
        func.count(Compra.id).label("total_compras"),
        func.sum(Compra.total).label("total_invertido"),
        func.avg(Compra.total).label("ticket_promedio"),
        func.max(Compra.fecha).label("ultima_compra"),
    ).where(Compra.proveedor_id == proveedor.persona_id)
    if fecha_desde:
        agg_stmt = agg_stmt.where(sa_cast(Compra.fecha, SADate) >= fecha_desde)
    if fecha_hasta:
        agg_stmt = agg_stmt.where(sa_cast(Compra.fecha, SADate) <= fecha_hasta)

    row = sesion.execute(agg_stmt).one()

    stmt_pag = stmt.order_by(Compra.fecha.desc()).limit(limite).offset(offset)
    compras = sesion.scalars(stmt_pag).all()
    persona = sesion.get(Persona, proveedor.persona_id)

    return {
        "proveedor_id": proveedor_id,
        "persona_id": proveedor.persona_id,
        "nombre": f"{persona.nombre} {persona.apellido}" if persona else "",
        "cuit": proveedor.cuit,
        "condiciones_comerciales": proveedor.condiciones_comerciales,
        "estadisticas": {
            "total_compras": int(row.total_compras or 0),
            "total_invertido": float(row.total_invertido or 0),
            "ticket_promedio": round(float(row.ticket_promedio or 0), 2),
            "ultima_compra": row.ultima_compra.isoformat() if row.ultima_compra else None,
        },
        "compras": [
            {
                "id": c.id,
                "total": float(c.total),
                "estado": c.estado,
                "fecha": c.fecha.isoformat() if c.fecha else None,
            }
            for c in compras
        ],
    }


def ranking_proveedores(
    sesion: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limite: int = 20,
) -> list[dict[str, Any]]:
    """
    Ranking de proveedores ordenados por volumen de compras en el período.
    Docs Módulo 6 §6.
    """
    from sqlalchemy import Date as SADate
    from backend.models.compra import Compra

    stmt = (
        select(
            Compra.proveedor_id,
            func.count(Compra.id).label("total_compras"),
            func.sum(Compra.total).label("total_invertido"),
            func.avg(Compra.total).label("ticket_promedio"),
        )
        .where(Compra.proveedor_id.is_not(None))
        .group_by(Compra.proveedor_id)
        .order_by(func.sum(Compra.total).desc())
        .limit(limite)
    )
    if fecha_desde:
        stmt = stmt.where(sa_cast(Compra.fecha, SADate) >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(sa_cast(Compra.fecha, SADate) <= fecha_hasta)

    rows = sesion.execute(stmt).all()

    resultado = []
    for pos, row in enumerate(rows, start=1):
        persona = sesion.get(Persona, row.proveedor_id)
        proveedor = sesion.scalars(
            select(Proveedor).where(Proveedor.persona_id == row.proveedor_id)
        ).first()
        resultado.append({
            "posicion": pos,
            "persona_id": row.proveedor_id,
            "proveedor_id": proveedor.id if proveedor else None,
            "nombre": f"{persona.nombre} {persona.apellido}" if persona else f"Persona {row.proveedor_id}",
            "cuit": proveedor.cuit if proveedor else None,
            "total_compras": int(row.total_compras or 0),
            "total_invertido": float(row.total_invertido or 0),
            "ticket_promedio": round(float(row.ticket_promedio or 0), 2),
        })
    return resultado
