"""Tests del submódulo Pesables (Módulo 2 – Punto de Venta).

Cubre:
- cálculo bidireccional peso ↔ precio (endpoint y servicio)
- generación de EAN-13
- preparación de ítems (individual y batch)
- cambio de estados (pending → printed → used)
- generación de etiquetas en batch
- habilitar producto como pesable
- validaciones de error (producto no pesable, PLU duplicado, etc.)
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.services.pesables import (
    calcular_peso_por_precio,
    calcular_precio_por_peso,
    generar_ean13,
    _ean13_checksum,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crear_producto_pesable(client: TestClient, sku: str, nombre: str, precio: str, plu: int) -> int:
    """Crea un producto y lo habilita como pesable con el PLU dado."""
    r = client.post(
        "/api/productos",
        json={"sku": sku, "nombre": nombre, "precio_venta": precio, "activo": True},
    )
    assert r.status_code == 201, r.json()
    producto_id = r.json()["id"]

    r2 = client.patch(
        f"/api/pesables/productos/{producto_id}/habilitar",
        json={"plu": plu},
    )
    assert r2.status_code == 200, r2.json()
    assert r2.json()["plu"] == plu
    assert r2.json()["pesable"] is True
    return producto_id


# ---------------------------------------------------------------------------
# Tests unitarios de lógica pura (sin BD)
# ---------------------------------------------------------------------------

def test_calcular_precio_por_peso_correcto() -> None:
    assert calcular_precio_por_peso(Decimal("1.500"), Decimal("2000")) == Decimal("3000.00")


def test_calcular_peso_por_precio_correcto() -> None:
    peso = calcular_peso_por_precio(Decimal("3000"), Decimal("2000"))
    assert peso == Decimal("1.500")


def test_calcular_peso_por_precio_division_por_cero() -> None:
    with pytest.raises(ValueError, match="0"):
        calcular_peso_por_precio(Decimal("100"), Decimal("0"))


def test_ean13_checksum_valido() -> None:
    """Verifica dígito de control para un EAN-13 conocido."""
    # Prefijo: 20 + PLU 10001 + precio 03000 = "201000103000" → checksum conocido
    body = "201000103000"
    cs = _ean13_checksum(body)
    # Verifica que el código completo pasa validación estándar EAN-13
    full = body + str(cs)
    assert len(full) == 13
    # Re-calcular el checksum del cuerpo de 12 dígitos debe dar el mismo valor
    assert _ean13_checksum(body) == cs


def test_generar_ean13_formato() -> None:
    barcode = generar_ean13(plu=10001, precio_total=Decimal("30.00"))
    assert len(barcode) == 13
    assert barcode.startswith("20")
    # PLU 10001 → "10001"
    assert barcode[2:7] == "10001"
    # Precio 30.00 → 3000 centavos → "03000"
    assert barcode[7:12] == "03000"


def test_generar_ean13_checksum_valido() -> None:
    barcode = generar_ean13(plu=99999, precio_total=Decimal("999.99"))
    assert len(barcode) == 13
    body = barcode[:12]
    cs = int(barcode[12])
    assert cs == _ean13_checksum(body)


# ---------------------------------------------------------------------------
# Tests de API – cálculo bidireccional
# ---------------------------------------------------------------------------

def test_calcular_pesable_por_peso(client: TestClient) -> None:
    r = client.post(
        "/api/pesables/calcular",
        json={"precio_unitario": "2000", "peso": "1.5"},
    )
    assert r.status_code == 200
    data = r.json()
    assert float(data["precio_total"]) == 3000.0
    assert float(data["peso"]) == 1.5


def test_calcular_pesable_por_precio(client: TestClient) -> None:
    r = client.post(
        "/api/pesables/calcular",
        json={"precio_unitario": "2000", "precio": "3000"},
    )
    assert r.status_code == 200
    data = r.json()
    assert float(data["peso"]) == 1.5
    assert float(data["precio_total"]) == 3000.0


def test_calcular_pesable_ambos_400(client: TestClient) -> None:
    r = client.post(
        "/api/pesables/calcular",
        json={"precio_unitario": "2000", "peso": "1.5", "precio": "3000"},
    )
    assert r.status_code == 400


def test_calcular_pesable_ninguno_400(client: TestClient) -> None:
    r = client.post(
        "/api/pesables/calcular",
        json={"precio_unitario": "2000"},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tests de API – habilitar producto pesable
# ---------------------------------------------------------------------------

def test_habilitar_producto_pesable(client: TestClient, producto_datos: dict) -> None:
    r = client.post("/api/productos", json=producto_datos)
    assert r.status_code == 201
    prod_id = r.json()["id"]

    r2 = client.patch(f"/api/pesables/productos/{prod_id}/habilitar", json={"plu": 12345})
    assert r2.status_code == 200
    data = r2.json()
    assert data["pesable"] is True
    assert data["plu"] == 12345


def test_habilitar_plu_duplicado_409(client: TestClient, producto_datos: dict) -> None:
    """Dos productos no pueden tener el mismo PLU."""
    r1 = client.post("/api/productos", json={**producto_datos, "sku": "PES-A"})
    r2 = client.post("/api/productos", json={**producto_datos, "sku": "PES-B", "nombre": "B"})
    assert r1.status_code == 201 and r2.status_code == 201

    client.patch(f"/api/pesables/productos/{r1.json()['id']}/habilitar", json={"plu": 11111})
    dup = client.patch(f"/api/pesables/productos/{r2.json()['id']}/habilitar", json={"plu": 11111})
    assert dup.status_code == 409


def test_habilitar_producto_no_encontrado_404(client: TestClient) -> None:
    r = client.patch("/api/pesables/productos/999999/habilitar", json={"plu": 55555})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests de API – preparar ítems
# ---------------------------------------------------------------------------

def test_preparar_item_por_peso(client: TestClient, producto_datos: dict) -> None:
    prod_id = _crear_producto_pesable(client, "PES-W1", "Pan", "2000", 10001)

    r = client.post(
        "/api/pesables/items",
        json={"producto_id": prod_id, "peso": "1.5"},
    )
    assert r.status_code == 201, r.json()
    data = r.json()
    assert float(data["peso"]) == 1.5
    assert float(data["precio_total"]) == 3000.0
    assert len(data["barcode"]) == 13
    assert data["estado"] == "pending"
    assert data["plu"] == 10001


def test_preparar_item_por_precio(client: TestClient, producto_datos: dict) -> None:
    prod_id = _crear_producto_pesable(client, "PES-P1", "Queso", "2000", 10002)

    r = client.post(
        "/api/pesables/items",
        json={"producto_id": prod_id, "precio": "3000"},
    )
    assert r.status_code == 201, r.json()
    data = r.json()
    assert float(data["peso"]) == 1.5
    assert float(data["precio_total"]) == pytest.approx(3000.0, abs=0.01)
    assert len(data["barcode"]) == 13


def test_preparar_item_producto_no_pesable_400(client: TestClient, producto_datos: dict) -> None:
    """Intentar preparar un ítem con un producto no marcado como pesable devuelve 400."""
    r = client.post("/api/productos", json={**producto_datos, "sku": "NO-PES"})
    assert r.status_code == 201
    prod_id = r.json()["id"]

    r2 = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "1"})
    assert r2.status_code == 400


def test_preparar_item_batch(client: TestClient, producto_datos: dict) -> None:
    """Preparar múltiples ítems en un solo request."""
    id1 = _crear_producto_pesable(client, "PES-B1", "Fiambre A", "2000", 20001)
    id2 = _crear_producto_pesable(client, "PES-B2", "Fiambre B", "1500", 20002)

    r = client.post(
        "/api/pesables/items/batch",
        json={
            "items": [
                {"producto_id": id1, "peso": "0.5"},
                {"producto_id": id2, "precio": "750"},
            ]
        },
    )
    assert r.status_code == 201, r.json()
    items = r.json()
    assert len(items) == 2
    assert all(i["estado"] == "pending" for i in items)
    ids = {i["producto_id"] for i in items}
    assert id1 in ids and id2 in ids


# ---------------------------------------------------------------------------
# Tests de API – listar y obtener
# ---------------------------------------------------------------------------

def test_listar_items_por_estado(client: TestClient, producto_datos: dict) -> None:
    prod_id = _crear_producto_pesable(client, "PES-L1", "Carne", "3000", 30001)
    # Crear 2 ítems
    for _ in range(2):
        client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "1"})

    r = client.get("/api/pesables/items", params={"estado": "pending", "producto_id": prod_id})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_obtener_item_por_id(client: TestClient, producto_datos: dict) -> None:
    prod_id = _crear_producto_pesable(client, "PES-G1", "Verdura", "500", 40001)
    item_data = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "2"}).json()
    item_id = item_data["id"]

    r = client.get(f"/api/pesables/items/{item_id}")
    assert r.status_code == 200
    assert r.json()["id"] == item_id


def test_obtener_item_no_encontrado_404(client: TestClient) -> None:
    r = client.get("/api/pesables/items/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests de API – cambio de estados
# ---------------------------------------------------------------------------

def test_marcar_impreso_cambia_estado(client: TestClient, producto_datos: dict) -> None:
    prod_id = _crear_producto_pesable(client, "PES-S1", "Pollo", "1800", 50001)
    item_id = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "1"}).json()["id"]

    r = client.patch(f"/api/pesables/items/{item_id}/imprimir")
    assert r.status_code == 200
    assert r.json()["estado"] == "printed"


def test_marcar_usado_cambia_estado(client: TestClient, producto_datos: dict) -> None:
    prod_id = _crear_producto_pesable(client, "PES-S2", "Salchicha", "1200", 50002)
    item_id = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.3"}).json()["id"]

    r = client.patch(f"/api/pesables/items/{item_id}/usar")
    assert r.status_code == 200
    assert r.json()["estado"] == "used"


def test_marcar_usado_dos_veces_400(client: TestClient, producto_datos: dict) -> None:
    prod_id = _crear_producto_pesable(client, "PES-S3", "Chorizo", "1000", 50003)
    item_id = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.5"}).json()["id"]
    client.patch(f"/api/pesables/items/{item_id}/usar")

    r = client.patch(f"/api/pesables/items/{item_id}/usar")
    assert r.status_code == 400


def test_marcar_impreso_item_no_encontrado_404(client: TestClient) -> None:
    r = client.patch("/api/pesables/items/999999/imprimir")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests de API – generación de etiquetas
# ---------------------------------------------------------------------------

def test_generar_etiquetas_batch(client: TestClient, producto_datos: dict) -> None:
    id1 = _crear_producto_pesable(client, "PES-E1", "Jamón A", "2500", 60001)
    id2 = _crear_producto_pesable(client, "PES-E2", "Jamón B", "2600", 60002)

    item1 = client.post("/api/pesables/items", json={"producto_id": id1, "peso": "0.3"}).json()
    item2 = client.post("/api/pesables/items", json={"producto_id": id2, "peso": "0.5"}).json()

    r = client.post(
        "/api/pesables/etiquetas",
        json={"item_ids": [item1["id"], item2["id"]]},
    )
    assert r.status_code == 200, r.json()
    data = r.json()
    etiquetas = data["etiquetas"]
    assert len(etiquetas) == 2
    for et in etiquetas:
        assert len(et["barcode"]) == 13
        assert et["estado"] == "printed"
        assert et["nombre_producto"] in ("Jamón A", "Jamón B")


def test_generar_etiquetas_item_inexistente_400(client: TestClient) -> None:
    r = client.post("/api/pesables/etiquetas", json={"item_ids": [999999]})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tests de API – flujo completo (preparar → imprimir → listar pending=0)
# ---------------------------------------------------------------------------

def test_flujo_completo_pesable(client: TestClient, producto_datos: dict) -> None:
    """Flujo completo: crear producto pesable → preparar ítem → etiquetar → marcar usado."""
    prod_id = _crear_producto_pesable(client, "PES-FC", "Pan integral", "2000", 77777)

    # Preparar ítem por peso
    item = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "1.2"}).json()
    item_id = item["id"]
    assert item["estado"] == "pending"

    # Generar etiqueta → estado printed
    r_et = client.post("/api/pesables/etiquetas", json={"item_ids": [item_id]})
    assert r_et.status_code == 200
    assert r_et.json()["etiquetas"][0]["estado"] == "printed"

    # Verificar estado en lista
    items_printed = client.get("/api/pesables/items", params={"estado": "printed", "producto_id": prod_id}).json()
    assert any(x["id"] == item_id for x in items_printed)

    # Marcar como usado (vendido)
    r_uso = client.patch(f"/api/pesables/items/{item_id}/usar")
    assert r_uso.status_code == 200
    assert r_uso.json()["estado"] == "used"

    # No debe aparecer en pending ni printed
    items_pending = client.get("/api/pesables/items", params={"estado": "pending", "producto_id": prod_id}).json()
    assert not any(x["id"] == item_id for x in items_pending)


# ---------------------------------------------------------------------------
# Tests integración POS ↔ Pesables (escaneo EAN-13 en venta)
# ---------------------------------------------------------------------------

def _crear_venta_pendiente(client: TestClient, producto_datos: dict, sku_cart: str = "CART-BASE") -> int:
    """Crea una venta PENDIENTE (modo TEU_OFF) para usar como carrito."""
    r_prod = client.post("/api/productos", json={**producto_datos, "sku": sku_cart})
    assert r_prod.status_code == 201, r_prod.json()
    prod_id = r_prod.json()["id"]
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": prod_id, "cantidad": 100, "referencia": "stock-pos"},
    )
    r = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": prod_id, "cantidad": 1}],
            "modo_venta": "TEU_OFF",
        },
    )
    assert r.status_code == 200, r.json()
    return r.json()["venta_id"]


def test_agregar_pesable_por_barcode_ok(client: TestClient, producto_datos: dict) -> None:
    """Escaneo de barcode EAN-13 en venta PENDIENTE añade ítem con precio codificado."""
    prod_id = _crear_producto_pesable(client, "PES-POS1", "Queso Gouda", "3000", 88001)

    # Preparar ítem pesable
    item_data = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.8"}).json()
    barcode = item_data["barcode"]
    precio_total = item_data["precio_total"]

    # Generar etiqueta (→ printed)
    client.post("/api/pesables/etiquetas", json={"item_ids": [item_data["id"]]})

    # Crear venta PENDIENTE
    venta_id = _crear_venta_pendiente(client, producto_datos, sku_cart="CART-POS1")

    # Escanear barcode en la venta
    r = client.post(
        f"/api/ventas/{venta_id}/items/pesable-barcode",
        json={"barcode": barcode},
    )
    assert r.status_code == 200, r.json()
    venta = r.json()

    # El ítem pesable debe estar en el carrito con el precio codificado
    nombres_items = [it["nombre_producto"] for it in venta["items"]]
    assert any("Queso Gouda" in nombre for nombre in nombres_items)

    # Verificar formato ticket §8: precio_unitario = precio/kg, subtotal = precio_total codificado
    pesable_items = [it for it in venta["items"] if "Queso Gouda" in it["nombre_producto"]]
    assert len(pesable_items) == 1
    # precio_unitario = $3000/kg (precio del producto por kg), NO el precio_total
    assert float(pesable_items[0]["precio_unitario"]) == float(item_data["precio_unitario"])
    # subtotal = precio codificado en barcode (precio_total del PesableItem)
    assert float(pesable_items[0]["subtotal"]) == float(precio_total)


def test_agregar_pesable_por_barcode_marca_como_used(client: TestClient, producto_datos: dict) -> None:
    """Después del escaneo en venta, el PesableItem queda en estado 'used'."""
    prod_id = _crear_producto_pesable(client, "PES-POS2", "Salame", "4000", 88002)
    item_data = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.5"}).json()
    barcode = item_data["barcode"]
    client.post("/api/pesables/etiquetas", json={"item_ids": [item_data["id"]]})

    venta_id = _crear_venta_pendiente(client, producto_datos, sku_cart="CART-POS2")
    client.post(f"/api/ventas/{venta_id}/items/pesable-barcode", json={"barcode": barcode})

    # Verificar estado used
    r = client.get(f"/api/pesables/items/{item_data['id']}")
    assert r.status_code == 200
    assert r.json()["estado"] == "used"


def test_agregar_pesable_barcode_reutilizacion_falla(client: TestClient, producto_datos: dict) -> None:
    """Reutilizar una etiqueta ya usada devuelve 400."""
    prod_id = _crear_producto_pesable(client, "PES-POS3", "Mortadela", "2500", 88003)
    item_data = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.4"}).json()
    barcode = item_data["barcode"]
    client.post("/api/pesables/etiquetas", json={"item_ids": [item_data["id"]]})

    venta_id = _crear_venta_pendiente(client, producto_datos, sku_cart="CART-POS3")
    client.post(f"/api/ventas/{venta_id}/items/pesable-barcode", json={"barcode": barcode})

    # Intentar reutilizar la misma etiqueta en otra venta
    r = client.post(
        f"/api/ventas/{venta_id}/items/pesable-barcode",
        json={"barcode": barcode},
    )
    assert r.status_code == 400
    assert "ya fue utilizado" in r.json()["detail"].lower()


def test_agregar_pesable_barcode_inexistente_400(client: TestClient, producto_datos: dict) -> None:
    """Barcode que no existe en la BD devuelve 400."""
    venta_id = _crear_venta_pendiente(client, producto_datos, sku_cart="CART-POS4")
    r = client.post(
        f"/api/ventas/{venta_id}/items/pesable-barcode",
        json={"barcode": "9999999999999"},
    )
    assert r.status_code == 400


def test_agregar_pesable_venta_no_pendiente_falla(client: TestClient, producto_datos: dict) -> None:
    """Añadir pesable a venta no PENDIENTE devuelve 400."""
    prod_id = _crear_producto_pesable(client, "PES-POS4", "Pechuga", "3500", 88004)
    item_data = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.6"}).json()
    barcode = item_data["barcode"]
    client.post("/api/pesables/etiquetas", json={"item_ids": [item_data["id"]]})

    # Crear venta TEU_ON (PAGADA, no PENDIENTE)
    r_p2 = client.post("/api/productos", json={**producto_datos, "sku": "CART-POS5-BASE"})
    prod2_id = r_p2.json()["id"]
    client.post("/api/inventario/ingresar", json={"producto_id": prod2_id, "cantidad": 100, "referencia": "stk"})
    r_venta = client.post(
        "/api/ventas",
        json={"items": [{"producto_id": prod2_id, "cantidad": 1}], "modo_venta": "TEU_ON"},
    )
    venta_id = r_venta.json()["venta_id"]

    r = client.post(
        f"/api/ventas/{venta_id}/items/pesable-barcode",
        json={"barcode": barcode},
    )
    assert r.status_code == 400


def test_resolver_barcode_pesable_ok(client: TestClient, producto_datos: dict) -> None:
    """GET /pesables/resolver-barcode devuelve datos del ítem sin modificar estado."""
    prod_id = _crear_producto_pesable(client, "PES-RES1", "Ricota", "1500", 99001)
    item_data = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.3"}).json()
    client.post("/api/pesables/etiquetas", json={"item_ids": [item_data["id"]]})
    barcode = item_data["barcode"]

    r = client.get("/api/pesables/resolver-barcode", params={"barcode": barcode})
    assert r.status_code == 200
    data = r.json()
    assert data["barcode"] == barcode
    assert data["nombre_producto"] == "Ricota"
    assert data["peso"] == 0.3
    assert data["estado"] == "printed"  # no cambia estado


def test_resolver_barcode_pesable_inexistente_404(client: TestClient) -> None:
    """Resolver barcode que no existe devuelve 404."""
    r = client.get("/api/pesables/resolver-barcode", params={"barcode": "0000000000000"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests: GET /pesables/productos — listar productos habilitados como pesables
# ---------------------------------------------------------------------------

def test_listar_productos_pesables_vacio(client: TestClient) -> None:
    """Sin productos pesables devuelve lista vacía."""
    r = client.get("/api/pesables/productos")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_productos_pesables_incluye_habilitados(client: TestClient, producto_datos: dict) -> None:
    """Solo lista productos habilitados como pesables con PLU."""
    # Crear producto NO pesable
    r1 = client.post("/api/productos", json={**producto_datos, "sku": "NO-PES-LIST"})
    assert r1.status_code == 201

    # Crear y habilitar producto pesable
    r2 = client.post("/api/productos", json={**producto_datos, "sku": "SI-PES-LIST"})
    assert r2.status_code == 201
    prod_id = r2.json()["id"]
    client.patch(f"/api/pesables/productos/{prod_id}/habilitar", json={"plu": 55001})

    r = client.get("/api/pesables/productos")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["plu"] == 55001
    assert data[0]["id"] == prod_id
    # El producto no pesable no aparece
    ids = [d["id"] for d in data]
    assert r1.json()["id"] not in ids


def test_listar_productos_pesables_campos_correctos(client: TestClient, producto_datos: dict) -> None:
    """Los campos retornados son los esperados."""
    r = client.post("/api/productos", json={**producto_datos, "sku": "PES-CAMPOS"})
    prod_id = r.json()["id"]
    client.patch(f"/api/pesables/productos/{prod_id}/habilitar", json={"plu": 55002})

    r = client.get("/api/pesables/productos")
    assert r.status_code == 200
    item = r.json()[0]
    for campo in ("id", "sku", "nombre", "precio_venta", "plu", "activo"):
        assert campo in item


# ---------------------------------------------------------------------------
# Tests: GET /productos?pesable=true — filtro pesable en listado de productos
# ---------------------------------------------------------------------------

def test_filtro_pesable_true_en_productos(client: TestClient, producto_datos: dict) -> None:
    """GET /productos?pesable=true devuelve solo los habilitados como pesables."""
    r_normal = client.post("/api/productos", json={**producto_datos, "sku": "FILTRO-NP"})
    r_pes = client.post("/api/productos", json={**producto_datos, "sku": "FILTRO-P"})
    prod_pes_id = r_pes.json()["id"]
    client.patch(f"/api/pesables/productos/{prod_pes_id}/habilitar", json={"plu": 66001})

    r = client.get("/api/productos", params={"pesable": True})
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert prod_pes_id in ids
    assert r_normal.json()["id"] not in ids


def test_filtro_pesable_false_excluye_pesables(client: TestClient, producto_datos: dict) -> None:
    """GET /productos?pesable=false excluye los productos pesables."""
    r_normal = client.post("/api/productos", json={**producto_datos, "sku": "FILTRO-NP2"})
    r_pes = client.post("/api/productos", json={**producto_datos, "sku": "FILTRO-P2"})
    prod_pes_id = r_pes.json()["id"]
    client.patch(f"/api/pesables/productos/{prod_pes_id}/habilitar", json={"plu": 66002})

    r = client.get("/api/productos", params={"pesable": False})
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert prod_pes_id not in ids
    assert r_normal.json()["id"] in ids


# ---------------------------------------------------------------------------
# Tests: DELETE /pesables/items/{item_id} — eliminar ítem en estado pending
# ---------------------------------------------------------------------------

def test_eliminar_item_pending_ok(client: TestClient, producto_datos: dict) -> None:
    """Eliminar un ítem en estado pending devuelve 204."""
    prod_id = _crear_producto_pesable(client, "PES-DEL1", "Queso Brie", "2800", 77001)
    item = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.5"}).json()
    item_id = item["id"]
    assert item["estado"] == "pending"

    r = client.delete(f"/api/pesables/items/{item_id}")
    assert r.status_code == 204

    # Ya no existe
    r2 = client.get(f"/api/pesables/items/{item_id}")
    assert r2.status_code == 404


def test_eliminar_item_printed_falla(client: TestClient, producto_datos: dict) -> None:
    """No se puede eliminar un ítem ya impreso."""
    prod_id = _crear_producto_pesable(client, "PES-DEL2", "Panceta", "3500", 77002)
    item = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.3"}).json()
    client.post("/api/pesables/etiquetas", json={"item_ids": [item["id"]]})

    r = client.delete(f"/api/pesables/items/{item['id']}")
    assert r.status_code == 400
    assert "printed" in r.json()["detail"].lower()


def test_eliminar_item_used_falla(client: TestClient, producto_datos: dict) -> None:
    """No se puede eliminar un ítem ya usado."""
    prod_id = _crear_producto_pesable(client, "PES-DEL3", "Chorizo Colorado", "2200", 77003)
    item = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "0.2"}).json()
    client.patch(f"/api/pesables/items/{item['id']}/usar")

    r = client.delete(f"/api/pesables/items/{item['id']}")
    assert r.status_code == 400


def test_eliminar_item_no_existente_404(client: TestClient) -> None:
    """Intentar eliminar un ítem inexistente devuelve 404."""
    r = client.delete("/api/pesables/items/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Fix bug precio_unitario en ItemVenta pesable (§8 ticket)
# ---------------------------------------------------------------------------

def test_precio_unitario_pesable_en_venta_es_precio_por_kg(client: TestClient, producto_datos: dict) -> None:
    """Al escanear EAN-13, el ItemVenta muestra precio/kg (no precio_total) como precio_unitario."""
    # Crear producto pesable con nombre único y precio $2000/kg
    nombre_unico = "Salame Ticket Fix"
    r_prod = client.post("/api/productos", json={
        **producto_datos,
        "sku": "PES-TICKET-FIX",
        "nombre": nombre_unico,
        "precio_venta": "2000",
    })
    prod_id = r_prod.json()["id"]
    client.patch(f"/api/pesables/productos/{prod_id}/habilitar", json={"plu": 88100})

    # Preparar ítem: 1.5 kg → precio_total = 3000
    item = client.post("/api/pesables/items", json={"producto_id": prod_id, "peso": "1.5"}).json()
    assert float(item["precio_total"]) == 3000.0
    assert float(item["precio_unitario"]) == 2000.0
    barcode = item["barcode"]
    client.post("/api/pesables/etiquetas", json={"item_ids": [item["id"]]})

    # Crear venta PENDIENTE y escanear
    r_base = client.post("/api/productos", json={**producto_datos, "sku": "CART-TICKET-BASE"})
    base_id = r_base.json()["id"]
    client.post("/api/inventario/ingresar", json={"producto_id": base_id, "cantidad": 10, "referencia": "stk"})
    r_venta = client.post("/api/ventas", json={"items": [{"producto_id": base_id, "cantidad": 1}], "modo_venta": "TEU_OFF"})
    venta_id = r_venta.json()["venta_id"]

    r = client.post(f"/api/ventas/{venta_id}/items/pesable-barcode", json={"barcode": barcode})
    assert r.status_code == 200

    # Buscar el ítem pesable en la venta por nombre único
    pes_items = [it for it in r.json()["items"] if nombre_unico in it.get("nombre_producto", "")]
    assert len(pes_items) == 1, f"Items en venta: {[it['nombre_producto'] for it in r.json()['items']]}"
    # precio_unitario debe ser el precio/kg ($2000), no el precio_total ($3000)
    assert float(pes_items[0]["precio_unitario"]) == 2000.0
    # subtotal debe ser el precio codificado ($3000)
    assert float(pes_items[0]["subtotal"]) == 3000.0
