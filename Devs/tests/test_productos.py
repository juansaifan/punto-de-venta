"""Tests de la API y lógica de productos."""
from fastapi.testclient import TestClient


def test_listar_productos_vacio(client: TestClient) -> None:
    """Listar productos sin datos devuelve lista vacía."""
    r = client.get("/api/productos")
    assert r.status_code == 200
    assert r.json() == []


def test_crear_producto_ok(client: TestClient, producto_datos: dict) -> None:
    """Crear producto con datos válidos devuelve 201 y el recurso."""
    r = client.post("/api/productos", json=producto_datos)
    assert r.status_code == 201
    data = r.json()
    assert data["sku"] == producto_datos["sku"]
    assert data["nombre"] == producto_datos["nombre"]
    assert float(data["precio_venta"]) == float(producto_datos["precio_venta"])
    assert "id" in data
    assert data["activo"] is True


def test_crear_producto_sku_duplicado_falla(client: TestClient, producto_datos: dict) -> None:
    """Crear dos productos con el mismo SKU devuelve 409 en el segundo."""
    client.post("/api/productos", json=producto_datos)
    r = client.post("/api/productos", json=producto_datos)
    assert r.status_code == 409
    assert "SKU" in r.json()["detail"] or "sku" in r.json()["detail"].lower()


def test_obtener_producto_por_id_ok(client: TestClient, producto_datos: dict) -> None:
    """Crear producto y obtenerlo por ID devuelve el mismo recurso."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    pid = crear.json()["id"]
    r = client.get(f"/api/productos/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid
    assert r.json()["nombre"] == producto_datos["nombre"]


def test_obtener_producto_por_id_404(client: TestClient) -> None:
    """Obtener producto por ID inexistente devuelve 404."""
    r = client.get("/api/productos/99999")
    assert r.status_code == 404


def test_obtener_producto_por_sku_ok(client: TestClient, producto_datos: dict) -> None:
    """Obtener producto por SKU devuelve el recurso."""
    client.post("/api/productos", json=producto_datos)
    r = client.get(f"/api/productos/por-sku/{producto_datos['sku']}")
    assert r.status_code == 200
    assert r.json()["sku"] == producto_datos["sku"]


def test_obtener_producto_por_sku_404(client: TestClient) -> None:
    """Obtener producto por SKU inexistente devuelve 404."""
    r = client.get("/api/productos/por-sku/NO-EXISTE")
    assert r.status_code == 404


def test_actualizar_producto_ok(client: TestClient, producto_datos: dict) -> None:
    """Actualizar producto existente devuelve 200 y datos actualizados."""
    crear = client.post("/api/productos", json=producto_datos)
    pid = crear.json()["id"]
    r = client.patch(
        f"/api/productos/{pid}",
        json={"nombre": "Nombre actualizado", "precio_venta": "15.00"},
    )
    assert r.status_code == 200
    assert r.json()["nombre"] == "Nombre actualizado"
    assert float(r.json()["precio_venta"]) == 15.0


def test_actualizar_producto_404(client: TestClient) -> None:
    """Actualizar producto inexistente devuelve 404."""
    r = client.patch(
        "/api/productos/99999",
        json={"nombre": "Algo"},
    )
    assert r.status_code == 404


def test_listar_productos_incluye_creados(client: TestClient, producto_datos: dict) -> None:
    """Después de crear productos, listar los incluye."""
    client.post("/api/productos", json=producto_datos)
    otro = {**producto_datos, "sku": "TEST-002", "nombre": "Otro producto"}
    client.post("/api/productos", json=otro)
    r = client.get("/api/productos?activo_only=false")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2
    skus = [p["sku"] for p in items]
    assert "TEST-001" in skus
    assert "TEST-002" in skus
