# Servicios del dominio Integraciones (docs Módulo 8)
import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from backend.models.integracion import IntegracionConfig, IntegracionLog

# Catálogo de tipos de integración soportados (estructura del módulo docs)
TIPOS_INTEGRACION = [
    {"codigo": "facturacion_electronica", "nombre": "Facturación electrónica", "descripcion": "Conexión con organismos fiscales (AFIP/ARCA). Emisión y validación de comprobantes."},
    {"codigo": "pasarelas_pago", "nombre": "Pasarelas de pago", "descripcion": "Integración con sistemas de pago electrónico (Mercado Pago, Getnet, etc.)."},
    {"codigo": "hardware_pos", "nombre": "Hardware POS", "descripcion": "Impresoras, lectores de código de barras, balanzas."},
    {"codigo": "mensajeria", "nombre": "Mensajería", "descripcion": "Envío de comprobantes y notificaciones (WhatsApp, email, SMS)."},
    {"codigo": "tienda_ecommerce", "nombre": "Tienda / E-commerce", "descripcion": "Sincronización con plataformas de comercio electrónico."},
    {"codigo": "integracion_contable", "nombre": "Integración contable", "descripcion": "Exportación hacia sistemas contables externos."},
    {"codigo": "api_externa", "nombre": "API externa", "descripcion": "Exposición de API para terceros y sistemas de gestión."},
    {"codigo": "backups_sincronizacion", "nombre": "Backups y sincronización", "descripcion": "Copias automáticas y sincronización en la nube."},
]

CODIGOS_VALIDOS = {t["codigo"] for t in TIPOS_INTEGRACION}

# Dispositivos del punto de venta (docs Módulo 8 — Hardware POS)
DISPOSITIVOS_POS = [
    {"codigo": "impresora", "nombre": "Impresora de tickets", "descripcion": "Impresión de tickets, facturas, comprobantes y etiquetas."},
    {"codigo": "lector_barras", "nombre": "Lector de código de barras", "descripcion": "Captura de códigos en ventas, inventario y conteos."},
    {"codigo": "balanza", "nombre": "Balanza", "descripcion": "Pesaje automático, etiquetas y transferencia de peso al POS (fiambres, quesos, productos frescos)."},
]


def listar_dispositivos_pos() -> list[dict[str, Any]]:
    """Lista los dispositivos de hardware POS esperados por el sistema (docs Módulo 8 §5)."""
    return [dict(d) for d in DISPOSITIVOS_POS]

# Flujo alternativo cuando no hay impresora (docs Módulo 8 §6)
FLUJO_ALTERNATIVO_SIN_IMPRESORA = {
    "activo": True,
    "descripcion": "Flujo que se activa cuando el sistema detecta que no hay impresora disponible durante el cobro.",
    "pasos": [
        {"orden": 1, "accion": "solicitar_dni", "titulo": "Solicitar DNI del cliente", "descripcion": "Capturar DNI para identificar o crear el cliente."},
        {"orden": 2, "accion": "buscar_cliente", "titulo": "Buscar cliente existente", "descripcion": "Buscar por DNI en la base de personas/clientes."},
        {"orden": 3, "accion": "crear_cliente_si_no_existe", "titulo": "Crear cliente si no existe", "descripcion": "Si no hay coincidencia, registrar nuevo cliente con DNI y datos mínimos."},
        {"orden": 4, "accion": "solicitar_email", "titulo": "Solicitar email", "descripcion": "Obtener correo para envío del comprobante digital."},
        {"orden": 5, "accion": "enviar_comprobante_digital", "titulo": "Enviar comprobante digital", "descripcion": "Enviar comprobante por email (integración mensajería)."},
    ],
    "beneficios": [
        "Registrar clientes",
        "Capturar datos de contacto",
        "Enviar comprobantes digitales",
        "Mantener continuidad operativa",
    ],
}


def get_flujo_alternativo_sin_impresora() -> dict[str, Any]:
    """Devuelve la definición del flujo alternativo cuando no hay impresora (docs Módulo 8 §6)."""
    return dict(FLUJO_ALTERNATIVO_SIN_IMPRESORA)


def listar_tipos_integracion() -> list[dict[str, Any]]:
    """Lista los tipos de integración soportados por el sistema (docs Módulo 8 estructura)."""
    return [dict(t) for t in TIPOS_INTEGRACION]


def obtener_estado_integraciones(sesion: Session) -> dict[str, dict[str, Any]]:
    """
    Devuelve el estado actual de cada tipo de integración desde la BD.
    Si no existe registro para un tipo: activo=False, mensaje='No configurado'.
    """
    configs = {c.tipo_codigo: c for c in sesion.query(IntegracionConfig).all()}
    resultado = {}
    for t in TIPOS_INTEGRACION:
        codigo = t["codigo"]
        cfg = configs.get(codigo)
        if cfg is None:
            resultado[codigo] = {"activo": False, "mensaje": "No configurado"}
        else:
            resultado[codigo] = {
                "activo": cfg.activo,
                "mensaje": "Activo" if cfg.activo else "Desactivado",
            }
    return resultado


def configurar_activo(sesion: Session, tipo_codigo: str, activo: bool) -> IntegracionConfig | None:
    """
    Activa o desactiva un tipo de integración. Valida que tipo_codigo esté en el catálogo.
    Retorna el registro creado o actualizado, o None si tipo_codigo no es válido.
    """
    if tipo_codigo not in CODIGOS_VALIDOS:
        return None
    cfg = sesion.query(IntegracionConfig).filter(IntegracionConfig.tipo_codigo == tipo_codigo).first()
    if cfg is None:
        cfg = IntegracionConfig(tipo_codigo=tipo_codigo, activo=activo)
        sesion.add(cfg)
    else:
        cfg.activo = activo
    return cfg


def obtener_config(sesion: Session, tipo_codigo: str) -> dict[str, Any] | None:
    """
    Obtiene la configuración (credenciales/parámetros) de un tipo de integración.
    Retorna None si tipo_codigo no es válido; dict (puede ser {}) si no hay config guardada.
    """
    if tipo_codigo not in CODIGOS_VALIDOS:
        return None
    cfg = sesion.query(IntegracionConfig).filter(IntegracionConfig.tipo_codigo == tipo_codigo).first()
    if cfg is None or not cfg.config_json:
        return {}
    try:
        return json.loads(cfg.config_json)
    except (json.JSONDecodeError, TypeError):
        return {}


def guardar_config(sesion: Session, tipo_codigo: str, config: dict[str, Any]) -> dict[str, Any] | None:
    """
    Guarda la configuración JSON para un tipo de integración. Crea el registro si no existe.
    Retorna el dict guardado o None si tipo_codigo no es válido.
    """
    if tipo_codigo not in CODIGOS_VALIDOS:
        return None
    cfg = sesion.query(IntegracionConfig).filter(IntegracionConfig.tipo_codigo == tipo_codigo).first()
    if cfg is None:
        cfg = IntegracionConfig(tipo_codigo=tipo_codigo, activo=False, config_json=json.dumps(config))
        sesion.add(cfg)
    else:
        cfg.config_json = json.dumps(config)
    return config


def registrar_log(
    sesion: Session,
    tipo_codigo: str,
    exito: bool,
    mensaje: str,
    detalle: str | None = None,
) -> dict[str, Any] | None:
    """
    Registra un log de integración (éxito o fallo). Docs Módulo 8: Logs de integración.
    tipo_codigo debe ser uno del catálogo. Retorna el log creado como dict o None si tipo no válido.
    """
    if tipo_codigo not in CODIGOS_VALIDOS:
        return None
    msg = (mensaje or "")[:512]
    log = IntegracionLog(tipo_codigo=tipo_codigo, exito=exito, mensaje=msg, detalle=detalle)
    sesion.add(log)
    sesion.flush()
    sesion.refresh(log)
    return {
        "id": log.id,
        "tipo_codigo": log.tipo_codigo,
        "exito": log.exito,
        "mensaje": log.mensaje,
        "detalle": log.detalle,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def listar_logs(
    sesion: Session,
    tipo_codigo: str | None = None,
    limite: int = 100,
) -> list[dict[str, Any]]:
    """
    Lista los últimos logs de integración, más recientes primero.
    tipo_codigo opcional filtra por tipo. limite máximo 500.
    """
    q = sesion.query(IntegracionLog).order_by(IntegracionLog.created_at.desc())
    if tipo_codigo:
        q = q.filter(IntegracionLog.tipo_codigo == tipo_codigo)
    cap = min(max(1, limite), 500)
    logs = q.limit(cap).all()
    return [
        {
            "id": log.id,
            "tipo_codigo": log.tipo_codigo,
            "exito": log.exito,
            "mensaje": log.mensaje,
            "detalle": log.detalle,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


def resumen_integraciones(sesion: Session) -> dict[str, Any]:
    """
    Devuelve un resumen/health de las integraciones:
    - resumen global: total_tipos, activos, configurados
    - por_tipo: activo/configurado y último log (éxito/mensaje/fecha) por tipo.
    """
    configs = {c.tipo_codigo: c for c in sesion.query(IntegracionConfig).all()}
    # Último log por tipo (más reciente)
    logs_por_tipo: dict[str, IntegracionLog] = {}
    for log in sesion.query(IntegracionLog).order_by(IntegracionLog.created_at.desc()).all():
        if log.tipo_codigo not in logs_por_tipo:
            logs_por_tipo[log.tipo_codigo] = log

    total_tipos = len(TIPOS_INTEGRACION)
    activos = 0
    configurados = 0
    detalle: dict[str, Any] = {}

    for t in TIPOS_INTEGRACION:
        codigo = t["codigo"]
        cfg = configs.get(codigo)
        log = logs_por_tipo.get(codigo)
        esta_activo = bool(cfg and cfg.activo)
        tiene_config = cfg is not None
        if esta_activo:
            activos += 1
        if tiene_config:
            configurados += 1
        detalle[codigo] = {
            "activo": esta_activo,
            "configurado": tiene_config,
            "ultimo_log_exito": log.exito if log is not None else None,
            "ultimo_log_mensaje": log.mensaje if log is not None else None,
            "ultimo_log_fecha": log.created_at.isoformat() if log and log.created_at else None,
        }

    return {
        "resumen": {
            "total_tipos": total_tipos,
            "activos": activos,
            "configurados": configurados,
        },
        "por_tipo": detalle,
    }


def obtener_estado_dispositivo(sesion: Session, codigo: str) -> dict[str, Any] | None:
    """
    Devuelve el estado de disponibilidad de un dispositivo POS (docs Módulo 8 §5-6).

    La disponibilidad se determina por la presencia de configuración activa en hardware_pos:
    - si hardware_pos está activo y el código del dispositivo existe en la config JSON → disponible
    - en caso contrario → no disponible

    Retorna None si el código de dispositivo no está en el catálogo.
    """
    codigos_dispositivos = {d["codigo"] for d in DISPOSITIVOS_POS}
    if codigo not in codigos_dispositivos:
        return None

    cfg = sesion.query(IntegracionConfig).filter(
        IntegracionConfig.tipo_codigo == "hardware_pos"
    ).first()

    disponible = False
    motivo = "hardware_pos no configurado"

    if cfg is not None and cfg.activo:
        # Si hay config JSON, verificar si el dispositivo está marcado explícitamente
        if cfg.config_json:
            try:
                config_dict = json.loads(cfg.config_json)
                estado_dispositivo = config_dict.get(codigo)
                if estado_dispositivo is True:
                    disponible = True
                    motivo = "configurado y activo"
                elif estado_dispositivo is False:
                    disponible = False
                    motivo = "configurado como no disponible"
                else:
                    # No está en config: si hardware_pos está activo, asumimos disponible
                    disponible = True
                    motivo = "hardware_pos activo (sin config específica del dispositivo)"
            except (json.JSONDecodeError, TypeError):
                disponible = True
                motivo = "hardware_pos activo"
        else:
            disponible = True
            motivo = "hardware_pos activo (sin config JSON)"
    elif cfg is not None and not cfg.activo:
        motivo = "hardware_pos desactivado"

    dispositivo = next(d for d in DISPOSITIVOS_POS if d["codigo"] == codigo)
    return {
        "codigo": codigo,
        "nombre": dispositivo["nombre"],
        "disponible": disponible,
        "motivo": motivo,
    }


def ejecutar_flujo_alternativo_sin_impresora(
    sesion: Session,
    *,
    venta_id: int,
    documento_cliente: str,
    email: str,
    nombre_cliente: str | None = None,
    apellido_cliente: str | None = None,
) -> dict[str, Any]:
    """
    Ejecuta el flujo alternativo cuando no hay impresora disponible (docs Módulo 8 §6).

    Pasos:
    1. Verificar que la venta existe
    2. Buscar cliente por documento (en Persona)
    3. Si no existe → crear Persona + Cliente
    4. Registrar log de mensajería (simulación de envío de comprobante digital)
    5. Retornar resumen del flujo

    Retorna dict con resultado del flujo.
    """
    from backend.models.persona import Persona, Cliente
    from sqlalchemy import select as sa_select

    # 1. Verificar que la venta existe
    from backend.models.venta import Venta
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        return {
            "exito": False,
            "motivo": "venta_no_encontrada",
            "mensaje": f"Venta {venta_id} no encontrada",
            "venta_id": venta_id,
            "cliente_id": None,
            "persona_id": None,
            "email": email,
        }

    # 2. Buscar cliente por documento
    doc_norm = (documento_cliente or "").strip()
    persona = sesion.scalars(
        sa_select(Persona).where(Persona.documento == doc_norm)
    ).first()

    cliente_id = None
    persona_id = None
    accion_cliente = "encontrado"

    if persona is None:
        # 3a. Crear persona + cliente
        nombre = (nombre_cliente or "Cliente").strip()
        apellido = (apellido_cliente or "").strip() or "Sin apellido"
        persona = Persona(
            nombre=nombre,
            apellido=apellido,
            documento=doc_norm,
            activo=True,
        )
        sesion.add(persona)
        sesion.flush()
        sesion.refresh(persona)
        cliente = Cliente(persona_id=persona.id, estado="ACTIVO")
        sesion.add(cliente)
        sesion.flush()
        sesion.refresh(cliente)
        cliente_id = cliente.id
        persona_id = persona.id
        accion_cliente = "creado"
    else:
        persona_id = persona.id
        # Buscar el cliente asociado
        cliente = sesion.scalars(
            sa_select(Cliente).where(Cliente.persona_id == persona.id)
        ).first()
        if cliente is None:
            cliente = Cliente(persona_id=persona.id, estado="ACTIVO")
            sesion.add(cliente)
            sesion.flush()
            sesion.refresh(cliente)
            accion_cliente = "cliente_creado_para_persona_existente"
        cliente_id = cliente.id

    # 4. Registrar log en mensajería (simulación de envío)
    mensaje_log = f"Comprobante digital enviado a {email} para venta {venta_id}"
    registrar_log(sesion, "mensajeria", True, mensaje_log, detalle=f"venta_id={venta_id}")

    return {
        "exito": True,
        "motivo": "comprobante_enviado",
        "mensaje": mensaje_log,
        "venta_id": venta_id,
        "cliente_id": cliente_id,
        "persona_id": persona_id,
        "email": email,
        "accion_cliente": accion_cliente,
    }


def enviar_comprobante_digital(
    sesion: Session,
    *,
    venta_id: int,
    email: str,
    tipo_comprobante: str = "ticket",
) -> dict[str, Any]:
    """
    Simula el envío de un comprobante digital por email (docs Módulo 8 §8 Mensajería).

    Verifica que la integración de mensajería esté activa (si está configurada).
    Registra un log de mensajería con el resultado.
    Retorna éxito o fallo con motivo.
    """
    from backend.models.venta import Venta

    # Verificar venta
    venta = sesion.get(Venta, venta_id)
    if venta is None:
        registrar_log(
            sesion, "mensajeria", False,
            f"Error al enviar comprobante: venta {venta_id} no encontrada",
            detalle=f"email={email}",
        )
        return {
            "exito": False,
            "motivo": "venta_no_encontrada",
            "venta_id": venta_id,
            "email": email,
        }

    # Verificar si mensajería está configurada/activa
    cfg = sesion.query(IntegracionConfig).filter(
        IntegracionConfig.tipo_codigo == "mensajeria"
    ).first()
    mensajeria_activa = cfg is not None and cfg.activo

    mensaje = f"Comprobante {tipo_comprobante} enviado a {email} (venta {venta_id})"
    if not mensajeria_activa:
        mensaje = f"[SIM] {mensaje}"

    registrar_log(
        sesion, "mensajeria", True, mensaje,
        detalle=f"tipo={tipo_comprobante},venta_id={venta_id}",
    )
    return {
        "exito": True,
        "motivo": "enviado",
        "venta_id": venta_id,
        "email": email,
        "tipo_comprobante": tipo_comprobante,
        "mensajeria_activa": mensajeria_activa,
        "mensaje": mensaje,
    }


def estadisticas_logs(
    sesion: Session,
    tipo_codigo: str | None = None,
) -> dict[str, Any]:
    """
    Devuelve estadísticas de éxito/fallo de logs de integración por tipo.
    Si tipo_codigo se especifica, filtra solo ese tipo.
    """
    q_base = select(
        IntegracionLog.tipo_codigo,
        func.count(IntegracionLog.id).label("total"),
        func.sum(
            func.cast(IntegracionLog.exito, Integer)
        ).label("exitosos"),
    ).group_by(IntegracionLog.tipo_codigo)

    if tipo_codigo:
        q_base = q_base.where(IntegracionLog.tipo_codigo == tipo_codigo)

    rows = sesion.execute(q_base).all()
    resultado: dict[str, Any] = {}
    for row in rows:
        total = int(row.total or 0)
        exitosos = int(row.exitosos or 0)
        fallos = total - exitosos
        resultado[row.tipo_codigo] = {
            "total": total,
            "exitosos": exitosos,
            "fallos": fallos,
            "tasa_exito_pct": round(exitosos / total * 100, 1) if total > 0 else 0.0,
        }
    return resultado


def probar_conexion(sesion: Session, tipo_codigo: str) -> dict[str, Any] | None:
    """
    Prueba de conexión simulada para una integración (docs Módulo 8).
    - Si el tipo no existe en el catálogo: None
    - Si el tipo existe pero no hay configuración: registra log de fallo y devuelve exito=False
    - Si existe configuración: registra log de éxito y devuelve exito=True
    """
    if tipo_codigo not in CODIGOS_VALIDOS:
        return None

    cfg = sesion.query(IntegracionConfig).filter(IntegracionConfig.tipo_codigo == tipo_codigo).first()
    if cfg is None or not cfg.config_json:
        registrar_log(
            sesion,
            tipo_codigo,
            False,
            "Sin configuración para la integración",
        )
        return {"tipo_codigo": tipo_codigo, "exito": False, "motivo": "sin_configuracion"}

    # En esta iteración la conexión es simulada. Se valida que exista config_json.
    registrar_log(
        sesion,
        tipo_codigo,
        True,
        "Prueba de conexión exitosa",
    )
    return {"tipo_codigo": tipo_codigo, "exito": True, "motivo": "ok", "configurado": True}


# --- Integración contable (docs Módulo 8 §10) ---


def exportacion_contable(
    sesion: Session,
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> dict[str, Any]:
    """
    Genera un paquete de exportación contable con:
    - ventas del período (id, total, estado, fecha)
    - movimientos de caja del período (tipo, monto, concepto)
    Para ser consumido por sistemas contables externos (Alegra, Contabilium, etc.).
    Docs Módulo 8 §10.
    """
    from backend.models.venta import Venta, EstadoVenta
    from backend.models.caja import MovimientoCaja
    from sqlalchemy import cast as sa_cast, Date as SADate

    # Ventas
    q_ventas = select(Venta)
    if fecha_desde:
        q_ventas = q_ventas.where(
            sa_cast(Venta.creado_en, SADate) >= fecha_desde
        )
    if fecha_hasta:
        q_ventas = q_ventas.where(
            sa_cast(Venta.creado_en, SADate) <= fecha_hasta
        )
    ventas = sesion.scalars(q_ventas.order_by(Venta.creado_en)).all()

    ventas_export = []
    total_ventas = 0.0
    for v in ventas:
        monto = float(v.total or 0)
        ventas_export.append({
            "id": v.id,
            "fecha": v.creado_en.date().isoformat() if v.creado_en else None,
            "total": monto,
            "estado": v.estado.value if hasattr(v.estado, "value") else str(v.estado),
        })
        if v.estado != EstadoVenta.CANCELADA:
            total_ventas += monto

    # Movimientos de caja
    q_mov = select(MovimientoCaja)
    if fecha_desde:
        q_mov = q_mov.where(
            sa_cast(MovimientoCaja.fecha, SADate) >= fecha_desde
        )
    if fecha_hasta:
        q_mov = q_mov.where(
            sa_cast(MovimientoCaja.fecha, SADate) <= fecha_hasta
        )
    movs = sesion.scalars(q_mov.order_by(MovimientoCaja.fecha)).all()

    movimientos_export = []
    total_ingresos_caja = 0.0
    total_egresos_caja = 0.0
    for m in movs:
        monto = float(m.monto or 0)
        tipo_str = m.tipo.value if hasattr(m.tipo, "value") else str(m.tipo)
        movimientos_export.append({
            "id": m.id,
            "fecha": m.fecha.date().isoformat() if m.fecha else None,
            "tipo": tipo_str,
            "monto": monto,
            "referencia": m.referencia,
        })
        if tipo_str in ("INGRESO", "VENTA"):
            total_ingresos_caja += monto
        else:
            total_egresos_caja += monto

    registrar_log(
        sesion,
        "integracion_contable",
        True,
        f"Exportacion contable generada: {len(ventas_export)} ventas, {len(movimientos_export)} movimientos de caja",
    )

    return {
        "periodo": {
            "desde": fecha_desde.isoformat() if fecha_desde else None,
            "hasta": fecha_hasta.isoformat() if fecha_hasta else None,
        },
        "ventas": ventas_export,
        "resumen_ventas": {
            "cantidad": len(ventas_export),
            "total_facturado": round(total_ventas, 2),
        },
        "movimientos_caja": movimientos_export,
        "resumen_caja": {
            "cantidad": len(movimientos_export),
            "total_ingresos": round(total_ingresos_caja, 2),
            "total_egresos": round(total_egresos_caja, 2),
            "resultado_neto": round(total_ingresos_caja - total_egresos_caja, 2),
        },
        "exportado_en": datetime.now(tz=timezone.utc).isoformat(),
    }


# --- API Externa (docs Módulo 8 §11) ---


def resumen_api_externa(sesion: Session) -> dict[str, Any]:
    """
    Devuelve un resumen de datos del POS para consumo de sistemas externos (apps, e-commerce, etc.).
    Expone: total de productos activos, stock consolidado, resumen de ventas del día, tipos de pago.
    Docs Módulo 8 §11.
    """
    from backend.models.producto import Producto
    from backend.models.inventario import Stock
    from backend.models.venta import Venta, EstadoVenta
    from sqlalchemy import cast as sa_cast, Date as SADate
    from datetime import date as date_type

    hoy = date_type.today()

    # Productos activos
    total_productos = sesion.scalar(
        select(func.count(Producto.id)).where(Producto.activo.is_(True))
    ) or 0
    stock_total = float(sesion.scalar(select(func.sum(Stock.cantidad))) or 0)

    # Productos activos sin stock
    prods_activos = sesion.execute(
        select(Producto.id).where(Producto.activo.is_(True))
    ).scalars().all()
    stocks_por_producto: dict[int, float] = {}
    for row in sesion.execute(
        select(Stock.producto_id, func.sum(Stock.cantidad).label("total"))
        .group_by(Stock.producto_id)
    ).all():
        stocks_por_producto[int(row.producto_id)] = float(row.total or 0)
    sin_stock = sum(
        1 for pid in prods_activos if stocks_por_producto.get(pid, 0) <= 0
    )

    # Ventas de hoy
    ventas_hoy = sesion.scalars(
        select(Venta).where(
            sa_cast(Venta.creado_en, SADate) == hoy,
            Venta.estado != EstadoVenta.CANCELADA,
        )
    ).all()
    total_hoy = sum(float(v.total or 0) for v in ventas_hoy)

    return {
        "inventario": {
            "total_productos_activos": total_productos,
            "stock_total_unidades": stock_total,
            "productos_sin_stock": sin_stock,
        },
        "ventas_hoy": {
            "cantidad": len(ventas_hoy),
            "total": round(total_hoy, 2),
            "fecha": hoy.isoformat(),
        },
        "sistema": {
            "version": "1.0",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
    }


def datos_producto_externo(sesion: Session, producto_id: int) -> dict[str, Any] | None:
    """
    Devuelve datos de un producto para consumo de API externa (apps, e-commerce).
    Retorna None si el producto no existe. Docs Módulo 8 §11.
    """
    from backend.models.producto import Producto
    from backend.models.inventario import Stock

    prod = sesion.get(Producto, producto_id)
    if prod is None:
        return None
    stock_total = float(
        sesion.scalar(
            select(func.sum(Stock.cantidad)).where(Stock.producto_id == producto_id)
        ) or 0
    )
    return {
        "id": prod.id,
        "sku": prod.sku,
        "nombre": prod.nombre,
        "precio": float(prod.precio_venta),
        "stock_actual": stock_total,
        "activo": prod.activo,
        "pesable": prod.pesable,
        "plu": prod.plu,
    }


# --- Backups y sincronización (docs Módulo 8 §12) ---

_ultimo_backup: dict[str, Any] = {
    "ultimo_backup": None,
    "estado": "sin_backup",
    "registros": [],
}


def obtener_estado_backup() -> dict[str, Any]:
    """
    Devuelve el estado actual del sistema de backups (último backup, estado, historial).
    Docs Módulo 8 §12.
    """
    return {
        "ultimo_backup": _ultimo_backup["ultimo_backup"],
        "estado": _ultimo_backup["estado"],
        "total_backups": len(_ultimo_backup["registros"]),
        "historial": list(_ultimo_backup["registros"][-10:]),
    }


def ejecutar_backup(sesion: Session, *, frecuencia: str = "manual") -> dict[str, Any]:
    """
    Ejecuta un backup del sistema (simulado). Registra log y actualiza estado.
    frecuencia: 'manual', 'hourly', 'daily', 'weekly'.
    Docs Módulo 8 §12.
    """
    frecuencias_validas = {"manual", "hourly", "daily", "weekly"}
    if frecuencia not in frecuencias_validas:
        raise ValueError(f"Frecuencia inválida. Opciones: {sorted(frecuencias_validas)}")

    ahora = datetime.now(tz=timezone.utc)
    entrada = {
        "timestamp": ahora.isoformat(),
        "frecuencia": frecuencia,
        "estado": "exitoso",
    }
    _ultimo_backup["ultimo_backup"] = ahora.isoformat()
    _ultimo_backup["estado"] = "ok"
    _ultimo_backup["registros"].append(entrada)

    registrar_log(
        sesion,
        "backups_sincronizacion",
        True,
        f"Backup {frecuencia} ejecutado exitosamente",
        detalle=f"timestamp={ahora.isoformat()}",
    )

    return {
        "exito": True,
        "timestamp": ahora.isoformat(),
        "frecuencia": frecuencia,
        "mensaje": f"Backup {frecuencia} ejecutado correctamente",
    }


# --- Datos fiscales de venta (docs Módulo 8 §4) ---


def datos_fiscales_venta(sesion: Session, venta_id: int) -> dict[str, Any] | None:
    """
    Devuelve los datos fiscales de una venta para emisión de comprobante electrónico (AFIP/ARCA).
    Retorna None si la venta no existe.
    Incluye: items, totales, cliente si existe, y configuración fiscal del sistema.
    Docs Módulo 8 §4.
    """
    from backend.models.venta import Venta, ItemVenta
    from backend.models.producto import Producto
    from backend.services.configuracion import get_configuracion_integraciones

    venta = sesion.get(Venta, venta_id)
    if venta is None:
        return None

    items_venta = sesion.scalars(
        select(ItemVenta).where(ItemVenta.venta_id == venta_id)
    ).all()

    items_fiscal = []
    for item in items_venta:
        prod = sesion.get(Producto, item.producto_id) if item.producto_id else None
        items_fiscal.append({
            "descripcion": prod.nombre if prod else f"Producto {item.producto_id}",
            "cantidad": float(item.cantidad),
            "precio_unitario": float(item.precio_unitario),
            "subtotal": float(item.subtotal),
        })

    cfg_integraciones = get_configuracion_integraciones(sesion)
    cred_fiscales = cfg_integraciones.get("credenciales_fiscales", {})

    estado_str = venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado)

    return {
        "venta_id": venta.id,
        "fecha": venta.creado_en.date().isoformat() if venta.creado_en else None,
        "estado": estado_str,
        "total": float(venta.total or 0),
        "items": items_fiscal,
        "emisor": {
            "cuit": cred_fiscales.get("cuit", ""),
            "punto_venta": cred_fiscales.get("punto_venta", 1),
            "modo_produccion": cred_fiscales.get("modo_produccion", False),
        },
        "tipo_comprobante": "ticket",
    }


# --- Reconciliación de pagos de pasarela (docs Módulo 8 §7) ---


def reconciliar_pagos_pasarela(
    sesion: Session,
    *,
    tipo_pasarela: str,
    pagos_externos: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Reconcilia pagos externos de una pasarela (MercadoPago, Getnet, etc.) contra ventas del sistema.
    pagos_externos: lista de dicts con al menos {referencia_externa, monto, estado}
    Docs Módulo 8 §7.
    """
    pasarelas_validas = {"mercadopago", "getnet", "posnet", "stripe"}
    if tipo_pasarela not in pasarelas_validas:
        raise ValueError(f"Pasarela inválida. Opciones: {sorted(pasarelas_validas)}")

    from backend.models.venta import Venta
    from sqlalchemy import cast as sa_cast, Date as SADate

    reconciliados = []
    sin_coincidencia = []

    for pago in pagos_externos:
        referencia = pago.get("referencia_externa") or pago.get("id") or ""
        monto = float(pago.get("monto", 0))
        estado_pago = pago.get("estado", "desconocido")

        venta_match = sesion.scalars(
            select(Venta).where(Venta.total == monto).limit(1)
        ).first()

        if venta_match:
            reconciliados.append({
                "referencia_externa": referencia,
                "monto": monto,
                "estado_pasarela": estado_pago,
                "venta_id": venta_match.id,
                "estado_venta": venta_match.estado.value if hasattr(venta_match.estado, "value") else str(venta_match.estado),
                "resultado": "conciliado",
            })
        else:
            sin_coincidencia.append({
                "referencia_externa": referencia,
                "monto": monto,
                "estado_pasarela": estado_pago,
                "resultado": "sin_coincidencia",
            })

    registrar_log(
        sesion,
        "pasarelas_pago",
        True,
        f"Reconciliacion {tipo_pasarela}: {len(reconciliados)} conciliados, {len(sin_coincidencia)} sin coincidencia",
        detalle=f"pasarela={tipo_pasarela},total={len(pagos_externos)}",
    )

    return {
        "tipo_pasarela": tipo_pasarela,
        "total_pagos": len(pagos_externos),
        "reconciliados": reconciliados,
        "sin_coincidencia": sin_coincidencia,
        "resumen": {
            "conciliados": len(reconciliados),
            "sin_coincidencia": len(sin_coincidencia),
            "tasa_conciliacion_pct": round(len(reconciliados) / len(pagos_externos) * 100, 1) if pagos_externos else 0.0,
        },
    }
