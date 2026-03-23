"""Endpoints REST para Integraciones (docs Módulo 8)."""
from datetime import date
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import integraciones as svc_integraciones

router = APIRouter(prefix="/integraciones", tags=["integraciones"])


class FlujoAlternativoRequest(BaseModel):
    venta_id: int = Field(..., gt=0)
    documento_cliente: str = Field(..., min_length=1, max_length=32)
    email: str = Field(..., min_length=3, max_length=128)
    nombre_cliente: Optional[str] = Field(None, max_length=128)
    apellido_cliente: Optional[str] = Field(None, max_length=128)


class EnviarComprobanteRequest(BaseModel):
    venta_id: int = Field(..., gt=0)
    email: str = Field(..., min_length=3, max_length=128)
    tipo_comprobante: str = Field("ticket", max_length=32)


class PagoExternoItem(BaseModel):
    referencia_externa: str = Field(..., min_length=1, max_length=128)
    monto: float = Field(..., ge=0)
    estado: str = Field("aprobado", max_length=32)


class ReconciliacionRequest(BaseModel):
    tipo_pasarela: str = Field(..., min_length=1, max_length=32)
    pagos: List[PagoExternoItem] = Field(..., min_length=1)


@router.get("/tipos")
def listar_tipos_integracion():
    """Lista los tipos de integración soportados (facturación, pasarelas, hardware, etc.)."""
    return svc_integraciones.listar_tipos_integracion()


@router.get("/estado")
def estado_integraciones(db: Session = Depends(get_db)):
    """Estado de cada integración (activo/desactivado) desde la configuración persistida."""
    return svc_integraciones.obtener_estado_integraciones(db)


# --- Resumen / health de integraciones ---


@router.get("/resumen")
def resumen_integraciones(db: Session = Depends(get_db)):
    """Resumen global de integraciones (activos/configurados y último log por tipo)."""
    return svc_integraciones.resumen_integraciones(db)


@router.get("/dispositivos")
def listar_dispositivos_pos():
    """Lista los dispositivos de hardware POS esperados (impresora, lector de barras, balanza). Docs Módulo 8 §5."""
    return svc_integraciones.listar_dispositivos_pos()


@router.get("/dispositivos/{codigo}/estado")
def estado_dispositivo(codigo: str, db: Session = Depends(get_db)):
    """Devuelve el estado de disponibilidad de un dispositivo POS (impresora/lector_barras/balanza). Docs Módulo 8 §5-6."""
    resultado = svc_integraciones.obtener_estado_dispositivo(db, codigo)
    if resultado is None:
        raise HTTPException(status_code=404, detail=f"Dispositivo '{codigo}' no existe en el catálogo")
    return resultado


@router.get("/flujo-alternativo-sin-impresora")
def get_flujo_alternativo_sin_impresora():
    """Devuelve el flujo a seguir cuando no hay impresora: solicitar DNI, buscar/crear cliente, email, enviar comprobante. Docs Módulo 8 §6."""
    return svc_integraciones.get_flujo_alternativo_sin_impresora()


@router.post("/flujo-alternativo-sin-impresora/ejecutar")
def ejecutar_flujo_alternativo_sin_impresora(
    body: FlujoAlternativoRequest,
    db: Session = Depends(get_db),
):
    """Ejecuta el flujo alternativo sin impresora: busca/crea cliente por DNI y simula envío de comprobante digital. Docs Módulo 8 §6."""
    return svc_integraciones.ejecutar_flujo_alternativo_sin_impresora(
        db,
        venta_id=body.venta_id,
        documento_cliente=body.documento_cliente,
        email=body.email,
        nombre_cliente=body.nombre_cliente,
        apellido_cliente=body.apellido_cliente,
    )


# --- Prueba de conexión (simulada) ---


@router.post("/{tipo_codigo}/probar")
def probar_conexion_integracion(tipo_codigo: str, db: Session = Depends(get_db)):
    """Ejecuta una prueba de conexión simulada para el tipo. Tipo no válido → 404."""
    resultado = svc_integraciones.probar_conexion(db, tipo_codigo)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Tipo de integración no encontrado")
    return resultado


# --- Logs de integración (docs Módulo 8: Logs de integración) ---


@router.get("/logs")
def listar_logs_integracion(
    tipo_codigo: str | None = None,
    limite: int = 100,
    db: Session = Depends(get_db),
):
    """Lista los últimos logs de integración (éxito/fallo). Filtro opcional por tipo_codigo; limite max 500."""
    return svc_integraciones.listar_logs(db, tipo_codigo=tipo_codigo, limite=limite)


@router.post("/logs")
def registrar_log_integracion(body: dict, db: Session = Depends(get_db)):
    """Registra un log de integración. Body: tipo_codigo, exito (bool), mensaje; opcional: detalle. Tipo no válido → 404."""
    tipo_codigo = body.get("tipo_codigo")
    exito = body.get("exito")
    mensaje = body.get("mensaje")
    detalle = body.get("detalle")
    if not tipo_codigo or not isinstance(tipo_codigo, str):
        raise HTTPException(status_code=422, detail="Se requiere 'tipo_codigo' (string)")
    if exito is None:
        raise HTTPException(status_code=422, detail="Se requiere 'exito' (true o false)")
    if not isinstance(exito, bool):
        raise HTTPException(status_code=422, detail="'exito' debe ser un booleano")
    if mensaje is None:
        raise HTTPException(status_code=422, detail="Se requiere 'mensaje' (string)")
    if not isinstance(mensaje, str):
        raise HTTPException(status_code=422, detail="'mensaje' debe ser un string")
    resultado = svc_integraciones.registrar_log(db, tipo_codigo, exito, mensaje, detalle)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Tipo de integración no encontrado")
    return resultado


@router.post("/mensajeria/enviar-comprobante")
def enviar_comprobante_digital(
    body: EnviarComprobanteRequest,
    db: Session = Depends(get_db),
):
    """Simula el envío de un comprobante digital por email (docs Módulo 8 §8 Mensajería). Registra log en mensajería."""
    return svc_integraciones.enviar_comprobante_digital(
        db,
        venta_id=body.venta_id,
        email=body.email,
        tipo_comprobante=body.tipo_comprobante,
    )


@router.patch("/{tipo_codigo}/activo")
def configurar_activo_integracion(
    tipo_codigo: str,
    body: dict,
    db: Session = Depends(get_db),
):
    """Activa o desactiva un tipo de integración. Body: {"activo": true|false}. Tipo no válido → 404."""
    activo = body.get("activo")
    if activo is None:
        raise HTTPException(status_code=422, detail="Se requiere 'activo' (true o false)")
    if not isinstance(activo, bool):
        raise HTTPException(status_code=422, detail="'activo' debe ser un booleano")
    cfg = svc_integraciones.configurar_activo(db, tipo_codigo, activo)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Tipo de integración no encontrado")
    return {"tipo_codigo": cfg.tipo_codigo, "activo": cfg.activo}


@router.get("/{tipo_codigo}/config")
def obtener_config_integracion(tipo_codigo: str, db: Session = Depends(get_db)):
    """Obtiene la configuración (credenciales/parámetros) del tipo de integración. Tipo no válido → 404."""
    resultado = svc_integraciones.obtener_config(db, tipo_codigo)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Tipo de integración no encontrado")
    return resultado


@router.put("/{tipo_codigo}/config")
def guardar_config_integracion(
    tipo_codigo: str,
    body: dict,
    db: Session = Depends(get_db),
):
    """Guarda la configuración JSON del tipo (credenciales, parámetros). Body: objeto JSON. Tipo no válido → 404."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    resultado = svc_integraciones.guardar_config(db, tipo_codigo, body)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Tipo de integración no encontrado")
    return resultado


# --- Estadísticas de logs (métricas de éxito/fallo) ---


@router.get("/logs/estadisticas")
def estadisticas_logs(
    tipo_codigo: Optional[str] = Query(None, description="Filtrar por tipo de integración"),
    db: Session = Depends(get_db),
):
    """Estadísticas de éxito/fallo de logs por tipo de integración (total, exitosos, fallos, tasa_exito_pct)."""
    return svc_integraciones.estadisticas_logs(db, tipo_codigo=tipo_codigo)


# --- Integración contable (docs Módulo 8 §10) ---


@router.get("/contable/exportar")
def exportar_datos_contables(
    fecha_desde: Optional[date] = Query(None, description="Fecha inicio del período (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin del período (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Genera paquete de exportación contable (ventas + movimientos de caja) para sistemas externos
    como Alegra, Contabilium, Bejerman. Docs Módulo 8 §10.
    """
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(status_code=400, detail="fecha_desde no puede ser mayor que fecha_hasta")
    return svc_integraciones.exportacion_contable(db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)


# --- API Externa (docs Módulo 8 §11) ---


@router.get("/api-externa/resumen")
def resumen_api_externa(db: Session = Depends(get_db)):
    """
    Resumen de datos del POS para consumo de sistemas externos (apps, e-commerce, gestión).
    Expone: inventario, ventas del día y datos del sistema. Docs Módulo 8 §11.
    """
    return svc_integraciones.resumen_api_externa(db)


@router.get("/api-externa/productos/{producto_id}")
def datos_producto_externo(producto_id: int, db: Session = Depends(get_db)):
    """
    Datos de un producto para consumo de API externa (apps, e-commerce).
    Retorna precio, stock, código y atributos. 404 si no existe. Docs Módulo 8 §11.
    """
    datos = svc_integraciones.datos_producto_externo(db, producto_id)
    if datos is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return datos


# --- Backups y sincronización (docs Módulo 8 §12) ---


@router.get("/backup/estado")
def estado_backup():
    """Estado del sistema de backups (último backup, historial reciente). Docs Módulo 8 §12."""
    return svc_integraciones.obtener_estado_backup()


class BackupRequest(BaseModel):
    frecuencia: str = Field("manual", description="manual | hourly | daily | weekly")


@router.post("/backup/ejecutar")
def ejecutar_backup(
    body: Optional[BackupRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Ejecuta un backup del sistema (simulado). Body opcional: {"frecuencia": "manual"|"hourly"|"daily"|"weekly"}.
    Docs Módulo 8 §12.
    """
    frecuencia = body.frecuencia if body else "manual"
    try:
        return svc_integraciones.ejecutar_backup(db, frecuencia=frecuencia)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Datos fiscales de venta (docs Módulo 8 §4) ---


@router.get("/fiscal/venta/{venta_id}")
def datos_fiscales_venta(venta_id: int, db: Session = Depends(get_db)):
    """
    Datos fiscales de una venta para emisión de comprobante electrónico (AFIP/ARCA).
    Incluye: items, totales, datos del emisor. 404 si la venta no existe. Docs Módulo 8 §4.
    """
    datos = svc_integraciones.datos_fiscales_venta(db, venta_id)
    if datos is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return datos


# --- Reconciliación de pagos de pasarela (docs Módulo 8 §7) ---


@router.post("/pasarela/reconciliar")
def reconciliar_pagos_pasarela(
    body: ReconciliacionRequest,
    db: Session = Depends(get_db),
):
    """
    Reconcilia pagos externos de una pasarela (mercadopago, getnet, posnet, stripe) contra ventas del sistema.
    Body: {"tipo_pasarela": "mercadopago", "pagos": [{referencia_externa, monto, estado}, ...]}.
    Docs Módulo 8 §7.
    """
    pagos = [p.model_dump() for p in body.pagos]
    try:
        return svc_integraciones.reconciliar_pagos_pasarela(
            db,
            tipo_pasarela=body.tipo_pasarela,
            pagos_externos=pagos,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
