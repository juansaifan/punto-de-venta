from decimal import Decimal

from fastapi.testclient import TestClient


def _ingresar_stock(client: TestClient, producto_id: int, cantidad: str | float) -> None:
    r = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": str(cantidad)},
    )
    assert r.status_code == 200, r.json()


def test_teu_off_generar_ticket_pendiente_sin_movimiento_caja(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """TEU_OFF debe crear ticket pendiente y no registrar movimiento de caja."""
    # Abrir caja (aunque TEU_OFF no debe registrar el cobro)
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    # Crear producto + stock
    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    # Registrar venta en TEU_OFF sin metodo de pago
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "modo_venta": "TEU_OFF",
            # metodo_pago omitido
        },
    )
    assert r.status_code == 200
    venta_id = r.json()["venta_id"]

    venta = client.get(f"/api/ventas/{venta_id}")
    assert venta.status_code == 200
    venta_data = venta.json()
    assert venta_data["estado"] == "PENDIENTE"
    assert venta_data["caja_id"] is None
    assert venta_data["numero_ticket"] is not None

    # La cola de pendientes debe incluir el ticket
    col = client.get("/api/caja/tickets/pendientes")
    assert col.status_code == 200
    pend = col.json()
    assert any(t["venta_id"] == venta_id for t in pend)

    # No debe haber movimientos VENTA por esta venta
    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    tipos = {m["tipo"] for m in movs}
    assert "VENTA" not in tipos


def test_cobrar_ticket_teu_off_efectivo(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Cobrar un ticket pendiente en EFECTIVO debe marcar PAGADA y registrar movimiento."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    _ingresar_stock(client, producto_id, 20)

    # total = precio_venta(10.50) * 2 = 21.00
    total = Decimal(str(producto_datos["precio_venta"])) * Decimal("2")
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "modo_venta": "TEU_OFF",
        },
    )
    assert r.status_code == 200
    venta_id = r.json()["venta_id"]

    cobro = client.post(
        f"/api/caja/tickets/{venta_id}/cobrar",
        json={
            "pagos": [
                {
                    "metodo_pago": "EFECTIVO",
                    "importe": str(total),
                    "medio_pago": "EFECTIVO",
                }
            ],
            "observaciones": "Cobro TEU_OFF en caja",
        },
    )
    assert cobro.status_code == 200, cobro.json()
    cobro_data = cobro.json()
    assert cobro_data["venta_id"] == venta_id
    assert cobro_data["estado"] == "PAGADA"
    assert cobro_data["metodo_pago"] == "EFECTIVO"
    assert cobro_data["caja_id"] == caja_id

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "PAGADA"
    assert venta["caja_id"] == caja_id

    movs = client.get(f"/api/caja/{caja_id}/movimientos").json()
    assert any(float(m["monto"]) == float(total) and m["tipo"] == "VENTA" for m in movs)

    # Ya no debe aparecer en la cola de pendientes
    col = client.get("/api/caja/tickets/pendientes").json()
    assert not any(t["venta_id"] == venta_id for t in col)


def test_cobrar_ticket_teu_off_cuenta_corriente_fiada_y_limite(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """Cobro CUENTA_CORRIENTE debe actualizar cuenta y respetar limite_credito."""
    # Crear persona + rol cliente
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    limite = Decimal("100.00")
    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "30 días",
            "limite_credito": str(limite),
        },
    )
    assert r_cliente.status_code == 201
    cliente_id = r_cliente.json()["id"]

    # Crear producto + stock
    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    _ingresar_stock(client, producto_id, 50)

    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    precio = Decimal(str(producto_datos["precio_venta"]))  # 10.50
    total1 = precio * Decimal("6")  # 63.00
    total2 = precio * Decimal("4")  # 42.00 => 105.00 > 100.00

    # Venta TEU_OFF #1
    r1 = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "6"}],
            "descuento": "0",
            "modo_venta": "TEU_OFF",
            "cliente_id": persona_id,
        },
    )
    assert r1.status_code == 200
    venta_id_1 = r1.json()["venta_id"]

    cobro1 = client.post(
        f"/api/caja/tickets/{venta_id_1}/cobrar",
        json={
            "pagos": [
                {
                    "metodo_pago": "CUENTA_CORRIENTE",
                    "importe": str(total1),
                }
            ],
            "observaciones": "Fiada TEU_OFF",
        },
    )
    assert cobro1.status_code == 200, cobro1.json()
    data1 = cobro1.json()
    assert data1["estado"] == "FIADA"
    assert data1["metodo_pago"] == "CUENTA_CORRIENTE"
    assert data1["caja_id"] == caja_id

    # Saldo cuenta corriente debe aumentar
    resumen = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    ).json()
    assert float(resumen["saldo"]) == float(total1)

    # Venta TEU_OFF #2 (debe exceder el limite)
    r2 = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "4"}],
            "descuento": "0",
            "modo_venta": "TEU_OFF",
            "cliente_id": persona_id,
        },
    )
    assert r2.status_code == 200
    venta_id_2 = r2.json()["venta_id"]

    cobro2 = client.post(
        f"/api/caja/tickets/{venta_id_2}/cobrar",
        json={
            "pagos": [
                {
                    "metodo_pago": "CUENTA_CORRIENTE",
                    "importe": str(total2),
                }
            ],
            "observaciones": "Fiada TEU_OFF 2",
        },
    )
    assert cobro2.status_code == 400
    assert "limite" in cobro2.json()["detail"].lower() or "crédito" in cobro2.json()["detail"].lower()

