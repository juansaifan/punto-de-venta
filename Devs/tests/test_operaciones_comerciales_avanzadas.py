from decimal import Decimal

from fastapi.testclient import TestClient


def _ingresar_stock(client: TestClient, producto_id: int, cantidad: str | float) -> None:
    r = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": str(cantidad)},
    )
    assert r.status_code == 200, r.json()


def test_cambio_producto_efectivo_actualiza_stock_y_caja(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Cambio de producto EFECTIVO reingresa el devuelto y descuenta el nuevo."""
    # Caja abierta
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    # Producto A (barato) y Producto B (caro)
    producto_a = dict(producto_datos)
    producto_a.update({"sku": "TEST-A", "nombre": "Producto A", "precio_venta": "10.00"})
    producto_b = dict(producto_datos)
    producto_b.update({"sku": "TEST-B", "nombre": "Producto B", "precio_venta": "15.00"})

    ra = client.post("/api/productos", json=producto_a)
    assert ra.status_code == 201
    producto_a_id = ra.json()["id"]
    rb = client.post("/api/productos", json=producto_b)
    assert rb.status_code == 201
    producto_b_id = rb.json()["id"]

    _ingresar_stock(client, producto_a_id, 10)
    _ingresar_stock(client, producto_b_id, 20)

    # Venta TEU_ON pagada con Producto A (2 unidades)
    precio_a = Decimal(str(producto_a["precio_venta"]))
    cantidad = Decimal("2")
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_a_id, "cantidad": str(cantidad)}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "PAGADA"
    item_venta_a_id = venta["items"][0]["id"]

    # Cambio: devolver 1 item (2 unidades de A) y recibir 2 unidades de B
    precio_b = Decimal(str(producto_b["precio_venta"]))
    diferencia = (precio_b - precio_a) * cantidad  # 10.00 para 2 unidades
    r_cam = client.post(
        "/api/operaciones-comerciales/cambios",
        json={
            "venta_id": venta_id,
            "items_devueltos": [{"item_venta_id": item_venta_a_id, "cantidad": str(cantidad)}],
            "items_nuevos": [{"producto_id": producto_b_id, "cantidad": str(cantidad)}],
            "reintegro_tipo_diferencia": "EFECTIVO",
            "reintegro_metodo_pago": "EFECTIVO",
            "motivo": "Cambio de producto",
        },
    )
    assert r_cam.status_code == 200, r_cam.json()
    assert r_cam.json()["tipo"] == "CAMBIO_PRODUCTO"
    assert float(r_cam.json()["importe_total"]) == float(diferencia)

    # Stock A debe volver al original (10)
    stock_a = client.get(f"/api/inventario/productos/{producto_a_id}/stock").json()["cantidad"]
    assert float(stock_a) == 10.0

    # Stock B debe descontar 2 unidades (20 -> 18)
    stock_b = client.get(f"/api/inventario/productos/{producto_b_id}/stock").json()["cantidad"]
    assert float(stock_b) == 18.0

    # Caja debe registrar movimiento VENTA por diferencia (diferencia>0)
    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert any(
        m["tipo"] == "VENTA" and float(m["monto"]) == float(diferencia) for m in movs
    )

    # Venta debe contener Producto B
    venta2 = client.get(f"/api/ventas/{venta_id}").json()
    assert len(venta2["items"]) == 1
    assert venta2["items"][0]["producto_id"] == producto_b_id


def test_nota_debito_efectivo_registra_caja_ingreso(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Nota de débito EFECTIVO registra MovimientoCaja INGRESO y no toca inventario."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    producto = dict(producto_datos)
    producto.update({"sku": "TEST-DEB", "nombre": "Producto Debito", "precio_venta": "10.00"})
    r_prod = client.post("/api/productos", json=producto)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    # Venta pagada
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    stock_antes = client.get(f"/api/inventario/productos/{producto_id}/stock").json()["cantidad"]
    importe = Decimal("5.50")

    r_nd = client.post(
        "/api/operaciones-comerciales/notas-debito",
        json={
            "venta_id": venta_id,
            "reintegro_tipo": "EFECTIVO",
            "reintegro_metodo_pago": "EFECTIVO",
            "importe": str(importe),
            "motivo": "Intereses por mora",
        },
    )
    assert r_nd.status_code == 200, r_nd.json()
    assert r_nd.json()["tipo"] == "NOTA_DEBITO"

    stock_despues = client.get(f"/api/inventario/productos/{producto_id}/stock").json()["cantidad"]
    assert float(stock_despues) == float(stock_antes)

    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert any(
        m["tipo"] == "INGRESO" and float(m["monto"]) == float(importe) for m in movs
    )


def test_credito_cuenta_corriente_reduce_saldo(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """Crédito en cuenta corriente registra MovimientoCuentaCorriente PAGO y reduce saldo."""
    # Persona + cliente
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "30 días",
            "limite_credito": "1000.00",
        },
    )
    assert r_cliente.status_code == 201
    cliente_id = r_cliente.json()["id"]

    # Producto + stock
    producto = dict(producto_datos)
    producto.update({"sku": "TEST-CC", "nombre": "Producto CC", "precio_venta": "10.00"})
    r_prod = client.post("/api/productos", json=producto)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    # Venta TEU_ON a CUENTA_CORRIENTE (aumenta saldo/deuda)
    total = Decimal("20.00")
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "CUENTA_CORRIENTE",
            "cliente_id": persona_id,
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    resumen0 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    assert float(resumen0["saldo"]) == float(total)

    # Crédito en cuenta corriente por 6 => saldo pasa a 14
    credito = Decimal("6.00")
    r_cc = client.post(
        "/api/operaciones-comerciales/creditos-cuenta-corriente",
        json={"venta_id": venta_id, "importe": str(credito), "motivo": "Ajuste comercial"},
    )
    assert r_cc.status_code == 200, r_cc.json()
    assert r_cc.json()["tipo"] == "CREDITO_CUENTA_CORRIENTE"

    resumen1 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    assert float(resumen1["saldo"]) == float(total - credito)


def test_cambio_producto_parcial_efectivo_ajusta_stock_y_items(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Cambio de producto parcial (EFECTIVO) ajusta stock e items del ticket."""
    # Caja abierta
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    # Productos A y B
    producto_a = dict(producto_datos)
    producto_a.update({"sku": "TEST-A2", "nombre": "Producto A2", "precio_venta": "10.00"})
    producto_b = dict(producto_datos)
    producto_b.update({"sku": "TEST-B2", "nombre": "Producto B2", "precio_venta": "15.00"})

    ra = client.post("/api/productos", json=producto_a)
    assert ra.status_code == 201
    producto_a_id = ra.json()["id"]
    rb = client.post("/api/productos", json=producto_b)
    assert rb.status_code == 201
    producto_b_id = rb.json()["id"]

    # Stock inicial
    _ingresar_stock(client, producto_a_id, 10)
    _ingresar_stock(client, producto_b_id, 20)

    precio_a = Decimal(str(producto_a["precio_venta"]))
    cantidad_a = Decimal("3")

    # Venta pagada con A (3 uds)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_a_id, "cantidad": str(cantidad_a)}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]
    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "PAGADA"

    item_a_id = venta["items"][0]["id"]

    # Cambio parcial: devolver 1 de A y agregar 1 de B
    dev = Decimal("1")
    diferencia = (Decimal(str(producto_b["precio_venta"])) - precio_a) * dev  # 5.00
    r_cam = client.post(
        "/api/operaciones-comerciales/cambios",
        json={
            "venta_id": venta_id,
            "items_devueltos": [{"item_venta_id": item_a_id, "cantidad": str(dev)}],
            "items_nuevos": [{"producto_id": producto_b_id, "cantidad": str(dev)}],
            "reintegro_tipo_diferencia": "EFECTIVO",
            "reintegro_metodo_pago": "EFECTIVO",
            "motivo": "Cambio parcial",
        },
    )
    assert r_cam.status_code == 200, r_cam.json()

    # Stock A: 10 - 3 + 1 = 8
    stock_a = client.get(f"/api/inventario/productos/{producto_a_id}/stock").json()["cantidad"]
    assert float(stock_a) == 8.0

    # Stock B: 20 - 1 = 19
    stock_b = client.get(f"/api/inventario/productos/{producto_b_id}/stock").json()["cantidad"]
    assert float(stock_b) == 19.0

    # Items del ticket: A queda en 2 y B agrega 1
    venta2 = client.get(f"/api/ventas/{venta_id}").json()
    items = {it["producto_id"]: it for it in venta2["items"]}
    assert float(items[producto_a_id]["cantidad"]) == 2.0
    assert float(items[producto_b_id]["cantidad"]) == 1.0

    # Caja registra movimiento VENTA por diferencia
    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert any(m["tipo"] == "VENTA" and float(m["monto"]) == float(diferencia) for m in movs)


def test_cambio_producto_parcial_cuenta_corriente_signo(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """Cambio parcial con CUENTA_CORRIENTE ajusta saldo con signo correcto."""
    # Crear persona + rol cliente
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "30 días",
            "limite_credito": "1000.00",
        },
    )
    assert r_cliente.status_code == 201
    cliente_id = r_cliente.json()["id"]

    # Productos A y B
    producto_a = dict(producto_datos)
    producto_a.update({"sku": "TEST-ACC-A", "nombre": "Producto CC A", "precio_venta": "10.00"})
    producto_b = dict(producto_datos)
    producto_b.update({"sku": "TEST-ACC-B", "nombre": "Producto CC B", "precio_venta": "15.00"})
    ra = client.post("/api/productos", json=producto_a)
    assert ra.status_code == 201
    producto_a_id = ra.json()["id"]
    rb = client.post("/api/productos", json=producto_b)
    assert rb.status_code == 201
    producto_b_id = rb.json()["id"]

    _ingresar_stock(client, producto_a_id, 10)
    _ingresar_stock(client, producto_b_id, 10)

    # Venta TEU_ON pagada a CUENTA_CORRIENTE (A x3 => total 30)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_a_id, "cantidad": "3"}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "CUENTA_CORRIENTE",
            "cliente_id": persona_id,
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]
    venta = client.get(f"/api/ventas/{venta_id}").json()
    item_a_id = venta["items"][0]["id"]

    resumen0 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    assert float(resumen0["saldo"]) == 30.0

    # Cambio parcial: devolver 1 A y agregar 1 B => diferencia +5
    r_cam = client.post(
        "/api/operaciones-comerciales/cambios",
        json={
            "venta_id": venta_id,
            "items_devueltos": [{"item_venta_id": item_a_id, "cantidad": "1"}],
            "items_nuevos": [{"producto_id": producto_b_id, "cantidad": "1"}],
            "reintegro_tipo_diferencia": "CUENTA_CORRIENTE",
            "reintegro_metodo_pago": None,
            "motivo": "Cambio parcial CC",
        },
    )
    assert r_cam.status_code == 200, r_cam.json()

    resumen1 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    # Saldo aumenta en +5
    assert float(resumen1["saldo"]) == 35.0


def test_cambio_producto_parcial_efectivo_diferencia_negativa(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Cambio parcial con EFECTIVO: si la diferencia es negativa, el comercio devuelve."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    # Producto B (caro) y A (barato)
    producto_a = dict(producto_datos)
    producto_a.update({"sku": "TEST-A-N1", "nombre": "Producto A-N1", "precio_venta": "10.00"})
    producto_b = dict(producto_datos)
    producto_b.update({"sku": "TEST-B-N1", "nombre": "Producto B-N1", "precio_venta": "15.00"})

    ra = client.post("/api/productos", json=producto_a)
    assert ra.status_code == 201
    producto_a_id = ra.json()["id"]
    rb = client.post("/api/productos", json=producto_b)
    assert rb.status_code == 201
    producto_b_id = rb.json()["id"]

    _ingresar_stock(client, producto_a_id, 10)
    _ingresar_stock(client, producto_b_id, 20)

    precio_b = Decimal(str(producto_b["precio_venta"]))
    precio_a = Decimal(str(producto_a["precio_venta"]))
    cantidad_v = Decimal("2")
    total_venta = precio_b * cantidad_v  # 30

    # Venta TEU_ON pagada con B (2 uds)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_b_id, "cantidad": str(cantidad_v)}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "PAGADA"
    item_b_id = venta["items"][0]["id"]

    # Cambio parcial: devolver 1 B y agregar 1 A => diferencia = (10 - 15) * 1 = -5
    dev = Decimal("1")
    diferencia = (precio_a - precio_b) * dev  # -5.00
    r_cam = client.post(
        "/api/operaciones-comerciales/cambios",
        json={
            "venta_id": venta_id,
            "items_devueltos": [{"item_venta_id": item_b_id, "cantidad": str(dev)}],
            "items_nuevos": [{"producto_id": producto_a_id, "cantidad": str(dev)}],
            "reintegro_tipo_diferencia": "EFECTIVO",
            "reintegro_metodo_pago": "EFECTIVO",
            "motivo": "Cambio parcial EFECTIVO diferencia negativa",
        },
    )
    assert r_cam.status_code == 200, r_cam.json()

    # Stock B: 20 - 2 + 1 = 19
    stock_b = client.get(f"/api/inventario/productos/{producto_b_id}/stock").json()[
        "cantidad"
    ]
    assert float(stock_b) == 19.0

    # Stock A: 10 - 1 = 9
    stock_a = client.get(f"/api/inventario/productos/{producto_a_id}/stock").json()[
        "cantidad"
    ]
    assert float(stock_a) == 9.0

    # Items del ticket: B queda en 1 y A agrega 1
    venta2 = client.get(f"/api/ventas/{venta_id}").json()
    items = {it["producto_id"]: it for it in venta2["items"]}
    assert float(items[producto_b_id]["cantidad"]) == 1.0
    assert float(items[producto_a_id]["cantidad"]) == 1.0

    # Caja registra DEVOLUCION por abs(diferencia)
    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert any(
        m["tipo"] == "DEVOLUCION" and float(m["monto"]) == float(abs(diferencia))
        for m in movs
    )


def test_cambio_producto_parcial_cuenta_corriente_diferencia_negativa(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """Cambio parcial con CUENTA_CORRIENTE: si la diferencia es negativa, el saldo disminuye."""
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "30 días",
            "limite_credito": "10000.00",
        },
    )
    assert r_cliente.status_code == 201
    cliente_id = r_cliente.json()["id"]

    producto_a = dict(producto_datos)
    producto_a.update({"sku": "TEST-A-N2", "nombre": "Producto A-N2", "precio_venta": "10.00"})
    producto_b = dict(producto_datos)
    producto_b.update({"sku": "TEST-B-N2", "nombre": "Producto B-N2", "precio_venta": "15.00"})
    ra = client.post("/api/productos", json=producto_a)
    assert ra.status_code == 201
    producto_a_id = ra.json()["id"]
    rb = client.post("/api/productos", json=producto_b)
    assert rb.status_code == 201
    producto_b_id = rb.json()["id"]

    _ingresar_stock(client, producto_a_id, 10)
    _ingresar_stock(client, producto_b_id, 10)

    precio_b = Decimal(str(producto_b["precio_venta"]))
    cantidad_v = Decimal("3")
    total_venta = precio_b * cantidad_v  # 45

    # Venta TEU_ON pagada a CUENTA_CORRIENTE (B x3)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_b_id, "cantidad": str(cantidad_v)}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "CUENTA_CORRIENTE",
            "cliente_id": persona_id,
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    resumen0 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    assert float(resumen0["saldo"]) == float(total_venta)

    venta = client.get(f"/api/ventas/{venta_id}").json()
    item_b_id = venta["items"][0]["id"]

    # Cambio parcial: devolver 1 B y agregar 1 A => diferencia = (10 - 15) * 1 = -5
    r_cam = client.post(
        "/api/operaciones-comerciales/cambios",
        json={
            "venta_id": venta_id,
            "items_devueltos": [{"item_venta_id": item_b_id, "cantidad": "1"}],
            "items_nuevos": [{"producto_id": producto_a_id, "cantidad": "1"}],
            "reintegro_tipo_diferencia": "CUENTA_CORRIENTE",
            "reintegro_metodo_pago": None,
            "motivo": "Cambio parcial CC diferencia negativa",
        },
    )
    assert r_cam.status_code == 200, r_cam.json()

    resumen1 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    # Saldo disminuye en 5
    assert float(resumen1["saldo"]) == float(total_venta - Decimal("5.00"))

