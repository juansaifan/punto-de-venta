# Servicios del dominio Inventario (stock, movimientos, lotes, categorías de productos)
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Sequence

from sqlalchemy import cast as sa_cast, func, select
from sqlalchemy.orm import Session

from backend.models.inventario import (
    Lote,
    MovimientoInventario,
    Stock,
    TipoMovimiento,
    UbicacionStock,
)
from backend.models.producto import CategoriaProducto, Producto


UBICACION_POR_DEFECTO = UbicacionStock.GONDOLA.value


def transferir_stock(
    sesion: Session,
    *,
    producto_id: int,
    cantidad: Decimal | float,
    origen: str,
    destino: str,
    referencia: Optional[str] = None,
) -> dict:
    """Transfiere stock entre ubicaciones (DEPOSITO → GONDOLA, etc.).

    Registra dos movimientos:
    - TRANSFERENCIA (salida) en origen con cantidad negativa
    - TRANSFERENCIA (entrada) en destino con cantidad positiva
    """
    cantidad_dec = Decimal(str(cantidad))
    if cantidad_dec <= 0:
        raise ValueError("La cantidad a transferir debe ser positiva")
    origen_norm = (origen or "").strip().upper()
    destino_norm = (destino or "").strip().upper()
    if not origen_norm or not destino_norm or origen_norm == destino_norm:
        raise ValueError("Origen y destino deben ser válidos y distintos")

    st_origen = _obtener_o_crear_stock(sesion, producto_id, origen_norm)
    if st_origen.cantidad < cantidad_dec:
        raise ValueError("Stock insuficiente en origen para transferir")
    st_dest = _obtener_o_crear_stock(sesion, producto_id, destino_norm)

    st_origen.cantidad -= cantidad_dec
    st_dest.cantidad += cantidad_dec
    sesion.add(st_origen)
    sesion.add(st_dest)

    mov_salida = MovimientoInventario(
        producto_id=producto_id,
        tipo=TipoMovimiento.TRANSFERENCIA.value,
        cantidad=-cantidad_dec,
        ubicacion=origen_norm,
        referencia=referencia,
    )
    mov_entrada = MovimientoInventario(
        producto_id=producto_id,
        tipo=TipoMovimiento.TRANSFERENCIA.value,
        cantidad=cantidad_dec,
        ubicacion=destino_norm,
        referencia=referencia,
    )
    sesion.add(mov_salida)
    sesion.add(mov_entrada)
    sesion.flush()
    sesion.refresh(mov_salida)
    sesion.refresh(mov_entrada)
    return {"salida": mov_salida, "entrada": mov_entrada}


def _obtener_o_crear_stock(
    sesion: Session,
    producto_id: int,
    ubicacion: str = UBICACION_POR_DEFECTO,
) -> Stock:
    """Obtiene el registro de stock para producto+ubicación; lo crea con cantidad 0 si no existe."""
    stmt = (
        select(Stock)
        .where(Stock.producto_id == producto_id)
        .where(Stock.ubicacion == ubicacion)
        .limit(1)
    )
    stock = sesion.execute(stmt).scalars().first()
    if stock is not None:
        return stock
    stock = Stock(
        producto_id=producto_id,
        ubicacion=ubicacion,
        cantidad=Decimal("0"),
    )
    sesion.add(stock)
    sesion.flush()
    sesion.refresh(stock)
    return stock


def descontar_stock_por_venta(
    sesion: Session,
    producto_id: int,
    cantidad: Decimal | float,
    referencia: Optional[str] = None,
    ubicacion: str = UBICACION_POR_DEFECTO,
) -> MovimientoInventario:
    """
    Descuenta stock por una venta. Crea registro de stock si no existe (cantidad 0).
    Lanza ValueError si no hay stock suficiente.
    """
    cantidad = Decimal(str(cantidad))
    if cantidad <= 0:
        raise ValueError(f"Cantidad a descontar debe ser positiva (producto_id={producto_id})")
    stock = _obtener_o_crear_stock(sesion, producto_id, ubicacion)
    if stock.cantidad < cantidad:
        raise ValueError(
            f"Stock insuficiente para producto {producto_id}: "
            f"disponible {stock.cantidad}, solicitado {cantidad}"
        )
    stock.cantidad -= cantidad
    sesion.add(stock)
    movimiento = MovimientoInventario(
        producto_id=producto_id,
        tipo=TipoMovimiento.VENTA.value,
        cantidad=-cantidad,
        ubicacion=ubicacion,
        referencia=referencia,
    )
    sesion.add(movimiento)
    sesion.flush()
    sesion.refresh(movimiento)
    return movimiento


def ingresar_stock(
    sesion: Session,
    producto_id: int,
    cantidad: Decimal | float,
    tipo: str = TipoMovimiento.COMPRA.value,
    referencia: Optional[str] = None,
    ubicacion: str = UBICACION_POR_DEFECTO,
) -> MovimientoInventario:
    """
    Ingresa stock (crea registro si no existe). Útil para cargas iniciales y tests.
    """
    cantidad = Decimal(str(cantidad))
    if cantidad <= 0:
        raise ValueError(f"Cantidad a ingresar debe ser positiva (producto_id={producto_id})")
    stock = _obtener_o_crear_stock(sesion, producto_id, ubicacion)
    stock.cantidad += cantidad
    sesion.add(stock)
    movimiento = MovimientoInventario(
        producto_id=producto_id,
        tipo=tipo,
        cantidad=cantidad,
        ubicacion=ubicacion,
        referencia=referencia,
    )
    sesion.add(movimiento)
    sesion.flush()
    sesion.refresh(movimiento)
    return movimiento


def crear_lote(
    sesion: Session,
    producto_id: int,
    cantidad: Decimal | float,
    fecha_vencimiento: date,
) -> Lote:
    """Registra un lote de producto con fecha de vencimiento (para alertas de vencimiento en dashboard)."""
    producto = sesion.get(Producto, producto_id)
    if producto is None:
        raise ValueError(f"Producto {producto_id} no encontrado")
    cantidad_dec = Decimal(str(cantidad))
    if cantidad_dec <= 0:
        raise ValueError("La cantidad del lote debe ser positiva")
    lote = Lote(
        producto_id=producto_id,
        cantidad=cantidad_dec,
        fecha_vencimiento=fecha_vencimiento,
    )
    sesion.add(lote)
    sesion.flush()
    sesion.refresh(lote)
    return lote


def obtener_cantidad_stock(
    sesion: Session,
    producto_id: int,
    ubicacion: str = UBICACION_POR_DEFECTO,
) -> Decimal:
    """Devuelve la cantidad en stock para un producto en la ubicación (0 si no hay registro)."""
    stmt = (
        select(Stock)
        .where(Stock.producto_id == producto_id)
        .where(Stock.ubicacion == ubicacion)
        .limit(1)
    )
    stock = sesion.execute(stmt).scalars().first()
    return stock.cantidad if stock is not None else Decimal("0")


def listar_distribucion_stock(
    sesion: Session,
    *,
    producto_id: Optional[int] = None,
    ubicacion: Optional[str] = None,
) -> Sequence[dict]:
    """Devuelve la tabla de distribución del inventario: producto, ubicación y cantidad."""
    stmt = select(Stock)
    if producto_id is not None:
        stmt = stmt.where(Stock.producto_id == producto_id)
    if ubicacion is not None:
        ubicacion_norm = ubicacion.strip().upper()
        if ubicacion_norm:
            stmt = stmt.where(Stock.ubicacion == ubicacion_norm)
    stmt = stmt.order_by(Stock.producto_id, Stock.ubicacion)
    filas = sesion.scalars(stmt).all()
    return [
        {"producto_id": f.producto_id, "ubicacion": f.ubicacion, "cantidad": f.cantidad}
        for f in filas
    ]


def listar_checklist_conteo_manual(
    sesion: Session,
    *,
    ubicacion: str,
    solo_activos: bool = True,
    limite: int = 200,
    offset: int = 0,
) -> Sequence[dict]:
    """Genera el listado (checklist) para conteo manual con stock actual."""
    ubicacion_norm = (ubicacion or "").strip().upper()
    if not ubicacion_norm:
        raise ValueError("La ubicación es obligatoria")

    q = select(Producto).order_by(Producto.id)
    if solo_activos:
        q = q.where(Producto.activo.is_(True))
    q = q.limit(limite).offset(offset)

    productos = sesion.scalars(q).all()
    return [
        {
            "producto_id": p.id,
            "sku": p.sku,
            "nombre": p.nombre,
            "ubicacion": ubicacion_norm,
            "stock_actual": obtener_cantidad_stock(
                sesion, producto_id=p.id, ubicacion=ubicacion_norm
            ),
            "cantidad_contada": None,
            "verificado": False,
        }
        for p in productos
    ]


def listar_checklist_conteo_rotativo(
    sesion: Session,
    *,
    ubicacion: str,
    fecha,
    solo_activos: bool = True,
    limite: int = 200,
    offset: int = 0,
) -> Sequence[dict]:
    """Genera checklist de conteo rotativo según mapeo día -> categoría (por código).

    Mapeo base (docs ejemplo):
    - Lunes -> Bebidas (código "BEB")
    - Martes -> Lácteos (código "LAC")
    - Miércoles -> Almacén (código "ALM")
    (y se repite en el resto de días con un patrón simple).
    """
    ubicacion_norm = (ubicacion or "").strip().upper()
    if not ubicacion_norm:
        raise ValueError("La ubicación es obligatoria")

    # Normalizamos la fecha a `date`.
    fecha_obj = fecha
    if isinstance(fecha, str):
        from datetime import datetime

        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    else:
        # datetime/date compat
        try:
            fecha_obj = fecha.date()
        except AttributeError:
            pass

    weekday = int(fecha_obj.weekday())  # Monday=0
    categoria_por_dia = {
        0: "BEB",
        1: "LAC",
        2: "ALM",
        3: "BEB",
        4: "LAC",
        5: "ALM",
        6: "ALM",
    }
    cat_codigo = categoria_por_dia.get(weekday)
    if not cat_codigo:
        return []

    categoria = sesion.scalars(select(CategoriaProducto).where(CategoriaProducto.codigo == cat_codigo)).first()
    if categoria is None:
        return []

    q = select(Producto).where(Producto.categoria_id == categoria.id)
    if solo_activos:
        q = q.where(Producto.activo.is_(True))
    q = q.order_by(Producto.id).limit(limite).offset(offset)

    productos = sesion.scalars(q).all()
    return [
        {
            "producto_id": p.id,
            "sku": p.sku,
            "nombre": p.nombre,
            "ubicacion": ubicacion_norm,
            "stock_actual": obtener_cantidad_stock(
                sesion, producto_id=p.id, ubicacion=ubicacion_norm
            ),
            "cantidad_contada": None,
            "verificado": False,
        }
        for p in productos
    ]


def ajustar_stock_por_conteo(
    sesion: Session,
    *,
    items: Sequence[dict],
    referencia: Optional[str] = None,
) -> list[MovimientoInventario]:
    """Ajusta el stock según conteo manual.

    Para cada ítem:
    - calcula diferencia = cantidad_contada - stock_actual
    - actualiza `stock.cantidad` a la cantidad contada
    - registra movimiento `AJUSTE` si la diferencia != 0
    """
    movimientos: list[MovimientoInventario] = []
    ref_final = referencia or "Conteo manual"

    for it in items:
        producto_id_raw = getattr(it, "producto_id", None)
        if producto_id_raw is None:
            producto_id_raw = it["producto_id"]
        producto_id = int(producto_id_raw)

        ubicacion_raw = getattr(it, "ubicacion", None)
        if ubicacion_raw is None:
            ubicacion_raw = it["ubicacion"]
        ubicacion_in = (ubicacion_raw or "").strip().upper()
        if not ubicacion_in:
            raise ValueError("Ubicación inválida en conteo manual")

        cantidad_raw = getattr(it, "cantidad_contada", None)
        if cantidad_raw is None:
            cantidad_raw = it["cantidad_contada"]
        cantidad_contada = Decimal(str(cantidad_raw))
        if cantidad_contada < 0:
            raise ValueError("La cantidad contada debe ser >= 0")

        stock = _obtener_o_crear_stock(sesion, producto_id, ubicacion_in)
        diferencia = cantidad_contada - stock.cantidad

        # Ajuste: siempre dejamos el stock en la cantidad contada.
        stock.cantidad = cantidad_contada
        sesion.add(stock)

        if diferencia != 0:
            mov = MovimientoInventario(
                producto_id=producto_id,
                tipo=TipoMovimiento.AJUSTE.value,
                cantidad=diferencia,
                ubicacion=ubicacion_in,
                referencia=ref_final,
            )
            sesion.add(mov)
            movimientos.append(mov)

    sesion.flush()
    # Refresh para que el contenido (id/fecha) esté listo para serialización.
    for mov in movimientos:
        sesion.refresh(mov)
    return movimientos


def listar_movimientos_inventario(
    sesion: Session,
    *,
    producto_id: Optional[int] = None,
    tipo: Optional[str] = None,
    ubicacion: Optional[str] = None,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[MovimientoInventario]:
    """
    Lista movimientos de inventario con filtros opcionales por producto y tipo.
    Orden: más recientes primero (fecha desc, id desc).
    """
    stmt = select(MovimientoInventario)
    if producto_id is not None:
        stmt = stmt.where(MovimientoInventario.producto_id == producto_id)
    if tipo is not None:
        stmt = stmt.where(MovimientoInventario.tipo == tipo.strip().upper())
    if ubicacion is not None:
        ubicacion_norm = ubicacion.strip().upper()
        if ubicacion_norm:
            stmt = stmt.where(MovimientoInventario.ubicacion == ubicacion_norm)
    stmt = (
        stmt.order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc())
        .limit(limite)
        .offset(offset)
    )
    return sesion.scalars(stmt).all()


def revertir_movimiento_inventario(
    sesion: Session,
    *,
    movimiento_id: int,
    referencia: Optional[str] = None,
) -> MovimientoInventario:
    """Registra una reversión de un movimiento existente.

    Se crea un nuevo movimiento con la cantidad inversa y se actualiza el stock
    en la misma ubicación del movimiento original.
    """
    mov = sesion.get(MovimientoInventario, movimiento_id)
    if mov is None:
        raise ValueError(f"Movimiento inventario {movimiento_id} no encontrado")

    # Evita reversión en cadena por error.
    if mov.tipo == TipoMovimiento.REVERSION.value:
        raise ValueError("No se puede revertir un movimiento de reversión")

    ubicacion_norm = mov.ubicacion or UBICACION_POR_DEFECTO
    stock = _obtener_o_crear_stock(sesion, mov.producto_id, ubicacion_norm)

    # Regla general: el stock siempre se actualiza con `stock += movimiento.cantidad`.
    # Por lo tanto, para revertir aplicamos `stock -= movimiento.cantidad`.
    stock.cantidad -= mov.cantidad

    sesion.add(stock)

    nuevo = MovimientoInventario(
        producto_id=mov.producto_id,
        tipo=TipoMovimiento.REVERSION.value,
        cantidad=-mov.cantidad,
        ubicacion=ubicacion_norm,
        referencia=referencia
        or f"Reversión de movimiento inventario {movimiento_id}",
    )
    sesion.add(nuevo)
    sesion.flush()
    sesion.refresh(nuevo)
    return nuevo


def registrar_movimiento_manual_inventario(
    sesion: Session,
    *,
    producto_id: int,
    tipo: str,
    cantidad: Decimal | float,
    ubicacion: str,
    referencia: Optional[str] = None,
) -> MovimientoInventario:
    """Registra un movimiento manual de inventario y actualiza el stock.

    Convención:
    - `cantidad` con signo: se aplica directamente al stock (`stock += cantidad`).
    """
    tipo_norm = (tipo or "").strip().upper()
    if not tipo_norm:
        raise ValueError("tipo es obligatorio")
    if tipo_norm == TipoMovimiento.REVERSION.value:
        raise ValueError("No se puede registrar un movimiento de reversión manual")
    tipos_validos = {
        TipoMovimiento.VENTA.value,
        TipoMovimiento.COMPRA.value,
        TipoMovimiento.TRANSFERENCIA.value,
        TipoMovimiento.DEVOLUCION.value,
        TipoMovimiento.AJUSTE.value,
        TipoMovimiento.MERMA.value,
        TipoMovimiento.CONSUMO_INTERNO.value,
    }
    if tipo_norm not in tipos_validos:
        raise ValueError(
            f"tipo inválido en movimiento manual; válidos: {', '.join(sorted(tipos_validos))}"
        )

    cantidad_dec = Decimal(str(cantidad))
    if cantidad_dec == 0:
        raise ValueError("cantidad no puede ser 0")
    if not ubicacion or not ubicacion.strip():
        raise ValueError("ubicacion es obligatoria")
    ubicacion_norm = ubicacion.strip().upper()

    stock = _obtener_o_crear_stock(sesion, producto_id, ubicacion_norm)
    stock.cantidad += cantidad_dec
    sesion.add(stock)

    mov = MovimientoInventario(
        producto_id=producto_id,
        tipo=tipo_norm,
        cantidad=cantidad_dec,
        ubicacion=ubicacion_norm,
        referencia=referencia,
    )
    sesion.add(mov)
    sesion.flush()
    sesion.refresh(mov)
    return mov


# --- Rotación de stock (docs Módulo 5 §11) ---


def rotacion_stock(
    sesion: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limite: int = 50,
    tipo_rotacion: str = "alta",
) -> list[dict[str, Any]]:
    """
    Análisis de rotación de stock. Calcula movimientos netos por producto en el período.
    tipo_rotacion: 'alta' (más movimientos), 'baja' (menos movimientos), 'sin_movimiento'.
    Docs Módulo 5 §11 — Rotación de productos.
    """
    from sqlalchemy import Date as SADate

    tipo_norm = (tipo_rotacion or "alta").strip().lower()
    tipos_validos = {"alta", "baja", "sin_movimiento"}
    if tipo_norm not in tipos_validos:
        raise ValueError(f"tipo_rotacion inválido. Opciones: {sorted(tipos_validos)}")

    q = select(
        MovimientoInventario.producto_id,
        func.count(MovimientoInventario.id).label("cantidad_movimientos"),
        func.sum(func.abs(MovimientoInventario.cantidad)).label("volumen_total"),
    ).group_by(MovimientoInventario.producto_id)

    if fecha_desde:
        q = q.where(sa_cast(MovimientoInventario.fecha, SADate) >= fecha_desde)
    if fecha_hasta:
        q = q.where(sa_cast(MovimientoInventario.fecha, SADate) <= fecha_hasta)

    if tipo_norm == "sin_movimiento":
        productos_con_movimiento_ids = {
            row.producto_id for row in sesion.execute(q).all()
        }
        q_prods = select(Producto).where(Producto.activo.is_(True))
        todos = sesion.scalars(q_prods).all()
        sin_mov = [p for p in todos if p.id not in productos_con_movimiento_ids]
        resultado = []
        for p in sin_mov[:limite]:
            stock_gondola = obtener_cantidad_stock(sesion, producto_id=p.id, ubicacion=UBICACION_POR_DEFECTO)
            resultado.append({
                "producto_id": p.id,
                "sku": p.sku,
                "nombre": p.nombre,
                "cantidad_movimientos": 0,
                "volumen_total": 0.0,
                "stock_actual": float(stock_gondola),
                "clasificacion": "sin_movimiento",
            })
        return resultado

    orden = (
        func.count(MovimientoInventario.id).desc()
        if tipo_norm == "alta"
        else func.count(MovimientoInventario.id).asc()
    )
    q = q.order_by(orden).limit(limite)
    rows = sesion.execute(q).all()

    resultado = []
    for row in rows:
        prod = sesion.get(Producto, row.producto_id)
        if prod is None:
            continue
        stock_gondola = obtener_cantidad_stock(sesion, producto_id=row.producto_id, ubicacion=UBICACION_POR_DEFECTO)
        resultado.append({
            "producto_id": row.producto_id,
            "sku": prod.sku,
            "nombre": prod.nombre,
            "cantidad_movimientos": int(row.cantidad_movimientos or 0),
            "volumen_total": float(row.volumen_total or 0),
            "stock_actual": float(stock_gondola),
            "clasificacion": tipo_norm,
        })
    return resultado


# --- Ranking de mermas (docs Módulo 5 §11) ---


def ranking_mermas(
    sesion: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limite: int = 20,
) -> list[dict[str, Any]]:
    """
    Ranking de productos con mayor merma en el período.
    Docs Módulo 5 §11 — Ranking de merma sin justificar.
    """
    from sqlalchemy import Date as SADate

    q = (
        select(
            MovimientoInventario.producto_id,
            func.count(MovimientoInventario.id).label("cantidad_movimientos_merma"),
            func.sum(func.abs(MovimientoInventario.cantidad)).label("total_merma"),
        )
        .where(MovimientoInventario.tipo == TipoMovimiento.MERMA.value)
        .group_by(MovimientoInventario.producto_id)
        .order_by(func.sum(func.abs(MovimientoInventario.cantidad)).desc())
        .limit(limite)
    )
    if fecha_desde:
        q = q.where(sa_cast(MovimientoInventario.fecha, SADate) >= fecha_desde)
    if fecha_hasta:
        q = q.where(sa_cast(MovimientoInventario.fecha, SADate) <= fecha_hasta)

    rows = sesion.execute(q).all()
    resultado = []
    for row in rows:
        prod = sesion.get(Producto, row.producto_id)
        if prod is None:
            continue
        resultado.append({
            "producto_id": row.producto_id,
            "sku": prod.sku,
            "nombre": prod.nombre,
            "cantidad_movimientos_merma": int(row.cantidad_movimientos_merma or 0),
            "total_merma": float(row.total_merma or 0),
            "costo_estimado_merma": float((row.total_merma or 0) * prod.costo_actual),
        })
    return resultado


# --- Lotes vencidos (docs Módulo 5 §11) ---


def listar_lotes_vencidos(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Lista lotes cuya fecha de vencimiento ya pasó (expirados).
    Docs Módulo 5 §11 — Control de vencimientos.
    """
    hoy = date.today()
    stmt = (
        select(Lote)
        .where(Lote.fecha_vencimiento < hoy)
        .order_by(Lote.fecha_vencimiento.asc())
        .limit(limite)
        .offset(offset)
    )
    lotes = sesion.scalars(stmt).all()
    resultado = []
    for lote in lotes:
        prod = sesion.get(Producto, lote.producto_id)
        dias_vencido = (hoy - lote.fecha_vencimiento).days
        resultado.append({
            "id": lote.id,
            "producto_id": lote.producto_id,
            "sku": prod.sku if prod else None,
            "nombre_producto": prod.nombre if prod else None,
            "cantidad": float(lote.cantidad),
            "fecha_vencimiento": lote.fecha_vencimiento.isoformat(),
            "dias_vencido": dias_vencido,
        })
    return resultado


# --- Lotes por producto (docs Módulo 5 §11) ---


def listar_lotes_por_producto(
    sesion: Session,
    *,
    producto_id: int,
    solo_vigentes: bool = False,
    limite: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Lista todos los lotes de un producto con su estado (vigente/vencido).
    Docs Módulo 5 §11 — Control de vencimientos / Históricos.
    """
    stmt = select(Lote).where(Lote.producto_id == producto_id)
    if solo_vigentes:
        stmt = stmt.where(Lote.fecha_vencimiento >= date.today())
    stmt = stmt.order_by(Lote.fecha_vencimiento.asc()).limit(limite).offset(offset)
    lotes = sesion.scalars(stmt).all()
    hoy = date.today()
    return [
        {
            "id": lote.id,
            "producto_id": lote.producto_id,
            "cantidad": float(lote.cantidad),
            "fecha_vencimiento": lote.fecha_vencimiento.isoformat(),
            "vencido": lote.fecha_vencimiento < hoy,
            "dias_para_vencer": (lote.fecha_vencimiento - hoy).days,
        }
        for lote in lotes
    ]


# --- Historial por producto (docs Módulo 5 §12) ---


def historial_producto(
    sesion: Session,
    *,
    producto_id: int,
    limite: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Devuelve el historial completo de un producto: datos maestros + movimientos de inventario.
    Docs Módulo 5 §12 — Históricos.
    """
    prod = sesion.get(Producto, producto_id)
    if prod is None:
        raise ValueError(f"Producto {producto_id} no encontrado")

    movimientos = listar_movimientos_inventario(
        sesion,
        producto_id=producto_id,
        limite=limite,
        offset=offset,
    )

    stocks = sesion.scalars(
        select(Stock).where(Stock.producto_id == producto_id)
    ).all()

    lotes = sesion.scalars(
        select(Lote)
        .where(Lote.producto_id == producto_id)
        .order_by(Lote.fecha_vencimiento)
    ).all()

    hoy = date.today()
    return {
        "producto": {
            "id": prod.id,
            "sku": prod.sku,
            "nombre": prod.nombre,
            "precio_venta": float(prod.precio_venta),
            "costo_actual": float(prod.costo_actual),
            "activo": prod.activo,
        },
        "stock_por_ubicacion": [
            {"ubicacion": s.ubicacion, "cantidad": float(s.cantidad)}
            for s in stocks
        ],
        "lotes": [
            {
                "id": lote.id,
                "cantidad": float(lote.cantidad),
                "fecha_vencimiento": lote.fecha_vencimiento.isoformat(),
                "vencido": lote.fecha_vencimiento < hoy,
            }
            for lote in lotes
        ],
        "movimientos_recientes": [
            {
                "id": m.id,
                "tipo": m.tipo,
                "cantidad": float(m.cantidad),
                "ubicacion": m.ubicacion,
                "referencia": m.referencia,
                "fecha": m.fecha.isoformat() if m.fecha else None,
            }
            for m in movimientos
        ],
        "total_movimientos": len(movimientos),
    }


# --- Alertas de punto de reorden (docs Módulo 5 §7) ---


def productos_bajo_punto_reorden(
    sesion: Session,
    *,
    ubicacion: str = UBICACION_POR_DEFECTO,
    solo_activos: bool = True,
    limite: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Lista productos cuyo stock está por debajo del punto de reorden.
    Docs Módulo 5 §7 — Solicitudes automáticas de compra.
    """
    ubicacion_norm = (ubicacion or UBICACION_POR_DEFECTO).strip().upper()

    q = select(Producto)
    if solo_activos:
        q = q.where(Producto.activo.is_(True))
    q = q.where(Producto.punto_reorden > 0).limit(limite + offset)
    productos = sesion.scalars(q).all()

    resultado = []
    for prod in productos:
        stock_actual = obtener_cantidad_stock(sesion, producto_id=prod.id, ubicacion=ubicacion_norm)
        if stock_actual <= prod.punto_reorden:
            resultado.append({
                "producto_id": prod.id,
                "sku": prod.sku,
                "nombre": prod.nombre,
                "stock_actual": float(stock_actual),
                "punto_reorden": float(prod.punto_reorden),
                "stock_minimo": float(prod.stock_minimo),
                "diferencia": float(prod.punto_reorden - stock_actual),
                "ubicacion": ubicacion_norm,
            })

    return resultado[offset: offset + limite]


# --- Valorización del inventario (docs Módulo 5 §8) ---


def valorizacion_inventario(
    sesion: Session,
    *,
    ubicacion: str | None = None,
    solo_activos: bool = True,
) -> dict[str, Any]:
    """
    Calcula el valor total del inventario (stock × costo_actual) por producto.
    Docs Módulo 5 §8 — Precios / costos.
    """
    q_stocks = select(Stock)
    if ubicacion:
        q_stocks = q_stocks.where(Stock.ubicacion == ubicacion.strip().upper())

    stocks = sesion.scalars(q_stocks).all()

    stocks_por_producto: dict[int, float] = {}
    for s in stocks:
        stocks_por_producto[s.producto_id] = stocks_por_producto.get(s.producto_id, 0.0) + float(s.cantidad)

    q_prods = select(Producto)
    if solo_activos:
        q_prods = q_prods.where(Producto.activo.is_(True))
    productos = sesion.scalars(q_prods).all()

    detalle = []
    total_costo = 0.0
    total_venta = 0.0

    for prod in productos:
        stock = stocks_por_producto.get(prod.id, 0.0)
        if stock == 0:
            continue
        valor_costo = stock * float(prod.costo_actual)
        valor_venta = stock * float(prod.precio_venta)
        total_costo += valor_costo
        total_venta += valor_venta
        detalle.append({
            "producto_id": prod.id,
            "sku": prod.sku,
            "nombre": prod.nombre,
            "stock_total": stock,
            "costo_unitario": float(prod.costo_actual),
            "precio_venta_unitario": float(prod.precio_venta),
            "valor_costo": round(valor_costo, 2),
            "valor_venta": round(valor_venta, 2),
        })

    return {
        "total_productos": len(detalle),
        "total_valor_costo": round(total_costo, 2),
        "total_valor_venta": round(total_venta, 2),
        "margen_potencial": round(total_venta - total_costo, 2),
        "detalle": detalle,
    }


# --- Categorías de productos (docs Módulo 5 §3) ---


def listar_categorias(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
    categoria_padre_id: Optional[int] = None,
) -> Sequence[CategoriaProducto]:
    """Lista categorías de productos. Opcionalmente filtra por categoria_padre_id (None = raíz)."""
    stmt = select(CategoriaProducto).order_by(CategoriaProducto.codigo)
    if categoria_padre_id is not None:
        stmt = stmt.where(CategoriaProducto.categoria_padre_id == categoria_padre_id)
    stmt = stmt.limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def obtener_categoria_por_id(sesion: Session, categoria_id: int) -> Optional[CategoriaProducto]:
    """Obtiene una categoría por ID."""
    return sesion.get(CategoriaProducto, categoria_id)


def crear_categoria(
    sesion: Session,
    *,
    codigo: str,
    nombre: str,
    descripcion: Optional[str] = None,
    categoria_padre_id: Optional[int] = None,
) -> CategoriaProducto:
    """Crea una categoría de producto. codigo debe ser único."""
    codigo_norm = codigo.strip()[:32]
    nombre_norm = nombre.strip()
    if not codigo_norm:
        raise ValueError("El código de categoría no puede estar vacío")
    if not nombre_norm:
        raise ValueError("El nombre de categoría no puede estar vacío")
    if sesion.execute(select(CategoriaProducto).where(CategoriaProducto.codigo == codigo_norm)).scalars().first():
        raise ValueError("Ya existe una categoría con ese código")
    if categoria_padre_id is not None:
        padre = sesion.get(CategoriaProducto, categoria_padre_id)
        if padre is None:
            raise ValueError(f"Categoría padre {categoria_padre_id} no encontrada")
    cat = CategoriaProducto(
        codigo=codigo_norm,
        nombre=nombre_norm,
        descripcion=descripcion.strip() if descripcion else None,
        categoria_padre_id=categoria_padre_id,
    )
    sesion.add(cat)
    sesion.flush()
    sesion.refresh(cat)
    return cat


def eliminar_categoria(sesion: Session, categoria_id: int) -> None:
    """Elimina una categoría de producto si no tiene productos activos ni subcategorías.

    Reglas de negocio:
    - No se puede eliminar si existen productos con esa categoría.
    - No se puede eliminar si tiene subcategorías (para mantener jerarquía).
    """
    cat = sesion.get(CategoriaProducto, categoria_id)
    if cat is None:
        raise ValueError(f"Categoría {categoria_id} no encontrada")

    # Verificar productos asociados
    productos_count = sesion.execute(
        select(func.count(Producto.id)).where(Producto.categoria_id == categoria_id)
    ).scalar() or 0
    if productos_count > 0:
        raise ValueError(
            f"No se puede eliminar la categoría '{cat.nombre}': "
            f"tiene {productos_count} producto(s) asociado(s)"
        )

    # Verificar subcategorías
    subcats_count = sesion.execute(
        select(func.count(CategoriaProducto.id)).where(
            CategoriaProducto.categoria_padre_id == categoria_id
        )
    ).scalar() or 0
    if subcats_count > 0:
        raise ValueError(
            f"No se puede eliminar la categoría '{cat.nombre}': "
            f"tiene {subcats_count} subcategoría(s)"
        )

    sesion.delete(cat)
    sesion.flush()


def actualizar_categoria(
    sesion: Session,
    categoria_id: int,
    *,
    codigo: Optional[str] = None,
    nombre: Optional[str] = None,
    descripcion: Optional[str] = None,
    categoria_padre_id: Optional[int] = None,
) -> CategoriaProducto:
    """Actualiza parcialmente una categoría. Al menos un campo debe enviarse."""
    cat = sesion.get(CategoriaProducto, categoria_id)
    if cat is None:
        raise ValueError("Categoría no encontrada")
    if codigo is None and nombre is None and descripcion is None and categoria_padre_id is None:
        raise ValueError("Se debe enviar al menos un campo a actualizar")
    if codigo is not None:
        codigo_norm = codigo.strip()
        if not codigo_norm:
            raise ValueError("El código no puede estar vacío")
        existente = sesion.execute(
            select(CategoriaProducto).where(CategoriaProducto.codigo == codigo_norm, CategoriaProducto.id != categoria_id)
        ).scalars().first()
        if existente:
            raise ValueError("Ya existe otra categoría con ese código")
        cat.codigo = codigo_norm
    if nombre is not None:
        nombre_norm = nombre.strip()
        if not nombre_norm:
            raise ValueError("El nombre no puede estar vacío")
        cat.nombre = nombre_norm
    if descripcion is not None:
        cat.descripcion = descripcion.strip() or None
    if categoria_padre_id is not None:
        if categoria_padre_id == categoria_id:
            raise ValueError("Una categoría no puede ser padre de sí misma")
        padre = sesion.get(CategoriaProducto, categoria_padre_id)
        if padre is None:
            raise ValueError(f"Categoría padre {categoria_padre_id} no encontrada")
        cat.categoria_padre_id = categoria_padre_id
    sesion.add(cat)
    sesion.flush()
    sesion.refresh(cat)
    return cat


# ---------------------------------------------------------------------------
# Importación masiva de productos (§9 Cargas de productos — Módulo 5)
# ---------------------------------------------------------------------------


def importar_productos(
    sesion: Session,
    items: list[dict],
    *,
    actualizar_si_existe: bool = True,
) -> dict:
    """Importa una lista de productos en bulk (create or update por SKU).

    Cada ítem puede contener:
        sku, nombre, precio_venta, costo_actual, descripcion, codigo_barra,
        stock_minimo, punto_reorden, categoria_id, pesable, plu.

    Campos obligatorios por ítem: sku, nombre, precio_venta.

    Retorna: {creados, actualizados, errores: [{idx, sku, error}]}
    """
    from decimal import Decimal as Dec

    creados = 0
    actualizados = 0
    errores: list[dict] = []

    for idx, item in enumerate(items):
        sku = str(item.get("sku", "")).strip()
        if not sku:
            errores.append({"idx": idx, "sku": "", "error": "SKU es obligatorio"})
            continue

        nombre = str(item.get("nombre", "")).strip()
        if not nombre:
            errores.append({"idx": idx, "sku": sku, "error": "nombre es obligatorio"})
            continue

        try:
            precio_venta = Dec(str(item["precio_venta"]))
        except (KeyError, Exception):
            errores.append({"idx": idx, "sku": sku, "error": "precio_venta inválido o faltante"})
            continue

        existente = sesion.execute(
            select(Producto).where(Producto.sku == sku)
        ).scalars().first()

        try:
            if existente is not None:
                if not actualizar_si_existe:
                    errores.append({"idx": idx, "sku": sku, "error": "SKU ya existe (actualizar desactivado)"})
                    continue
                existente.nombre = nombre
                existente.precio_venta = precio_venta
                if "costo_actual" in item:
                    existente.costo_actual = Dec(str(item["costo_actual"]))
                if "descripcion" in item:
                    existente.descripcion = str(item["descripcion"]).strip() or None
                if "codigo_barra" in item:
                    existente.codigo_barra = str(item["codigo_barra"]).strip() or None
                if "stock_minimo" in item:
                    existente.stock_minimo = Dec(str(item["stock_minimo"]))
                if "punto_reorden" in item:
                    existente.punto_reorden = Dec(str(item["punto_reorden"]))
                if "categoria_id" in item and item["categoria_id"] is not None:
                    existente.categoria_id = int(item["categoria_id"])
                if "pesable" in item:
                    existente.pesable = bool(item["pesable"])
                if "plu" in item and item["plu"] is not None:
                    existente.plu = int(item["plu"])
                sesion.add(existente)
                actualizados += 1
            else:
                nuevo = Producto(
                    sku=sku,
                    nombre=nombre,
                    precio_venta=precio_venta,
                    costo_actual=Dec(str(item.get("costo_actual", 0))),
                    descripcion=str(item.get("descripcion", "")).strip() or None,
                    codigo_barra=str(item.get("codigo_barra", "")).strip() or None,
                    stock_minimo=Dec(str(item.get("stock_minimo", 0))),
                    punto_reorden=Dec(str(item.get("punto_reorden", 0))),
                    categoria_id=int(item["categoria_id"]) if item.get("categoria_id") else None,
                    pesable=bool(item.get("pesable", False)),
                    plu=int(item["plu"]) if item.get("plu") else None,
                    activo=bool(item.get("activo", True)),
                )
                sesion.add(nuevo)
                creados += 1
        except Exception as exc:
            errores.append({"idx": idx, "sku": sku, "error": str(exc)})
            continue

    sesion.flush()
    return {
        "creados": creados,
        "actualizados": actualizados,
        "errores": errores,
        "total_procesados": creados + actualizados + len(errores),
    }
