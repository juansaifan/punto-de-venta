"""Tests de la API de personas (dominio Personas)."""
from fastapi.testclient import TestClient


def test_listar_personas_vacio(client: TestClient) -> None:
    """Listar personas sin datos devuelve lista vacía."""
    r = client.get("/api/personas")
    assert r.status_code == 200
    assert r.json() == []


def test_crear_persona_ok(client: TestClient, persona_datos: dict) -> None:
    """Crear persona con datos válidos devuelve 201 y el recurso."""
    r = client.post("/api/personas", json=persona_datos)
    assert r.status_code == 201
    data = r.json()
    assert data["nombre"] == persona_datos["nombre"]
    assert data["apellido"] == persona_datos["apellido"]
    assert data["telefono"] == persona_datos["telefono"]
    assert "id" in data
    assert data["activo"] is True


def test_obtener_persona_por_id_ok(client: TestClient, persona_datos: dict) -> None:
    """Crear persona y obtenerla por ID devuelve el mismo recurso."""
    crear = client.post("/api/personas", json=persona_datos)
    assert crear.status_code == 201
    pid = crear.json()["id"]
    r = client.get(f"/api/personas/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid
    assert r.json()["nombre"] == persona_datos["nombre"]


def test_obtener_persona_por_id_404(client: TestClient) -> None:
    """Obtener persona por ID inexistente devuelve 404."""
    r = client.get("/api/personas/99999")
    assert r.status_code == 404


def test_actualizar_persona_ok(client: TestClient, persona_datos: dict) -> None:
    """Actualizar persona existente devuelve 200 y datos actualizados."""
    crear = client.post("/api/personas", json=persona_datos)
    pid = crear.json()["id"]
    r = client.patch(
        f"/api/personas/{pid}",
        json={"nombre": "María", "apellido": "García"},
    )
    assert r.status_code == 200
    assert r.json()["nombre"] == "María"
    assert r.json()["apellido"] == "García"


def test_actualizar_persona_404(client: TestClient) -> None:
    """Actualizar persona inexistente devuelve 404."""
    r = client.patch(
        "/api/personas/99999",
        json={"nombre": "Algo"},
    )
    assert r.status_code == 404


def test_listar_personas_incluye_creadas(client: TestClient, persona_datos: dict) -> None:
    """Después de crear personas, listar las incluye."""
    client.post("/api/personas", json=persona_datos)
    otra = {
        "nombre": "Ana",
        "apellido": "López",
        "documento": None,
        "telefono": None,
        "activo": True,
    }
    client.post("/api/personas", json=otra)
    r = client.get("/api/personas?activo_only=false")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2
    nombres = [p["nombre"] for p in items]
    assert "Juan" in nombres
    assert "Ana" in nombres


def test_crear_y_listar_clientes(client: TestClient, persona_datos: dict) -> None:
    """Crear un cliente asociado a persona y listarlo."""
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    body = {
        "persona_id": persona_id,
        "segmento": "cliente frecuente",
        "condicion_pago": "30 días",
        "limite_credito": 1000.0,
        "estado": "ACTIVO",
        "observaciones": "Cliente de prueba",
    }
    r_cliente = client.post("/api/personas/clientes", json=body)
    assert r_cliente.status_code == 201
    data = r_cliente.json()
    assert data["persona_id"] == persona_id
    assert data["segmento"] == "cliente frecuente"

    # Listado
    r_list = client.get("/api/personas/clientes")
    assert r_list.status_code == 200
    items = r_list.json()
    assert any(c["id"] == data["id"] for c in items)


def test_crear_cliente_persona_inexistente_404(client: TestClient) -> None:
    """No se puede crear un cliente para una persona inexistente."""
    body = {"persona_id": 99999}
    r = client.post("/api/personas/clientes", json=body)
    assert r.status_code == 404


def test_crear_y_listar_proveedores(client: TestClient, persona_datos: dict) -> None:
    """Crear un proveedor asociado a persona y listarlo."""
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    body = {
        "persona_id": persona_id,
        "cuit": "20-12345678-9",
        "condiciones_comerciales": "Entrega semanal",
        "condiciones_pago": "Contado",
        "lista_precios": "Lista mayorista",
        "estado": "ACTIVO",
    }
    r_proveedor = client.post("/api/personas/proveedores", json=body)
    assert r_proveedor.status_code == 201
    data = r_proveedor.json()
    assert data["persona_id"] == persona_id
    assert data["cuit"] == "20-12345678-9"

    # Listado
    r_list = client.get("/api/personas/proveedores")
    assert r_list.status_code == 200
    items = r_list.json()
    assert any(p["id"] == data["id"] for p in items)


def test_crear_proveedor_persona_inexistente_404(client: TestClient) -> None:
    """No se puede crear un proveedor para una persona inexistente."""
    body = {"persona_id": 99999}
    r = client.post("/api/personas/proveedores", json=body)
    assert r.status_code == 404


def test_crear_empleado_y_contacto_basico(client: TestClient, persona_datos: dict) -> None:
    """Crear empleado y contacto asociados a persona."""
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_empleado = client.post(
        "/api/personas/empleados",
        json={
            "persona_id": persona_id,
            "documento": "12345678",
            "cargo": "Cajero",
            "estado": "ACTIVO",
        },
    )
    assert r_empleado.status_code == 201
    emp = r_empleado.json()
    assert emp["persona_id"] == persona_id
    assert emp["cargo"] == "Cajero"

    r_contacto = client.post(
        "/api/personas/contactos",
        json={
            "persona_id": persona_id,
            "nombre": "Contacto Admin",
            "cargo": "Administración",
            "telefono": "123456",
            "email": "admin@example.com",
        },
    )
    assert r_contacto.status_code == 201
    cont = r_contacto.json()
    assert cont["persona_id"] == persona_id
    assert cont["nombre"] == "Contacto Admin"

    # Listar contactos filtrando por persona
    r_list = client.get(f"/api/personas/contactos?persona_id={persona_id}")
    assert r_list.status_code == 200
    items = r_list.json()
    assert any(c["id"] == cont["id"] for c in items)


def test_vincular_y_listar_usuarios_de_persona(client: TestClient, persona_datos: dict) -> None:
    """PUT /personas/{id}/usuarios/{usuario_id} vincula y GET lista usuarios asociados."""
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_usuario = client.post("/api/configuracion/usuarios", json={"nombre": "user_persona"})
    assert r_usuario.status_code == 201
    usuario_id = r_usuario.json()["id"]

    r_vinc = client.put(f"/api/personas/{persona_id}/usuarios/{usuario_id}")
    assert r_vinc.status_code == 200
    assert r_vinc.json()["persona_id"] == persona_id

    r_list = client.get(f"/api/personas/{persona_id}/usuarios")
    assert r_list.status_code == 200
    datos = r_list.json()
    assert isinstance(datos, list)
    assert any(u["id"] == usuario_id for u in datos)


def test_desvincular_usuario_de_persona(client: TestClient, persona_datos: dict) -> None:
    """DELETE /personas/{id}/usuarios/{usuario_id} desvincula el usuario."""
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_usuario = client.post("/api/configuracion/usuarios", json={"nombre": "user_unlink"})
    assert r_usuario.status_code == 201
    usuario_id = r_usuario.json()["id"]

    r_vinc = client.put(f"/api/personas/{persona_id}/usuarios/{usuario_id}")
    assert r_vinc.status_code == 200

    r_del = client.delete(f"/api/personas/{persona_id}/usuarios/{usuario_id}")
    assert r_del.status_code == 200
    assert r_del.json()["persona_id"] is None

    r_list = client.get(f"/api/personas/{persona_id}/usuarios")
    assert r_list.status_code == 200
    assert all(u["id"] != usuario_id for u in r_list.json())


def test_lookup_persona_por_usuario(client: TestClient, persona_datos: dict) -> None:
    """GET /personas/usuarios/{usuario_id}/persona devuelve la persona vinculada."""
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_usuario = client.post("/api/configuracion/usuarios", json={"nombre": "user_lookup"})
    assert r_usuario.status_code == 201
    usuario_id = r_usuario.json()["id"]

    r_vinc = client.put(f"/api/personas/{persona_id}/usuarios/{usuario_id}")
    assert r_vinc.status_code == 200

    r_lookup = client.get(f"/api/personas/usuarios/{usuario_id}/persona")
    assert r_lookup.status_code == 200
    assert r_lookup.json()["id"] == persona_id


def test_lookup_persona_por_usuario_sin_vinculo_404(client: TestClient) -> None:
    """GET /personas/usuarios/{usuario_id}/persona sin vínculo devuelve 404."""
    r_usuario = client.post("/api/configuracion/usuarios", json={"nombre": "user_sin_persona"})
    usuario_id = r_usuario.json()["id"]
    r_lookup = client.get(f"/api/personas/usuarios/{usuario_id}/persona")
    assert r_lookup.status_code == 404


def test_no_permite_dos_usuarios_para_misma_persona(client: TestClient, persona_datos: dict) -> None:
    """Una persona no debe tener más de un usuario asociado (409)."""
    r_persona = client.post("/api/personas", json=persona_datos)
    persona_id = r_persona.json()["id"]

    u1 = client.post("/api/configuracion/usuarios", json={"nombre": "u1"}).json()["id"]
    u2 = client.post("/api/configuracion/usuarios", json={"nombre": "u2"}).json()["id"]

    r_v1 = client.put(f"/api/personas/{persona_id}/usuarios/{u1}")
    assert r_v1.status_code == 200

    r_v2 = client.put(f"/api/personas/{persona_id}/usuarios/{u2}")
    assert r_v2.status_code == 409


def test_no_permite_reasignar_usuario_sin_desvincular(client: TestClient, persona_datos: dict) -> None:
    """Un usuario ya vinculado no se puede reasignar a otra persona sin desvincular (409)."""
    p1 = client.post("/api/personas", json=persona_datos).json()["id"]
    # crear otra persona cambiando documento para no chocar unicidad
    persona_datos2 = {**persona_datos, "documento": "87654321"}
    p2 = client.post("/api/personas", json=persona_datos2).json()["id"]

    u = client.post("/api/configuracion/usuarios", json={"nombre": "u_reasignar"}).json()["id"]

    r_v1 = client.put(f"/api/personas/{p1}/usuarios/{u}")
    assert r_v1.status_code == 200

    r_v2 = client.put(f"/api/personas/{p2}/usuarios/{u}")
    assert r_v2.status_code == 409


def test_vincular_empleado_a_usuario_y_lookup(client: TestClient, persona_datos: dict) -> None:
    """Vincular empleado a usuario debe asociar por persona_id y GET devuelve el usuario."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    emp = client.post(
        "/api/personas/empleados",
        json={"persona_id": persona_id, "documento": "123", "cargo": "Cajero", "estado": "ACTIVO"},
    )
    assert emp.status_code == 201
    empleado_id = emp.json()["id"]

    u = client.post("/api/configuracion/usuarios", json={"nombre": "u_emp"}).json()["id"]
    r_v = client.put(f"/api/personas/empleados/{empleado_id}/usuario/{u}")
    assert r_v.status_code == 200
    assert r_v.json()["persona_id"] == persona_id

    r_get = client.get(f"/api/personas/empleados/{empleado_id}/usuario")
    assert r_get.status_code == 200
    assert r_get.json()["id"] == u


def test_desvincular_empleado_de_usuario(client: TestClient, persona_datos: dict) -> None:
    """DELETE empleado/usuario desvincula el usuario (persona_id -> null)."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    emp = client.post(
        "/api/personas/empleados",
        json={"persona_id": persona_id, "documento": "123", "cargo": "Cajero", "estado": "ACTIVO"},
    )
    empleado_id = emp.json()["id"]
    u = client.post("/api/configuracion/usuarios", json={"nombre": "u_emp2"}).json()["id"]
    client.put(f"/api/personas/empleados/{empleado_id}/usuario/{u}")

    r_del = client.delete(f"/api/personas/empleados/{empleado_id}/usuario/{u}")
    assert r_del.status_code == 200
    assert r_del.json()["persona_id"] is None

    r_get = client.get(f"/api/personas/empleados/{empleado_id}/usuario")
    assert r_get.status_code == 200
    assert r_get.json() is None


def test_buscar_clientes_para_pos_incluye_datos_persona(client: TestClient, persona_datos: dict) -> None:
    """GET /personas/clientes/buscar permite lookup por nombre y devuelve datos de persona."""
    # crear persona y rol cliente
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]
    r_cliente = client.post(
        "/api/personas/clientes",
        json={"persona_id": persona_id, "limite_credito": 500.0, "estado": "ACTIVO"},
    )
    assert r_cliente.status_code == 201
    cliente_id = r_cliente.json()["id"]

    r_buscar = client.get("/api/personas/clientes/buscar", params={"q": "Juan"})
    assert r_buscar.status_code == 200
    items = r_buscar.json()
    assert any(it["cliente_id"] == cliente_id and it["persona_id"] == persona_id for it in items)


def test_alta_rapida_cliente_crea_persona_y_cliente(client: TestClient) -> None:
    """POST /personas/clientes/alta-rapida crea persona+cliente y devuelve lookup."""
    r = client.post(
        "/api/personas/clientes/alta-rapida",
        json={"nombre": "Carla", "apellido": "Suarez", "documento": "123", "telefono": "555"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["nombre"] == "Carla"
    assert data["apellido"] == "Suarez"
    assert data["documento"] == "123"
    assert data["telefono"] == "555"
    assert "cliente_id" in data
    assert "persona_id" in data

    # debe aparecer al buscar por documento
    r2 = client.get("/api/personas/clientes/buscar", params={"q": "123"})
    assert r2.status_code == 200
    assert any(it["persona_id"] == data["persona_id"] for it in r2.json())


# ---------------------------------------------------------------------------
# Tests de actualización (PATCH)
# ---------------------------------------------------------------------------

def test_patch_cliente_actualiza_datos(client: TestClient, persona_datos: dict) -> None:
    """PATCH /personas/clientes/{id} actualiza segmento, estado y límite de crédito."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    cliente = client.post(
        "/api/personas/clientes",
        json={"persona_id": persona_id, "segmento": "ocasional", "limite_credito": 100.0, "estado": "ACTIVO"},
    ).json()
    cliente_id = cliente["id"]

    r = client.patch(
        f"/api/personas/clientes/{cliente_id}",
        json={"segmento": "frecuente", "estado": "BLOQUEADO", "limite_credito": 500.0},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["segmento"] == "frecuente"
    assert data["estado"] == "BLOQUEADO"
    assert float(data["limite_credito"]) == 500.0


def test_patch_cliente_no_encontrado_404(client: TestClient) -> None:
    r = client.patch("/api/personas/clientes/999999", json={"estado": "INACTIVO"})
    assert r.status_code == 404


def test_patch_proveedor_actualiza_datos(client: TestClient, persona_datos: dict) -> None:
    """PATCH /personas/proveedores/{id} actualiza condiciones y estado."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    proveedor = client.post(
        "/api/personas/proveedores",
        json={"persona_id": persona_id, "cuit": "20-11111111-1", "estado": "ACTIVO"},
    ).json()
    prov_id = proveedor["id"]

    r = client.patch(
        f"/api/personas/proveedores/{prov_id}",
        json={
            "cuit": "30-99999999-9",
            "condiciones_pago": "60 días",
            "estado": "INACTIVO",
            "minimo_compra": 2500.0,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["cuit"] == "30-99999999-9"
    assert data["condiciones_pago"] == "60 días"
    assert data["estado"] == "INACTIVO"
    assert float(data["minimo_compra"]) == 2500.0


def test_patch_proveedor_no_encontrado_404(client: TestClient) -> None:
    r = client.patch("/api/personas/proveedores/999999", json={"estado": "INACTIVO"})
    assert r.status_code == 404


def test_patch_empleado_actualiza_cargo_y_estado(client: TestClient, persona_datos: dict) -> None:
    """PATCH /personas/empleados/{id} actualiza cargo y estado."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    empleado = client.post(
        "/api/personas/empleados",
        json={"persona_id": persona_id, "cargo": "Cajero", "estado": "ACTIVO"},
    ).json()
    emp_id = empleado["id"]

    r = client.patch(
        f"/api/personas/empleados/{emp_id}",
        json={"cargo": "Supervisor", "estado": "INACTIVO"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["cargo"] == "Supervisor"
    assert data["estado"] == "INACTIVO"


def test_patch_empleado_no_encontrado_404(client: TestClient) -> None:
    r = client.patch("/api/personas/empleados/999999", json={"cargo": "X"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests de lookup por persona_id
# ---------------------------------------------------------------------------

def test_obtener_cliente_por_persona_id(client: TestClient, persona_datos: dict) -> None:
    """GET /personas/clientes/por-persona/{persona_id} devuelve el cliente."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    cliente = client.post(
        "/api/personas/clientes",
        json={"persona_id": persona_id, "estado": "ACTIVO"},
    ).json()

    r = client.get(f"/api/personas/clientes/por-persona/{persona_id}")
    assert r.status_code == 200
    assert r.json()["id"] == cliente["id"]
    assert r.json()["persona_id"] == persona_id


def test_obtener_cliente_por_persona_sin_cliente_404(client: TestClient, persona_datos: dict) -> None:
    """GET /personas/clientes/por-persona/{persona_id} devuelve 404 si no hay cliente."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    r = client.get(f"/api/personas/clientes/por-persona/{persona_id}")
    assert r.status_code == 404


def test_obtener_empleado_por_persona_id(client: TestClient, persona_datos: dict) -> None:
    """GET /personas/empleados/por-persona/{persona_id} devuelve el empleado."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    empleado = client.post(
        "/api/personas/empleados",
        json={"persona_id": persona_id, "cargo": "Cajero", "estado": "ACTIVO"},
    ).json()

    r = client.get(f"/api/personas/empleados/por-persona/{persona_id}")
    assert r.status_code == 200
    assert r.json()["id"] == empleado["id"]
    assert r.json()["persona_id"] == persona_id


def test_obtener_empleado_por_persona_sin_empleado_404(client: TestClient, persona_datos: dict) -> None:
    """GET /personas/empleados/por-persona/{persona_id} devuelve 404 si no hay empleado."""
    persona_id = client.post("/api/personas", json=persona_datos).json()["id"]
    r = client.get(f"/api/personas/empleados/por-persona/{persona_id}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests de filtro por estado en listados
# ---------------------------------------------------------------------------

def test_listar_empleados_filtra_por_estado(client: TestClient, persona_datos: dict) -> None:
    """GET /personas/empleados?estado=ACTIVO solo devuelve empleados activos."""
    p1 = client.post("/api/personas", json=persona_datos).json()["id"]
    p2 = client.post("/api/personas", json={**persona_datos, "documento": "DOC-E2"}).json()["id"]

    emp1 = client.post(
        "/api/personas/empleados", json={"persona_id": p1, "cargo": "Cajero", "estado": "ACTIVO"}
    ).json()
    emp2 = client.post(
        "/api/personas/empleados", json={"persona_id": p2, "cargo": "Limpieza", "estado": "INACTIVO"}
    ).json()

    r_activos = client.get("/api/personas/empleados", params={"estado": "ACTIVO"})
    assert r_activos.status_code == 200
    ids_activos = [e["id"] for e in r_activos.json()]
    assert emp1["id"] in ids_activos
    assert emp2["id"] not in ids_activos


def test_listar_proveedores_filtra_por_estado(client: TestClient, persona_datos: dict) -> None:
    """GET /personas/proveedores?estado=ACTIVO solo devuelve proveedores activos."""
    p1 = client.post("/api/personas", json=persona_datos).json()["id"]
    p2 = client.post("/api/personas", json={**persona_datos, "documento": "DOC-P2"}).json()["id"]

    prov1 = client.post(
        "/api/personas/proveedores", json={"persona_id": p1, "estado": "ACTIVO"}
    ).json()
    prov2 = client.post(
        "/api/personas/proveedores", json={"persona_id": p2, "estado": "INACTIVO"}
    ).json()

    r_activos = client.get("/api/personas/proveedores", params={"estado": "ACTIVO"})
    assert r_activos.status_code == 200
    ids = [p["id"] for p in r_activos.json()]
    assert prov1["id"] in ids
    assert prov2["id"] not in ids


# ---------------------------------------------------------------------------
# Tests: analisis comercial de clientes (docs Modulo 6 ss5, ss10)
# ---------------------------------------------------------------------------

def _crear_venta_para_cliente(client, persona_id: int, total: str = "100") -> dict:
    """Helper: crea una venta asociada a un cliente (por persona_id)."""
    prod = client.post("/api/productos", json={"sku": f"VPROD-{total}-{persona_id}", "nombre": "Producto venta", "precio_venta": total}).json()
    r = client.post("/api/ventas", json={
        "cliente_id": persona_id,
        "items": [{"producto_id": prod["id"], "cantidad": "1", "precio_unitario": total}],
        "metodo_pago": "EFECTIVO",
    })
    return r.json()


def test_ventas_por_cliente_sin_ventas(client: TestClient, persona_datos: dict) -> None:
    """GET /clientes/{id}/ventas sin ventas devuelve estadisticas en 0."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post("/api/personas/clientes", json={"persona_id": p["id"]}).json()
    r = client.get(f"/api/personas/clientes/{cli['id']}/ventas")
    assert r.status_code == 200
    data = r.json()
    assert data["estadisticas"]["total_ventas"] == 0
    assert data["estadisticas"]["total_facturado"] == 0.0
    assert data["ventas"] == []


def test_ventas_por_cliente_404(client: TestClient) -> None:
    """GET /clientes/{id}/ventas con cliente inexistente retorna 404."""
    r = client.get("/api/personas/clientes/999999/ventas")
    assert r.status_code == 404


def test_ventas_por_cliente_con_ventas(client: TestClient, persona_datos: dict) -> None:
    """GET /clientes/{id}/ventas refleja ventas realizadas al cliente."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post("/api/personas/clientes", json={"persona_id": p["id"]}).json()
    prod = client.post("/api/productos", json={"sku": "VCLIENTE-01", "nombre": "Prod", "precio_venta": "200"}).json()
    # Ingresar stock antes de vender
    client.post("/api/inventario/ingresar", json={"producto_id": prod["id"], "cantidad": "10"})
    client.post("/api/ventas", json={
        "cliente_id": p["id"],
        "items": [{"producto_id": prod["id"], "cantidad": "1", "precio_unitario": "200"}],
        "metodo_pago": "EFECTIVO",
    })
    r = client.get(f"/api/personas/clientes/{cli['id']}/ventas")
    assert r.status_code == 200
    data = r.json()
    assert data["estadisticas"]["total_ventas"] == 1
    assert data["estadisticas"]["total_facturado"] == 200.0
    assert len(data["ventas"]) == 1
    assert data["ventas"][0]["total"] == 200.0


def test_ranking_clientes_sin_datos(client: TestClient) -> None:
    """GET /clientes/ranking sin ventas devuelve lista vacia."""
    r = client.get("/api/personas/clientes/ranking")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_ranking_clientes_con_ventas(client: TestClient, persona_datos: dict) -> None:
    """GET /clientes/ranking incluye clientes con ventas, ordenados por total."""
    p1 = client.post("/api/personas", json=persona_datos).json()
    p2 = client.post("/api/personas", json={**persona_datos, "documento": "RK-DOC2"}).json()
    # Venta grande para p1
    prod1 = client.post("/api/productos", json={"sku": "RK-PROD1", "nombre": "Prod1", "precio_venta": "500"}).json()
    client.post("/api/inventario/ingresar", json={"producto_id": prod1["id"], "cantidad": "10"})
    client.post("/api/ventas", json={
        "cliente_id": p1["id"],
        "items": [{"producto_id": prod1["id"], "cantidad": "1", "precio_unitario": "500"}],
        "metodo_pago": "EFECTIVO",
    })
    # Venta pequeña para p2
    prod2 = client.post("/api/productos", json={"sku": "RK-PROD2", "nombre": "Prod2", "precio_venta": "50"}).json()
    client.post("/api/inventario/ingresar", json={"producto_id": prod2["id"], "cantidad": "10"})
    client.post("/api/ventas", json={
        "cliente_id": p2["id"],
        "items": [{"producto_id": prod2["id"], "cantidad": "1", "precio_unitario": "50"}],
        "metodo_pago": "EFECTIVO",
    })
    r = client.get("/api/personas/clientes/ranking?limite=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2
    # El primero debe tener mayor facturacion
    assert data[0]["total_facturado"] >= data[1]["total_facturado"]
    assert "posicion" in data[0]


def test_cuenta_corriente_cliente_sin_cuenta(client: TestClient, persona_datos: dict) -> None:
    """GET /clientes/{id}/cuenta-corriente sin cc devuelve saldo 0."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post("/api/personas/clientes", json={"persona_id": p["id"]}).json()
    r = client.get(f"/api/personas/clientes/{cli['id']}/cuenta-corriente")
    assert r.status_code == 200
    data = r.json()
    assert data["saldo_deuda"] == 0.0
    assert "movimientos_recientes" in data


def test_cuenta_corriente_cliente_404(client: TestClient) -> None:
    """GET /clientes/{id}/cuenta-corriente con cliente inexistente retorna 404."""
    r = client.get("/api/personas/clientes/999999/cuenta-corriente")
    assert r.status_code == 404


def test_cuenta_corriente_cliente_con_limite_credito(client: TestClient, persona_datos: dict) -> None:
    """GET /clientes/{id}/cuenta-corriente refleja limite_credito y margen_disponible."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post(
        "/api/personas/clientes",
        json={"persona_id": p["id"], "limite_credito": "1000"}
    ).json()
    r = client.get(f"/api/personas/clientes/{cli['id']}/cuenta-corriente")
    assert r.status_code == 200
    data = r.json()
    assert data["limite_credito"] == 1000.0
    assert data["margen_disponible"] == 1000.0  # saldo 0, limite 1000


# ---------------------------------------------------------------------------
# Tests: analisis comercial de proveedores (docs Modulo 6 ss6, ss10)
# ---------------------------------------------------------------------------

def test_compras_por_proveedor_sin_compras(client: TestClient, persona_datos: dict) -> None:
    """GET /proveedores/{id}/compras sin compras devuelve estadisticas en 0."""
    p = client.post("/api/personas", json=persona_datos).json()
    prov = client.post("/api/personas/proveedores", json={"persona_id": p["id"]}).json()
    r = client.get(f"/api/personas/proveedores/{prov['id']}/compras")
    assert r.status_code == 200
    data = r.json()
    assert data["estadisticas"]["total_compras"] == 0
    assert data["estadisticas"]["total_invertido"] == 0.0
    assert data["compras"] == []


def test_compras_por_proveedor_404(client: TestClient) -> None:
    """GET /proveedores/{id}/compras con proveedor inexistente retorna 404."""
    r = client.get("/api/personas/proveedores/999999/compras")
    assert r.status_code == 404


def test_compras_por_proveedor_con_compras(client: TestClient, persona_datos: dict) -> None:
    """GET /proveedores/{id}/compras refleja compras realizadas al proveedor."""
    p = client.post("/api/personas", json=persona_datos).json()
    prov = client.post("/api/personas/proveedores", json={"persona_id": p["id"]}).json()
    prod = client.post("/api/productos", json={"sku": "COMPROV-01", "nombre": "Prod compra", "precio_venta": "50", "costo_actual": "30"}).json()
    # Crear compra
    client.post("/api/compras", json={
        "proveedor_id": p["id"],
        "items": [{"producto_id": prod["id"], "cantidad": "10", "costo_unitario": "30"}],
    })
    r = client.get(f"/api/personas/proveedores/{prov['id']}/compras")
    assert r.status_code == 200
    data = r.json()
    assert data["estadisticas"]["total_compras"] == 1
    assert data["estadisticas"]["total_invertido"] > 0
    assert len(data["compras"]) == 1


def test_ranking_proveedores_sin_datos(client: TestClient) -> None:
    """GET /proveedores/ranking sin compras devuelve lista vacia."""
    r = client.get("/api/personas/proveedores/ranking")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_ranking_proveedores_con_compras(client: TestClient, persona_datos: dict) -> None:
    """GET /proveedores/ranking incluye proveedores con compras, ordenados por volumen."""
    p1 = client.post("/api/personas", json=persona_datos).json()
    p2 = client.post("/api/personas", json={**persona_datos, "documento": "RKPROV-DOC2"}).json()
    # Compra grande de p1
    prod1 = client.post("/api/productos", json={"sku": "RKPROV-P1", "nombre": "ProdRK1", "precio_venta": "100", "costo_actual": "80"}).json()
    client.post("/api/compras", json={
        "proveedor_id": p1["id"],
        "items": [{"producto_id": prod1["id"], "cantidad": "10", "costo_unitario": "80"}],
    })
    # Compra pequeña de p2
    prod2 = client.post("/api/productos", json={"sku": "RKPROV-P2", "nombre": "ProdRK2", "precio_venta": "20", "costo_actual": "10"}).json()
    client.post("/api/compras", json={
        "proveedor_id": p2["id"],
        "items": [{"producto_id": prod2["id"], "cantidad": "2", "costo_unitario": "10"}],
    })
    r = client.get("/api/personas/proveedores/ranking?limite=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2
    assert data[0]["total_invertido"] >= data[1]["total_invertido"]
    assert "posicion" in data[0]


