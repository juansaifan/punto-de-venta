"""Endpoints REST para Configuración (usuarios, roles)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services import configuracion as svc_configuracion

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


@router.get("/usuarios")
def listar_usuarios(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista usuarios del sistema."""
    return [
        {"id": u.id, "nombre": u.nombre, "activo": u.activo, "rol_id": u.rol_id}
        for u in svc_configuracion.listar_usuarios(db, limite=limite, offset=offset)
    ]


@router.get("/usuarios/{usuario_id}")
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obtiene un usuario por ID."""
    usuario = svc_configuracion.obtener_usuario_por_id(db, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"id": usuario.id, "nombre": usuario.nombre, "activo": usuario.activo, "rol_id": usuario.rol_id}


@router.patch("/usuarios/{usuario_id}")
def actualizar_usuario(usuario_id: int, body: dict, db: Session = Depends(get_db)):
    """Actualiza campos del usuario: activo (bool) y/o rol_id (int o null para desasignar). Al menos uno debe enviarse."""
    activo = body.get("activo")
    rol_id = body.get("rol_id")
    if activo is None and "rol_id" not in body:
        raise HTTPException(
            status_code=422,
            detail="Se debe enviar al menos uno: 'activo' (true/false) o 'rol_id' (número o null)",
        )
    usuario = None
    if activo is not None:
        try:
            usuario = svc_configuracion.actualizar_usuario_activo(
                db, usuario_id, activo=bool(activo)
            )
        except ValueError as e:
            if "no encontrado" in str(e).lower():
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))
    if "rol_id" in body:
        r_id = rol_id if rol_id is None else int(rol_id)
        try:
            usuario = svc_configuracion.asignar_rol_a_usuario(db, usuario_id, rol_id=r_id)
        except ValueError as e:
            if "no encontrado" in str(e).lower():
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))
    if usuario is None:
        usuario = svc_configuracion.obtener_usuario_por_id(db, usuario_id)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"id": usuario.id, "nombre": usuario.nombre, "activo": usuario.activo, "rol_id": usuario.rol_id}


@router.post("/usuarios", status_code=201)
def crear_usuario(body: dict, db: Session = Depends(get_db)):
    """Crea un usuario básico activo."""
    nombre = (body.get("nombre") or "").strip()
    persona_id = body.get("persona_id")
    if not nombre:
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    try:
        usuario = svc_configuracion.crear_usuario(
            db,
            nombre=nombre,
            persona_id=persona_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": usuario.id, "nombre": usuario.nombre, "activo": usuario.activo, "rol_id": usuario.rol_id}


@router.get("/roles")
def listar_roles(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista roles del sistema."""
    return [
        {"id": r.id, "codigo": r.codigo, "nombre": r.nombre}
        for r in svc_configuracion.listar_roles(db, limite=limite, offset=offset)
    ]


@router.get("/roles/{rol_id}")
def obtener_rol(rol_id: int, db: Session = Depends(get_db)):
    """Obtiene un rol por ID."""
    rol = svc_configuracion.obtener_rol_por_id(db, rol_id)
    if rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return {"id": rol.id, "codigo": rol.codigo, "nombre": rol.nombre}


@router.post("/roles", status_code=201)
def crear_rol(body: dict, db: Session = Depends(get_db)):
    """Crea un rol operativo."""
    codigo = (body.get("codigo") or "").strip()
    nombre = (body.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise HTTPException(status_code=422, detail="Código y nombre son obligatorios")
    try:
        rol = svc_configuracion.crear_rol(
            db,
            codigo=codigo,
            nombre=nombre,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": rol.id, "codigo": rol.codigo, "nombre": rol.nombre}


@router.patch("/roles/{rol_id}")
def actualizar_rol(rol_id: int, body: dict, db: Session = Depends(get_db)):
    """Actualiza parcialmente un rol (código y/o nombre). Al menos un campo debe enviarse."""
    codigo = body.get("codigo")
    nombre = body.get("nombre")
    if codigo is not None:
        codigo = codigo.strip() if isinstance(codigo, str) else None
    if nombre is not None:
        nombre = nombre.strip() if isinstance(nombre, str) else None
    if codigo is None and nombre is None:
        raise HTTPException(
            status_code=422,
            detail="Se debe enviar al menos uno: codigo o nombre",
        )
    try:
        rol = svc_configuracion.actualizar_rol(
            db,
            rol_id,
            codigo=codigo,
            nombre=nombre,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrado" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        if "ya existe" in msg or "vacío" in msg:
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": rol.id, "codigo": rol.codigo, "nombre": rol.nombre}


# --- Permisos (ROADMAP Fase 7; docs Módulo 9 §11) ---


@router.get("/permisos")
def listar_permisos(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista permisos del sistema."""
    items = svc_configuracion.listar_permisos(db, limite=limite, offset=offset)
    return [
        {"id": p.id, "codigo": p.codigo, "nombre": p.nombre, "descripcion": p.descripcion}
        for p in items
    ]


@router.get("/permisos/{permiso_id}")
def obtener_permiso(permiso_id: int, db: Session = Depends(get_db)):
    """Obtiene un permiso por ID."""
    perm = svc_configuracion.obtener_permiso_por_id(db, permiso_id)
    if perm is None:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    return {"id": perm.id, "codigo": perm.codigo, "nombre": perm.nombre, "descripcion": perm.descripcion}


@router.post("/permisos", status_code=201)
def crear_permiso(body: dict, db: Session = Depends(get_db)):
    """Crea un permiso (código único)."""
    codigo = (body.get("codigo") or "").strip()
    nombre = (body.get("nombre") or "").strip()
    descripcion = (body.get("descripcion") or "").strip() or None
    if not codigo:
        raise HTTPException(status_code=422, detail="El código es obligatorio")
    if not nombre:
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    try:
        perm = svc_configuracion.crear_permiso(
            db, codigo=codigo, nombre=nombre, descripcion=descripcion
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": perm.id, "codigo": perm.codigo, "nombre": perm.nombre, "descripcion": perm.descripcion}


@router.get("/roles/{rol_id}/permisos")
def obtener_permisos_del_rol(rol_id: int, db: Session = Depends(get_db)):
    """Lista los permisos asignados a un rol."""
    try:
        permisos = svc_configuracion.obtener_permisos_del_rol(db, rol_id)
    except ValueError as e:
        if "no encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return [
        {"id": p.id, "codigo": p.codigo, "nombre": p.nombre, "descripcion": p.descripcion}
        for p in permisos
    ]


@router.put("/roles/{rol_id}/permisos")
def asignar_permisos_rol(rol_id: int, body: dict, db: Session = Depends(get_db)):
    """Asigna la lista de permisos al rol (reemplaza los anteriores). Body: {"permiso_ids": [1, 2, ...]}."""
    permiso_ids = body.get("permiso_ids")
    if permiso_ids is None:
        raise HTTPException(status_code=422, detail="Se requiere 'permiso_ids' (lista de IDs)")
    if not isinstance(permiso_ids, list):
        raise HTTPException(status_code=422, detail="permiso_ids debe ser una lista")
    ids = [int(x) for x in permiso_ids]
    try:
        rol = svc_configuracion.asignar_permisos_a_rol(db, rol_id, permiso_ids=ids)
    except ValueError as e:
        if "no encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    permisos = svc_configuracion.obtener_permisos_del_rol(db, rol.id)
    return {
        "rol_id": rol.id,
        "permisos": [
            {"id": p.id, "codigo": p.codigo, "nombre": p.nombre}
            for p in permisos
        ],
    }


# --- Medios de pago (docs Módulo 9 §6) ---


@router.get("/medios-pago")
def listar_medios_pago(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    solo_activos: bool = Query(False, description="Solo medios de pago activos"),
):
    """Lista medios de pago configurados."""
    items = svc_configuracion.listar_medios_pago(
        db, limite=limite, offset=offset, solo_activos=solo_activos
    )
    return [
        {
            "id": m.id,
            "codigo": m.codigo,
            "nombre": m.nombre,
            "activo": m.activo,
            "comision": float(m.comision),
            "dias_acreditacion": m.dias_acreditacion,
        }
        for m in items
    ]


@router.get("/medios-pago/{medio_pago_id}")
def obtener_medio_pago(medio_pago_id: int, db: Session = Depends(get_db)):
    """Obtiene un medio de pago por ID."""
    mp = svc_configuracion.obtener_medio_pago_por_id(db, medio_pago_id)
    if mp is None:
        raise HTTPException(status_code=404, detail="Medio de pago no encontrado")
    return {
        "id": mp.id,
        "codigo": mp.codigo,
        "nombre": mp.nombre,
        "activo": mp.activo,
        "comision": float(mp.comision),
        "dias_acreditacion": mp.dias_acreditacion,
    }


@router.post("/medios-pago", status_code=201)
def crear_medio_pago(body: dict, db: Session = Depends(get_db)):
    """Crea un medio de pago (código único)."""
    codigo = (body.get("codigo") or "").strip()
    nombre = (body.get("nombre") or "").strip()
    if not codigo:
        raise HTTPException(status_code=422, detail="El código es obligatorio")
    if not nombre:
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    activo = body.get("activo", True)
    comision = body.get("comision", 0)
    dias_acreditacion = body.get("dias_acreditacion", 0)
    try:
        mp = svc_configuracion.crear_medio_pago(
            db,
            codigo=codigo,
            nombre=nombre,
            activo=activo,
            comision=comision,
            dias_acreditacion=dias_acreditacion,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "ya existe" in msg:
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": mp.id,
        "codigo": mp.codigo,
        "nombre": mp.nombre,
        "activo": mp.activo,
        "comision": float(mp.comision),
        "dias_acreditacion": mp.dias_acreditacion,
    }


@router.patch("/medios-pago/{medio_pago_id}")
def actualizar_medio_pago(medio_pago_id: int, body: dict, db: Session = Depends(get_db)):
    """Actualiza parcialmente un medio de pago (nombre, activo, comision, dias_acreditacion)."""
    nombre = body.get("nombre")
    if nombre is not None:
        nombre = nombre.strip() if isinstance(nombre, str) else None
    activo = body.get("activo")
    comision = body.get("comision")
    dias_acreditacion = body.get("dias_acreditacion")
    if nombre is None and activo is None and comision is None and dias_acreditacion is None:
        raise HTTPException(
            status_code=422,
            detail="Se debe enviar al menos uno: nombre, activo, comision, dias_acreditacion",
        )
    try:
        mp = svc_configuracion.actualizar_medio_pago(
            db,
            medio_pago_id,
            nombre=nombre,
            activo=activo,
            comision=comision,
            dias_acreditacion=dias_acreditacion,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrado" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": mp.id,
        "codigo": mp.codigo,
        "nombre": mp.nombre,
        "activo": mp.activo,
        "comision": float(mp.comision),
        "dias_acreditacion": mp.dias_acreditacion,
    }


# --- Empresa (datos del negocio, docs Módulo 9 §3) ---


def _empresa_a_dict(emp):
    return {
        "id": emp.id,
        "nombre": emp.nombre,
        "razon_social": emp.razon_social,
        "cuit": emp.cuit,
        "condicion_fiscal": emp.condicion_fiscal,
        "direccion": emp.direccion,
        "telefono": emp.telefono,
        "email": emp.email,
        "logo_url": emp.logo_url,
    }


@router.get("/empresa")
def obtener_empresa(db: Session = Depends(get_db)):
    """Obtiene los datos de la empresa (comprobantes, reportes, integraciones fiscales). 404 si no están configurados."""
    emp = svc_configuracion.obtener_empresa(db)
    if emp is None:
        raise HTTPException(status_code=404, detail="Datos de empresa no configurados")
    return _empresa_a_dict(emp)


@router.put("/empresa")
def actualizar_empresa(body: dict, db: Session = Depends(get_db)):
    """Crea o actualiza los datos de la empresa. Campos opcionales; en primera creación se puede enviar solo nombre."""
    nombre = body.get("nombre")
    if nombre is not None:
        nombre = nombre.strip() if isinstance(nombre, str) else None
    razon_social = body.get("razon_social")
    cuit = body.get("cuit")
    condicion_fiscal = body.get("condicion_fiscal")
    direccion = body.get("direccion")
    telefono = body.get("telefono")
    email = body.get("email")
    logo_url = body.get("logo_url")
    try:
        emp = svc_configuracion.actualizar_empresa(
            db,
            nombre=nombre,
            razon_social=razon_social,
            cuit=cuit,
            condicion_fiscal=condicion_fiscal,
            direccion=direccion,
            telefono=telefono,
            email=email,
            logo_url=logo_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _empresa_a_dict(emp)


# --- Sucursales (docs Módulo 9 §4) ---


@router.get("/sucursales")
def listar_sucursales(
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    solo_activas: bool = Query(False, description="Solo sucursales activas"),
):
    """Lista sucursales del negocio."""
    items = svc_configuracion.listar_sucursales(
        db, limite=limite, offset=offset, solo_activas=solo_activas
    )
    return [
        {"id": s.id, "nombre": s.nombre, "direccion": s.direccion, "telefono": s.telefono, "activo": s.activo}
        for s in items
    ]


@router.get("/sucursales/{sucursal_id}")
def obtener_sucursal(sucursal_id: int, db: Session = Depends(get_db)):
    """Obtiene una sucursal por ID."""
    suc = svc_configuracion.obtener_sucursal_por_id(db, sucursal_id)
    if suc is None:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return {"id": suc.id, "nombre": suc.nombre, "direccion": suc.direccion, "telefono": suc.telefono, "activo": suc.activo}


@router.post("/sucursales", status_code=201)
def crear_sucursal(body: dict, db: Session = Depends(get_db)):
    """Crea una sucursal."""
    nombre = (body.get("nombre") or "").strip()
    if not nombre:
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    direccion = body.get("direccion")
    telefono = body.get("telefono")
    activo = body.get("activo", True)
    try:
        suc = svc_configuracion.crear_sucursal(
            db, nombre=nombre, direccion=direccion, telefono=telefono, activo=activo
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": suc.id, "nombre": suc.nombre, "direccion": suc.direccion, "telefono": suc.telefono, "activo": suc.activo}


@router.patch("/sucursales/{sucursal_id}")
def actualizar_sucursal(sucursal_id: int, body: dict, db: Session = Depends(get_db)):
    """Actualiza parcialmente una sucursal (nombre, direccion, telefono, activo)."""
    nombre = body.get("nombre")
    direccion = body.get("direccion")
    telefono = body.get("telefono")
    activo = body.get("activo")
    if nombre is None and direccion is None and telefono is None and activo is None:
        raise HTTPException(
            status_code=422,
            detail="Se debe enviar al menos uno: nombre, direccion, telefono, activo",
        )
    try:
        suc = svc_configuracion.actualizar_sucursal(
            db, sucursal_id, nombre=nombre, direccion=direccion, telefono=telefono, activo=activo
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrada" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": suc.id, "nombre": suc.nombre, "direccion": suc.direccion, "telefono": suc.telefono, "activo": suc.activo}


# --- Parámetros de sistema (facturación, caja, etc.; docs Módulo 9 §5, §7) ---


@router.get("/parametros")
def listar_parametros(db: Session = Depends(get_db)):
    """Lista las claves de todos los parámetros de sistema configurados."""
    return {"claves": svc_configuracion.listar_claves_parametros(db)}


@router.get("/parametros/{clave}")
def obtener_parametro(clave: str, db: Session = Depends(get_db)):
    """Obtiene el valor JSON del parámetro de sistema (ej. facturacion, caja). Si no existe devuelve {}."""
    if not (clave or "").strip():
        raise HTTPException(status_code=400, detail="Clave no válida")
    return svc_configuracion.get_parametro(db, clave)


@router.put("/parametros/{clave}")
def guardar_parametro(clave: str, body: dict, db: Session = Depends(get_db)):
    """Guarda el valor JSON del parámetro. Body: objeto JSON. Clave vacía → 400."""
    if not (clave or "").strip():
        raise HTTPException(status_code=400, detail="Clave no válida")
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    try:
        return svc_configuracion.set_parametro(db, clave, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Configuración Caja (docs Módulo 9 §7) ---


@router.get("/caja")
def obtener_configuracion_caja(db: Session = Depends(get_db)):
    """Obtiene la configuración de caja (monto mínimo apertura, arqueo, diferencias, permisos). Devuelve defaults si no está configurada."""
    return svc_configuracion.get_configuracion_caja(db)


@router.put("/caja")
def actualizar_configuracion_caja(body: dict, db: Session = Depends(get_db)):
    """Actualiza la configuración de caja. Body: campos a actualizar (monto_minimo_apertura, obligar_arqueo, permitir_cierre_con_diferencia, requerir_autorizacion_supervisor_cierre)."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    return svc_configuracion.set_configuracion_caja(db, body)


# --- Configuración Sistema (docs Módulo 9 §11) ---


@router.get("/sistema")
def obtener_configuracion_sistema(db: Session = Depends(get_db)):
    """Obtiene la configuración de sistema (zona horaria, idioma, formato fecha/moneda, seguridad). Devuelve defaults si no está configurada."""
    return svc_configuracion.get_configuracion_sistema(db)


@router.put("/sistema")
def actualizar_configuracion_sistema(body: dict, db: Session = Depends(get_db)):
    """Actualiza la configuración de sistema. Body: campos a actualizar (zona_horaria, idioma, formato_fecha, formato_moneda, tiempo_sesion_minutos, registro_auditoria)."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    return svc_configuracion.set_configuracion_sistema(db, body)


# --- Configuración Facturación (docs Módulo 9 §5) ---


@router.get("/facturacion")
def obtener_configuracion_facturacion(db: Session = Depends(get_db)):
    """Obtiene la configuración de facturación (comprobantes habilitados, numeración, formato). Devuelve defaults si no está configurada."""
    return svc_configuracion.get_configuracion_facturacion(db)


@router.put("/facturacion")
def actualizar_configuracion_facturacion(body: dict, db: Session = Depends(get_db)):
    """Actualiza la configuración de facturación. Body: campos a actualizar (habilitar_ticket, habilitar_factura, prefijos, formato_comprobante, etc.)."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    return svc_configuracion.set_configuracion_facturacion(db, body)


# --- Configuración POS (docs Módulo 9 §9) ---


@router.get("/pos")
def obtener_configuracion_pos(db: Session = Depends(get_db)):
    """Obtiene la configuración del POS (modo, visualización, impresión, confirmaciones). Devuelve defaults si no está configurada."""
    return svc_configuracion.get_configuracion_pos(db)


@router.put("/pos")
def actualizar_configuracion_pos(body: dict, db: Session = Depends(get_db)):
    """Actualiza la configuración del POS. Body: campos a actualizar (modo_caja_rapida, mostrar_precios, impresion_automatica_tickets, etc.)."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    return svc_configuracion.set_configuracion_pos(db, body)


# --- Configuración Inventario (docs Módulo 9 §8) ---


@router.get("/inventario")
def obtener_configuracion_inventario(db: Session = Depends(get_db)):
    """Obtiene la configuración de inventario (niveles, vencimientos, lotes, automatizaciones). Devuelve defaults si no está configurada."""
    return svc_configuracion.get_configuracion_inventario(db)


@router.put("/inventario")
def actualizar_configuracion_inventario(body: dict, db: Session = Depends(get_db)):
    """Actualiza la configuración de inventario. Body: campos a actualizar (stock_minimo_global, control_vencimientos, alertas_reposicion, etc.)."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    return svc_configuracion.set_configuracion_inventario(db, body)


# --- Configuración Integraciones (docs Módulo 9 §10) ---


@router.get("/integraciones")
def obtener_configuracion_integraciones(db: Session = Depends(get_db)):
    """Obtiene la configuración de integraciones externas (credenciales fiscales, impresoras, balanzas, pasarelas de pago)."""
    return svc_configuracion.get_configuracion_integraciones(db)


@router.put("/integraciones")
def actualizar_configuracion_integraciones(body: dict, db: Session = Depends(get_db)):
    """Actualiza la configuración de integraciones. Body: secciones a actualizar (credenciales_fiscales, impresoras, balanzas, pasarelas_pago)."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    return svc_configuracion.set_configuracion_integraciones(db, body)


# --- Configuración Dashboard (objetivos, métricas) ---


@router.get("/dashboard")
def obtener_configuracion_dashboard(db: Session = Depends(get_db)):
    """Obtiene la configuración del dashboard (objetivos de ventas diario/semanal/mensual, métricas visibles)."""
    return svc_configuracion.get_configuracion_dashboard(db)


@router.put("/dashboard")
def actualizar_configuracion_dashboard(body: dict, db: Session = Depends(get_db)):
    """Actualiza la configuración del dashboard. Body: campos a actualizar (objetivo_ventas_diario, objetivo_ventas_semanal, objetivo_ventas_mensual, mostrar_margen, etc.)."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="El body debe ser un objeto JSON")
    return svc_configuracion.set_configuracion_dashboard(db, body)


# --- Resumen consolidado ---


@router.get("/resumen")
def obtener_resumen_configuracion(db: Session = Depends(get_db)):
    """Devuelve un resumen consolidado de todas las secciones de configuración del sistema."""
    return svc_configuracion.get_resumen_configuracion(db)


# --- Reset de parámetros ---


@router.delete("/parametros/{clave}", status_code=200)
def eliminar_parametro(clave: str, db: Session = Depends(get_db)):
    """Elimina el parámetro personalizado y restaura el comportamiento por defecto. 404 si no existe."""
    if not (clave or "").strip():
        raise HTTPException(status_code=400, detail="Clave no válida")
    try:
        eliminado = svc_configuracion.reset_parametro(db, clave)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not eliminado:
        raise HTTPException(status_code=404, detail=f"Parámetro '{clave}' no encontrado")
    return {"eliminado": True, "clave": clave}
