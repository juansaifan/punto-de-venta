"""Tests del API Configuración."""
from fastapi.testclient import TestClient


def test_listar_usuarios(client: TestClient) -> None:
    """Listar usuarios devuelve lista."""
    r = client.get("/api/configuracion/usuarios")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_listar_roles(client: TestClient) -> None:
    """Listar roles devuelve lista."""
    r = client.get("/api/configuracion/roles")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_crear_usuario_ok(client: TestClient) -> None:
    """Crear usuario devuelve 201 y el usuario creado."""
    payload = {"nombre": "usuario_test"}
    r = client.post("/api/configuracion/usuarios", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["nombre"] == "usuario_test"
    assert data["activo"] is True


def test_crear_usuario_nombre_obligatorio(client: TestClient) -> None:
    """Crear usuario sin nombre devuelve 422."""
    r = client.post("/api/configuracion/usuarios", json={})
    assert r.status_code == 422


def test_crear_rol_ok(client: TestClient) -> None:
    """Crear rol devuelve 201 y el rol creado."""
    payload = {"codigo": "ADMIN", "nombre": "Administrador"}
    r = client.post("/api/configuracion/roles", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["codigo"] == "ADMIN"
    assert data["nombre"] == "Administrador"


def test_crear_rol_campos_obligatorios(client: TestClient) -> None:
    """Crear rol sin código o nombre devuelve 422."""
    r = client.post("/api/configuracion/roles", json={"codigo": "SIN_NOMBRE"})
    assert r.status_code == 422


def test_obtener_usuario_ok(client: TestClient) -> None:
    """Obtener usuario por ID devuelve el usuario creado."""
    crear = client.post("/api/configuracion/usuarios", json={"nombre": "juan"})
    assert crear.status_code == 201
    usuario_id = crear.json()["id"]
    r = client.get(f"/api/configuracion/usuarios/{usuario_id}")
    assert r.status_code == 200
    assert r.json()["id"] == usuario_id
    assert r.json()["nombre"] == "juan"
    assert r.json()["activo"] is True


def test_obtener_usuario_404(client: TestClient) -> None:
    """Obtener usuario inexistente devuelve 404."""
    r = client.get("/api/configuracion/usuarios/99999")
    assert r.status_code == 404


def test_obtener_rol_ok(client: TestClient) -> None:
    """Obtener rol por ID devuelve el rol creado."""
    crear = client.post("/api/configuracion/roles", json={"codigo": "VEND", "nombre": "Vendedor"})
    assert crear.status_code == 201
    rol_id = crear.json()["id"]
    r = client.get(f"/api/configuracion/roles/{rol_id}")
    assert r.status_code == 200
    assert r.json()["id"] == rol_id
    assert r.json()["codigo"] == "VEND"
    assert r.json()["nombre"] == "Vendedor"


def test_obtener_rol_404(client: TestClient) -> None:
    """Obtener rol inexistente devuelve 404."""
    r = client.get("/api/configuracion/roles/99999")
    assert r.status_code == 404


def test_actualizar_usuario_activo_desactivar(client: TestClient) -> None:
    """PATCH usuario con activo=false desactiva al usuario."""
    crear = client.post("/api/configuracion/usuarios", json={"nombre": "para_desactivar"})
    assert crear.status_code == 201
    usuario_id = crear.json()["id"]
    r = client.patch(f"/api/configuracion/usuarios/{usuario_id}", json={"activo": False})
    assert r.status_code == 200
    assert r.json()["activo"] is False
    r_get = client.get(f"/api/configuracion/usuarios/{usuario_id}")
    assert r_get.json()["activo"] is False


def test_actualizar_usuario_activo_reactivar(client: TestClient) -> None:
    """PATCH usuario con activo=true reactiva al usuario."""
    crear = client.post("/api/configuracion/usuarios", json={"nombre": "para_reactivar"})
    assert crear.status_code == 201
    usuario_id = crear.json()["id"]
    client.patch(f"/api/configuracion/usuarios/{usuario_id}", json={"activo": False})
    r = client.patch(f"/api/configuracion/usuarios/{usuario_id}", json={"activo": True})
    assert r.status_code == 200
    assert r.json()["activo"] is True


def test_actualizar_usuario_404(client: TestClient) -> None:
    """PATCH usuario inexistente devuelve 404."""
    r = client.patch("/api/configuracion/usuarios/99999", json={"activo": False})
    assert r.status_code == 404


def test_actualizar_usuario_sin_activo_422(client: TestClient) -> None:
    """PATCH usuario sin enviar activo ni rol_id devuelve 422."""
    crear = client.post("/api/configuracion/usuarios", json={"nombre": "x"})
    usuario_id = crear.json()["id"]
    r = client.patch(f"/api/configuracion/usuarios/{usuario_id}", json={})
    assert r.status_code == 422


def test_asignar_rol_a_usuario_ok(client: TestClient) -> None:
    """PATCH usuario con rol_id asigna el rol y GET devuelve rol_id."""
    crear_u = client.post("/api/configuracion/usuarios", json={"nombre": "user_rol"})
    assert crear_u.status_code == 201
    usuario_id = crear_u.json()["id"]
    crear_r = client.post("/api/configuracion/roles", json={"codigo": "ADMIN", "nombre": "Administrador"})
    assert crear_r.status_code == 201
    rol_id = crear_r.json()["id"]
    r = client.patch(f"/api/configuracion/usuarios/{usuario_id}", json={"rol_id": rol_id})
    assert r.status_code == 200
    assert r.json()["rol_id"] == rol_id
    r_get = client.get(f"/api/configuracion/usuarios/{usuario_id}")
    assert r_get.json()["rol_id"] == rol_id


def test_desasignar_rol_a_usuario_ok(client: TestClient) -> None:
    """PATCH usuario con rol_id null quita el rol."""
    crear_u = client.post("/api/configuracion/usuarios", json={"nombre": "user_sin_rol"})
    usuario_id = crear_u.json()["id"]
    crear_r = client.post("/api/configuracion/roles", json={"codigo": "VEND", "nombre": "Vendedor"})
    rol_id = crear_r.json()["id"]
    client.patch(f"/api/configuracion/usuarios/{usuario_id}", json={"rol_id": rol_id})
    r = client.patch(f"/api/configuracion/usuarios/{usuario_id}", json={"rol_id": None})
    assert r.status_code == 200
    assert r.json()["rol_id"] is None


def test_asignar_rol_usuario_404(client: TestClient) -> None:
    """PATCH usuario con rol_id inexistente devuelve 404."""
    crear = client.post("/api/configuracion/usuarios", json={"nombre": "u"})
    usuario_id = crear.json()["id"]
    r = client.patch(f"/api/configuracion/usuarios/{usuario_id}", json={"rol_id": 99999})
    assert r.status_code == 404


def test_obtener_usuario_incluye_rol_id(client: TestClient) -> None:
    """GET usuario devuelve rol_id (null si no tiene)."""
    crear = client.post("/api/configuracion/usuarios", json={"nombre": "con_rol_id"})
    usuario_id = crear.json()["id"]
    r = client.get(f"/api/configuracion/usuarios/{usuario_id}")
    assert r.status_code == 200
    assert "rol_id" in r.json()
    assert r.json()["rol_id"] is None


def test_actualizar_rol_nombre_ok(client: TestClient) -> None:
    """PATCH rol con nombre actualiza el rol."""
    crear = client.post("/api/configuracion/roles", json={"codigo": "CAJERO", "nombre": "Cajero"})
    assert crear.status_code == 201
    rol_id = crear.json()["id"]
    r = client.patch(f"/api/configuracion/roles/{rol_id}", json={"nombre": "Cajero principal"})
    assert r.status_code == 200
    assert r.json()["codigo"] == "CAJERO"
    assert r.json()["nombre"] == "Cajero principal"
    r_get = client.get(f"/api/configuracion/roles/{rol_id}")
    assert r_get.json()["nombre"] == "Cajero principal"


def test_actualizar_rol_codigo_ok(client: TestClient) -> None:
    """PATCH rol con codigo actualiza el rol."""
    crear = client.post("/api/configuracion/roles", json={"codigo": "VEND", "nombre": "Vendedor"})
    assert crear.status_code == 201
    rol_id = crear.json()["id"]
    r = client.patch(f"/api/configuracion/roles/{rol_id}", json={"codigo": "VENDEDOR"})
    assert r.status_code == 200
    assert r.json()["codigo"] == "VENDEDOR"
    assert r.json()["nombre"] == "Vendedor"


def test_actualizar_rol_404(client: TestClient) -> None:
    """PATCH rol inexistente devuelve 404."""
    r = client.patch("/api/configuracion/roles/99999", json={"nombre": "X"})
    assert r.status_code == 404


def test_actualizar_rol_sin_campos_422(client: TestClient) -> None:
    """PATCH rol sin codigo ni nombre devuelve 422."""
    crear = client.post("/api/configuracion/roles", json={"codigo": "R1", "nombre": "Rol 1"})
    rol_id = crear.json()["id"]
    r = client.patch(f"/api/configuracion/roles/{rol_id}", json={})
    assert r.status_code == 422


def test_actualizar_rol_codigo_duplicado_400(client: TestClient) -> None:
    """PATCH rol con código ya usado por otro rol devuelve 400."""
    client.post("/api/configuracion/roles", json={"codigo": "UNICO", "nombre": "Rol A"})
    crear2 = client.post("/api/configuracion/roles", json={"codigo": "OTRO", "nombre": "Rol B"})
    assert crear2.status_code == 201
    rol_id_b = crear2.json()["id"]
    r = client.patch(f"/api/configuracion/roles/{rol_id_b}", json={"codigo": "UNICO"})
    assert r.status_code == 400
    assert "ya existe" in r.json()["detail"].lower()


# --- Medios de pago ---


def test_listar_medios_pago_vacio(client: TestClient) -> None:
    """Listar medios de pago sin datos devuelve lista vacía."""
    r = client.get("/api/configuracion/medios-pago")
    assert r.status_code == 200
    assert r.json() == []


def test_crear_medio_pago_ok(client: TestClient) -> None:
    """Crear medio de pago devuelve 201 y el recurso con codigo y nombre."""
    r = client.post(
        "/api/configuracion/medios-pago",
        json={"codigo": "EFECTIVO", "nombre": "Efectivo", "comision": 0},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["codigo"] == "EFECTIVO"
    assert data["nombre"] == "Efectivo"
    assert data["activo"] is True
    assert data["comision"] == 0.0
    assert data["dias_acreditacion"] == 0


def test_crear_medio_pago_con_comision_y_dias(client: TestClient) -> None:
    """Crear medio de pago con comisión y días de acreditación."""
    r = client.post(
        "/api/configuracion/medios-pago",
        json={
            "codigo": "TARJETA_CREDITO",
            "nombre": "Tarjeta de crédito",
            "comision": 2.5,
            "dias_acreditacion": 30,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["comision"] == 2.5
    assert data["dias_acreditacion"] == 30


def test_obtener_medio_pago_por_id(client: TestClient) -> None:
    """Obtener medio de pago por ID devuelve el recurso."""
    crear = client.post(
        "/api/configuracion/medios-pago",
        json={"codigo": "TRANSFERENCIA", "nombre": "Transferencia"},
    )
    medio_id = crear.json()["id"]
    r = client.get(f"/api/configuracion/medios-pago/{medio_id}")
    assert r.status_code == 200
    assert r.json()["codigo"] == "TRANSFERENCIA"


def test_obtener_medio_pago_404(client: TestClient) -> None:
    """Obtener medio de pago inexistente devuelve 404."""
    r = client.get("/api/configuracion/medios-pago/99999")
    assert r.status_code == 404


def test_crear_medio_pago_codigo_duplicado_409(client: TestClient) -> None:
    """Crear medio de pago con código ya existente devuelve 409."""
    client.post(
        "/api/configuracion/medios-pago",
        json={"codigo": "EFECTIVO", "nombre": "Efectivo"},
    )
    r = client.post(
        "/api/configuracion/medios-pago",
        json={"codigo": "EFECTIVO", "nombre": "Otro efectivo"},
    )
    assert r.status_code == 409
    assert "ya existe" in r.json()["detail"].lower()


def test_listar_medios_pago_solo_activos(client: TestClient) -> None:
    """Filtro solo_activos=true devuelve solo medios activos."""
    client.post(
        "/api/configuracion/medios-pago",
        json={"codigo": "ACT", "nombre": "Activo", "activo": True},
    )
    client.post(
        "/api/configuracion/medios-pago",
        json={"codigo": "INACT", "nombre": "Inactivo", "activo": False},
    )
    r = client.get("/api/configuracion/medios-pago?solo_activos=true")
    assert r.status_code == 200
    codigos = [m["codigo"] for m in r.json()]
    assert "ACT" in codigos
    assert "INACT" not in codigos


def test_actualizar_medio_pago_ok(client: TestClient) -> None:
    """PATCH medio de pago actualiza nombre, activo, comision."""
    crear = client.post(
        "/api/configuracion/medios-pago",
        json={"codigo": "MP", "nombre": "Medio", "comision": 0},
    )
    medio_id = crear.json()["id"]
    r = client.patch(
        f"/api/configuracion/medios-pago/{medio_id}",
        json={"activo": False, "comision": 1.5, "dias_acreditacion": 2},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["activo"] is False
    assert data["comision"] == 1.5
    assert data["dias_acreditacion"] == 2
    assert data["codigo"] == "MP"


def test_actualizar_medio_pago_sin_campos_422(client: TestClient) -> None:
    """PATCH medio de pago sin ningún campo devuelve 422."""
    crear = client.post(
        "/api/configuracion/medios-pago",
        json={"codigo": "X", "nombre": "X"},
    )
    medio_id = crear.json()["id"]
    r = client.patch(f"/api/configuracion/medios-pago/{medio_id}", json={})
    assert r.status_code == 422


# --- Empresa (datos del negocio) ---


def test_obtener_empresa_sin_config_404(client: TestClient) -> None:
    """GET empresa sin datos configurados devuelve 404."""
    r = client.get("/api/configuracion/empresa")
    assert r.status_code == 404
    assert "no configurados" in r.json()["detail"].lower()


def test_put_empresa_crea_registro(client: TestClient) -> None:
    """PUT empresa con nombre crea el registro y devuelve datos."""
    r = client.put(
        "/api/configuracion/empresa",
        json={
            "nombre": "Mi Negocio",
            "razon_social": "Mi Negocio S.A.",
            "cuit": "20-12345678-9",
            "direccion": "Calle Falsa 123",
            "email": "contacto@minegocio.com",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nombre"] == "Mi Negocio"
    assert data["razon_social"] == "Mi Negocio S.A."
    assert data["cuit"] == "20-12345678-9"
    assert data["direccion"] == "Calle Falsa 123"
    assert data["email"] == "contacto@minegocio.com"
    assert data["id"] == 1


def test_get_empresa_devuelve_datos(client: TestClient) -> None:
    """GET empresa después de PUT devuelve los datos guardados."""
    client.put(
        "/api/configuracion/empresa",
        json={"nombre": "Empresa Test", "telefono": "111-2222"},
    )
    r = client.get("/api/configuracion/empresa")
    assert r.status_code == 200
    data = r.json()
    assert data["nombre"] == "Empresa Test"
    assert data["telefono"] == "111-2222"


def test_put_empresa_actualiza_parcial(client: TestClient) -> None:
    """PUT empresa actualiza solo los campos enviados."""
    client.put(
        "/api/configuracion/empresa",
        json={"nombre": "Original", "cuit": "20-11111111-1"},
    )
    r = client.put(
        "/api/configuracion/empresa",
        json={"condicion_fiscal": "Monotributista", "email": "nuevo@mail.com"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nombre"] == "Original"
    assert data["cuit"] == "20-11111111-1"
    assert data["condicion_fiscal"] == "Monotributista"
    assert data["email"] == "nuevo@mail.com"


# --- Sucursales ---


def test_listar_sucursales_vacio(client: TestClient) -> None:
    """Listar sucursales sin datos devuelve lista vacía."""
    r = client.get("/api/configuracion/sucursales")
    assert r.status_code == 200
    assert r.json() == []


def test_crear_sucursal_ok(client: TestClient) -> None:
    """Crear sucursal devuelve 201 y el recurso."""
    r = client.post(
        "/api/configuracion/sucursales",
        json={"nombre": "Sucursal Centro", "direccion": "Av. Principal 100", "telefono": "555-0001"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["nombre"] == "Sucursal Centro"
    assert data["direccion"] == "Av. Principal 100"
    assert data["telefono"] == "555-0001"
    assert data["activo"] is True


def test_obtener_sucursal_por_id(client: TestClient) -> None:
    """Obtener sucursal por ID devuelve el recurso."""
    crear = client.post(
        "/api/configuracion/sucursales",
        json={"nombre": "Sucursal Norte"},
    )
    suc_id = crear.json()["id"]
    r = client.get(f"/api/configuracion/sucursales/{suc_id}")
    assert r.status_code == 200
    assert r.json()["nombre"] == "Sucursal Norte"


def test_obtener_sucursal_404(client: TestClient) -> None:
    """Obtener sucursal inexistente devuelve 404."""
    r = client.get("/api/configuracion/sucursales/99999")
    assert r.status_code == 404


def test_listar_sucursales_solo_activas(client: TestClient) -> None:
    """Filtro solo_activas=true devuelve solo sucursales activas."""
    client.post("/api/configuracion/sucursales", json={"nombre": "Activa", "activo": True})
    client.post("/api/configuracion/sucursales", json={"nombre": "Inactiva", "activo": False})
    r = client.get("/api/configuracion/sucursales?solo_activas=true")
    assert r.status_code == 200
    nombres = [s["nombre"] for s in r.json()]
    assert "Activa" in nombres
    assert "Inactiva" not in nombres


def test_actualizar_sucursal_ok(client: TestClient) -> None:
    """PATCH sucursal actualiza nombre y activo."""
    crear = client.post(
        "/api/configuracion/sucursales",
        json={"nombre": "Suc Original", "direccion": "Calle 1"},
    )
    suc_id = crear.json()["id"]
    r = client.patch(
        f"/api/configuracion/sucursales/{suc_id}",
        json={"nombre": "Suc Actualizada", "activo": False},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nombre"] == "Suc Actualizada"
    assert data["activo"] is False
    assert data["direccion"] == "Calle 1"


def test_actualizar_sucursal_sin_campos_422(client: TestClient) -> None:
    """PATCH sucursal sin ningún campo devuelve 422."""
    crear = client.post("/api/configuracion/sucursales", json={"nombre": "X"})
    suc_id = crear.json()["id"]
    r = client.patch(f"/api/configuracion/sucursales/{suc_id}", json={})
    assert r.status_code == 422


# --- Permisos (ROADMAP Fase 7) ---


def test_listar_permisos(client: TestClient) -> None:
    """Listar permisos devuelve lista."""
    r = client.get("/api/configuracion/permisos")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_crear_permiso_ok(client: TestClient) -> None:
    """Crear permiso devuelve 201 y el permiso creado."""
    r = client.post(
        "/api/configuracion/permisos",
        json={"codigo": "ventas.crear", "nombre": "Crear ventas", "descripcion": "Registrar ventas"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["codigo"] == "ventas.crear"
    assert data["nombre"] == "Crear ventas"
    assert data["descripcion"] == "Registrar ventas"


def test_crear_permiso_codigo_duplicado_400(client: TestClient) -> None:
    """Crear permiso con código duplicado devuelve 400."""
    client.post("/api/configuracion/permisos", json={"codigo": "dup", "nombre": "Uno"})
    r = client.post("/api/configuracion/permisos", json={"codigo": "dup", "nombre": "Dos"})
    assert r.status_code == 400


def test_obtener_permiso_ok(client: TestClient) -> None:
    """Obtener permiso por ID devuelve el permiso."""
    crear = client.post("/api/configuracion/permisos", json={"codigo": "p.get", "nombre": "Ver"})
    perm_id = crear.json()["id"]
    r = client.get(f"/api/configuracion/permisos/{perm_id}")
    assert r.status_code == 200
    assert r.json()["id"] == perm_id
    assert r.json()["codigo"] == "p.get"


def test_obtener_permiso_404(client: TestClient) -> None:
    """Obtener permiso inexistente devuelve 404."""
    r = client.get("/api/configuracion/permisos/99999")
    assert r.status_code == 404


def test_roles_permisos_vacio(client: TestClient) -> None:
    """GET roles/{id}/permisos sin permisos asignados devuelve lista vacía."""
    crear = client.post("/api/configuracion/roles", json={"codigo": "R1", "nombre": "Rol 1"})
    rol_id = crear.json()["id"]
    r = client.get(f"/api/configuracion/roles/{rol_id}/permisos")
    assert r.status_code == 200
    assert r.json() == []


def test_roles_permisos_404(client: TestClient) -> None:
    """GET roles/99999/permisos devuelve 404."""
    r = client.get("/api/configuracion/roles/99999/permisos")
    assert r.status_code == 404


def test_asignar_permisos_a_rol_ok(client: TestClient) -> None:
    """PUT roles/{id}/permisos asigna permisos y devuelve la lista."""
    p1 = client.post("/api/configuracion/permisos", json={"codigo": "a", "nombre": "Perm A"})
    p2 = client.post("/api/configuracion/permisos", json={"codigo": "b", "nombre": "Perm B"})
    rol = client.post("/api/configuracion/roles", json={"codigo": "R2", "nombre": "Rol 2"})
    rol_id = rol.json()["id"]
    r = client.put(
        f"/api/configuracion/roles/{rol_id}/permisos",
        json={"permiso_ids": [p1.json()["id"], p2.json()["id"]]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["rol_id"] == rol_id
    assert len(data["permisos"]) == 2
    codigos = [x["codigo"] for x in data["permisos"]]
    assert "a" in codigos and "b" in codigos

    r2 = client.get(f"/api/configuracion/roles/{rol_id}/permisos")
    assert r2.status_code == 200
    assert len(r2.json()) == 2


def test_asignar_permisos_rol_404(client: TestClient) -> None:
    """PUT roles/99999/permisos devuelve 404."""
    r = client.put("/api/configuracion/roles/99999/permisos", json={"permiso_ids": []})
    assert r.status_code == 404


def test_asignar_permisos_permiso_inexistente_404(client: TestClient) -> None:
    """PUT roles/{id}/permisos con permiso_id inexistente devuelve 404."""
    rol = client.post("/api/configuracion/roles", json={"codigo": "R3", "nombre": "Rol 3"})
    r = client.put(
        f"/api/configuracion/roles/{rol.json()['id']}/permisos",
        json={"permiso_ids": [99999]},
    )
    assert r.status_code == 404


# --- Parámetros de sistema ---


def test_parametro_inexistente_devuelve_objeto_vacio(client: TestClient) -> None:
    """GET parametros/{clave} con clave no guardada devuelve 200 y {}."""
    r = client.get("/api/configuracion/parametros/clave_que_no_existe")
    assert r.status_code == 200
    assert r.json() == {}


def test_put_parametro_luego_get_devuelve_mismo_valor(client: TestClient) -> None:
    """PUT parametros/{clave} y GET devuelve el mismo objeto."""
    payload = {"almacen_id": 1, "moneda": "MXN"}
    put_r = client.put("/api/configuracion/parametros/facturacion", json=payload)
    assert put_r.status_code == 200
    assert put_r.json() == payload
    get_r = client.get("/api/configuracion/parametros/facturacion")
    assert get_r.status_code == 200
    assert get_r.json() == payload


def test_put_parametro_sobrescribe_y_get_refleja_cambio(client: TestClient) -> None:
    """PUT sobrescribe valor; GET refleja el nuevo valor."""
    client.put("/api/configuracion/parametros/caja", json={"a": 1})
    nuevo = {"caja_abierta": True, "monto": 100.5}
    put_r = client.put("/api/configuracion/parametros/caja", json=nuevo)
    assert put_r.status_code == 200
    assert put_r.json() == nuevo
    get_r = client.get("/api/configuracion/parametros/caja")
    assert get_r.status_code == 200
    assert get_r.json() == nuevo


def test_put_parametro_clave_vacia_400(client: TestClient) -> None:
    """PUT parametros con clave solo espacios devuelve 400."""
    r = client.put("/api/configuracion/parametros/  ", json={})
    assert r.status_code == 400


def test_put_parametro_body_no_objeto_422(client: TestClient) -> None:
    """PUT con body que no es objeto (ej. array) devuelve 422."""
    r = client.put("/api/configuracion/parametros/ok", json=[1, 2, 3])
    assert r.status_code == 422


def test_listar_parametros_vacio(client: TestClient) -> None:
    """GET parametros sin claves configuradas devuelve claves vacías."""
    r = client.get("/api/configuracion/parametros")
    assert r.status_code == 200
    assert r.json() == {"claves": []}


def test_listar_parametros_incluye_claves_guardadas(client: TestClient) -> None:
    """GET parametros devuelve las claves de los parámetros ya guardados."""
    client.put("/api/configuracion/parametros/facturacion", json={"almacen_id": 1})
    client.put("/api/configuracion/parametros/caja", json={"moneda": "MXN"})
    r = client.get("/api/configuracion/parametros")
    assert r.status_code == 200
    claves = r.json()["claves"]
    assert "caja" in claves
    assert "facturacion" in claves
    assert len(claves) == 2


# --- Configuración Caja (docs Módulo 9 §7) ---


def test_get_configuracion_caja_sin_config_devuelve_defaults(client: TestClient) -> None:
    """GET /configuracion/caja sin datos previos devuelve estructura por defecto."""
    r = client.get("/api/configuracion/caja")
    assert r.status_code == 200
    data = r.json()
    assert "monto_minimo_apertura" in data
    assert "obligar_arqueo" in data
    assert "permitir_cierre_con_diferencia" in data
    assert "requerir_autorizacion_supervisor_cierre" in data
    assert data["obligar_arqueo"] is True
    assert data["permitir_cierre_con_diferencia"] is False


def test_put_configuracion_caja_actualiza_y_get_refleja(client: TestClient) -> None:
    """PUT /configuracion/caja actualiza; GET devuelve los valores guardados."""
    payload = {"monto_minimo_apertura": 500, "permitir_cierre_con_diferencia": True}
    put_r = client.put("/api/configuracion/caja", json=payload)
    assert put_r.status_code == 200
    data = put_r.json()
    assert data["monto_minimo_apertura"] == 500
    assert data["permitir_cierre_con_diferencia"] is True
    get_r = client.get("/api/configuracion/caja")
    assert get_r.status_code == 200
    assert get_r.json()["monto_minimo_apertura"] == 500
    assert get_r.json()["permitir_cierre_con_diferencia"] is True


def test_put_configuracion_caja_body_no_objeto_422(client: TestClient) -> None:
    """PUT /configuracion/caja con body no objeto devuelve 422."""
    r = client.put("/api/configuracion/caja", json=[])
    assert r.status_code == 422


# --- Configuración Sistema (docs Módulo 9 §11) ---


def test_get_configuracion_sistema_sin_config_devuelve_defaults(client: TestClient) -> None:
    """GET /configuracion/sistema sin datos previos devuelve estructura por defecto."""
    r = client.get("/api/configuracion/sistema")
    assert r.status_code == 200
    data = r.json()
    assert "zona_horaria" in data
    assert "idioma" in data
    assert "formato_fecha" in data
    assert "formato_moneda" in data
    assert "tiempo_sesion_minutos" in data
    assert "registro_auditoria" in data
    assert data["idioma"] == "es"


def test_put_configuracion_sistema_actualiza_y_get_refleja(client: TestClient) -> None:
    """PUT /configuracion/sistema actualiza; GET devuelve los valores guardados."""
    payload = {"zona_horaria": "UTC", "idioma": "en", "tiempo_sesion_minutos": 30}
    put_r = client.put("/api/configuracion/sistema", json=payload)
    assert put_r.status_code == 200
    data = put_r.json()
    assert data["zona_horaria"] == "UTC"
    assert data["idioma"] == "en"
    assert data["tiempo_sesion_minutos"] == 30
    get_r = client.get("/api/configuracion/sistema")
    assert get_r.status_code == 200
    assert get_r.json()["zona_horaria"] == "UTC"
    assert get_r.json()["tiempo_sesion_minutos"] == 30


def test_put_configuracion_sistema_body_no_objeto_422(client: TestClient) -> None:
    """PUT /configuracion/sistema con body no objeto devuelve 422."""
    r = client.put("/api/configuracion/sistema", json="texto")
    assert r.status_code == 422


# --- Configuración Facturación (docs Módulo 9 §5) ---


def test_get_configuracion_facturacion_sin_config_devuelve_defaults(client: TestClient) -> None:
    """GET /configuracion/facturacion sin datos previos devuelve estructura por defecto."""
    r = client.get("/api/configuracion/facturacion")
    assert r.status_code == 200
    data = r.json()
    assert "habilitar_ticket" in data
    assert "habilitar_factura" in data
    assert "prefijo_factura" in data
    assert "formato_comprobante" in data
    assert data["habilitar_ticket"] is True


def test_put_configuracion_facturacion_actualiza_y_get_refleja(client: TestClient) -> None:
    """PUT /configuracion/facturacion actualiza; GET devuelve los valores guardados."""
    payload = {"habilitar_nota_credito": False, "prefijo_factura": "002"}
    put_r = client.put("/api/configuracion/facturacion", json=payload)
    assert put_r.status_code == 200
    assert put_r.json()["prefijo_factura"] == "002"
    assert put_r.json()["habilitar_nota_credito"] is False
    get_r = client.get("/api/configuracion/facturacion")
    assert get_r.status_code == 200
    assert get_r.json()["prefijo_factura"] == "002"


# --- Configuración POS (docs Módulo 9 §9) ---


def test_get_configuracion_pos_sin_config_devuelve_defaults(client: TestClient) -> None:
    """GET /configuracion/pos sin datos previos devuelve estructura por defecto."""
    r = client.get("/api/configuracion/pos")
    assert r.status_code == 200
    data = r.json()
    assert "modo_caja_rapida" in data
    assert "mostrar_precios" in data
    assert "impresion_automatica_tickets" in data
    assert data["mostrar_precios"] is True


def test_put_configuracion_pos_actualiza_y_get_refleja(client: TestClient) -> None:
    """PUT /configuracion/pos actualiza; GET devuelve los valores guardados."""
    payload = {"modo_caja_rapida": True, "sonidos_confirmacion": False}
    put_r = client.put("/api/configuracion/pos", json=payload)
    assert put_r.status_code == 200
    assert put_r.json()["modo_caja_rapida"] is True
    get_r = client.get("/api/configuracion/pos")
    assert get_r.json()["sonidos_confirmacion"] is False


# --- Configuración Inventario (docs Módulo 9 §8) ---


def test_get_configuracion_inventario_sin_config_devuelve_defaults(client: TestClient) -> None:
    """GET /configuracion/inventario sin datos previos devuelve estructura por defecto."""
    r = client.get("/api/configuracion/inventario")
    assert r.status_code == 200
    data = r.json()
    assert "stock_minimo_global" in data
    assert "control_vencimientos" in data
    assert "alertas_reposicion" in data
    assert data["control_lotes"] is True


def test_put_configuracion_inventario_actualiza_y_get_refleja(client: TestClient) -> None:
    """PUT /configuracion/inventario actualiza; GET devuelve los valores guardados."""
    payload = {"stock_minimo_global": 10, "alertas_reposicion": False}
    put_r = client.put("/api/configuracion/inventario", json=payload)
    assert put_r.status_code == 200
    assert put_r.json()["stock_minimo_global"] == 10
    get_r = client.get("/api/configuracion/inventario")
    assert get_r.json()["alertas_reposicion"] is False


# --- Configuracion Integraciones (docs Modulo 9 ss10) ---


def test_get_configuracion_integraciones_sin_config_devuelve_defaults(client: TestClient) -> None:
    """GET /configuracion/integraciones sin datos previos devuelve estructura por defecto."""
    r = client.get("/api/configuracion/integraciones")
    assert r.status_code == 200
    data = r.json()
    assert "credenciales_fiscales" in data
    assert "impresoras" in data
    assert "balanzas" in data
    assert "pasarelas_pago" in data
    assert data["balanzas"]["habilitada"] is False
    assert data["credenciales_fiscales"]["modo_produccion"] is False


def test_put_configuracion_integraciones_actualiza_seccion(client: TestClient) -> None:
    """PUT /configuracion/integraciones actualiza una seccion; GET refleja el cambio."""
    payload = {"balanzas": {"habilitada": True, "puerto": "COM3", "baudrate": 4800}}
    put_r = client.put("/api/configuracion/integraciones", json=payload)
    assert put_r.status_code == 200
    data = put_r.json()
    assert data["balanzas"]["habilitada"] is True
    assert data["balanzas"]["puerto"] == "COM3"
    assert data["balanzas"]["baudrate"] == 4800
    get_r = client.get("/api/configuracion/integraciones")
    assert get_r.json()["balanzas"]["habilitada"] is True


def test_put_configuracion_integraciones_actualiza_credenciales(client: TestClient) -> None:
    """PUT /configuracion/integraciones actualiza credenciales fiscales."""
    payload = {"credenciales_fiscales": {"cuit": "20123456789", "punto_venta": 5, "modo_produccion": True}}
    put_r = client.put("/api/configuracion/integraciones", json=payload)
    assert put_r.status_code == 200
    data = put_r.json()
    assert data["credenciales_fiscales"]["cuit"] == "20123456789"
    assert data["credenciales_fiscales"]["punto_venta"] == 5
    assert data["credenciales_fiscales"]["modo_produccion"] is True


def test_put_configuracion_integraciones_body_no_objeto_422(client: TestClient) -> None:
    """PUT /configuracion/integraciones con body no objeto retorna 422."""
    r = client.put("/api/configuracion/integraciones", content=b'"cadena"', headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_get_configuracion_integraciones_mantiene_defaults_no_enviados(client: TestClient) -> None:
    """PUT parcial no borra otras secciones de integraciones."""
    payload = {"pasarelas_pago": {"mercadopago_habilitado": True, "mercadopago_token": "tok123"}}
    client.put("/api/configuracion/integraciones", json=payload)
    r = client.get("/api/configuracion/integraciones")
    data = r.json()
    assert data["pasarelas_pago"]["mercadopago_habilitado"] is True
    assert "balanzas" in data
    assert "impresoras" in data


# --- Configuracion Dashboard (objetivos) ---


def test_get_configuracion_dashboard_sin_config_devuelve_defaults(client: TestClient) -> None:
    """GET /configuracion/dashboard sin datos previos devuelve estructura por defecto."""
    r = client.get("/api/configuracion/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "objetivo_ventas_diario" in data
    assert "objetivo_ventas_semanal" in data
    assert "objetivo_ventas_mensual" in data
    assert "mostrar_margen" in data
    assert data["mostrar_margen"] is True


def test_put_configuracion_dashboard_actualiza_y_get_refleja(client: TestClient) -> None:
    """PUT /configuracion/dashboard actualiza objetivos; GET devuelve los valores guardados."""
    payload = {"objetivo_ventas_diario": 50000, "objetivo_ventas_mensual": 1500000, "mostrar_margen": False}
    put_r = client.put("/api/configuracion/dashboard", json=payload)
    assert put_r.status_code == 200
    data = put_r.json()
    assert data["objetivo_ventas_diario"] == 50000
    assert data["objetivo_ventas_mensual"] == 1500000
    assert data["mostrar_margen"] is False
    get_r = client.get("/api/configuracion/dashboard")
    assert get_r.json()["objetivo_ventas_diario"] == 50000


def test_put_configuracion_dashboard_body_no_objeto_422(client: TestClient) -> None:
    """PUT /configuracion/dashboard con body no objeto retorna 422."""
    r = client.put("/api/configuracion/dashboard", content=b'"cadena"', headers={"Content-Type": "application/json"})
    assert r.status_code == 422


# --- Resumen consolidado ---


def test_get_resumen_configuracion_estructura(client: TestClient) -> None:
    """GET /configuracion/resumen devuelve todas las secciones."""
    r = client.get("/api/configuracion/resumen")
    assert r.status_code == 200
    data = r.json()
    assert "empresa" in data
    assert "caja" in data
    assert "sistema" in data
    assert "facturacion" in data
    assert "pos" in data
    assert "inventario" in data
    assert "integraciones" in data
    assert "dashboard" in data
    assert "sucursales_activas" in data
    assert "medios_pago_activos" in data


def test_get_resumen_configuracion_refleja_cambios(client: TestClient) -> None:
    """GET /configuracion/resumen refleja valores guardados en secciones."""
    client.put("/api/configuracion/empresa", json={"nombre": "Negocio Test"})
    client.put("/api/configuracion/caja", json={"monto_minimo_apertura": 500})
    r = client.get("/api/configuracion/resumen")
    assert r.status_code == 200
    data = r.json()
    assert data["empresa"]["nombre"] == "Negocio Test"
    assert data["caja"]["monto_minimo_apertura"] == 500


# --- Reset (DELETE) de parametros ---


def test_delete_parametro_existente(client: TestClient) -> None:
    """DELETE /configuracion/parametros/{clave} elimina el parametro; GET devuelve {} luego."""
    client.put("/api/configuracion/parametros/param_test", json={"x": 1})
    r = client.delete("/api/configuracion/parametros/param_test")
    assert r.status_code == 200
    data = r.json()
    assert data["eliminado"] is True
    assert data["clave"] == "param_test"
    get_r = client.get("/api/configuracion/parametros/param_test")
    assert get_r.json() == {}


def test_delete_parametro_inexistente_404(client: TestClient) -> None:
    """DELETE /configuracion/parametros/{clave} con clave inexistente retorna 404."""
    r = client.delete("/api/configuracion/parametros/clave_que_no_existe_xyz")
    assert r.status_code == 404


def test_delete_parametro_resetea_caja_a_defaults(client: TestClient) -> None:
    """Al eliminar el parametro 'caja', GET /configuracion/caja devuelve defaults."""
    client.put("/api/configuracion/caja", json={"monto_minimo_apertura": 999})
    check = client.get("/api/configuracion/caja")
    assert check.json()["monto_minimo_apertura"] == 999
    client.delete("/api/configuracion/parametros/caja")
    r = client.get("/api/configuracion/caja")
    assert r.json()["monto_minimo_apertura"] == 0
