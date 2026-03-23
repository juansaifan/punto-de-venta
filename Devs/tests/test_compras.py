"""Tests del API de Compras/Proveedores."""
from fastapi.testclient import TestClient


def test_listar_compras_sin_datos_devuelve_lista_vacia(client: TestClient) -> None:
    """GET /compras sin datos devuelve lista vacía."""
    r = client.get("/api/compras")
    assert r.status_code == 200
    assert r.json() == []


def test_crear_compra_con_items_crea_registro(client: TestClient, producto_datos: dict, persona_datos: dict) -> None:
    """Crear una compra con ítems calcula el total y la asocia a un proveedor."""
    # Crear proveedor como Persona
    r_prov = client.post("/api/personas", json=persona_datos)
    assert r_prov.status_code == 201
    proveedor_id = r_prov.json()["id"]

    # Crear producto
    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    body = {
        "proveedor_id": proveedor_id,
        "items": [
            {
                "producto_id": producto_id,
                "cantidad": "5",
                "costo_unitario": "10.50",
            }
        ],
    }
    r = client.post("/api/compras", json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["proveedor_id"] == proveedor_id
    assert data["total"] == 52.5  # 5 * 10.50
    assert data["estado"] == "CONFIRMADA"
    assert "fecha" in data

    # La compra debe aparecer en el listado
    r_list = client.get("/api/compras")
    assert r_list.status_code == 200
    compras = r_list.json()
    assert any(c["id"] == data["id"] for c in compras)


def test_crear_compra_sin_items_422(client: TestClient, persona_datos: dict) -> None:
    """Crear compra sin items devuelve 422."""
    r_prov = client.post("/api/personas", json=persona_datos)
    assert r_prov.status_code == 201
    proveedor_id = r_prov.json()["id"]

    r = client.post(
        "/api/compras",
        json={"proveedor_id": proveedor_id, "items": []},
    )
    assert r.status_code == 422


def test_crear_compra_proveedor_inexistente_404(client: TestClient, producto_datos: dict) -> None:
    """Crear compra con proveedor inexistente devuelve 404."""
    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    body = {
        "proveedor_id": 99999,
        "items": [
            {
                "producto_id": producto_id,
                "cantidad": "1",
                "costo_unitario": "10",
            }
        ],
    }
    r = client.post("/api/compras", json=body)
    assert r.status_code == 404


def test_crear_compra_producto_inexistente_404(client: TestClient, persona_datos: dict) -> None:
    """Crear compra con producto inexistente devuelve 404."""
    r_prov = client.post("/api/personas", json=persona_datos)
    assert r_prov.status_code == 201
    proveedor_id = r_prov.json()["id"]

    body = {
        "proveedor_id": proveedor_id,
        "items": [
            {
                "producto_id": 99999,
                "cantidad": "1",
                "costo_unitario": "10",
            }
        ],
    }
    r = client.post("/api/compras", json=body)
    assert r.status_code == 404


def test_crear_compra_ingresa_stock_y_registra_gasto(
    client: TestClient,
    persona_datos: dict,
    producto_datos: dict,
) -> None:
    """Al crear una compra se ingresa stock y se registra un gasto financiero en alguna cuenta."""
    # Crear proveedor
    r_prov = client.post("/api/personas", json=persona_datos)
    assert r_prov.status_code == 201
    proveedor_id = r_prov.json()["id"]

    # Crear producto
    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    # Crear cuenta financiera que actuará como cuenta de compras
    r_cuenta = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Compras", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert r_cuenta.status_code == 201
    cuenta_id = r_cuenta.json()["id"]

    # Registrar compra
    r_compra = client.post(
        "/api/compras",
        json={
            "proveedor_id": proveedor_id,
            "items": [
                {
                    "producto_id": producto_id,
                    "cantidad": "4",
                    "costo_unitario": "5.00",
                }
            ],
        },
    )
    assert r_compra.status_code == 201
    compra = r_compra.json()
    assert compra["total"] == 20.0

    # Verificar stock ingresado
    r_stock = client.get(f"/api/inventario/productos/{producto_id}/stock")
    assert r_stock.status_code == 200
    assert float(r_stock.json()["cantidad"]) == 4.0

    # Verificar que se registró al menos una transacción de gasto en la cuenta
    r_tx = client.get(f"/api/finanzas/cuentas/{cuenta_id}/transacciones")
    assert r_tx.status_code == 200
    transacciones = r_tx.json()
    assert any(tx["tipo"] == "gasto" and tx["monto"] == 20.0 for tx in transacciones)

