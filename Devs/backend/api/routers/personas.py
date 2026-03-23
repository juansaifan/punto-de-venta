"""Endpoints REST para el dominio Personas (persona base + roles)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas.persona import (
    PersonaCreate,
    PersonaUpdate,
    PersonaResponse,
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse,
    ClienteAltaRapidaCreate,
    ClienteLookupResponse,
    ProveedorCreate,
    ProveedorUpdate,
    ProveedorResponse,
    EmpleadoCreate,
    EmpleadoUpdate,
    EmpleadoResponse,
    ContactoCreate,
    ContactoResponse,
)
from backend.models.usuario import Usuario
from backend.services import personas as svc_personas
from backend.services import personas_usuarios as svc_personas_usuarios
from backend.services import empleados_usuarios as svc_empleados_usuarios

router = APIRouter(prefix="/personas", tags=["personas"])


# Personas base -----------------------------------------------------------------


@router.get("", response_model=list[PersonaResponse])
def listar_personas(
    db: Session = Depends(get_db),
    activo_only: bool = Query(True, description="Solo personas activas"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista personas con paginación."""
    items = svc_personas.listar_personas(
        db, activo_only=activo_only, limite=limite, offset=offset
    )
    return list(items)


@router.post("", response_model=PersonaResponse, status_code=201)
def crear_persona(payload: PersonaCreate, db: Session = Depends(get_db)):
    """Crea una nueva persona base."""
    persona = svc_personas.crear_persona(
        db,
        nombre=payload.nombre,
        apellido=payload.apellido,
        documento=payload.documento,
        telefono=payload.telefono,
        activo=payload.activo,
    )
    db.refresh(persona)
    return persona


# Usuarios del sistema (vínculo con Personas) -----------------------------------


@router.get("/usuarios/{usuario_id}/persona", response_model=PersonaResponse)
def obtener_persona_de_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
):
    """Lookup inverso: devuelve la persona vinculada a un usuario."""
    try:
        persona = svc_personas_usuarios.obtener_persona_de_usuario(db, usuario_id=usuario_id)
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrado" in msg or "sin persona" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return persona


@router.get("/{persona_id}/usuarios")
def listar_usuarios_de_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista usuarios del sistema asociados a una persona."""
    try:
        usuarios = svc_personas_usuarios.listar_usuarios_por_persona(
            db, persona_id=persona_id, limite=limite, offset=offset
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [
        {
            "id": u.id,
            "nombre": u.nombre,
            "activo": u.activo,
            "rol_id": u.rol_id,
            "persona_id": u.persona_id,
        }
        for u in usuarios
    ]


@router.put("/{persona_id}/usuarios/{usuario_id}")
def vincular_usuario_a_persona(
    persona_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
):
    """Vincula un usuario existente a una persona (setea usuario.persona_id)."""
    try:
        usuario = svc_personas_usuarios.asignar_persona_a_usuario(
            db, usuario_id=usuario_id, persona_id=persona_id
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrado" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        if "ya tiene un usuario" in msg or "ya está vinculado" in msg:
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "activo": usuario.activo,
        "rol_id": usuario.rol_id,
        "persona_id": usuario.persona_id,
    }


@router.delete("/{persona_id}/usuarios/{usuario_id}")
def desvincular_usuario_de_persona(
    persona_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
):
    """Desvincula el usuario de la persona si coincide el vínculo actual."""
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.persona_id != persona_id:
        raise HTTPException(status_code=400, detail="El usuario no está vinculado a esta persona")
    usuario = svc_personas_usuarios.asignar_persona_a_usuario(
        db, usuario_id=usuario_id, persona_id=None
    )
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "activo": usuario.activo,
        "rol_id": usuario.rol_id,
        "persona_id": usuario.persona_id,
    }


# Clientes ----------------------------------------------------------------------


@router.post("/clientes", response_model=ClienteResponse, status_code=201)
def crear_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    """
    Crea un cliente a partir de una persona existente.

    La persona debe haber sido creada previamente mediante /personas.
    """
    try:
        cliente = svc_personas.crear_cliente(
            db,
            persona_id=payload.persona_id,
            segmento=payload.segmento,
            condicion_pago=payload.condicion_pago,
            limite_credito=payload.limite_credito,
            estado=payload.estado,
            observaciones=payload.observaciones,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return cliente


@router.get("/clientes", response_model=list[ClienteResponse])
def listar_clientes(
    db: Session = Depends(get_db),
    busqueda: str | None = Query(None, description="Búsqueda por nombre/apellido/documento/teléfono"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista clientes configurados en el sistema."""
    items = svc_personas.listar_clientes(db, busqueda=busqueda, limite=limite, offset=offset)
    return list(items)


@router.get("/clientes/buscar", response_model=list[ClienteLookupResponse])
def buscar_clientes(
    q: str = Query(..., min_length=1, description="Texto a buscar (nombre/apellido/documento/teléfono)"),
    db: Session = Depends(get_db),
    limite: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Búsqueda rápida de clientes para POS (incluye datos de persona)."""
    rows = svc_personas.buscar_clientes_lookup(db, busqueda=q, limite=limite, offset=offset)
    return [
        ClienteLookupResponse(
            cliente_id=cli.id,
            persona_id=per.id,
            nombre=per.nombre,
            apellido=per.apellido,
            documento=per.documento,
            telefono=per.telefono,
            limite_credito=float(cli.limite_credito) if cli.limite_credito is not None else None,
            estado=cli.estado,
        )
        for (cli, per) in rows
    ]


@router.post("/clientes/alta-rapida", response_model=ClienteLookupResponse, status_code=201)
def alta_rapida_cliente(payload: ClienteAltaRapidaCreate, db: Session = Depends(get_db)):
    """Crea persona + cliente en una sola llamada (pensado para POS)."""
    cliente, persona = svc_personas.alta_rapida_cliente(
        db,
        nombre=payload.nombre,
        apellido=payload.apellido,
        documento=payload.documento,
        telefono=payload.telefono,
        segmento=payload.segmento,
        condicion_pago=payload.condicion_pago,
        limite_credito=payload.limite_credito,
        estado=payload.estado,
        observaciones=payload.observaciones,
    )
    return ClienteLookupResponse(
        cliente_id=cliente.id,
        persona_id=persona.id,
        nombre=persona.nombre,
        apellido=persona.apellido,
        documento=persona.documento,
        telefono=persona.telefono,
        limite_credito=float(cliente.limite_credito) if cliente.limite_credito is not None else None,
        estado=cliente.estado,
    )


@router.get("/clientes/por-persona/{persona_id}", response_model=ClienteResponse)
def obtener_cliente_por_persona(persona_id: int, db: Session = Depends(get_db)):
    """Obtiene el cliente vinculado a una persona por su persona_id."""
    cliente = svc_personas.obtener_cliente_por_persona_id(db, persona_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="No se encontró cliente para esa persona")
    return cliente


@router.get("/clientes/ranking")
def ranking_clientes_endpoint(
    db: Session = Depends(get_db),
    fecha_desde: str | None = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha fin YYYY-MM-DD"),
    limite: int = Query(20, ge=1, le=100),
    excluir_canceladas: bool = Query(True, description="Excluir ventas canceladas del ranking"),
):
    """
    Ranking de clientes por total facturado en el período.
    Docs Módulo 6 §5 — Segmentación de clientes.
    """
    from datetime import datetime as dt

    def parse_date(s: str | None):
        if not s:
            return None
        try:
            return dt.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Fecha inválida: {s}. Use YYYY-MM-DD")

    return svc_personas.ranking_clientes(
        db,
        fecha_desde=parse_date(fecha_desde),
        fecha_hasta=parse_date(fecha_hasta),
        limite=limite,
        excluir_canceladas=excluir_canceladas,
    )


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtiene un cliente por ID."""
    cliente = svc_personas.obtener_cliente_por_id(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.patch("/clientes/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int,
    payload: ClienteUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza los datos comerciales de un cliente (segmento, límite de crédito, estado, etc.)."""
    cliente = svc_personas.actualizar_cliente(
        db,
        cliente_id,
        segmento=payload.segmento,
        condicion_pago=payload.condicion_pago,
        limite_credito=payload.limite_credito,
        estado=payload.estado,
        observaciones=payload.observaciones,
    )
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


# Proveedores -------------------------------------------------------------------


@router.post("/proveedores", response_model=ProveedorResponse, status_code=201)
def crear_proveedor(payload: ProveedorCreate, db: Session = Depends(get_db)):
    """
    Crea un proveedor a partir de una persona existente.

    Nota: las compras actuales usan directamente persona_id como proveedor,
    pero este recurso permite registrar información específica de proveedor.
    """
    try:
        proveedor = svc_personas.crear_proveedor(
            db,
            persona_id=payload.persona_id,
            cuit=payload.cuit,
            condiciones_comerciales=payload.condiciones_comerciales,
            condiciones_pago=payload.condiciones_pago,
            lista_precios=payload.lista_precios,
            estado=payload.estado,
            frecuencia_entrega=payload.frecuencia_entrega,
            minimo_compra=payload.minimo_compra,
            tiempo_estimado_entrega=payload.tiempo_estimado_entrega,
            observaciones=payload.observaciones,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return proveedor


@router.get("/proveedores", response_model=list[ProveedorResponse])
def listar_proveedores(
    db: Session = Depends(get_db),
    estado: str | None = Query(None, description="Filtrar por estado (ACTIVO/INACTIVO)"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista proveedores configurados en el sistema."""
    items = svc_personas.listar_proveedores(db, estado=estado, limite=limite, offset=offset)
    return list(items)


@router.get("/proveedores/ranking")
def ranking_proveedores_endpoint(
    db: Session = Depends(get_db),
    fecha_desde: str | None = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha fin YYYY-MM-DD"),
    limite: int = Query(20, ge=1, le=100),
):
    """
    Ranking de proveedores por volumen de compras en el período.
    Docs Módulo 6 §6.
    """
    from datetime import datetime as dt

    def parse_date(s: str | None):
        if not s:
            return None
        try:
            return dt.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Fecha inválida: {s}. Use YYYY-MM-DD")

    return svc_personas.ranking_proveedores(
        db,
        fecha_desde=parse_date(fecha_desde),
        fecha_hasta=parse_date(fecha_hasta),
        limite=limite,
    )


@router.get("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
def obtener_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    """Obtiene un proveedor por ID."""
    proveedor = svc_personas.obtener_proveedor_por_id(db, proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


@router.patch("/proveedores/{proveedor_id}", response_model=ProveedorResponse)
def actualizar_proveedor(
    proveedor_id: int,
    payload: ProveedorUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza los datos de un proveedor (condiciones comerciales, estado, etc.)."""
    proveedor = svc_personas.actualizar_proveedor(
        db,
        proveedor_id,
        cuit=payload.cuit,
        condiciones_comerciales=payload.condiciones_comerciales,
        condiciones_pago=payload.condiciones_pago,
        lista_precios=payload.lista_precios,
        estado=payload.estado,
        frecuencia_entrega=payload.frecuencia_entrega,
        minimo_compra=payload.minimo_compra,
        tiempo_estimado_entrega=payload.tiempo_estimado_entrega,
        observaciones=payload.observaciones,
    )
    if proveedor is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


# Empleados ---------------------------------------------------------------------


@router.post("/empleados", response_model=EmpleadoResponse, status_code=201)
def crear_empleado(payload: EmpleadoCreate, db: Session = Depends(get_db)):
    """Crea un empleado a partir de una persona existente."""
    try:
        empleado = svc_personas.crear_empleado(
            db,
            persona_id=payload.persona_id,
            documento=payload.documento,
            cargo=payload.cargo,
            estado=payload.estado,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return empleado


@router.get("/empleados", response_model=list[EmpleadoResponse])
def listar_empleados(
    db: Session = Depends(get_db),
    estado: str | None = Query(None, description="Filtrar por estado (ACTIVO/INACTIVO)"),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista empleados configurados en el sistema."""
    items = svc_personas.listar_empleados(db, estado=estado, limite=limite, offset=offset)
    return list(items)


@router.get("/empleados/por-persona/{persona_id}", response_model=EmpleadoResponse)
def obtener_empleado_por_persona(persona_id: int, db: Session = Depends(get_db)):
    """Obtiene el empleado vinculado a una persona por su persona_id."""
    empleado = svc_personas.obtener_empleado_por_persona_id(db, persona_id)
    if empleado is None:
        raise HTTPException(status_code=404, detail="No se encontró empleado para esa persona")
    return empleado


@router.get("/empleados/{empleado_id}", response_model=EmpleadoResponse)
def obtener_empleado(empleado_id: int, db: Session = Depends(get_db)):
    """Obtiene un empleado por ID."""
    empleado = svc_personas.obtener_empleado_por_id(db, empleado_id)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado


@router.patch("/empleados/{empleado_id}", response_model=EmpleadoResponse)
def actualizar_empleado(
    empleado_id: int,
    payload: EmpleadoUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza los datos de un empleado (cargo, estado, documento)."""
    empleado = svc_personas.actualizar_empleado(
        db,
        empleado_id,
        documento=payload.documento,
        cargo=payload.cargo,
        estado=payload.estado,
    )
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado


@router.get("/empleados/{empleado_id}/usuario")
def obtener_usuario_de_empleado(empleado_id: int, db: Session = Depends(get_db)):
    """Devuelve el usuario asociado al empleado (si existe) vía persona_id."""
    try:
        usuario = svc_empleados_usuarios.obtener_usuario_de_empleado(db, empleado_id=empleado_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if usuario is None:
        return None
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "activo": usuario.activo,
        "rol_id": usuario.rol_id,
        "persona_id": usuario.persona_id,
    }


@router.put("/empleados/{empleado_id}/usuario/{usuario_id}")
def vincular_empleado_a_usuario(empleado_id: int, usuario_id: int, db: Session = Depends(get_db)):
    """Vincula un empleado a un usuario (asegura usuario.persona_id = empleado.persona_id)."""
    try:
        usuario = svc_empleados_usuarios.vincular_empleado_a_usuario(
            db, empleado_id=empleado_id, usuario_id=usuario_id
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrado" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        if "ya tiene un usuario" in msg or "ya está vinculado" in msg:
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "activo": usuario.activo,
        "rol_id": usuario.rol_id,
        "persona_id": usuario.persona_id,
    }


@router.delete("/empleados/{empleado_id}/usuario/{usuario_id}")
def desvincular_empleado_de_usuario(
    empleado_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
):
    """Desvincula el usuario del empleado si coincide el vínculo actual."""
    try:
        usuario = svc_empleados_usuarios.desvincular_empleado_de_usuario(
            db, empleado_id=empleado_id, usuario_id=usuario_id
        )
    except ValueError as e:
        msg = str(e).lower()
        if "no encontrado" in msg:
            raise HTTPException(status_code=404, detail=str(e))
        if "no está vinculado" in msg:
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "activo": usuario.activo,
        "rol_id": usuario.rol_id,
        "persona_id": usuario.persona_id,
    }


# Contactos ---------------------------------------------------------------------


@router.post("/contactos", response_model=ContactoResponse, status_code=201)
def crear_contacto(payload: ContactoCreate, db: Session = Depends(get_db)):
    """Crea un contacto asociado a una persona existente."""
    try:
        contacto = svc_personas.crear_contacto(
            db,
            persona_id=payload.persona_id,
            nombre=payload.nombre,
            cargo=payload.cargo,
            telefono=payload.telefono,
            email=payload.email,
            observaciones=payload.observaciones,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return contacto


@router.get("/contactos", response_model=list[ContactoResponse])
def listar_contactos(
    db: Session = Depends(get_db),
    persona_id: int | None = Query(
        None, description="Filtrar contactos por persona_id si se especifica"
    ),
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista contactos, opcionalmente filtrados por persona."""
    items = svc_personas.listar_contactos(
        db, persona_id=persona_id, limite=limite, offset=offset
    )
    return list(items)


@router.get("/contactos/{contacto_id}", response_model=ContactoResponse)
def obtener_contacto(contacto_id: int, db: Session = Depends(get_db)):
    """Obtiene un contacto por ID."""
    contacto = svc_personas.obtener_contacto_por_id(db, contacto_id)
    if contacto is None:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contacto


@router.get("/clientes/{cliente_id}/ventas")
def ventas_por_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    fecha_desde: str | None = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha fin YYYY-MM-DD"),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Historial de ventas de un cliente con estadísticas agregadas (total, ticket promedio, fiadas).
    Docs Módulo 6 §5 / §10 — Integración con Ventas.
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
        return svc_personas.ventas_por_cliente(
            db,
            cliente_id=cliente_id,
            fecha_desde=parse_date(fecha_desde),
            fecha_hasta=parse_date(fecha_hasta),
            limite=limite,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/clientes/{cliente_id}/cuenta-corriente")
def resumen_cuenta_corriente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    """
    Resumen de cuenta corriente de un cliente: saldo, límite de crédito, margen disponible y últimos movimientos.
    Docs Módulo 6 §5 / §10 — Integración con Tesorería.
    """
    try:
        return svc_personas.resumen_cuenta_corriente_cliente(db, cliente_id=cliente_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/proveedores/{proveedor_id}/compras")
def compras_por_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db),
    fecha_desde: str | None = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha fin YYYY-MM-DD"),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Historial de compras de un proveedor con estadísticas agregadas.
    Docs Módulo 6 §6 / §10 — Integración con Inventario.
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
        return svc_personas.compras_por_proveedor(
            db,
            proveedor_id=proveedor_id,
            fecha_desde=parse_date(fecha_desde),
            fecha_hasta=parse_date(fecha_hasta),
            limite=limite,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{persona_id}", response_model=PersonaResponse)
def obtener_persona(persona_id: int, db: Session = Depends(get_db)):
    """Obtiene una persona por ID."""
    persona = svc_personas.obtener_persona_por_id(db, persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return persona


@router.patch("/{persona_id}", response_model=PersonaResponse)
def actualizar_persona(
    persona_id: int,
    payload: PersonaUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza una persona existente."""
    persona = svc_personas.actualizar_persona(
        db,
        persona_id,
        nombre=payload.nombre,
        apellido=payload.apellido,
        documento=payload.documento,
        telefono=payload.telefono,
        activo=payload.activo,
    )
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    db.refresh(persona)
    return persona

