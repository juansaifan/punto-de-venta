from decimal import Decimal

from fastapi.testclient import TestClient


def test_anulacion_venta_pagada_efectivo_reingresa_stock_y_debita_caja(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Anular una venta PAGADA EFECTIVO debe restaurar stock y registrar DEVOLUCION en caja."""
    # Stock inicial
    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]

    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10"},
    )

    # Abrir caja
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    precio = Decimal(str(producto_datos["precio_venta"]))
    cantidad = Decimal("2")
    total = precio * cantidad

    # Venta TEU_ON PAGADA EFECTIVO
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": str(cantidad)}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    # Stock disminuye
    stock_post = client.get(
        f"/api/inventario/productos/{producto_id}/stock"
    ).json()["cantidad"]
    assert float(stock_post) == float(Decimal("8"))

    # Anular
    r_anul = client.post(
        "/api/operaciones-comerciales/anulaciones",
        json={"venta_id": venta_id, "motivo": "Anulacion test"},
    )
    assert r_anul.status_code == 200
    assert r_anul.json()["tipo"] == "ANULACION"
    assert r_anul.json()["estado"] == "EJECUTADA"

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "CANCELADA"

    # Stock restaurado
    stock_final = client.get(
        f"/api/inventario/productos/{producto_id}/stock"
    ).json()["cantidad"]
    assert float(stock_final) == float(Decimal("10"))

    # Caja registra DEVOLUCION por total
    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert any(
        m["tipo"] == "DEVOLUCION" and float(m["monto"]) == float(total)
        for m in movs
    )


def test_anulacion_venta_fiada_cuenta_corriente_no_debita_caja(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """Anular una venta FIADA CUENTA_CORRIENTE debe revertir cuenta corriente pero no requiere movimiento de caja DEVOLUCION."""
    # Persona y cliente con cuenta corriente
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "30 dias",
            "limite_credito": "1000.00",
        },
    )
    assert r_cliente.status_code == 201
    cliente_id = r_cliente.json()["id"]

    # Producto + stock
    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10"},
    )

    # Abrir caja para que el flujo TEU_OFF asigne caja_id (pero no habrá movimiento de caja en CUENTA_CORRIENTE)
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    _caja_id = abrir.json()["id"]

    precio = Decimal(str(producto_datos["precio_venta"]))
    cantidad = Decimal("2")
    total = precio * cantidad

    # TEU_OFF => pendiente
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": str(cantidad)}],
            "descuento": "0",
            "modo_venta": "TEU_OFF",
            "cliente_id": persona_id,
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    # Cobrar FIADA con CUENTA_CORRIENTE
    r_cobro = client.post(
        f"/api/caja/tickets/{venta_id}/cobrar",
        json={
            "pagos": [{"metodo_pago": "CUENTA_CORRIENTE", "importe": str(total)}]
        },
    )
    assert r_cobro.status_code == 200
    assert r_cobro.json()["estado"] == "FIADA"

    # Cuenta corriente saldo debe ser total
    resumen0 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    assert float(resumen0["saldo"]) == float(total)

    # Anular (revertir cuenta corriente)
    r_anul = client.post(
        "/api/operaciones-comerciales/anulaciones",
        json={"venta_id": venta_id, "motivo": "Anulacion FIADA test"},
    )
    assert r_anul.status_code == 200
    assert r_anul.json()["tipo"] == "ANULACION"

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "CANCELADA"

    # Cuenta corriente saldo vuelve a 0
    resumen1 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    assert float(resumen1["saldo"]) == 0.0


def test_anulacion_venta_pagada_efectivo_con_caja_cerrada_no_falla(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Anular una venta PAGADA EFECTIVO no depende de la caja 'abierta' actual."""
    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]

    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10"},
    )

    # Abrir caja y registrar venta TEU_ON pagada en efectivo.
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    precio = Decimal(str(producto_datos["precio_venta"]))
    cantidad = Decimal("2")
    total = precio * cantidad

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": str(cantidad)}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]

    # Cerrar la caja antes de anular.
    r_cerrar = client.post(
        f"/api/caja/{caja_id}/cerrar",
        json={"saldo_final": str(total), "supervisor_autorizado": False},
    )
    assert r_cerrar.status_code == 200

    # Anular: debe restaurar stock y cancelar la venta (sin depender de caja abierta).
    r_anul = client.post(
        "/api/operaciones-comerciales/anulaciones",
        json={"venta_id": venta_id, "motivo": "Anulacion caja cerrada"},
    )
    assert r_anul.status_code == 200
    assert r_anul.json()["estado"] == "EJECUTADA"

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "CANCELADA"

    stock_final = client.get(
        f"/api/inventario/productos/{producto_id}/stock"
    ).json()["cantidad"]
    assert float(stock_final) == float(Decimal("10"))

    # Como la caja está cerrada, el movimiento de DEVOLUCION puede no registrarse.
    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert not any(
        m["tipo"] == "DEVOLUCION" and float(m["monto"]) == float(total)
        for m in movs
    )

