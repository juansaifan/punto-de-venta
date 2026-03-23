"""Endpoints REST para inventario (stock y movimientos)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from backend.api.deps import get_db
from backend.api.schemas.inventario import (
    CategoriaProductoResponse,
    DistribucionStockItemResponse,
    ConteoManualRequest,
    ConteoManualResponse,
    ConteoManualChecklistItemResponse,
    MovimientoManualRequest,
    IngresarStockRequest,
    MovimientoInventarioResponse,
    TransferirStockRequest,
    TransferirStockResponse,
    RevertirMovimientoInventarioRequest,
    StockResponse,
)
from backend.services import inventario as svc_inventario
from backend.services import alertas_inventario as svc_alertas_inventario

router = APIRouter(prefix="/inventario", tags=["inventario"])


@router.post("/ingresar")
def ingresar_stock(
    body: IngresarStockRequest,
    db: Session = Depends(get_db),
):
    """Ingresa stock a un producto (crea registro si no existe)."""
    try:
        svc_inventario.ingresar_stock(
            db,
            producto_id=body.producto_id,
            cantidad=body.cantidad,
            ubicacion=body.ubicacion or svc_inventario.UBICACION_POR_DEFECTO,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"mensaje": "Stock ingresado correctamente"}


@router.post("/productos/{producto_id}/lotes", status_code=201)
def crear_lote(
    producto_id: int,
    body: dict,
    db: Session = Depends(get_db),
):
    """Registra un lote con fecha de vencimiento (para alertas 'productos próximos a vencer'). Body: { cantidad, fecha_vencimiento (YYYY-MM-DD) }."""
    cantidad = body.get("cantidad")
    fecha_vencimiento = body.get("fecha_vencimiento")
    if cantidad is None:
        raise HTTPException(status_code=422, detail="Se requiere 'cantidad'")
    if not fecha_vencimiento:
        raise HTTPException(status_code=422, detail="Se requiere 'fecha_vencimiento' (YYYY-MM-DD)")
    try:
        from datetime import datetime
        if isinstance(fecha_vencimiento, str):
            fv = datetime.strptime(fecha_vencimiento, "%Y-%m-%d").date()
        else:
            fv = fecha_vencimiento
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="fecha_vencimiento debe ser YYYY-MM-DD")
    try:
        lote = svc_inventario.crear_lote(db, producto_id=producto_id, cantidad=cantidad, fecha_vencimiento=fv)
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return {"id": lote.id, "producto_id": lote.producto_id, "cantidad": float(lote.cantidad), "fecha_vencimiento": lote.fecha_vencimiento.isoformat()}


@router.get("/productos/{producto_id}/stock", response_model=StockResponse)
def obtener_stock(
    producto_id: int,
    db: Session = Depends(get_db),
    ubicacion: str = Query(svc_inventario.UBICACION_POR_DEFECTO, description="Ubicación (GONDOLA/DEPOSITO)"),
):
    """Obtiene la cantidad en stock de un producto para una ubicación."""
    cantidad = svc_inventario.obtener_cantidad_stock(db, producto_id=producto_id, ubicacion=ubicacion)
    return StockResponse(producto_id=producto_id, cantidad=cantidad)


@router.get("/distribucion", response_model=list[DistribucionStockItemResponse])
def listar_distribucion_stock(
    db: Session = Depends(get_db),
    producto_id: int | None = Query(None, description="Filtrar por producto"),
    ubicacion: str | None = Query(None, description="Filtrar por ubicación (GONDOLA/DEPOSITO)"),
):
    """Tabla de distribución del inventario: producto + ubicación + cantidad."""
    return svc_inventario.listar_distribucion_stock(
        db, producto_id=producto_id, ubicacion=ubicacion
    )


@router.get("/movimientos", response_model=list[MovimientoInventarioResponse])
def listar_movimientos(
    db: Session = Depends(get_db),
    producto_id: int | None = Query(None, description="Filtrar por producto"),
    tipo: str | None = Query(None, description="Filtrar por tipo (VENTA, COMPRA, AJUSTE, etc.)"),
    ubicacion: str | None = Query(None, description="Filtrar por ubicación (GONDOLA/DEPOSITO)"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista movimientos de inventario (más recientes primero). Filtros opcionales: producto_id, tipo."""
    movimientos = svc_inventario.listar_movimientos_inventario(
        db,
        producto_id=producto_id,
        tipo=tipo,
        ubicacion=ubicacion,
        limite=limite,
        offset=offset,
    )
    return list(movimientos)


@router.get("/alertas")
def obtener_alertas_inventario(
    db: Session = Depends(get_db),
    ubicacion: str = Query("GONDOLA", description="Ubicación de stock (GONDOLA/DEPOSITO)"),
    dias_vencimiento: int = Query(7, ge=0, le=365, description="Días hacia adelante para alertas de vencimiento"),
    solo_activos: bool = Query(True, description="Solo productos activos"),
    emitir_eventos: bool = Query(False, description="Emitir eventos de alertas (para auditoría/automatización)"),
):
    """Devuelve alertas operativas: stock bajo y lotes próximos a vencer."""
    try:
        return svc_alertas_inventario.detectar_alertas(
            db,
            ubicacion=ubicacion,
            dias_vencimiento=dias_vencimiento,
            solo_activos=solo_activos,
            emitir_eventos=emitir_eventos,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reposicion/ejecutar")
def ejecutar_reposicion_automatica(
    db: Session = Depends(get_db),
    solo_activos: bool = Query(True),
    max_items: int = Query(100, ge=1, le=500),
):
    """Ejecuta reposición automática DEPOSITO → GONDOLA (si está habilitada en Configuración)."""
    from backend.services import reposicion_automatica as svc_reposicion

    return svc_reposicion.ejecutar_reposicion_automatica(
        db, solo_activos=solo_activos, max_items=max_items
    )


@router.post("/transferir", response_model=TransferirStockResponse)
def transferir_stock(
    body: TransferirStockRequest,
    db: Session = Depends(get_db),
):
    """Transfiere stock entre ubicaciones registrando dos movimientos (salida/entrada)."""
    try:
        return svc_inventario.transferir_stock(
            db,
            producto_id=body.producto_id,
            cantidad=body.cantidad,
            origen=body.origen,
            destino=body.destino,
            referencia=body.referencia,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/movimientos/{movimiento_id}/revertir",
    response_model=MovimientoInventarioResponse,
)
def revertir_movimiento(
    movimiento_id: int,
    body: RevertirMovimientoInventarioRequest | None = None,
    db: Session = Depends(get_db),
):
    """Registra una reversión: crea un movimiento inverso y ajusta el `stock`."""
    try:
        referencia = body.referencia if body else None
        return svc_inventario.revertir_movimiento_inventario(
            db, movimiento_id=movimiento_id, referencia=referencia
        )
    except ValueError as e:
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.post(
    "/movimientos/manual",
    response_model=MovimientoInventarioResponse,
)
def registrar_movimiento_manual(
    body: MovimientoManualRequest,
    db: Session = Depends(get_db),
):
    """Registra un movimiento de inventario manual y actualiza el stock."""
    try:
        return svc_inventario.registrar_movimiento_manual_inventario(
            db,
            producto_id=body.producto_id,
            tipo=body.tipo,
            cantidad=body.cantidad,
            ubicacion=body.ubicacion,
            referencia=body.referencia,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/conteos/manual", response_model=ConteoManualResponse)
def conteo_manual(
    body: ConteoManualRequest,
    db: Session = Depends(get_db),
):
    """Conteo manual: ajusta stock y registra movimientos AJUSTE por diferencia."""
    try:
        movimientos = svc_inventario.ajustar_stock_por_conteo(
            db,
            items=body.items,
            referencia=body.referencia,
        )
        return ConteoManualResponse(movimientos=movimientos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/conteos/manual/checklist",
    response_model=list[ConteoManualChecklistItemResponse],
)
def checklist_conteo_manual(
    db: Session = Depends(get_db),
    ubicacion: str = Query(svc_inventario.UBICACION_POR_DEFECTO, description="Ubicación (GONDOLA/DEPOSITO)"),
    solo_activos: bool = Query(True, description="Solo productos activos"),
    limite: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Genera checklist de conteo manual con stock actual por producto."""
    try:
        return svc_inventario.listar_checklist_conteo_manual(
            db,
            ubicacion=ubicacion,
            solo_activos=solo_activos,
            limite=limite,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/conteos/rotativos/checklist",
    response_model=list[ConteoManualChecklistItemResponse],
)
def checklist_conteo_rotativo(
    db: Session = Depends(get_db),
    ubicacion: str = Query(svc_inventario.UBICACION_POR_DEFECTO, description="Ubicación (GONDOLA/DEPOSITO)"),
    fecha: str = Query(datetime.now().strftime("%Y-%m-%d"), description="Fecha en formato YYYY-MM-DD"),
    solo_activos: bool = Query(True, description="Solo productos activos"),
    limite: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Genera checklist de conteo rotativo según mapeo día -> categoría."""
    try:
        return svc_inventario.listar_checklist_conteo_rotativo(
            db,
            ubicacion=ubicacion,
            fecha=fecha,
            solo_activos=solo_activos,
            limite=limite,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Rotación de stock (docs Módulo 5 §11) ---


@router.get("/rotacion")
def rotacion_stock(
    db: Session = Depends(get_db),
    fecha_desde: str | None = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha fin YYYY-MM-DD"),
    tipo_rotacion: str = Query("alta", description="alta | baja | sin_movimiento"),
    limite: int = Query(50, ge=1, le=200),
):
    """
    Análisis de rotación de stock: alta rotación, baja rotación o sin movimiento.
    Docs Módulo 5 §11.
    """
    from datetime import datetime as dt

    def parse_date(s: str | None):
        if not s:
            return None
        try:
            return dt.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Fecha inválida: {s}. Use YYYY-MM-DD")

    try:
        return svc_inventario.rotacion_stock(
            db,
            fecha_desde=parse_date(fecha_desde),
            fecha_hasta=parse_date(fecha_hasta),
            limite=limite,
            tipo_rotacion=tipo_rotacion,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Ranking de mermas (docs Módulo 5 §11) ---


@router.get("/mermas/ranking")
def ranking_mermas(
    db: Session = Depends(get_db),
    fecha_desde: str | None = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha fin YYYY-MM-DD"),
    limite: int = Query(20, ge=1, le=100),
):
    """
    Top productos con mayor merma en el período (cantidad y costo estimado).
    Docs Módulo 5 §11 — Ranking de merma sin justificar.
    """
    from datetime import datetime as dt

    def parse_date(s: str | None):
        if not s:
            return None
        try:
            return dt.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Fecha inválida: {s}. Use YYYY-MM-DD")

    return svc_inventario.ranking_mermas(
        db,
        fecha_desde=parse_date(fecha_desde),
        fecha_hasta=parse_date(fecha_hasta),
        limite=limite,
    )


# --- Lotes vencidos (docs Módulo 5 §11) ---


@router.get("/lotes/vencidos")
def listar_lotes_vencidos(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Lista lotes cuya fecha de vencimiento ya pasó. Ordenados por fecha (más antiguos primero).
    Docs Módulo 5 §11 — Control de vencimientos.
    """
    return svc_inventario.listar_lotes_vencidos(db, limite=limite, offset=offset)


# --- Lotes por producto (docs Módulo 5 §11) ---


@router.get("/productos/{producto_id}/lotes")
def listar_lotes_por_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    solo_vigentes: bool = Query(False, description="Solo lotes cuya fecha de vencimiento no ha pasado"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Lista todos los lotes de un producto con estado vigente/vencido.
    Docs Módulo 5 §11.
    """
    return svc_inventario.listar_lotes_por_producto(
        db,
        producto_id=producto_id,
        solo_vigentes=solo_vigentes,
        limite=limite,
        offset=offset,
    )


# --- Historial por producto (docs Módulo 5 §12) ---


@router.get("/productos/{producto_id}/historial")
def historial_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Historial completo de un producto: datos maestros, stock por ubicación, lotes y movimientos recientes.
    Docs Módulo 5 §12 — Históricos.
    """
    try:
        return svc_inventario.historial_producto(
            db,
            producto_id=producto_id,
            limite=limite,
            offset=offset,
        )
    except ValueError as e:
        if "no encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


# --- Punto de reorden (docs Módulo 5 §7) ---


@router.get("/reorden")
def productos_bajo_punto_reorden(
    db: Session = Depends(get_db),
    ubicacion: str = Query("GONDOLA", description="Ubicación de stock (GONDOLA/DEPOSITO)"),
    solo_activos: bool = Query(True, description="Solo productos activos"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Lista productos cuyo stock está por debajo del punto de reorden (genera solicitud de compra).
    Docs Módulo 5 §7.
    """
    return svc_inventario.productos_bajo_punto_reorden(
        db,
        ubicacion=ubicacion,
        solo_activos=solo_activos,
        limite=limite,
        offset=offset,
    )


# --- Valorización del inventario (docs Módulo 5 §8) ---


@router.get("/valorizacion")
def valorizacion_inventario(
    db: Session = Depends(get_db),
    ubicacion: str | None = Query(None, description="Filtrar por ubicación (GONDOLA/DEPOSITO)"),
    solo_activos: bool = Query(True, description="Solo productos activos"),
):
    """
    Valorización del inventario: stock × costo_actual y stock × precio_venta por producto.
    Docs Módulo 5 §8 — Precios / costos.
    """
    return svc_inventario.valorizacion_inventario(db, ubicacion=ubicacion, solo_activos=solo_activos)


# --- Categorías de productos (docs Módulo 5 §3) ---


@router.get("/categorias", response_model=list[CategoriaProductoResponse])
def listar_categorias(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    categoria_padre_id: int | None = Query(None, description="Filtrar por categoría padre (raíz si no se envía)"),
):
    """Lista categorías de productos. Filtro opcional por categoría padre."""
    items = svc_inventario.listar_categorias(
        db,
        limite=limite,
        offset=offset,
        categoria_padre_id=categoria_padre_id,
    )
    return list(items)


@router.get("/categorias/{categoria_id}", response_model=CategoriaProductoResponse)
def obtener_categoria(categoria_id: int, db: Session = Depends(get_db)):
    """Obtiene una categoría por ID."""
    cat = svc_inventario.obtener_categoria_por_id(db, categoria_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return cat


@router.post("/categorias", status_code=201, response_model=CategoriaProductoResponse)
def crear_categoria(body: dict, db: Session = Depends(get_db)):
    """Crea una categoría de producto (código único)."""
    codigo = (body.get("codigo") or "").strip()
    nombre = (body.get("nombre") or "").strip()
    if not codigo:
        raise HTTPException(status_code=422, detail="El código es obligatorio")
    if not nombre:
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    descripcion = body.get("descripcion")
    categoria_padre_id = body.get("categoria_padre_id")
    try:
        cat = svc_inventario.crear_categoria(
            db,
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
            categoria_padre_id=categoria_padre_id,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "ya existe" in msg:
            raise HTTPException(status_code=409, detail=str(e))
        if "no encontrada" in msg or "no encontrado" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return cat


@router.patch("/categorias/{categoria_id}", response_model=CategoriaProductoResponse)
def actualizar_categoria(categoria_id: int, body: dict, db: Session = Depends(get_db)):
    """Actualiza parcialmente una categoría (código, nombre, descripcion, categoria_padre_id)."""
    codigo = body.get("codigo")
    nombre = body.get("nombre")
    descripcion = body.get("descripcion")
    categoria_padre_id = body.get("categoria_padre_id")
    if codigo is None and nombre is None and descripcion is None and categoria_padre_id is None:
        raise HTTPException(
            status_code=422,
            detail="Se debe enviar al menos uno: codigo, nombre, descripcion, categoria_padre_id",
        )
    try:
        cat = svc_inventario.actualizar_categoria(
            db,
            categoria_id,
            codigo=codigo.strip() if isinstance(codigo, str) else None,
            nombre=nombre.strip() if isinstance(nombre, str) else None,
            descripcion=descripcion,
            categoria_padre_id=categoria_padre_id,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrada" in msg or "no encontrado" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return cat


@router.delete("/categorias/{categoria_id}", status_code=204)
def eliminar_categoria(categoria_id: int, db: Session = Depends(get_db)):
    """Elimina una categoría si no tiene productos ni subcategorías asociadas.

    Retorna 204 si se eliminó con éxito.
    Retorna 400 si tiene productos o subcategorías.
    Retorna 404 si no existe.
    """
    try:
        svc_inventario.eliminar_categoria(db, categoria_id)
    except ValueError as e:
        msg = str(e)
        if "no encontrada" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.post("/productos/importar", status_code=201)
def importar_productos(
    body: dict,
    db: Session = Depends(get_db),
):
    """Importa productos en bulk desde una lista JSON (§9 Cargas de productos — Módulo 5).

    Body:
      {
        "items": [{sku, nombre, precio_venta, ...}, ...],
        "actualizar_si_existe": true
      }

    Campos obligatorios por ítem: sku, nombre, precio_venta.
    Retorna: {creados, actualizados, errores, total_procesados}.
    """
    items = body.get("items", [])
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=422, detail="Se debe enviar 'items' como lista no vacía")
    actualizar_si_existe = bool(body.get("actualizar_si_existe", True))
    try:
        resultado = svc_inventario.importar_productos(
            db, items, actualizar_si_existe=actualizar_si_existe
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return resultado
