"""Tests de la API y lógica de ventas."""
from fastapi.testclient import TestClient

from backend.events import clear_handlers, subscribe


def _ingresar_stock(client: TestClient, producto_id: int, cantidad: str | float) -> None:
    """Ingresa stock para un producto (requerido antes de registrar venta)."""
    r = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": str(cantidad)},
    )
    assert r.status_code == 200, r.json()


def test_listar_ventas_vacio(client: TestClient) -> None:
    """Listar ventas sin datos devuelve lista vacía."""
    r = client.get("/api/ventas")
    assert r.status_code == 200
    assert r.json() == []


def test_registrar_venta_ok(client: TestClient, producto_datos: dict) -> None:
    """Registrar venta con un ítem devuelve venta_id y total."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    precio = float(producto_datos["precio_venta"])
    payload = {
        "items": [{"producto_id": producto_id, "cantidad": "2"}],
        "descuento": "0",
        "metodo_pago": "EFECTIVO",
    }
    r = client.post("/api/ventas", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "venta_id" in data
    assert float(data["total"]) == 2 * precio
    assert "Venta registrada" in data["mensaje"]


def test_registrar_venta_con_descuento(client: TestClient, producto_datos: dict) -> None:
    """Registrar venta con descuento actualiza el total."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    payload = {
        "items": [{"producto_id": producto_id, "cantidad": "1"}],
        "descuento": "1.50",
        "metodo_pago": "EFECTIVO",
    }
    r = client.post("/api/ventas", json=payload)
    assert r.status_code == 200
    total_esperado = float(producto_datos["precio_venta"]) - 1.50
    assert float(r.json()["total"]) == total_esperado


def test_registrar_venta_sin_items_falla(client: TestClient) -> None:
    """Registrar venta sin ítems devuelve 422 (validación)."""
    r = client.post(
        "/api/ventas",
        json={"items": [], "descuento": "0", "metodo_pago": "EFECTIVO"},
    )
    assert r.status_code == 422


def test_registrar_venta_sin_stock_falla(client: TestClient, producto_datos: dict) -> None:
    """Registrar venta sin stock previo devuelve 400 (stock insuficiente)."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    # No ingresar stock
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r.status_code == 400
    assert "stock" in r.json()["detail"].lower() or "insuficiente" in r.json()["detail"].lower()


def test_registrar_venta_descuenta_stock(client: TestClient, producto_datos: dict) -> None:
    """Al registrar una venta se descuenta el stock."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r.status_code == 200
    stock = client.get(f"/api/inventario/productos/{producto_id}/stock")
    assert stock.status_code == 200
    assert float(stock.json()["cantidad"]) == 8


def test_registrar_venta_producto_inexistente_404(client: TestClient) -> None:
    """Registrar venta con producto_id inexistente devuelve 404."""
    payload = {
        "items": [{"producto_id": 99999, "cantidad": "1"}],
        "descuento": "0",
        "metodo_pago": "EFECTIVO",
    }
    r = client.post("/api/ventas", json=payload)
    assert r.status_code == 404
    assert "no encontrado" in r.json()["detail"].lower()


def test_obtener_venta_por_id_ok(client: TestClient, producto_datos: dict) -> None:
    """Registrar venta y obtenerla por ID devuelve venta con ítems."""
    crear_p = client.post("/api/productos", json=producto_datos)
    producto_id = crear_p.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    payload = {
        "items": [{"producto_id": producto_id, "cantidad": "3"}],
        "descuento": "0",
        "metodo_pago": "TARJETA",
    }
    crear_v = client.post("/api/ventas", json=payload)
    assert crear_v.status_code == 200
    venta_id = crear_v.json()["venta_id"]
    r = client.get(f"/api/ventas/{venta_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == venta_id
    assert data["metodo_pago"] == "TARJETA"
    assert len(data["items"]) == 1
    assert data["items"][0]["producto_id"] == producto_id
    assert float(data["items"][0]["cantidad"]) == 3
    assert float(data["total"]) == 3 * float(producto_datos["precio_venta"])


def test_obtener_venta_por_id_404(client: TestClient) -> None:
    """Obtener venta por ID inexistente devuelve 404."""
    r = client.get("/api/ventas/99999")
    assert r.status_code == 404


def test_listar_ventas_incluye_registradas(client: TestClient, producto_datos: dict) -> None:
    """Después de registrar ventas, listar las incluye."""
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    r = client.get("/api/ventas")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2


def test_registrar_venta_con_caja_abierta_vincula_caja(client: TestClient, producto_datos: dict) -> None:
    """Si hay caja abierta, la venta queda vinculada a esa caja (caja_id)."""
    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja = client.get("/api/caja/abierta")
    assert caja.status_code == 200 and caja.json() is not None
    caja_id = caja.json()["id"]
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r.status_code == 200
    venta_id = r.json()["venta_id"]
    venta = client.get(f"/api/ventas/{venta_id}")
    assert venta.status_code == 200
    assert venta.json()["caja_id"] == caja_id


def test_registrar_venta_sin_caja_abierta_caja_id_nulo(client: TestClient, producto_datos: dict) -> None:
    """Si no hay caja abierta, la venta se registra con caja_id null."""
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r.status_code == 200
    venta_id = r.json()["venta_id"]
    venta = client.get(f"/api/ventas/{venta_id}")
    assert venta.status_code == 200
    assert venta.json().get("caja_id") is None


def test_registrar_venta_emite_evento_venta_registrada(client: TestClient, producto_datos: dict) -> None:
    """Al registrar una venta se emite el evento VentaRegistrada con venta_id, fecha, total, caja_id."""
    clear_handlers()
    capturados = []

    def guardar(payload):
        capturados.append(payload)

    subscribe("VentaRegistrada", guardar)
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r.status_code == 200
    venta_id = r.json()["venta_id"]
    assert len(capturados) == 1
    assert capturados[0]["venta_id"] == venta_id
    assert "fecha" in capturados[0]
    assert "total" in capturados[0]
    assert capturados[0].get("caja_id") is None or isinstance(capturados[0].get("caja_id"), int)


def test_registrar_venta_con_cliente_id(client: TestClient, producto_datos: dict, persona_datos: dict) -> None:
    """Registrar venta con cliente_id asocia la venta al cliente (persona)."""
    crear_p = client.post("/api/personas", json=persona_datos)
    assert crear_p.status_code == 201
    cliente_id = crear_p.json()["id"]
    crear_prod = client.post("/api/productos", json=producto_datos)
    assert crear_prod.status_code == 201
    producto_id = crear_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
            "cliente_id": cliente_id,
        },
    )
    assert r.status_code == 200
    venta_id = r.json()["venta_id"]
    venta = client.get(f"/api/ventas/{venta_id}")
    assert venta.status_code == 200
    assert venta.json().get("cliente_id") == cliente_id


def test_registrar_venta_sin_cliente_id_tiene_null(client: TestClient, producto_datos: dict) -> None:
    """Registrar venta sin cliente_id deja cliente_id en null."""
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r.status_code == 200
    venta = client.get(f"/api/ventas/{r.json()['venta_id']}")
    assert venta.json().get("cliente_id") is None


def test_registrar_venta_cliente_inexistente_404(client: TestClient, producto_datos: dict) -> None:
    """Registrar venta con cliente_id de persona inexistente devuelve 404."""
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
            "cliente_id": 99999,
        },
    )
    assert r.status_code == 404
    assert "no encontrado" in r.json()["detail"].lower() or "cliente" in r.json()["detail"].lower()


def test_venta_a_credito_respeta_limite_de_credito(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """
    Ventas con metodo_pago='CUENTA_CORRIENTE' deben respetar el limite_credito
    configurado en el rol Cliente asociado a la persona.
    """
    # Crear persona y rol cliente con limite_credito=100
    crear_p = client.post("/api/personas", json=persona_datos)
    assert crear_p.status_code == 201
    persona_id = crear_p.json()["id"]

    crear_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "CUENTA_CORRIENTE",
            "limite_credito": "100.00",
        },
    )
    assert crear_cliente.status_code == 201

    # Crear producto y stock
    crear_prod = client.post("/api/productos", json=producto_datos)
    assert crear_prod.status_code == 201
    producto_id = crear_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    precio = float(producto_datos["precio_venta"])

    # Primera venta a crédito por debajo del límite (por ejemplo 40)
    cantidad1 = 40.0 / precio
    r1 = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": str(cantidad1)}],
            "descuento": "0",
            "metodo_pago": "CUENTA_CORRIENTE",
            "cliente_id": persona_id,
        },
    )
    assert r1.status_code == 200

    # Segunda venta que intenta superar el límite (total acumulado > 100)
    cantidad2 = 70.0 / precio
    r2 = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": str(cantidad2)}],
            "descuento": "0",
            "metodo_pago": "CUENTA_CORRIENTE",
            "cliente_id": persona_id,
        },
    )
    assert r2.status_code == 400
    assert "límite" in r2.json()["detail"].lower() or "credito" in r2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: filtros en GET /ventas (docs Modulo 2 ss13)
# ---------------------------------------------------------------------------

def test_listar_ventas_filtro_estado(client: TestClient, producto_datos: dict) -> None:
    """GET /ventas?estado=PENDIENTE filtra por estado correctamente."""
    prod = client.post("/api/productos", json=producto_datos).json()
    _ingresar_stock(client, prod["id"], 20)
    r_teu_off = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "modo_venta": "TEU_OFF",
    })
    assert r_teu_off.status_code == 200

    r = client.get("/api/ventas?estado=PENDIENTE")
    assert r.status_code == 200
    data = r.json()
    assert all(v["estado"] == "PENDIENTE" for v in data)


def test_listar_ventas_filtro_cliente(client: TestClient, producto_datos: dict, persona_datos: dict) -> None:
    """GET /ventas?cliente_id= filtra por cliente."""
    persona = client.post("/api/personas", json=persona_datos).json()
    persona_id = persona["id"]
    prod = client.post("/api/productos", json=producto_datos).json()
    _ingresar_stock(client, prod["id"], 20)
    client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "metodo_pago": "EFECTIVO",
        "cliente_id": persona_id,
    })
    r = client.get(f"/api/ventas?cliente_id={persona_id}")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert all(v["cliente_id"] == persona_id for v in data)


# ---------------------------------------------------------------------------
# Tests: buscar ventas (docs Modulo 2 ss3)
# ---------------------------------------------------------------------------

def test_buscar_ventas_por_ticket(client: TestClient, producto_datos: dict) -> None:
    """GET /ventas/buscar?q=TCK- encuentra ventas por numero de ticket."""
    prod = client.post("/api/productos", json=producto_datos).json()
    _ingresar_stock(client, prod["id"], 10)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "metodo_pago": "EFECTIVO",
    })
    assert r_v.status_code == 200
    venta_id = r_v.json()["venta_id"]
    ticket = client.get(f"/api/ventas/{venta_id}").json()["numero_ticket"]

    r = client.get(f"/api/ventas/buscar?q={ticket[:8]}")
    assert r.status_code == 200
    data = r.json()
    assert any(d["numero_ticket"] == ticket for d in data)


def test_buscar_ventas_por_producto(client: TestClient, producto_datos: dict) -> None:
    """GET /ventas/buscar?q=<nombre producto> encuentra ventas por nombre de producto."""
    prod_data = {**producto_datos, "nombre": "ProductoUnico-XQZZ", "sku": "BUSQ-XQZZ"}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 10)
    client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "metodo_pago": "EFECTIVO",
    })
    r = client.get("/api/ventas/buscar?q=ProductoUnico-XQZZ")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1


def test_buscar_ventas_sin_resultado(client: TestClient) -> None:
    """GET /ventas/buscar?q=NADA_EXISTE devuelve lista vacia."""
    r = client.get("/api/ventas/buscar?q=TICKET_INEXISTENTE_12345XYZ")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# Tests: cancelar venta (docs Modulo 2 ss13)
# ---------------------------------------------------------------------------

def test_cancelar_venta_pendiente(client: TestClient, producto_datos: dict) -> None:
    """POST /ventas/{id}/cancelar cancela una venta PENDIENTE."""
    prod = client.post("/api/productos", json=producto_datos).json()
    _ingresar_stock(client, prod["id"], 10)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "modo_venta": "TEU_OFF",
    })
    venta_id = r_v.json()["venta_id"]

    r = client.post(f"/api/ventas/{venta_id}/cancelar", json={"motivo": "Cliente desistio"})
    assert r.status_code == 200
    assert r.json()["estado"] == "CANCELADA"


def test_cancelar_venta_pagada_rechaza(client: TestClient, producto_datos: dict) -> None:
    """POST /ventas/{id}/cancelar rechaza cancelar una venta ya PAGADA."""
    prod = client.post("/api/productos", json=producto_datos).json()
    _ingresar_stock(client, prod["id"], 10)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "metodo_pago": "EFECTIVO",
    })
    venta_id = r_v.json()["venta_id"]
    r = client.post(f"/api/ventas/{venta_id}/cancelar")
    assert r.status_code == 400


def test_cancelar_venta_no_existente(client: TestClient) -> None:
    """POST /ventas/999999/cancelar devuelve 404."""
    r = client.post("/api/ventas/999999/cancelar")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests: gestión de items del carrito (docs Modulo 2 ss8)
# ---------------------------------------------------------------------------

def test_agregar_item_a_venta_pendiente(client: TestClient, producto_datos: dict) -> None:
    """POST /ventas/{id}/items agrega un producto al carrito de una venta PENDIENTE."""
    prod1_data = {**producto_datos, "sku": "CART-A1", "nombre": "Prod Carrito A"}
    prod2_data = {**producto_datos, "sku": "CART-B1", "nombre": "Prod Carrito B", "precio_venta": "20"}
    prod1 = client.post("/api/productos", json=prod1_data).json()
    prod2 = client.post("/api/productos", json=prod2_data).json()
    _ingresar_stock(client, prod1["id"], 20)
    _ingresar_stock(client, prod2["id"], 20)

    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod1["id"], "cantidad": "1"}],
        "modo_venta": "TEU_OFF",
    })
    venta_id = r_v.json()["venta_id"]
    total_anterior = float(client.get(f"/api/ventas/{venta_id}").json()["total"])

    r = client.post(f"/api/ventas/{venta_id}/items", json={"producto_id": prod2["id"], "cantidad": "2"})
    assert r.status_code == 200
    data = r.json()
    assert float(data["total"]) > total_anterior
    assert len(data["items"]) == 2


def test_agregar_item_duplicado_incrementa_cantidad(client: TestClient, producto_datos: dict) -> None:
    """POST /ventas/{id}/items con producto ya existente incrementa su cantidad."""
    prod_data = {**producto_datos, "sku": "CART-DUP1"}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 30)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "modo_venta": "TEU_OFF",
    })
    venta_id = r_v.json()["venta_id"]
    items_antes = client.get(f"/api/ventas/{venta_id}").json()["items"]

    client.post(f"/api/ventas/{venta_id}/items", json={"producto_id": prod["id"], "cantidad": "2"})
    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert len(venta["items"]) == len(items_antes)
    item = next(i for i in venta["items"] if i["producto_id"] == prod["id"])
    assert float(item["cantidad"]) == 3.0


def test_actualizar_item_cantidad(client: TestClient, producto_datos: dict) -> None:
    """PATCH /ventas/{id}/items/{item_id} actualiza la cantidad del item."""
    prod_data = {**producto_datos, "sku": "CART-UPD1"}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 20)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "modo_venta": "TEU_OFF",
    })
    venta_id = r_v.json()["venta_id"]
    item_id = client.get(f"/api/ventas/{venta_id}").json()["items"][0]["id"]

    r = client.patch(f"/api/ventas/{venta_id}/items/{item_id}", json={"cantidad": "5"})
    assert r.status_code == 200
    item = next(i for i in r.json()["items"] if i["id"] == item_id)
    assert float(item["cantidad"]) == 5.0


def test_eliminar_item_de_venta(client: TestClient, producto_datos: dict) -> None:
    """DELETE /ventas/{id}/items/{item_id} elimina un item del carrito."""
    prod1_data = {**producto_datos, "sku": "CART-DEL-A"}
    prod2_data = {**producto_datos, "sku": "CART-DEL-B", "nombre": "Prod Del B"}
    prod1 = client.post("/api/productos", json=prod1_data).json()
    prod2 = client.post("/api/productos", json=prod2_data).json()
    _ingresar_stock(client, prod1["id"], 10)
    _ingresar_stock(client, prod2["id"], 10)
    r_v = client.post("/api/ventas", json={
        "items": [
            {"producto_id": prod1["id"], "cantidad": "1"},
            {"producto_id": prod2["id"], "cantidad": "1"},
        ],
        "modo_venta": "TEU_OFF",
    })
    venta_id = r_v.json()["venta_id"]
    items = client.get(f"/api/ventas/{venta_id}").json()["items"]
    item_a_eliminar = items[0]["id"]

    r = client.delete(f"/api/ventas/{venta_id}/items/{item_a_eliminar}")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1


def test_eliminar_unico_item_rechaza(client: TestClient, producto_datos: dict) -> None:
    """DELETE del unico item rechaza con 400."""
    prod_data = {**producto_datos, "sku": "CART-SOLO1"}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 10)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "modo_venta": "TEU_OFF",
    })
    venta_id = r_v.json()["venta_id"]
    item_id = client.get(f"/api/ventas/{venta_id}").json()["items"][0]["id"]
    r = client.delete(f"/api/ventas/{venta_id}/items/{item_id}")
    assert r.status_code == 400


def test_aplicar_descuento_a_venta(client: TestClient, producto_datos: dict) -> None:
    """PATCH /ventas/{id}/descuento aplica descuento y recalcula total."""
    prod_data = {**producto_datos, "sku": "CART-DESC1", "precio_venta": "100"}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 10)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "2"}],
        "modo_venta": "TEU_OFF",
    })
    venta_id = r_v.json()["venta_id"]
    r = client.patch(f"/api/ventas/{venta_id}/descuento", json={"descuento": "50"})
    assert r.status_code == 200
    assert float(r.json()["total"]) == 150.0
