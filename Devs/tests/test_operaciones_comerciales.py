from decimal import Decimal

from fastapi.testclient import TestClient


def test_anular_venta_pendiente_restaurar_stock(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Anular una venta TEU_OFF pendiente debe revertir el descuento de stock."""
    # Crear producto + stock inicial
    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]

    ingresar = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10"},
    )
    assert ingresar.status_code == 200

    # Venta TEU_OFF en estado PENDIENTE
    venta_resp = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "modo_venta": "TEU_OFF",
        },
    )
    assert venta_resp.status_code == 200
    venta_id = venta_resp.json()["venta_id"]

    stock_antes = client.get(
        f"/api/inventario/productos/{producto_id}/stock"
    ).json()["cantidad"]
    assert float(stock_antes) == float(Decimal("10") - Decimal("2"))

    # Anular ticket pendiente
    anul = client.post(
        "/api/operaciones-comerciales/anulaciones",
        json={"venta_id": venta_id, "motivo": "Cancelación operativa"},
    )
    assert anul.status_code == 200, anul.json()
    assert anul.json()["tipo"] == "ANULACION"

    # Venta debe quedar cancelada
    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "CANCELADA"

    # Stock debe volver al valor inicial
    stock_despues = client.get(
        f"/api/inventario/productos/{producto_id}/stock"
    ).json()["cantidad"]
    assert float(stock_despues) == float(Decimal("10"))

    # Debe existir movimiento de inventario DEVOLUCION (reingreso)
    movs = client.get(
        "/api/inventario/movimientos",
        params={"producto_id": producto_id, "tipo": "DEVOLUCION"},
    ).json()
    assert any(float(m["cantidad"]) >= 2 for m in movs)


def test_devolucion_a_efectivo_reingresa_stock_y_registra_caja(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Una devolución EFECTIVO reingresa stock y registra movimiento de caja DEVOLUCION."""
    # Abrir caja
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    # Producto + stock
    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    assert client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10"},
    ).status_code == 200

    precio = Decimal(str(producto_datos["precio_venta"]))
    # Venta TEU_ON PAGADA
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "PAGADA"
    item_venta_id = venta["items"][0]["id"]

    # Devolver 1 unidad
    importe_dev = precio * Decimal("1")
    r_dev = client.post(
        "/api/operaciones-comerciales/devoluciones",
        json={
            "venta_id": venta_id,
            "reintegro_tipo": "EFECTIVO",
            "reintegro_metodo_pago": "EFECTIVO",
            "motivo": "Devolución de 1 unidad",
            "items": [{"item_venta_id": item_venta_id, "cantidad": "1"}],
        },
    )
    assert r_dev.status_code == 200, r_dev.json()
    assert r_dev.json()["tipo"] == "DEVOLUCION"
    assert float(r_dev.json()["importe_total"]) == float(importe_dev)

    # Stock debe aumentar en 1
    stock = client.get(
        f"/api/inventario/productos/{producto_id}/stock"
    ).json()["cantidad"]
    assert float(stock) == float(Decimal("9"))

    # Caja debe tener movimiento DEVOLUCION por importe_dev
    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert any(
        m["tipo"] == "DEVOLUCION" and float(m["monto"]) == float(importe_dev)
        for m in movs
    )


def test_nota_credito_efectivo_registra_caja_sin_modificar_stock(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Nota de crédito EFECTIVO registra caja DEVOLUCION y no toca inventario."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    assert client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10"},
    ).status_code == 200

    # Venta TEU_ON pagada
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    stock_antes = client.get(
        f"/api/inventario/productos/{producto_id}/stock"
    ).json()["cantidad"]

    nota = client.post(
        "/api/operaciones-comerciales/notas-credito",
        json={
            "venta_id": venta_id,
            "reintegro_tipo": "EFECTIVO",
            "reintegro_metodo_pago": "EFECTIVO",
            "importe": "5.00",
            "motivo": "Ajuste comercial",
        },
    )
    assert nota.status_code == 200, nota.json()
    assert nota.json()["tipo"] == "NOTA_CREDITO"

    stock_despues = client.get(
        f"/api/inventario/productos/{producto_id}/stock"
    ).json()["cantidad"]
    assert float(stock_despues) == float(stock_antes)

    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert any(
        m["tipo"] == "DEVOLUCION" and float(m["monto"]) == 5.0
        for m in movs
    )

