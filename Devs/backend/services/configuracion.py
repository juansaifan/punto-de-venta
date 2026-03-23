# Servicios del dominio Configuración (usuarios, roles, medios de pago, parámetros sistema)
import json
from decimal import Decimal
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.usuario import Usuario
from backend.models.rol import Rol
from backend.models.configuracion import EMPRESA_ID, Empresa, MedioPago, ParametroSistema, Permiso, Sucursal


def obtener_usuario_por_id(sesion: Session, usuario_id: int) -> Optional[Usuario]:
    """Obtiene un usuario por ID."""
    return sesion.get(Usuario, usuario_id)


def obtener_rol_por_id(sesion: Session, rol_id: int) -> Optional[Rol]:
    """Obtiene un rol por ID."""
    return sesion.get(Rol, rol_id)


def listar_usuarios(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Usuario]:
    """Lista usuarios."""
    stmt = select(Usuario).order_by(Usuario.id).limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def listar_roles(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Rol]:
    """Lista roles."""
    stmt = select(Rol).order_by(Rol.id).limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def actualizar_usuario_activo(
    sesion: Session,
    usuario_id: int,
    *,
    activo: bool,
) -> Usuario:
    """Actualiza el estado activo de un usuario. Lanza ValueError si no existe."""
    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("Usuario no encontrado")
    usuario.activo = activo
    sesion.add(usuario)
    sesion.flush()
    sesion.refresh(usuario)
    return usuario


def asignar_rol_a_usuario(
    sesion: Session,
    usuario_id: int,
    rol_id: int | None,
) -> Usuario:
    """Asigna o desasigna un rol a un usuario. Si rol_id es None, quita el rol. Lanza ValueError si usuario o rol no existen."""
    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("Usuario no encontrado")
    if rol_id is not None:
        rol = sesion.get(Rol, rol_id)
        if rol is None:
            raise ValueError("Rol no encontrado")
    usuario.rol_id = rol_id
    sesion.add(usuario)
    sesion.flush()
    sesion.refresh(usuario)
    return usuario


def crear_usuario(
    sesion: Session,
    *,
    nombre: str,
    persona_id: int | None = None,
) -> Usuario:
    """Crea un usuario básico activo."""
    nombre_norm = nombre.strip()
    if not nombre_norm:
        raise ValueError("El nombre de usuario no puede estar vacío")
    usuario = Usuario(nombre=nombre_norm, persona_id=persona_id)
    sesion.add(usuario)
    sesion.flush()
    sesion.refresh(usuario)
    return usuario


def crear_rol(
    sesion: Session,
    *,
    codigo: str,
    nombre: str,
) -> Rol:
    """Crea un rol operativo."""
    codigo_norm = codigo.strip()
    nombre_norm = nombre.strip()
    if not codigo_norm:
        raise ValueError("El código de rol no puede estar vacío")
    if not nombre_norm:
        raise ValueError("El nombre de rol no puede estar vacío")
    rol = Rol(codigo=codigo_norm, nombre=nombre_norm)
    sesion.add(rol)
    sesion.flush()
    sesion.refresh(rol)
    return rol


def actualizar_rol(
    sesion: Session,
    rol_id: int,
    *,
    codigo: str | None = None,
    nombre: str | None = None,
) -> Rol:
    """Actualiza parcialmente un rol (código y/o nombre). Al menos un campo debe enviarse. Lanza ValueError si no existe o código duplicado."""
    rol = sesion.get(Rol, rol_id)
    if rol is None:
        raise ValueError("Rol no encontrado")
    if codigo is None and nombre is None:
        raise ValueError("Se debe enviar al menos uno: codigo o nombre")
    if codigo is not None:
        codigo_norm = codigo.strip()
        if not codigo_norm:
            raise ValueError("El código de rol no puede estar vacío")
        # Unicidad: otro rol con mismo código (excluyendo el actual)
        existente = (
            sesion.execute(select(Rol).where(Rol.codigo == codigo_norm, Rol.id != rol_id))
            .scalars()
            .first()
        )
        if existente is not None:
            raise ValueError("Ya existe un rol con ese código")
        rol.codigo = codigo_norm
    if nombre is not None:
        nombre_norm = nombre.strip()
        if not nombre_norm:
            raise ValueError("El nombre de rol no puede estar vacío")
        rol.nombre = nombre_norm
    sesion.add(rol)
    sesion.flush()
    sesion.refresh(rol)
    return rol


# --- Permisos (ROADMAP Fase 7; docs Módulo 9 §11) ---


def listar_permisos(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Permiso]:
    """Lista permisos del sistema."""
    stmt = select(Permiso).order_by(Permiso.codigo).limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def obtener_permiso_por_id(sesion: Session, permiso_id: int) -> Optional[Permiso]:
    """Obtiene un permiso por ID."""
    return sesion.get(Permiso, permiso_id)


def obtener_permisos_del_rol(sesion: Session, rol_id: int) -> list[Permiso]:
    """Devuelve la lista de permisos asignados a un rol. Rol debe existir."""
    rol = sesion.get(Rol, rol_id)
    if rol is None:
        raise ValueError("Rol no encontrado")
    return list(rol.permisos)


def asignar_permisos_a_rol(
    sesion: Session,
    rol_id: int,
    permiso_ids: list[int],
) -> Rol:
    """Asigna exactamente la lista de permisos al rol (reemplaza los anteriores). Valida que rol y todos los permisos existan."""
    rol = sesion.get(Rol, rol_id)
    if rol is None:
        raise ValueError("Rol no encontrado")
    permisos_nuevos: list[Permiso] = []
    for pid in permiso_ids:
        p = sesion.get(Permiso, pid)
        if p is None:
            raise ValueError(f"Permiso con id {pid} no encontrado")
        permisos_nuevos.append(p)
    rol.permisos = permisos_nuevos
    sesion.add(rol)
    sesion.flush()
    sesion.refresh(rol, ["permisos"])
    return rol


def crear_permiso(
    sesion: Session,
    *,
    codigo: str,
    nombre: str,
    descripcion: Optional[str] = None,
) -> Permiso:
    """Crea un permiso. codigo debe ser único."""
    codigo_norm = codigo.strip()
    nombre_norm = nombre.strip()
    if not codigo_norm:
        raise ValueError("El código de permiso no puede estar vacío")
    if not nombre_norm:
        raise ValueError("El nombre de permiso no puede estar vacío")
    if sesion.execute(select(Permiso).where(Permiso.codigo == codigo_norm)).scalars().first():
        raise ValueError("Ya existe un permiso con ese código")
    perm = Permiso(
        codigo=codigo_norm,
        nombre=nombre_norm,
        descripcion=descripcion.strip() if descripcion else None,
    )
    sesion.add(perm)
    sesion.flush()
    sesion.refresh(perm)
    return perm


# --- Medios de pago (docs Módulo 9 §6) ---


def listar_medios_pago(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
    solo_activos: bool = False,
) -> Sequence[MedioPago]:
    """Lista medios de pago. Si solo_activos=True, filtra por activo=True."""
    stmt = select(MedioPago).order_by(MedioPago.id)
    if solo_activos:
        stmt = stmt.where(MedioPago.activo.is_(True))
    stmt = stmt.limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def obtener_medio_pago_por_id(sesion: Session, medio_pago_id: int) -> Optional[MedioPago]:
    """Obtiene un medio de pago por ID."""
    return sesion.get(MedioPago, medio_pago_id)


def obtener_medio_pago_por_codigo(sesion: Session, codigo: str) -> Optional[MedioPago]:
    """Obtiene un medio de pago por código (ej. EFECTIVO)."""
    stmt = select(MedioPago).where(MedioPago.codigo == codigo.strip())
    return sesion.execute(stmt).scalars().first()


def crear_medio_pago(
    sesion: Session,
    *,
    codigo: str,
    nombre: str,
    activo: bool = True,
    comision: Decimal | float = 0,
    dias_acreditacion: int = 0,
) -> MedioPago:
    """Crea un medio de pago. codigo debe ser único."""
    codigo_norm = codigo.strip()[:32]
    nombre_norm = nombre.strip()
    if not codigo_norm:
        raise ValueError("El código del medio de pago no puede estar vacío")
    if not nombre_norm:
        raise ValueError("El nombre del medio de pago no puede estar vacío")
    if sesion.execute(select(MedioPago).where(MedioPago.codigo == codigo_norm)).scalars().first():
        raise ValueError("Ya existe un medio de pago con ese código")
    mp = MedioPago(
        codigo=codigo_norm,
        nombre=nombre_norm,
        activo=activo,
        comision=Decimal(str(comision)),
        dias_acreditacion=max(0, int(dias_acreditacion)),
    )
    sesion.add(mp)
    sesion.flush()
    sesion.refresh(mp)
    return mp


def actualizar_medio_pago(
    sesion: Session,
    medio_pago_id: int,
    *,
    nombre: str | None = None,
    activo: bool | None = None,
    comision: Decimal | float | None = None,
    dias_acreditacion: int | None = None,
) -> MedioPago:
    """Actualiza parcialmente un medio de pago. Al menos un campo debe enviarse."""
    mp = sesion.get(MedioPago, medio_pago_id)
    if mp is None:
        raise ValueError("Medio de pago no encontrado")
    if nombre is None and activo is None and comision is None and dias_acreditacion is None:
        raise ValueError("Se debe enviar al menos un campo a actualizar")
    if nombre is not None:
        nombre_norm = nombre.strip()
        if not nombre_norm:
            raise ValueError("El nombre no puede estar vacío")
        mp.nombre = nombre_norm
    if activo is not None:
        mp.activo = bool(activo)
    if comision is not None:
        mp.comision = Decimal(str(comision))
    if dias_acreditacion is not None:
        mp.dias_acreditacion = max(0, int(dias_acreditacion))
    sesion.add(mp)
    sesion.flush()
    sesion.refresh(mp)
    return mp


# --- Empresa (datos del negocio, docs Módulo 9 §3) ---


def obtener_empresa(sesion: Session) -> Optional[Empresa]:
    """Obtiene los datos de la empresa (registro singleton id=EMPRESA_ID)."""
    return sesion.get(Empresa, EMPRESA_ID)


def actualizar_empresa(
    sesion: Session,
    *,
    nombre: str | None = None,
    razon_social: str | None = None,
    cuit: str | None = None,
    condicion_fiscal: str | None = None,
    direccion: str | None = None,
    telefono: str | None = None,
    email: str | None = None,
    logo_url: str | None = None,
) -> Empresa:
    """
    Crea o actualiza los datos de la empresa (singleton). Al menos nombre debe enviarse en la primera creación.
    Los campos omitidos (None) no se actualizan; para borrar un campo enviar cadena vacía donde aplique.
    """
    emp = sesion.get(Empresa, EMPRESA_ID)
    if emp is None:
        nombre_val = (nombre or "").strip() if nombre is not None else ""
        emp = Empresa(
            id=EMPRESA_ID,
            nombre=nombre_val,
            razon_social=razon_social.strip() if razon_social else None,
            cuit=cuit.strip() if cuit else None,
            condicion_fiscal=condicion_fiscal.strip() if condicion_fiscal else None,
            direccion=direccion.strip() if direccion else None,
            telefono=telefono.strip() if telefono else None,
            email=email.strip() if email else None,
            logo_url=logo_url.strip() if logo_url else None,
        )
        sesion.add(emp)
        sesion.flush()
        sesion.refresh(emp)
        return emp

    if nombre is not None:
        emp.nombre = nombre.strip() if nombre else ""
    if razon_social is not None:
        emp.razon_social = razon_social.strip() or None
    if cuit is not None:
        emp.cuit = cuit.strip() or None
    if condicion_fiscal is not None:
        emp.condicion_fiscal = condicion_fiscal.strip() or None
    if direccion is not None:
        emp.direccion = direccion.strip() or None
    if telefono is not None:
        emp.telefono = telefono.strip() or None
    if email is not None:
        emp.email = email.strip() or None
    if logo_url is not None:
        emp.logo_url = logo_url.strip() or None

    sesion.add(emp)
    sesion.flush()
    sesion.refresh(emp)
    return emp


# --- Sucursales (docs Módulo 9 §4) ---


def listar_sucursales(
    sesion: Session,
    *,
    limite: int = 100,
    offset: int = 0,
    solo_activas: bool = False,
) -> Sequence[Sucursal]:
    """Lista sucursales. Si solo_activas=True, filtra por activo=True."""
    stmt = select(Sucursal).order_by(Sucursal.id)
    if solo_activas:
        stmt = stmt.where(Sucursal.activo.is_(True))
    stmt = stmt.limit(limite).offset(offset)
    return sesion.scalars(stmt).all()


def obtener_sucursal_por_id(sesion: Session, sucursal_id: int) -> Optional[Sucursal]:
    """Obtiene una sucursal por ID."""
    return sesion.get(Sucursal, sucursal_id)


def crear_sucursal(
    sesion: Session,
    *,
    nombre: str,
    direccion: Optional[str] = None,
    telefono: Optional[str] = None,
    activo: bool = True,
) -> Sucursal:
    """Crea una sucursal."""
    nombre_norm = nombre.strip()
    if not nombre_norm:
        raise ValueError("El nombre de sucursal no puede estar vacío")
    suc = Sucursal(
        nombre=nombre_norm,
        direccion=direccion.strip() if direccion else None,
        telefono=telefono.strip() if telefono else None,
        activo=activo,
    )
    sesion.add(suc)
    sesion.flush()
    sesion.refresh(suc)
    return suc


def actualizar_sucursal(
    sesion: Session,
    sucursal_id: int,
    *,
    nombre: Optional[str] = None,
    direccion: Optional[str] = None,
    telefono: Optional[str] = None,
    activo: Optional[bool] = None,
) -> Sucursal:
    """Actualiza parcialmente una sucursal. Al menos un campo debe enviarse."""
    suc = sesion.get(Sucursal, sucursal_id)
    if suc is None:
        raise ValueError("Sucursal no encontrada")
    if nombre is None and direccion is None and telefono is None and activo is None:
        raise ValueError("Se debe enviar al menos un campo a actualizar")
    if nombre is not None:
        nombre_norm = nombre.strip()
        if not nombre_norm:
            raise ValueError("El nombre no puede estar vacío")
        suc.nombre = nombre_norm
    if direccion is not None:
        suc.direccion = direccion.strip() or None
    if telefono is not None:
        suc.telefono = telefono.strip() or None
    if activo is not None:
        suc.activo = bool(activo)
    sesion.add(suc)
    sesion.flush()
    sesion.refresh(suc)
    return suc


def get_parametro(sesion: Session, clave: str) -> dict[str, Any]:
    """
    Obtiene el valor JSON de un parámetro de sistema (facturacion, caja, etc.).
    Si no existe o valor_json es vacío, devuelve {}.
    """
    stmt = select(ParametroSistema).where(ParametroSistema.clave == clave).limit(1)
    row = sesion.execute(stmt).scalars().first()
    if row is None or not row.valor_json:
        return {}
    try:
        return json.loads(row.valor_json)
    except (json.JSONDecodeError, TypeError):
        return {}


def set_parametro(sesion: Session, clave: str, valor: dict[str, Any]) -> dict[str, Any]:
    """
    Guarda el valor JSON de un parámetro de sistema. Crea el registro si no existe.
    clave debe ser no vacía. valor debe ser un dict (se serializa a JSON).
    """
    clave_norm = (clave or "").strip()
    if not clave_norm:
        raise ValueError("La clave del parámetro no puede estar vacía")
    stmt = select(ParametroSistema).where(ParametroSistema.clave == clave_norm).limit(1)
    param = sesion.execute(stmt).scalars().first()
    valor_str = json.dumps(valor) if isinstance(valor, dict) else "{}"
    if param is None:
        param = ParametroSistema(clave=clave_norm, valor_json=valor_str)
        sesion.add(param)
    else:
        param.valor_json = valor_str
    sesion.flush()
    sesion.refresh(param)
    return json.loads(param.valor_json) if param.valor_json else {}


def listar_claves_parametros(sesion: Session) -> list[str]:
    """Lista todas las claves de parámetros de sistema existentes, ordenadas alfabéticamente."""
    stmt = select(ParametroSistema.clave).order_by(ParametroSistema.clave)
    return list(sesion.execute(stmt).scalars().all())


# --- Configuración Caja (docs Módulo 9 §7) ---

DEFAULT_CAJA: dict[str, Any] = {
    "monto_minimo_apertura": 0,
    "obligar_arqueo": True,
    "permitir_cierre_con_diferencia": False,
    "requerir_autorizacion_supervisor_cierre": True,
}


def get_configuracion_caja(sesion: Session) -> dict[str, Any]:
    """
    Obtiene la configuración de caja (monto mínimo apertura, arqueo, diferencias, permisos).
    Si no existe, devuelve valores por defecto.
    """
    data = get_parametro(sesion, "caja")
    if not data:
        return dict(DEFAULT_CAJA)
    out = dict(DEFAULT_CAJA)
    for k in DEFAULT_CAJA:
        if k in data:
            out[k] = data[k]
    return out


def set_configuracion_caja(sesion: Session, valor: dict[str, Any]) -> dict[str, Any]:
    """Guarda la configuración de caja. Mezcla con defaults para claves no enviadas."""
    actual = get_configuracion_caja(sesion)
    for k, v in valor.items():
        if k in DEFAULT_CAJA:
            actual[k] = v
    return set_parametro(sesion, "caja", actual)


# --- Configuración Sistema (docs Módulo 9 §11) ---

DEFAULT_SISTEMA: dict[str, Any] = {
    "zona_horaria": "America/Argentina/Buenos_Aires",
    "idioma": "es",
    "formato_fecha": "DD/MM/YYYY",
    "formato_moneda": "ARS",
    "tiempo_sesion_minutos": 60,
    "registro_auditoria": True,
}


def get_configuracion_sistema(sesion: Session) -> dict[str, Any]:
    """
    Obtiene la configuración de sistema (zona horaria, idioma, formato fecha/moneda, seguridad).
    Si no existe, devuelve valores por defecto.
    """
    data = get_parametro(sesion, "sistema")
    if not data:
        return dict(DEFAULT_SISTEMA)
    out = dict(DEFAULT_SISTEMA)
    for k in DEFAULT_SISTEMA:
        if k in data:
            out[k] = data[k]
    return out


def set_configuracion_sistema(sesion: Session, valor: dict[str, Any]) -> dict[str, Any]:
    """Guarda la configuración de sistema. Mezcla con defaults para claves no enviadas."""
    actual = get_configuracion_sistema(sesion)
    for k, v in valor.items():
        if k in DEFAULT_SISTEMA:
            actual[k] = v
    return set_parametro(sesion, "sistema", actual)


# --- Configuración Facturación (docs Módulo 9 §5) ---

DEFAULT_FACTURACION: dict[str, Any] = {
    "habilitar_ticket": True,
    "habilitar_factura": True,
    "habilitar_nota_credito": True,
    "habilitar_nota_debito": True,
    "prefijo_factura": "001",
    "prefijo_nota_credito": "001",
    "prefijo_nota_debito": "001",
    "formato_comprobante": "A4",
    "punto_venta_afip": 1,
}


def get_configuracion_facturacion(sesion: Session) -> dict[str, Any]:
    """
    Obtiene la configuración de facturación (comprobantes habilitados, numeración, formato).
    Si no existe, devuelve valores por defecto.
    """
    data = get_parametro(sesion, "facturacion")
    if not data:
        return dict(DEFAULT_FACTURACION)
    out = dict(DEFAULT_FACTURACION)
    for k in DEFAULT_FACTURACION:
        if k in data:
            out[k] = data[k]
    return out


def set_configuracion_facturacion(sesion: Session, valor: dict[str, Any]) -> dict[str, Any]:
    """Guarda la configuración de facturación. Mezcla con defaults para claves no enviadas."""
    actual = get_configuracion_facturacion(sesion)
    for k, v in valor.items():
        if k in DEFAULT_FACTURACION:
            actual[k] = v
    return set_parametro(sesion, "facturacion", actual)


# --- Configuración POS (docs Módulo 9 §9) ---

DEFAULT_POS: dict[str, Any] = {
    "modo_caja_rapida": False,
    "modo_pos_independiente": True,
    "mostrar_precios": True,
    "confirmar_cancelaciones": True,
    "impresion_automatica_tickets": True,
    "confirmar_anular_ventas": True,
    "sonidos_confirmacion": True,
}


def get_configuracion_pos(sesion: Session) -> dict[str, Any]:
    """
    Obtiene la configuración del POS (modo, visualización, impresión, confirmaciones).
    Si no existe, devuelve valores por defecto.
    """
    data = get_parametro(sesion, "pos")
    if not data:
        return dict(DEFAULT_POS)
    out = dict(DEFAULT_POS)
    for k in DEFAULT_POS:
        if k in data:
            out[k] = data[k]
    return out


def set_configuracion_pos(sesion: Session, valor: dict[str, Any]) -> dict[str, Any]:
    """Guarda la configuración del POS. Mezcla con defaults para claves no enviadas."""
    actual = get_configuracion_pos(sesion)
    for k, v in valor.items():
        if k in DEFAULT_POS:
            actual[k] = v
    return set_parametro(sesion, "pos", actual)


# --- Configuración Inventario (docs Módulo 9 §8) ---

DEFAULT_INVENTARIO: dict[str, Any] = {
    "stock_minimo_global": 0,
    "stock_maximo_global": 0,
    "control_vencimientos": True,
    "control_lotes": True,
    "transferencias_automaticas": False,
    "pedidos_automaticos": False,
    "alertas_reposicion": True,
}


def get_configuracion_inventario(sesion: Session) -> dict[str, Any]:
    """
    Obtiene la configuración de inventario (niveles, vencimientos, lotes, automatizaciones).
    Si no existe, devuelve valores por defecto.
    """
    data = get_parametro(sesion, "inventario")
    if not data:
        return dict(DEFAULT_INVENTARIO)
    out = dict(DEFAULT_INVENTARIO)
    for k in DEFAULT_INVENTARIO:
        if k in data:
            out[k] = data[k]
    return out


def set_configuracion_inventario(sesion: Session, valor: dict[str, Any]) -> dict[str, Any]:
    """Guarda la configuración de inventario. Mezcla con defaults para claves no enviadas."""
    actual = get_configuracion_inventario(sesion)
    for k, v in valor.items():
        if k in DEFAULT_INVENTARIO:
            actual[k] = v
    return set_parametro(sesion, "inventario", actual)


# --- Configuración Integraciones (docs Módulo 9 §10) ---


DEFAULT_INTEGRACIONES: dict[str, Any] = {
    "credenciales_fiscales": {
        "cuit": "",
        "certificado_afip": "",
        "clave_privada_afip": "",
        "punto_venta": 1,
        "modo_produccion": False,
    },
    "impresoras": {
        "impresora_tickets": "",
        "impresora_facturas": "",
        "tipo_conexion": "usb",
        "puerto": "",
    },
    "balanzas": {
        "habilitada": False,
        "tipo": "serial",
        "puerto": "COM1",
        "baudrate": 9600,
    },
    "pasarelas_pago": {
        "mercadopago_habilitado": False,
        "mercadopago_token": "",
        "getnet_habilitado": False,
        "getnet_token": "",
        "modo_produccion": False,
    },
}


def get_configuracion_integraciones(sesion: Session) -> dict[str, Any]:
    """
    Obtiene la configuración de integraciones externas (credenciales fiscales, impresoras,
    balanzas, pasarelas de pago). Si no existe, devuelve valores por defecto.
    """
    data = get_parametro(sesion, "integraciones")
    if not data:
        return {k: dict(v) if isinstance(v, dict) else v for k, v in DEFAULT_INTEGRACIONES.items()}
    out: dict[str, Any] = {}
    for k, default_v in DEFAULT_INTEGRACIONES.items():
        if k in data and isinstance(data[k], dict) and isinstance(default_v, dict):
            merged = dict(default_v)
            merged.update(data[k])
            out[k] = merged
        elif k in data:
            out[k] = data[k]
        else:
            out[k] = dict(default_v) if isinstance(default_v, dict) else default_v
    return out


def set_configuracion_integraciones(sesion: Session, valor: dict[str, Any]) -> dict[str, Any]:
    """Guarda la configuración de integraciones. Mezcla con defaults en claves no enviadas."""
    actual = get_configuracion_integraciones(sesion)
    for k, v in valor.items():
        if k in DEFAULT_INTEGRACIONES:
            if isinstance(v, dict) and isinstance(actual.get(k), dict):
                actual[k] = {**actual[k], **v}
            else:
                actual[k] = v
    return set_parametro(sesion, "integraciones", actual)


# --- Configuración Dashboard (objetivos; usada por Módulo 1) ---


DEFAULT_DASHBOARD: dict[str, Any] = {
    "objetivo_ventas_diario": 0,
    "objetivo_ventas_semanal": 0,
    "objetivo_ventas_mensual": 0,
    "mostrar_margen": True,
    "mostrar_productos_criticos": True,
    "dias_proximos_vencimiento": 30,
}


def get_configuracion_dashboard(sesion: Session) -> dict[str, Any]:
    """
    Obtiene la configuración del dashboard (objetivos de ventas, métricas visibles).
    Si no existe, devuelve valores por defecto.
    """
    data = get_parametro(sesion, "dashboard")
    if not data:
        return dict(DEFAULT_DASHBOARD)
    out = dict(DEFAULT_DASHBOARD)
    for k in DEFAULT_DASHBOARD:
        if k in data:
            out[k] = data[k]
    return out


def set_configuracion_dashboard(sesion: Session, valor: dict[str, Any]) -> dict[str, Any]:
    """Guarda la configuración del dashboard. Mezcla con defaults para claves no enviadas."""
    actual = get_configuracion_dashboard(sesion)
    for k, v in valor.items():
        if k in DEFAULT_DASHBOARD:
            actual[k] = v
    return set_parametro(sesion, "dashboard", actual)


# --- Resumen consolidado de configuración ---


def get_resumen_configuracion(sesion: Session) -> dict[str, Any]:
    """
    Devuelve un resumen consolidado de todas las secciones de configuración del sistema.
    Útil para que el frontend cargue toda la configuración en una sola petición.
    """
    return {
        "empresa": (lambda e: {
            "nombre": e.nombre if e else None,
            "razon_social": e.razon_social if e else None,
            "cuit": e.cuit if e else None,
            "condicion_fiscal": e.condicion_fiscal if e else None,
        })(sesion.get(Empresa, EMPRESA_ID)),
        "sucursales_activas": sesion.execute(
            select(Sucursal).where(Sucursal.activo.is_(True)).limit(50)
        ).scalars().all().__len__(),
        "medios_pago_activos": sesion.execute(
            select(MedioPago).where(MedioPago.activo.is_(True)).limit(50)
        ).scalars().all().__len__(),
        "caja": get_configuracion_caja(sesion),
        "sistema": get_configuracion_sistema(sesion),
        "facturacion": get_configuracion_facturacion(sesion),
        "pos": get_configuracion_pos(sesion),
        "inventario": get_configuracion_inventario(sesion),
        "integraciones": get_configuracion_integraciones(sesion),
        "dashboard": get_configuracion_dashboard(sesion),
    }


# --- Reset de parámetro ---


def reset_parametro(sesion: Session, clave: str) -> bool:
    """
    Elimina el parámetro personalizado de sistema, restaurando el comportamiento por defecto.
    Devuelve True si existía y fue eliminado, False si no existía.
    """
    clave_norm = (clave or "").strip()
    if not clave_norm:
        raise ValueError("La clave del parámetro no puede estar vacía")
    stmt = select(ParametroSistema).where(ParametroSistema.clave == clave_norm).limit(1)
    param = sesion.execute(stmt).scalars().first()
    if param is None:
        return False
    sesion.delete(param)
    sesion.flush()
    return True
