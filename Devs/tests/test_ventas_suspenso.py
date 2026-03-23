from decimal import Decimal

from fastapi.testclient import TestClient


def _ingresar_stock(client: TestClient, producto_id: int, cantidad: str | float) -> None:
    r = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": str(cantidad)},
    )
    assert r.status_code == 200, r.json()


def test_suspender_y_reanudar_venta_teu_off(client: TestClient, producto_datos: dict) -> None:
    """Suspender TEU_OFF saca el ticket de la cola; reanudar lo vuelve a poner."""
    # Abrir caja (para usar endpoints de caja/tickets)
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    # Producto + stock
    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    # Venta TEU_OFF pendiente
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

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "PENDIENTE"

    # Suspender
    susp = client.post(f"/api/ventas/{venta_id}/suspender")
    assert susp.status_code == 200
    assert susp.json()["estado"] == "SUSPENDIDA"

    # No aparece en cola de pendientes
    cola = client.get("/api/caja/tickets/pendientes").json()
    assert not any(t["venta_id"] == venta_id for t in cola)

    # Reanudar
    rea = client.post(f"/api/ventas/{venta_id}/reanudar")
    assert rea.status_code == 200
    assert rea.json()["estado"] == "PENDIENTE"

    cola2 = client.get("/api/caja/tickets/pendientes").json()
    assert any(t["venta_id"] == venta_id for t in cola2)


def test_no_permite_suspender_venta_pagada(client: TestClient, producto_datos: dict) -> None:
    """No se puede suspender una venta ya pagada (PAGADA)."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200

    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    venta_resp = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "modo_venta": "TEU_ON",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert venta_resp.status_code == 200
    venta_id = venta_resp.json()["venta_id"]

    venta = client.get(f"/api/ventas/{venta_id}").json()
    assert venta["estado"] == "PAGADA"

    susp = client.post(f"/api/ventas/{venta_id}/suspender")
    assert susp.status_code == 400
    assert "pendiente" in susp.json()["detail"].lower()


def test_cobrar_ticket_suspendido_falla(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Un ticket suspendido no puede cobrarse."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200
    _ = abrir.json()["id"]

    crear_p = client.post("/api/productos", json=producto_datos)
    assert crear_p.status_code == 201
    producto_id = crear_p.json()["id"]
    _ingresar_stock(client, producto_id, 10)

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

    susp = client.post(f"/api/ventas/{venta_id}/suspender")
    assert susp.status_code == 200

    venta = client.get(f"/api/ventas/{venta_id}").json()
    total = Decimal(str(venta["total"]))

    cobro = client.post(
        f"/api/caja/tickets/{venta_id}/cobrar",
        json={
            "pagos": [{"metodo_pago": "EFECTIVO", "importe": str(total)}],
            "observaciones": "Intento de cobro estando suspendido",
        },
    )
    assert cobro.status_code == 400
    assert "pendiente" in cobro.json()["detail"].lower()

