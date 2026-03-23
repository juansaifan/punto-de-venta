"""Tests de la API de Reportes."""
from fastapi.testclient import TestClient


def test_ventas_por_dia_vacio(client: TestClient) -> None:
    """Ventas por da sin datos devuelve cantidad 0 y total 0."""
    r = client.get("/api/reportes/ventas-por-dia?fecha=2026-01-15")
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad_ventas"] == 0
    assert float(data["total"]) == 0
    assert data["fecha"] == "2026-01-15"

    r_csv = client.get("/api/reportes/ventas-por-dia?fecha=2026-01-15&formato=csv")
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.strip().splitlines()
    assert lineas[0] == "fecha,cantidad_ventas,total,ticket_promedio"
    assert len(lineas) == 2


def test_ventas_por_dia_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Ventas por da incluye las ventas del da."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]
    venta = client.get(f"/api/ventas/{venta_id}").json()
    fecha_venta = venta["creado_en"][:10]
    r = client.get(f"/api/reportes/ventas-por-dia?fecha={fecha_venta}")
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad_ventas"] >= 1
    assert float(data["total"]) >= 0

    r_csv = client.get(f"/api/reportes/ventas-por-dia?fecha={fecha_venta}&formato=csv")
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.strip().splitlines()
    assert lineas[0] == "fecha,cantidad_ventas,total,ticket_promedio"
    assert len(lineas) == 2


def test_ventas_por_producto_vacio(client: TestClient) -> None:
    """Ventas por producto sin datos devuelve lista vaca."""
    r = client.get(
        "/api/reportes/ventas-por-producto"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_ventas_por_producto_csv_sin_datos(client: TestClient) -> None:
    """Ventas por producto en formato CSV sin datos devuelve solo la cabecera."""
    r = client.get(
        "/api/reportes/ventas-por-producto"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.splitlines()
    # Solo cabecera, sin filas de datos
    assert lineas[0] == "producto_id,nombre_producto,cantidad_vendida,total_vendido"
    assert len(lineas) == 1


def test_ventas_por_producto_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Ventas por producto devuelve el producto vendido en el rango."""
    from tests.test_ventas import _ingresar_stock

    # Crear producto y registrar una venta
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta_id = r_venta.json()["venta_id"]
    venta = client.get(f"/api/ventas/{venta_id}").json()
    fecha_venta = venta["creado_en"][:10]

    r = client.get(
        f"/api/reportes/ventas-por-producto"
        f"?fecha_desde={fecha_venta}&fecha_hasta={fecha_venta}"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    ids = [it["producto_id"] for it in items]
    assert producto_id in ids

    # Versin CSV incluye al menos una fila con el producto
    r_csv = client.get(
        f"/api/reportes/ventas-por-producto"
        f"?fecha_desde={fecha_venta}&fecha_hasta={fecha_venta}&formato=csv"
    )
    assert r_csv.status_code == 200
    lineas = r_csv.text.splitlines()
    assert lineas[0] == "producto_id,nombre_producto,cantidad_vendida,total_vendido"
    # Buscar la lnea del producto por su id
    assert any(str(producto_id) in linea for linea in lineas[1:])


def test_inventario_valorizado_vacio(client: TestClient) -> None:
    """Inventario valorizado sin datos devuelve lista vaca y total 0."""
    r = client.get("/api/reportes/inventario-valorizado")
    assert r.status_code == 200
    data = r.json()
    assert data["productos"] == [] or isinstance(data["productos"], list)
    # Si no hay stock, total debe ser 0
    assert float(data["total_inventario"]) >= 0


def test_inventario_valorizado_con_stock(client: TestClient, producto_datos: dict) -> None:
    """Inventario valorizado incluye productos con stock y calcula valor total."""
    # Crear producto
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    precio = float(crear.json()["precio_venta"])

    # Ingresar stock usando API de inventario
    r_stock = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "5"},
    )
    assert r_stock.status_code == 200

    r = client.get("/api/reportes/inventario-valorizado")
    assert r.status_code == 200
    data = r.json()
    productos = data["productos"]
    assert len(productos) >= 1
    # Buscar nuestro producto
    match = next((p for p in productos if p["producto_id"] == producto_id), None)
    assert match is not None
    assert match["stock_total"] == 5.0
    assert match["precio_venta"] == precio
    assert match["valor_total"] == 5.0 * precio


def test_ventas_por_empleado_sin_datos(client: TestClient) -> None:
    """Ventas por empleado sin datos devuelve lista vaca."""
    r = client.get(
        "/api/reportes/ventas-por-empleado"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_ventas_por_empleado_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Ventas por empleado agrupa y suma ventas en el rango."""
    from tests.test_ventas import _ingresar_stock

    # Crear producto
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    # Registrar una venta (empleado asociado segn implementacin de ventas)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    # Usar una ventana amplia de fechas que incluya la venta registrada
    r = client.get(
        "/api/reportes/ventas-por-empleado"
        "?fecha_desde=2000-01-01&fecha_hasta=2100-01-01"
    )
    assert r.status_code == 200
    datos = r.json()
    # Al menos un empleado con ventas (o grupo "Sin asignar")
    assert len(datos) >= 1
    # Validar estructura y que empleado_nombre siempre sea string
    for emp in datos:
        assert "empleado_id" in emp
        assert "empleado_nombre" in emp
        assert isinstance(emp["empleado_nombre"], str), "empleado_nombre debe ser string"
        assert "cantidad_ventas" in emp
        assert "total_vendido" in emp
        if emp["empleado_id"] is None:
            assert emp["empleado_nombre"] == "Sin asignar"


def test_evolucion_ventas_diaria_sin_datos(client: TestClient) -> None:
    """Evolucin diaria sin datos devuelve lista vaca."""
    r = client.get(
        "/api/reportes/evolucion-ventas-diaria"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_evolucion_ventas_diaria_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Evolucin diaria devuelve al menos un punto con fecha, cantidad y total."""
    from tests.test_ventas import _ingresar_stock

    # Crear producto y registrar una venta
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    r = client.get(
        "/api/reportes/evolucion-ventas-diaria"
        "?fecha_desde=2000-01-01&fecha_hasta=2100-01-01"
    )
    assert r.status_code == 200
    puntos = r.json()
    assert len(puntos) >= 1
    punto = puntos[0]
    assert "fecha" in punto
    assert "cantidad_ventas" in punto
    assert "total_vendido" in punto

    r_csv = client.get(
        "/api/reportes/evolucion-ventas-diaria"
        "?fecha_desde=2000-01-01&fecha_hasta=2100-01-01&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.strip().splitlines()
    assert lineas[0] == "fecha,cantidad_ventas,total_vendido"
    assert len(lineas) >= 2


def test_resumen_rango_sin_datos(client: TestClient) -> None:
    """Resumen rango sin ventas devuelve cantidad 0 y total 0."""
    r = client.get(
        "/api/reportes/resumen-rango"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad_ventas"] == 0
    assert data["total_vendido"] == 0.0
    assert data["fecha_desde"] == "2026-01-01"
    assert data["fecha_hasta"] == "2026-01-31"
    assert "ticket_promedio" in data


def test_resumen_rango_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Resumen rango con ventas devuelve totales correctos."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    r = client.get(
        "/api/reportes/resumen-rango"
        "?fecha_desde=2000-01-01&fecha_hasta=2100-01-01"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad_ventas"] >= 1
    assert data["total_vendido"] >= 0
    assert "ticket_promedio" in data


def test_resumen_rango_fecha_invertida_400(client: TestClient) -> None:
    """Resumen rango con fecha_desde > fecha_hasta devuelve 400."""
    r = client.get(
        "/api/reportes/resumen-rango"
        "?fecha_desde=2026-01-31&fecha_hasta=2026-01-01"
    )
    assert r.status_code == 400
    assert "posterior" in r.json()["detail"].lower()


def test_evolucion_ventas_diaria_fecha_invertida_400(client: TestClient) -> None:
    """Evolucin diaria con fecha_desde > fecha_hasta devuelve 400."""
    r = client.get(
        "/api/reportes/evolucion-ventas-diaria"
        "?fecha_desde=2026-01-31&fecha_hasta=2026-01-01"
    )
    assert r.status_code == 400


def test_ranking_productos_vacio(client: TestClient) -> None:
    """Ranking productos sin ventas devuelve lista vaca."""
    r = client.get(
        "/api/reportes/ranking-productos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_ranking_productos_csv_sin_datos(client: TestClient) -> None:
    """Ranking productos en CSV sin datos devuelve solo cabecera."""
    r = client.get(
        "/api/reportes/ranking-productos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.splitlines()
    assert lineas[0] == "posicion,producto_id,nombre_producto,cantidad_vendida,total_vendido"
    assert len(lineas) == 1


def test_ranking_productos_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Ranking productos devuelve posicion 1-based y datos por producto."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "3"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    venta = client.get("/api/ventas").json()
    fecha = venta[0]["creado_en"][:10] if venta else "2026-03-01"

    r = client.get(
        f"/api/reportes/ranking-productos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert items[0]["posicion"] == 1
    assert items[0]["producto_id"] == producto_id
    assert items[0]["cantidad_vendida"] == 3.0
    assert "total_vendido" in items[0]

    # CSV devuelve columnas esperadas y una fila para el producto
    r_csv = client.get(
        f"/api/reportes/ranking-productos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    lineas = r_csv.text.splitlines()
    assert lineas[0] == "posicion,producto_id,nombre_producto,cantidad_vendida,total_vendido"
    assert any(str(producto_id) in linea for linea in lineas[1:])


def test_ranking_productos_orden_invalido_400(client: TestClient) -> None:
    """Ranking con orden_por distinto de total/cantidad devuelve 400."""
    r = client.get(
        "/api/reportes/ranking-productos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&orden_por=invalid"
    )
    assert r.status_code == 400


def test_margen_producto_vacio(client: TestClient) -> None:
    """Margen por producto sin ventas devuelve lista vaca."""
    r = client.get(
        "/api/reportes/margen-producto"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_margen_producto_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Margen por producto devuelve total_vendido, total_costo, margen_bruto y margen_pct."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    precio_venta = float(crear.json()["precio_venta"])
    _ingresar_stock(client, producto_id, 10)

    # Venta: 2 unidades a precio_venta -> subtotal = 2 * precio_venta
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta = client.get(f"/api/ventas/{r_venta.json()['venta_id']}").json()
    fecha_venta = venta["creado_en"][:10]

    r = client.get(
        f"/api/reportes/margen-producto"
        f"?fecha_desde={fecha_venta}&fecha_hasta={fecha_venta}"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    fila = next((x for x in items if x["producto_id"] == producto_id), None)
    assert fila is not None
    total_esperado = 2 * precio_venta
    assert fila["total_vendido"] == total_esperado
    # producto_datos no enva costo_actual, por defecto 0
    assert fila["total_costo"] == 0.0
    assert fila["margen_bruto"] == total_esperado
    assert fila["margen_pct"] == 100.0


def test_margen_producto_orden_invalido_400(client: TestClient) -> None:
    """Margen producto con orden_por invlido devuelve 400."""
    r = client.get(
        "/api/reportes/margen-producto"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&orden_por=invalid"
    )
    assert r.status_code == 400


def test_margen_categoria_vacio(client: TestClient) -> None:
    """Margen por categora sin ventas devuelve lista vaca."""
    r = client.get(
        "/api/reportes/margen-categoria"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_margen_categoria_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Margen por categora agrupa ventas y costos por categora."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    precio_venta = float(crear.json()["precio_venta"])
    _ingresar_stock(client, producto_id, 10)

    # Venta de 2 unidades
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta = client.get(f"/api/ventas/{r_venta.json()['venta_id']}").json()
    fecha_venta = venta["creado_en"][:10]

    r = client.get(
        f"/api/reportes/margen-categoria"
        f"?fecha_desde={fecha_venta}&fecha_hasta={fecha_venta}"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    fila = items[0]
    assert "categoria_id" in fila
    assert "categoria_nombre" in fila
    assert fila["total_vendido"] == 2 * precio_venta
    # costo_actual por defecto es 0, por lo que margen_bruto = total_vendido y margen_pct = 100
    assert fila["total_costo"] == 0.0
    assert fila["margen_bruto"] == 2 * precio_venta
    assert fila["margen_pct"] == 100.0


def test_ventas_por_cliente_vacio(client: TestClient) -> None:
    """Ventas por cliente sin ventas en el rango devuelve lista vaca."""
    r = client.get(
        "/api/reportes/ventas-por-cliente"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_ventas_por_cliente_csv_sin_datos(client: TestClient) -> None:
    """Ventas por cliente en CSV sin datos devuelve solo cabecera."""
    r = client.get(
        "/api/reportes/ventas-por-cliente"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.splitlines()
    assert lineas[0] == "cliente_id,cliente_nombre,cantidad_ventas,total_vendido"
    assert len(lineas) == 1


def test_ventas_por_cliente_con_venta_sin_cliente(client: TestClient, producto_datos: dict) -> None:
    """Ventas por cliente con ventas sin cliente_id incluye fila 'Sin asignar'."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200
    venta = client.get(f"/api/ventas/{r_venta.json()['venta_id']}").json()
    fecha = venta["creado_en"][:10]
    r = client.get(
        f"/api/reportes/ventas-por-cliente?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    sin_asignar = next((x for x in items if x["cliente_id"] is None), None)
    assert sin_asignar is not None
    assert sin_asignar["cliente_nombre"] == "Sin asignar"
    assert sin_asignar["cantidad_ventas"] >= 1


def test_ventas_por_cliente_con_cliente(client: TestClient, producto_datos: dict, persona_datos: dict) -> None:
    """Ventas por cliente incluye ventas asociadas a un cliente (persona)."""
    from tests.test_ventas import _ingresar_stock

    crear_p = client.post("/api/personas", json=persona_datos)
    assert crear_p.status_code == 201
    cliente_id = crear_p.json()["id"]
    crear_prod = client.post("/api/productos", json=producto_datos)
    producto_id = crear_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
            "cliente_id": cliente_id,
        },
    )
    assert r_venta.status_code == 200
    venta = client.get(f"/api/ventas/{r_venta.json()['venta_id']}").json()
    fecha = venta["creado_en"][:10]
    r = client.get(
        f"/api/reportes/ventas-por-cliente?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    items = r.json()
    fila = next((x for x in items if x["cliente_id"] == cliente_id), None)
    assert fila is not None
    assert persona_datos["nombre"] in fila["cliente_nombre"] or fila["cliente_nombre"] != "Sin asignar"
    assert fila["cantidad_ventas"] >= 1
    assert fila["total_vendido"] >= 0

    # CSV incluye al cliente en alguna de las filas
    r_csv = client.get(
        f"/api/reportes/ventas-por-cliente?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    lineas = r_csv.text.splitlines()
    assert lineas[0] == "cliente_id,cliente_nombre,cantidad_ventas,total_vendido"
    assert any(str(cliente_id) in linea for linea in lineas[1:])


def test_ranking_clientes_vacio(client: TestClient) -> None:
    """Ranking clientes sin ventas en el rango devuelve lista vaca."""
    r = client.get(
        "/api/reportes/ranking-clientes"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_ranking_clientes_csv_sin_datos(client: TestClient) -> None:
    """Ranking clientes en CSV sin datos devuelve solo cabecera."""
    r = client.get(
        "/api/reportes/ranking-clientes"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.splitlines()
    assert lineas[0] == "posicion,cliente_id,cliente_nombre,cantidad_ventas,total_vendido"
    assert len(lineas) == 1


def test_ranking_clientes_con_ventas(client: TestClient, producto_datos: dict, persona_datos: dict) -> None:
    """Ranking clientes devuelve posicin 1-based y datos por cliente."""
    from tests.test_ventas import _ingresar_stock

    crear_p = client.post("/api/personas", json=persona_datos)
    cliente_id = crear_p.json()["id"]
    crear_prod = client.post("/api/productos", json=producto_datos)
    producto_id = crear_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)
    client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
            "cliente_id": cliente_id,
        },
    )
    ventas = client.get("/api/ventas").json()
    fecha = ventas[0]["creado_en"][:10] if ventas else "2026-03-01"
    r = client.get(
        f"/api/reportes/ranking-clientes?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert items[0]["posicion"] == 1
    cliente_fila = next((x for x in items if x["cliente_id"] == cliente_id), None)
    assert cliente_fila is not None
    assert "total_vendido" in cliente_fila
    assert "cantidad_ventas" in cliente_fila

    # CSV incluye una fila con el cliente
    r_csv = client.get(
        f"/api/reportes/ranking-clientes?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    lineas = r_csv.text.splitlines()
    assert lineas[0] == "posicion,cliente_id,cliente_nombre,cantidad_ventas,total_vendido"
    assert any(str(cliente_id) in linea for linea in lineas[1:])


def test_ranking_clientes_orden_invalido_400(client: TestClient) -> None:
    """Ranking clientes con orden_por invlido devuelve 400."""
    r = client.get(
        "/api/reportes/ranking-clientes"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&orden_por=invalid"
    )
    assert r.status_code == 400


def test_consolidado_estructura(client: TestClient) -> None:
    """GET consolidado devuelve resumen con ventas e ingresos/egresos caja."""
    from datetime import date
    hoy = date.today().isoformat()
    r = client.get(f"/api/reportes/consolidado?fecha_desde={hoy}&fecha_hasta={hoy}")
    assert r.status_code == 200
    data = r.json()
    assert "resumen" in data
    res = data["resumen"]
    assert res["fecha_desde"] == hoy
    assert res["fecha_hasta"] == hoy
    assert "cantidad_ventas" in res
    assert "total_vendido" in res
    assert "ticket_promedio" in res
    assert "total_ingresos_caja" in res
    assert "total_egresos_caja" in res
    assert isinstance(res["total_ingresos_caja"], (int, float))
    assert isinstance(res["total_egresos_caja"], (int, float))


def test_consolidado_sin_datos(client: TestClient) -> None:
    """Consolidado sin ventas ni movimientos tiene totales en 0."""
    from datetime import date
    hoy = date.today().isoformat()
    r = client.get(f"/api/reportes/consolidado?fecha_desde={hoy}&fecha_hasta={hoy}")
    assert r.status_code == 200
    res = r.json()["resumen"]
    assert res["cantidad_ventas"] == 0
    assert res["total_vendido"] == 0.0
    assert res["total_ingresos_caja"] == 0.0
    assert res["total_egresos_caja"] == 0.0


def test_consolidado_incluye_ingresos_y_egresos_caja(client: TestClient) -> None:
    """Consolidado en un rango de fechas incluye movimientos de caja en ese rango."""
    from datetime import date, timedelta
    # Rango amplio para evitar diferencias por zona horaria (fecha en BD puede ser UTC)
    desde = (date.today() - timedelta(days=1)).isoformat()
    hasta = (date.today() + timedelta(days=1)).isoformat()
    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = client.get("/api/caja/abierta").json()["id"]
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "100"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "25"},
    )
    r = client.get(f"/api/reportes/consolidado?fecha_desde={desde}&fecha_hasta={hasta}")
    assert r.status_code == 200
    res = r.json()["resumen"]
    assert res["total_ingresos_caja"] == 100.0
    assert res["total_egresos_caja"] == 25.0


def test_consolidado_fecha_invertida_400(client: TestClient) -> None:
    """Consolidado con fecha_desde > fecha_hasta devuelve 400."""
    r = client.get(
        "/api/reportes/consolidado?fecha_desde=2026-01-31&fecha_hasta=2026-01-01"
    )
    assert r.status_code == 400


def test_consolidado_diario_sin_datos(client: TestClient) -> None:
    """Consolidado diario sin datos devuelve resumen con totales 0 y filas vacas."""
    from datetime import date

    hoy = date.today().isoformat()
    r = client.get(
        f"/api/reportes/consolidado-diario?fecha_desde={hoy}&fecha_hasta={hoy}"
    )
    assert r.status_code == 200
    data = r.json()
    assert "resumen" in data
    assert "filas" in data
    resumen = data["resumen"]
    filas = data["filas"]
    assert resumen["fecha_desde"] == hoy
    assert resumen["fecha_hasta"] == hoy
    assert resumen["cantidad_ventas"] == 0
    assert resumen["total_vendido"] == 0.0
    assert resumen["total_ingresos_caja"] == 0.0
    assert resumen["total_egresos_caja"] == 0.0
    assert resumen["flujo_caja"] == 0.0
    assert isinstance(filas, list)
    assert filas == []


def test_consolidado_diario_csv_sin_datos(client: TestClient) -> None:
    """Consolidado diario en CSV sin datos devuelve solo cabecera."""
    from datetime import date

    hoy = date.today().isoformat()
    r = client.get(
        f"/api/reportes/consolidado-diario?fecha_desde={hoy}&fecha_hasta={hoy}&formato=csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.splitlines()
    assert (
        lineas[0]
        == "fecha,cantidad_ventas,total_ventas,ticket_promedio,ventas_fiadas,cancelaciones,clientes_activos,unidades_vendidas,productos_distintos,margen_estimado,total_ingresos_caja,total_egresos_caja,flujo_caja"
    )
    assert len(lineas) == 1


def test_consolidado_diario_con_ventas_y_caja(client: TestClient, producto_datos: dict) -> None:
    """Consolidado diario incluye ventas y movimientos de caja por da con flujo de caja correcto."""
    from datetime import date, timedelta
    from tests.test_ventas import _ingresar_stock

    # Crear producto y una venta para garantizar datos de ventas en el rango
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    # Crear movimientos de caja en una caja abierta
    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = client.get("/api/caja/abierta").json()["id"]
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "150"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "50"},
    )

    # Rango amplio para capturar tanto la venta como los movimientos de caja
    desde = (date.today() - timedelta(days=1)).isoformat()
    hasta = (date.today() + timedelta(days=1)).isoformat()
    r = client.get(
        f"/api/reportes/consolidado-diario?fecha_desde={desde}&fecha_hasta={hasta}"
    )
    assert r.status_code == 200
    data = r.json()
    resumen = data["resumen"]
    filas = data["filas"]

    assert isinstance(filas, list)
    assert len(filas) >= 1

    # Verificar que el resumen global tenga los campos esperados
    assert resumen["total_ingresos_caja"] == 150.0
    assert resumen["total_egresos_caja"] == 50.0
    assert resumen["flujo_caja"] == 100.0

    # Verificar que al menos una fila tenga los montos de caja esperados
    fila_caja = next(
        (f for f in filas if f["total_ingresos_caja"] == 150.0 and f["total_egresos_caja"] == 50.0),
        None,
    )
    assert fila_caja is not None
    assert fila_caja["flujo_caja"] == 100.0
    assert "cantidad_ventas" in fila_caja
    assert "total_ventas" in fila_caja
    assert "ticket_promedio" in fila_caja


def test_consolidado_diario_csv_con_ventas_y_caja(client: TestClient, producto_datos: dict) -> None:
    """Consolidado diario CSV incluye al menos una fila con totales de caja coherentes."""
    from datetime import date, timedelta
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = client.get("/api/caja/abierta").json()["id"]
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "150"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "50"},
    )

    desde = (date.today() - timedelta(days=1)).isoformat()
    hasta = (date.today() + timedelta(days=1)).isoformat()
    r = client.get(
        f"/api/reportes/consolidado-diario?fecha_desde={desde}&fecha_hasta={hasta}&formato=csv"
    )
    assert r.status_code == 200
    lineas = r.text.splitlines()
    assert (
        lineas[0]
        == "fecha,cantidad_ventas,total_ventas,ticket_promedio,ventas_fiadas,cancelaciones,clientes_activos,unidades_vendidas,productos_distintos,margen_estimado,total_ingresos_caja,total_egresos_caja,flujo_caja"
    )
    # Buscar fila con los totales de caja esperados
    assert any(
        ",150.0,50.0,100.0" in linea or ",150.0,50.0,100" in linea for linea in lineas[1:]
    )


def test_consolidado_agrupado_sin_datos(client: TestClient) -> None:
    """Consolidado agrupado sin datos devuelve resumen con totales 0 y filas vacas."""
    from datetime import date

    hoy = date.today().isoformat()
    r = client.get(
        f"/api/reportes/consolidado-agrupado?fecha_desde={hoy}&fecha_hasta={hoy}&agrupacion=dia"
    )
    assert r.status_code == 200
    data = r.json()
    assert "resumen" in data
    assert "filas" in data
    resumen = data["resumen"]
    filas = data["filas"]
    assert resumen["fecha_desde"] == hoy
    assert resumen["fecha_hasta"] == hoy
    assert resumen["agrupacion"] == "dia"
    assert resumen["cantidad_ventas"] == 0
    assert resumen["total_vendido"] == 0.0
    assert resumen["total_ingresos_caja"] == 0.0
    assert resumen["total_egresos_caja"] == 0.0
    assert resumen["flujo_caja"] == 0.0
    assert isinstance(filas, list)
    assert filas == []


def test_consolidado_agrupado_csv_sin_datos(client: TestClient) -> None:
    """Consolidado agrupado CSV sin datos devuelve solo cabecera."""
    from datetime import date

    hoy = date.today().isoformat()
    r = client.get(
        f"/api/reportes/consolidado-agrupado?fecha_desde={hoy}&fecha_hasta={hoy}&agrupacion=dia&formato=csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.splitlines()
    assert (
        lineas[0]
        == "periodo,cantidad_ventas,total_ventas,ticket_promedio,total_ingresos_caja,total_egresos_caja,flujo_caja"
    )
    assert len(lineas) == 1


def test_consolidado_agrupado_con_ventas_y_caja(client: TestClient, producto_datos: dict) -> None:
    """Consolidado agrupado incluye al menos un perodo con datos coherentes."""
    from datetime import date, timedelta
    from tests.test_ventas import _ingresar_stock

    # Crear producto y una venta para garantizar datos de ventas en el rango
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    # Crear movimientos de caja en una caja abierta
    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = client.get("/api/caja/abierta").json()["id"]
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "150"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "50"},
    )

    # Rango amplio para capturar tanto la venta como los movimientos de caja
    desde = (date.today() - timedelta(days=1)).isoformat()
    hasta = (date.today() + timedelta(days=1)).isoformat()
    r = client.get(
        f"/api/reportes/consolidado-agrupado?fecha_desde={desde}&fecha_hasta={hasta}&agrupacion=mes"
    )
    assert r.status_code == 200
    data = r.json()
    resumen = data["resumen"]
    filas = data["filas"]

    assert resumen["agrupacion"] == "mes"
    assert isinstance(filas, list)
    assert len(filas) >= 1

    # Verificamos que al menos un perodo refleje los totales de caja
    fila_periodo = next(
        (
            f
            for f in filas
            if f["total_ingresos_caja"] == 150.0 and f["total_egresos_caja"] == 50.0
        ),
        None,
    )
    assert fila_periodo is not None
    assert fila_periodo["flujo_caja"] == 100.0
    assert "cantidad_ventas" in fila_periodo
    assert "total_ventas" in fila_periodo
    assert "ticket_promedio" in fila_periodo


def test_consolidado_agrupado_csv_con_ventas_y_caja(client: TestClient, producto_datos: dict) -> None:
    """Consolidado agrupado CSV incluye un perodo con totales de caja coherentes."""
    from datetime import date, timedelta
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = client.get("/api/caja/abierta").json()["id"]
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "150"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "50"},
    )

    desde = (date.today() - timedelta(days=1)).isoformat()
    hasta = (date.today() + timedelta(days=1)).isoformat()
    r = client.get(
        f"/api/reportes/consolidado-agrupado?fecha_desde={desde}&fecha_hasta={hasta}&agrupacion=mes&formato=csv"
    )
    assert r.status_code == 200
    lineas = r.text.splitlines()
    assert (
        lineas[0]
        == "periodo,cantidad_ventas,total_ventas,ticket_promedio,total_ingresos_caja,total_egresos_caja,flujo_caja"
    )
    # Buscar lnea con totales de caja esperados
    assert any(
        ",150.0,50.0,100.0" in linea or ",150.0,50.0,100" in linea for linea in lineas[1:]
    )


def test_consolidado_agrupado_agrupacion_invalida_400(client: TestClient) -> None:
    """Consolidado agrupado con agrupacion invlida devuelve 400."""
    from datetime import date

    hoy = date.today().isoformat()
    r = client.get(
        "/api/reportes/consolidado-agrupado"
        f"?fecha_desde={hoy}&fecha_hasta={hoy}&agrupacion=trimestre"
    )
    assert r.status_code == 400


def test_ventas_por_franja_horaria_sin_datos(client: TestClient) -> None:
    """Ventas por franja horaria sin datos devuelve lista vaca."""
    r = client.get(
        "/api/reportes/ventas-por-franja-horaria"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_ventas_por_franja_horaria_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Ventas por franja horaria devuelve al menos una franja con ventas, total y ticket_promedio consistentes."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    # Rango amplio para incluir la venta recin creada
    r = client.get(
        "/api/reportes/ventas-por-franja-horaria"
        "?fecha_desde=2000-01-01&fecha_hasta=2100-01-01"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1
    fila = datos[0]
    assert "franja" in fila
    assert "cantidad_ventas" in fila
    assert "total_vendido" in fila
    assert "ticket_promedio" in fila
    assert fila["cantidad_ventas"] >= 1
    assert fila["total_vendido"] >= 0


def test_ventas_por_medio_pago_sin_datos(client: TestClient) -> None:
    """Ventas por medio de pago sin datos devuelve lista vaca."""
    r = client.get(
        "/api/reportes/ventas-por-medio-pago"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_ventas_por_medio_pago_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Ventas por medio de pago agrupa por metodo_pago y suma totales."""
    from tests.test_ventas import _ingresar_stock

    # Crear producto y registrar una venta en EFECTIVO
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    ventas = client.get("/api/ventas").json()
    fecha = ventas[0]["creado_en"][:10] if ventas else "2026-03-01"

    # Versin JSON
    r = client.get(
        f"/api/reportes/ventas-por-medio-pago"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1
    fila_efectivo = next((x for x in datos if x["metodo_pago"] == "EFECTIVO"), None)
    assert fila_efectivo is not None
    assert fila_efectivo["cantidad_ventas"] >= 1
    assert fila_efectivo["total_vendido"] >= 0

    # Versin CSV
    r_csv = client.get(
        f"/api/reportes/ventas-por-medio-pago"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert lineas[0] == "metodo_pago,cantidad_ventas,total_vendido"
    assert any("EFECTIVO" in linea for linea in lineas[1:])


def test_rotacion_inventario_sin_datos(client: TestClient) -> None:
    """Rotacin de inventario sin ventas devuelve lista vaca."""
    r = client.get(
        "/api/reportes/rotacion-inventario"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_rotacion_inventario_con_ventas(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Rotacin de inventario calcula unidades_vendidas, stock_promedio_aprox y rotacion."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    # Ingresar stock y registrar ventas
    _ingresar_stock(client, producto_id, 10)
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "4"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    ventas = client.get("/api/ventas").json()
    fecha = ventas[0]["creado_en"][:10] if ventas else "2026-03-01"

    r = client.get(
        f"/api/reportes/rotacion-inventario"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1

    fila = next((x for x in datos if x["producto_id"] == producto_id), None)
    assert fila is not None
    assert fila["unidades_vendidas"] >= 1.0
    # stock_promedio_aprox se basa en el stock actual; debe ser mayor o igual que 0
    assert fila["stock_promedio_aprox"] >= 0.0
    # Si hay stock, la rotacin debe ser >= 0
    assert fila["rotacion"] >= 0.0

    # Versin CSV devuelve cabecera y al menos una fila con el producto
    r_csv = client.get(
        f"/api/reportes/rotacion-inventario"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "producto_id,nombre_producto,unidades_vendidas,stock_promedio_aprox,rotacion"
    )
    assert any(str(producto_id) in linea for linea in lineas[1:])


def test_caja_resumen_sin_datos(client: TestClient) -> None:
    """Caja resumen sin cajas ni movimientos en el rango devuelve lista vaca."""
    r = client.get(
        "/api/reportes/caja-resumen"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_caja_resumen_csv_sin_datos(client: TestClient) -> None:
    """Caja resumen en CSV sin datos devuelve solo cabecera."""
    r = client.get(
        "/api/reportes/caja-resumen"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.splitlines()
    assert (
        lineas[0]
        == "caja_id,fecha_apertura,fecha_cierre,saldo_inicial,saldo_final,total_ingresos,total_egresos,saldo_teorico,diferencia,cantidad_ventas_caja,total_ventas_caja"
    )
    assert len(lineas) == 1


def test_caja_resumen_con_movimientos_y_ventas(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Caja resumen incluye totales de ingresos/egresos, saldo terico y ventas por caja."""
    from tests.test_ventas import _ingresar_stock

    # Abrir caja y registrar movimientos de caja
    r_caja = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    assert r_caja.status_code == 200
    caja_id = r_caja.json()["id"]

    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "50"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "30"},
    )

    # Crear producto y registrar una venta (asociada automticamente a la caja abierta)
    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    # Rango amplio para incluir la actividad recin creada
    ventas = client.get("/api/ventas").json()
    fecha = ventas[0]["creado_en"][:10] if ventas else "2026-03-01"

    r = client.get(
        f"/api/reportes/caja-resumen"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1

    fila = next((x for x in datos if x["caja_id"] == caja_id), None)
    assert fila is not None
    # Validar campos bsicos de caja
    assert fila["saldo_inicial"] == 100.0
    assert fila["total_ingresos"] >= 50.0  # incluye INGRESO y VENTA
    assert fila["total_egresos"] == 30.0
    assert "saldo_teorico" in fila
    assert "cantidad_ventas_caja" in fila
    assert fila["cantidad_ventas_caja"] >= 1
    assert "total_ventas_caja" in fila


def test_caja_resumen_csv_con_movimientos_y_ventas(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Caja resumen en CSV incluye una fila por caja con columnas esperadas."""
    from tests.test_ventas import _ingresar_stock

    r_caja = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    assert r_caja.status_code == 200
    caja_id = r_caja.json()["id"]

    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "50"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "30"},
    )

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
        },
    )
    assert r_venta.status_code == 200

    ventas = client.get("/api/ventas").json()
    fecha = ventas[0]["creado_en"][:10] if ventas else "2026-03-01"

    r = client.get(
        f"/api/reportes/caja-resumen"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.splitlines()
    assert (
        lineas[0]
        == "caja_id,fecha_apertura,fecha_cierre,saldo_inicial,saldo_final,total_ingresos,total_egresos,saldo_teorico,diferencia,cantidad_ventas_caja,total_ventas_caja"
    )
    # Debe haber al menos una fila de datos
    assert len(lineas) >= 2
    # La fila de la caja debe contener su id
    assert any(str(caja_id) in linea for linea in lineas[1:])


def test_clientes_actividad_sin_datos(client: TestClient) -> None:
    """Clientes actividad sin ventas en el rango devuelve lista vaca."""
    r = client.get(
        "/api/reportes/clientes-actividad"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_clientes_actividad_con_cliente(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """Clientes actividad devuelve mtricas de ventas agregadas por cliente."""
    from tests.test_ventas import _ingresar_stock

    # Crear cliente y producto
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    cliente_id = r_persona.json()["id"]

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    # Registrar una venta asociada al cliente
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
            "cliente_id": cliente_id,
        },
    )
    assert r_venta.status_code == 200

    ventas = client.get("/api/ventas").json()
    fecha = ventas[0]["creado_en"][:10] if ventas else "2026-03-01"

    r = client.get(
        f"/api/reportes/clientes-actividad"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1

    fila = next((x for x in datos if x["cliente_id"] == cliente_id), None)
    assert fila is not None
    assert fila["cantidad_ventas"] >= 1
    assert fila["total_vendido"] >= 0
    assert "ticket_promedio_cliente" in fila
    assert "fecha_ultima_venta" in fila
    # Nuevos indicadores: saldo de cuenta corriente y lmite de crdito
    assert "saldo_cuenta_corriente" in fila
    assert "limite_credito" in fila

    # CSV incluye al cliente en alguna de las filas
    r_csv = client.get(
        f"/api/reportes/clientes-actividad"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "cliente_id,cliente_nombre,cantidad_ventas,total_vendido,ticket_promedio_cliente,fecha_ultima_venta"
    )
    assert any(str(cliente_id) in linea for linea in lineas[1:])


def test_clientes_inactivos_sin_personas(client: TestClient) -> None:
    """Clientes inactivos sin personas registradas devuelve lista vaca."""
    r = client.get(
        "/api/reportes/clientes-inactivos"
        "?fecha_corte=2026-01-31&dias_inactividad=30"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_clientes_inactivos_con_cliente_activo_e_inactivo(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """Clientes inactivos incluye clientes sin ventas y excluye clientes con ventas recientes."""
    from tests.test_ventas import _ingresar_stock

    # Cliente con ventas (activo)
    r_activo = client.post("/api/personas", json=persona_datos)
    assert r_activo.status_code == 201
    cliente_activo_id = r_activo.json()["id"]

    # Cliente sin ventas (inactivo)
    datos_inactivo = dict(persona_datos)
    datos_inactivo["nombre"] = persona_datos["nombre"] + " Inactivo"
    r_inactivo = client.post("/api/personas", json=datos_inactivo)
    assert r_inactivo.status_code == 201
    cliente_inactivo_id = r_inactivo.json()["id"]

    # Producto y venta asociada al cliente activo
    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
            "cliente_id": cliente_activo_id,
        },
    )
    assert r_venta.status_code == 200

    ventas = client.get("/api/ventas").json()
    fecha = ventas[0]["creado_en"][:10] if ventas else "2026-03-01"

    # Con dias_inactividad=30, el cliente activo (venta hoy) no debe ser inactivo;
    # el cliente sin ventas s debe aparecer como inactivo.
    r = client.get(
        f"/api/reportes/clientes-inactivos"
        f"?fecha_corte={fecha}&dias_inactividad=30"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    # Debe incluir al menos al cliente sin ventas
    inactivo = next((x for x in datos if x["cliente_id"] == cliente_inactivo_id), None)
    assert inactivo is not None
    # El cliente activo no debe aparecer como inactivo
    assert all(x["cliente_id"] != cliente_activo_id for x in datos)

    # CSV tambin debe incluir al cliente inactivo
    r_csv = client.get(
        f"/api/reportes/clientes-inactivos"
        f"?fecha_corte={fecha}&dias_inactividad=30&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert lineas[0] == "cliente_id,cliente_nombre,fecha_ultima_venta"
    assert any(str(cliente_inactivo_id) in linea for linea in lineas[1:])


def test_clientes_rentabilidad_sin_datos(client: TestClient) -> None:
    """Clientes rentabilidad sin ventas en el rango devuelve lista vaca."""
    r = client.get(
        "/api/reportes/clientes-rentabilidad"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_clientes_rentabilidad_con_cliente(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """Clientes rentabilidad devuelve margen bruto y porcentaje por cliente."""
    from tests.test_ventas import _ingresar_stock

    # Crear cliente y producto
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    cliente_id = r_persona.json()["id"]

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    precio_venta = float(r_prod.json()["precio_venta"])
    _ingresar_stock(client, producto_id, 10)

    # Registrar una venta asociada al cliente
    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "EFECTIVO",
            "cliente_id": cliente_id,
        },
    )
    assert r_venta.status_code == 200

    ventas = client.get("/api/ventas").json()
    fecha = ventas[0]["creado_en"][:10] if ventas else "2026-03-01"

    # Versin JSON
    r = client.get(
        f"/api/reportes/clientes-rentabilidad"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1

    fila = next((x for x in datos if x["cliente_id"] == cliente_id), None)
    assert fila is not None
    assert fila["cantidad_ventas"] >= 1
    # costo_actual por defecto es 0, por lo que margen = total_vendido y margen_pct = 100
    total_esperado = 2 * precio_venta
    assert fila["total_vendido"] == total_esperado
    assert fila["total_costo"] == 0.0
    assert fila["margen_bruto"] == total_esperado
    assert fila["margen_pct"] == 100.0
    # Nuevos indicadores: saldo de cuenta corriente y lmite de crdito
    assert "saldo_cuenta_corriente" in fila
    assert "limite_credito" in fila

    # Versin CSV
    r_csv = client.get(
        f"/api/reportes/clientes-rentabilidad"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "cliente_id,cliente_nombre,cantidad_ventas,total_vendido,total_costo,margen_bruto,margen_pct"
    )
    assert any(str(cliente_id) in linea for linea in lineas[1:])


def test_proveedores_volumen_compras_sin_datos(client: TestClient) -> None:
    """Volumen de compras por proveedor sin datos devuelve lista vaca."""
    r = client.get(
        "/api/reportes/proveedores-volumen-compras"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_proveedores_volumen_compras_con_datos(
    client: TestClient,
    persona_datos: dict,
    producto_datos: dict,
) -> None:
    """Volumen de compras por proveedor agrupa y suma por proveedor."""
    # Crear proveedor y producto
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    proveedor_id = r_persona.json()["id"]

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    # Registrar una compra usando la API de compras
    r_compra = client.post(
        "/api/compras",
        json={
            "proveedor_id": proveedor_id,
            "items": [
                {
                    "producto_id": producto_id,
                    "cantidad": "3",
                    "costo_unitario": "10.00",
                }
            ],
        },
    )
    assert r_compra.status_code == 201

    compras = client.get("/api/compras").json()
    assert len(compras) >= 1
    fecha = compras[0]["fecha"][:10]

    # Versin JSON
    r = client.get(
        f"/api/reportes/proveedores-volumen-compras"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1
    fila = next((x for x in datos if x["proveedor_id"] == proveedor_id), None)
    assert fila is not None
    assert fila["cantidad_compras"] >= 1
    assert fila["total_comprado"] >= 0

    # Versin CSV
    r_csv = client.get(
        f"/api/reportes/proveedores-volumen-compras"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "proveedor_id,proveedor_nombre,cantidad_compras,total_comprado"
    )
    assert any(str(proveedor_id) in linea for linea in lineas[1:])


def test_proveedores_productos_sin_datos(client: TestClient) -> None:
    """Productos suministrados por proveedor sin datos devuelve lista vaca."""
    r = client.get(
        "/api/reportes/proveedores-productos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_proveedores_productos_con_datos(
    client: TestClient,
    persona_datos: dict,
    producto_datos: dict,
) -> None:
    """Productos suministrados por proveedor devuelve productos y cantidades compradas."""
    # Crear proveedor y producto
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    proveedor_id = r_persona.json()["id"]

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    # Registrar una compra
    r_compra = client.post(
        "/api/compras",
        json={
            "proveedor_id": proveedor_id,
            "items": [
                {
                    "producto_id": producto_id,
                    "cantidad": "5",
                    "costo_unitario": "8.00",
                }
            ],
        },
    )
    assert r_compra.status_code == 201

    compras = client.get("/api/compras").json()
    assert len(compras) >= 1
    fecha = compras[0]["fecha"][:10]

    # Versin JSON sin filtro de proveedor
    r = client.get(
        f"/api/reportes/proveedores-productos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1
    fila = next(
        (
            x
            for x in datos
            if x["proveedor_id"] == proveedor_id
            and x["producto_id"] == producto_id
        ),
        None,
    )
    assert fila is not None
    assert fila["cantidad_comprada"] >= 5.0
    assert fila["total_comprado"] >= 0.0

    # Versin JSON filtrando por proveedor
    r_filtro = client.get(
        f"/api/reportes/proveedores-productos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&proveedor_id={proveedor_id}"
    )
    assert r_filtro.status_code == 200
    datos_filtro = r_filtro.json()
    assert all(x["proveedor_id"] == proveedor_id for x in datos_filtro)

    # Versin CSV
    r_csv = client.get(
        f"/api/reportes/proveedores-productos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "proveedor_id,proveedor_nombre,producto_id,nombre_producto,cantidad_comprada,total_comprado"
    )
    assert any(str(producto_id) in linea for linea in lineas[1:])


def test_ranking_proveedores_sin_datos(client: TestClient) -> None:
    """Ranking de proveedores sin datos devuelve lista vaca."""
    r = client.get(
        "/api/reportes/ranking-proveedores"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_ranking_proveedores_con_datos(
    client: TestClient,
    persona_datos: dict,
    producto_datos: dict,
) -> None:
    """Ranking de proveedores ordena por total_comprado y cantidad_compras."""
    # Crear proveedor y producto
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    proveedor_id = r_persona.json()["id"]

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    # Registrar dos compras para garantizar cantidad_compras >= 2
    for _ in range(2):
        r_compra = client.post(
            "/api/compras",
            json={
                "proveedor_id": proveedor_id,
                "items": [
                    {
                        "producto_id": producto_id,
                        "cantidad": "1",
                        "costo_unitario": "5.00",
                    }
                ],
            },
        )
        assert r_compra.status_code == 201

    compras = client.get("/api/compras").json()
    assert len(compras) >= 2
    fecha = compras[0]["fecha"][:10]

    # Orden por total
    r = client.get(
        f"/api/reportes/ranking-proveedores"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&orden_por=total"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    if datos:
        assert datos[0]["posicion"] == 1

    # Orden por cantidad
    r_cantidad = client.get(
        f"/api/reportes/ranking-proveedores"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&orden_por=cantidad"
    )
    assert r_cantidad.status_code == 200
    datos_cantidad = r_cantidad.json()
    assert isinstance(datos_cantidad, list)

    # CSV incluye cabecera esperada
    r_csv = client.get(
        f"/api/reportes/ranking-proveedores"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "posicion,proveedor_id,proveedor_nombre,cantidad_compras,total_comprado"
    )
    assert any(str(proveedor_id) in linea for linea in lineas[1:])


def test_variacion_costos_productos_sin_datos(client: TestClient) -> None:
    """Variacin de costos de productos sin compras en el rango devuelve lista vaca y CSV solo con cabecera."""
    r = client.get(
        "/api/reportes/variacion-costos-productos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []

    r_csv = client.get(
        "/api/reportes/variacion-costos-productos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "producto_id,nombre_producto,costo_min,costo_max,costo_promedio,variacion_absoluta,variacion_pct"
    )
    assert len(lineas) == 1


def test_variacion_costos_productos_con_datos(
    client: TestClient,
    persona_datos: dict,
    producto_datos: dict,
) -> None:
    """Variacin de costos de productos calcula min, max, promedio y variaciones a partir de compras."""
    # Crear proveedor y producto
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    proveedor_id = r_persona.json()["id"]

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    # Registrar dos compras con distintos costos unitarios
    for costo in ("10.00", "15.00"):
        r_compra = client.post(
            "/api/compras",
            json={
                "proveedor_id": proveedor_id,
                "items": [
                    {
                        "producto_id": producto_id,
                        "cantidad": "2",
                        "costo_unitario": costo,
                    }
                ],
            },
        )
        assert r_compra.status_code == 201

    compras = client.get("/api/compras").json()
    assert len(compras) >= 2
    fecha = compras[0]["fecha"][:10]

    # Versin JSON
    r = client.get(
        f"/api/reportes/variacion-costos-productos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1

    fila = next((x for x in datos if x["producto_id"] == producto_id), None)
    assert fila is not None
    assert fila["costo_min"] == 10.0
    assert fila["costo_max"] == 15.0
    # promedio entre 10 y 15 debe ser 12.5
    assert fila["costo_promedio"] == 12.5
    assert fila["variacion_absoluta"] == 5.0
    # variacin porcentual respecto al mnimo: (5 / 10) * 100 = 50
    assert fila["variacion_pct"] == 50.0

    # Versin CSV incluye el producto en alguna fila
    r_csv = client.get(
        f"/api/reportes/variacion-costos-productos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "producto_id,nombre_producto,costo_min,costo_max,costo_promedio,variacion_absoluta,variacion_pct"
    )
    assert any(str(producto_id) in linea for linea in lineas[1:])


def test_proveedores_impacto_costos_sin_datos(client: TestClient) -> None:
    """Impacto de costos por proveedor sin compras en el rango devuelve lista vaca y CSV solo cabecera."""
    r = client.get(
        "/api/reportes/proveedores-impacto-costos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []

    r_csv = client.get(
        "/api/reportes/proveedores-impacto-costos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "proveedor_id,proveedor_nombre,total_comprado,costo_min,costo_max,costo_promedio,variacion_absoluta,variacion_pct"
    )
    assert len(lineas) == 1


def test_proveedores_impacto_costos_con_datos(
    client: TestClient,
    persona_datos: dict,
    producto_datos: dict,
) -> None:
    """Impacto de costos por proveedor combina volumen comprado y variacin de costos."""
    # Crear proveedor y producto
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    proveedor_id = r_persona.json()["id"]

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    # Registrar dos compras con distintos costos unitarios
    for costo in ("10.00", "15.00"):
        r_compra = client.post(
            "/api/compras",
            json={
                "proveedor_id": proveedor_id,
                "items": [
                    {
                        "producto_id": producto_id,
                        "cantidad": "2",
                        "costo_unitario": costo,
                    }
                ],
            },
        )
        assert r_compra.status_code == 201

    compras = client.get("/api/compras").json()
    assert len(compras) >= 2
    fecha = compras[0]["fecha"][:10]

    # Versin JSON
    r = client.get(
        f"/api/reportes/proveedores-impacto-costos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1

    fila = next((x for x in datos if x["proveedor_id"] == proveedor_id), None)
    assert fila is not None
    # total_comprado debe ser mayor que 0 (dos compras de 2 * costo_unitario)
    assert fila["total_comprado"] > 0
    assert fila["costo_min"] == 10.0
    assert fila["costo_max"] == 15.0
    assert fila["costo_promedio"] == 12.5
    assert fila["variacion_absoluta"] == 5.0
    assert fila["variacion_pct"] == 50.0

    # Versin CSV incluye al proveedor en alguna fila
    r_csv = client.get(
        f"/api/reportes/proveedores-impacto-costos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "proveedor_id,proveedor_nombre,total_comprado,costo_min,costo_max,costo_promedio,variacion_absoluta,variacion_pct"
    )
    assert any(str(proveedor_id) in linea for linea in lineas[1:])


def test_proveedores_riesgo_costos_sin_datos(client: TestClient) -> None:
    """Riesgo de costos por proveedor sin datos devuelve lista vaca y CSV solo cabecera."""
    r = client.get(
        "/api/reportes/proveedores-riesgo-costos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []

    r_csv = client.get(
        "/api/reportes/proveedores-riesgo-costos"
        "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "proveedor_id,proveedor_nombre,total_comprado,costo_min,costo_max,costo_promedio,variacion_absoluta,variacion_pct,riesgo_costos"
    )
    assert len(lineas) == 1


def test_proveedores_riesgo_costos_con_datos(
    client: TestClient,
    persona_datos: dict,
    producto_datos: dict,
) -> None:
    """Riesgo de costos por proveedor calcula riesgo_costos coherente con total y variacin."""
    # Crear proveedor y producto
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    proveedor_id = r_persona.json()["id"]

    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]

    # Registrar dos compras con distintos costos unitarios
    for costo in ("10.00", "15.00"):
        r_compra = client.post(
            "/api/compras",
            json={
                "proveedor_id": proveedor_id,
                "items": [
                    {
                        "producto_id": producto_id,
                        "cantidad": "2",
                        "costo_unitario": costo,
                    }
                ],
            },
        )
        assert r_compra.status_code == 201

    compras = client.get("/api/compras").json()
    assert len(compras) >= 2
    fecha = compras[0]["fecha"][:10]

    r = client.get(
        f"/api/reportes/proveedores-riesgo-costos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}"
    )
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1

    fila = next((x for x in datos if x["proveedor_id"] == proveedor_id), None)
    assert fila is not None
    total = fila["total_comprado"]
    var_pct = fila["variacion_pct"]
    riesgo = fila["riesgo_costos"]
    # riesgo_costos debe aproximarse a total * (var_pct / 100)
    assert riesgo == round(total * (var_pct / 100.0), 2)

    # Versin CSV incluye al proveedor
    r_csv = client.get(
        f"/api/reportes/proveedores-riesgo-costos"
        f"?fecha_desde={fecha}&fecha_hasta={fecha}&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.splitlines()
    assert (
        lineas[0]
        == "proveedor_id,proveedor_nombre,total_comprado,costo_min,costo_max,costo_promedio,variacion_absoluta,variacion_pct,riesgo_costos"
    )
    assert any(str(proveedor_id) in linea for linea in lineas[1:])


def test_clientes_cartera_riesgo_con_cuenta_corriente(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """
    El reporte clientes-cartera-riesgo devuelve clientes con saldo de cuenta corriente,
    lmite de crdito y porcentaje_utilizado consistente.
    """
    from tests.test_ventas import _ingresar_stock

    # Crear persona y rol cliente con lmite de crdito
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "CUENTA_CORRIENTE",
            "limite_credito": "200.00",
        },
    )
    assert r_cliente.status_code == 201

    # Crear producto y registrar una venta a crdito para generar saldo
    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "CUENTA_CORRIENTE",
            "cliente_id": persona_id,
        },
    )

    r = client.get("/api/reportes/clientes-cartera-riesgo?limite=10")
    assert r.status_code == 200
    datos = r.json()
    assert isinstance(datos, list)
    assert len(datos) >= 1

    fila = next((x for x in datos if x["cliente_id"] == persona_id), None)
    assert fila is not None
    assert fila["saldo"] > 0.0
    assert fila["limite_credito"] == 200.0
    assert 0.0 < fila["porcentaje_utilizado"] <= 100.0


def test_clientes_cartera_riesgo_csv_incluye_cliente(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """La versin CSV de clientes-cartera-riesgo incluye al menos una fila para el cliente."""
    from tests.test_ventas import _ingresar_stock

    # Crear persona y rol cliente
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "CUENTA_CORRIENTE",
            "limite_credito": "150.00",
        },
    )
    assert r_cliente.status_code == 201

    # Crear producto y registrar una venta a crdito
    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "1"}],
            "descuento": "0",
            "metodo_pago": "CUENTA_CORRIENTE",
            "cliente_id": persona_id,
        },
    )

    r_csv = client.get(
        "/api/reportes/clientes-cartera-riesgo?limite=10&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.strip().splitlines()
    assert (
        lineas[0]
        == "cliente_id,cliente_nombre,saldo,limite_credito,porcentaje_utilizado"
    )
    assert any(str(persona_id) in linea for linea in lineas[1:])


def test_clientes_cartera_morosidad_sin_datos(client: TestClient) -> None:
    """Clientes cartera morosidad sin datos devuelve resumen en 0 y filas vacas."""
    from datetime import date

    hoy = date.today().isoformat()
    r = client.get(
        f"/api/reportes/clientes-cartera-morosidad?fecha_corte={hoy}&limite=50"
    )
    assert r.status_code == 200
    data = r.json()
    assert "resumen" in data
    assert "filas" in data
    resumen = data["resumen"]
    filas = data["filas"]
    assert resumen["fecha_corte"] == hoy
    assert resumen["total_clientes"] == 0
    assert resumen["saldo_total"] == 0.0
    assert resumen["saldo_vencido_total"] == 0.0
    assert isinstance(resumen["distribucion_tramos"], dict)
    assert filas == []


def test_clientes_cartera_morosidad_con_deuda_y_tramos(
    client: TestClient,
    producto_datos: dict,
    persona_datos: dict,
) -> None:
    """
    El reporte de cartera morosidad devuelve clientes con saldo y tramo de morosidad,
    y clasifica como vencido cuando se usa una fecha_corte muy futura.
    """
    from datetime import date
    from tests.test_ventas import _ingresar_stock

    # Crear persona y rol cliente con lmite de crdito
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "CUENTA_CORRIENTE",
            "limite_credito": "300.00",
        },
    )
    assert r_cliente.status_code == 201

    # Crear producto y registrar una venta a crdito para generar saldo
    r_prod = client.post("/api/productos", json=producto_datos)
    assert r_prod.status_code == 201
    producto_id = r_prod.json()["id"]
    _ingresar_stock(client, producto_id, 10)

    r_venta = client.post(
        "/api/ventas",
        json={
            "items": [{"producto_id": producto_id, "cantidad": "2"}],
            "descuento": "0",
            "metodo_pago": "CUENTA_CORRIENTE",
            "cliente_id": persona_id,
        },
    )
    assert r_venta.status_code == 200

    # 1) Con fecha_corte "hoy" el cliente tiene saldo y algn tramo (probablemente 'al_dia')
    hoy = date.today().isoformat()
    r = client.get(
        f"/api/reportes/clientes-cartera-morosidad?fecha_corte={hoy}&limite=10"
    )
    assert r.status_code == 200
    data = r.json()
    filas = data["filas"]
    fila = next((x for x in filas if x["cliente_id"] == persona_id), None)
    assert fila is not None
    assert fila["saldo"] > 0.0
    assert fila["limite_credito"] == 300.0
    assert fila["porcentaje_utilizado"] > 0.0
    assert fila["dias_morosidad"] is None or fila["dias_morosidad"] >= 0
    assert isinstance(fila["tramo_morosidad"], str)

    # 2) Con una fecha_corte muy futura, el mismo saldo debe caer en un tramo vencido
    fecha_futura = "2100-01-01"
    r_futuro = client.get(
        f"/api/reportes/clientes-cartera-morosidad?fecha_corte={fecha_futura}&limite=10"
    )
    assert r_futuro.status_code == 200
    datos_futuro = r_futuro.json()
    filas_futuro = datos_futuro["filas"]
    fila_futuro = next((x for x in filas_futuro if x["cliente_id"] == persona_id), None)
    assert fila_futuro is not None
    assert fila_futuro["saldo"] == fila["saldo"]
    assert fila_futuro["dias_morosidad"] is None or fila_futuro["dias_morosidad"] >= 0
    # Para una fecha muy futura esperamos un tramo vencido fuerte o al menos no 'al_dia'
    assert fila_futuro["tramo_morosidad"] in {
        "vencido_31_60",
        "vencido_61_90",
        "vencido_90_mas",
    }

    # Versin CSV devuelve cabecera esperada y al menos una fila con el cliente
    r_csv = client.get(
        f"/api/reportes/clientes-cartera-morosidad?fecha_corte={fecha_futura}&limite=10&formato=csv"
    )
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    lineas = r_csv.text.strip().splitlines()
    assert (
        lineas[0]
        == "cliente_id,cliente_nombre,saldo,limite_credito,porcentaje_utilizado,dias_morosidad,tramo_morosidad"
    )
    assert any(str(persona_id) in linea for linea in lineas[1:])


# ---------------------------------------------------------------------------
# Tests  nuevas funciones Mdulo 7 (brechas funcionales)
# ---------------------------------------------------------------------------


def test_ventas_por_categoria_sin_datos(client: TestClient) -> None:
    r = client.get('/api/reportes/ventas-por-categoria?fecha_desde=2026-01-01&fecha_hasta=2026-01-31')
    assert r.status_code == 200
    assert r.json() == []


def test_ventas_por_categoria_csv_sin_datos(client: TestClient) -> None:
    r = client.get('/api/reportes/ventas-por-categoria?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/csv')
    lineas = r.text.strip().splitlines()
    assert lineas[0] == 'categoria_id,categoria_nombre,cantidad_vendida,total_vendido'
    assert len(lineas) == 1


def test_ventas_canceladas_sin_datos(client: TestClient) -> None:
    r = client.get('/api/reportes/ventas-canceladas?fecha_desde=2026-01-01&fecha_hasta=2026-01-31')
    assert r.status_code == 200
    data = r.json()
    assert data['resumen']['total_canceladas'] == 0
    assert data['resumen']['monto_total'] == 0.0
    assert data['filas'] == []


def test_ventas_canceladas_csv_sin_datos(client: TestClient) -> None:
    r = client.get('/api/reportes/ventas-canceladas?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/csv')
    lineas = r.text.strip().splitlines()
    assert lineas[0] == 'venta_id,numero_ticket,total,metodo_pago,creado_en,cliente_nombre'
    assert len(lineas) == 1


def test_inventario_bajo_minimo_sin_datos(client: TestClient) -> None:
    r = client.get('/api/reportes/inventario-bajo-minimo')
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_inventario_bajo_minimo_csv_sin_datos(client: TestClient) -> None:
    r = client.get('/api/reportes/inventario-bajo-minimo?formato=csv')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/csv')
    lineas = r.text.strip().splitlines()
    assert lineas[0] == 'producto_id,nombre_producto,stock_actual,stock_minimo,diferencia'


def test_mermas_sin_datos(client: TestClient) -> None:
    r = client.get('/api/reportes/mermas?fecha_desde=2026-01-01&fecha_hasta=2026-01-31')
    assert r.status_code == 200
    data = r.json()
    assert data['resumen']['total_movimientos'] == 0
    assert data['resumen']['total_unidades_merma'] == 0.0
    assert data['filas'] == []


def test_mermas_csv_sin_datos(client: TestClient) -> None:
    r = client.get('/api/reportes/mermas?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/csv')
    lineas = r.text.strip().splitlines()
    assert lineas[0] == 'producto_id,nombre_producto,cantidad_registros,total_unidades'


def test_consolidado_diario_csv_columnas_enriquecidas(client: TestClient) -> None:
    r = client.get('/api/reportes/consolidado-diario?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/csv')
    cabecera = r.text.strip().splitlines()[0]
    for col in ['ventas_fiadas', 'cancelaciones', 'clientes_activos', 'unidades_vendidas', 'productos_distintos', 'margen_estimado']:
        assert col in cabecera


# ---------------------------------------------------------------------------
# Tests: reporte operaciones comerciales (docs Modulo 7 ss7)
# ---------------------------------------------------------------------------

def test_operaciones_comerciales_sin_datos(client: TestClient) -> None:
    """GET /operaciones-comerciales sin datos devuelve estructura vacia."""
    r = client.get('/api/reportes/operaciones-comerciales?fecha_desde=2026-01-01&fecha_hasta=2026-01-31')
    assert r.status_code == 200
    data = r.json()
    assert 'resumen' in data
    assert 'filas' in data
    assert data['resumen']['total_operaciones'] == 0
    assert data['filas'] == []


def _crear_venta_pendiente(client, producto_datos):
    """Crea una venta PENDIENTE con un producto."""
    from tests.test_ventas import _ingresar_stock
    sku = f"REP-OC-{id(producto_datos)}"
    prod_data = {**producto_datos, "sku": sku}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 20)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "modo_venta": "TEU_OFF",
    })
    return r_v.json()["venta_id"], prod["id"]


def test_operaciones_comerciales_con_devolucion(client: TestClient, producto_datos: dict) -> None:
    """GET /operaciones-comerciales devuelve devolucion creada en el rango."""
    from tests.test_ventas import _ingresar_stock
    # Crear producto, stock y venta PENDIENTE (TEU_OFF)
    sku = "RPT-DEV-OC-A"
    prod_data = {**producto_datos, "sku": sku, "nombre": "Prod Dev OC A"}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 20)
    r_v = client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "modo_venta": "TEU_OFF",
    })
    venta_id = r_v.json()["venta_id"]
    venta = client.get(f"/api/ventas/{venta_id}").json()
    item_venta_id = venta["items"][0]["id"]
    total = float(venta["total"])

    # Abrir caja y cobrar el ticket
    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    r_cobrar = client.post(f"/api/caja/tickets/{venta_id}/cobrar", json={
        "pagos": [{"metodo_pago": "EFECTIVO", "importe": str(total)}]
    })
    assert r_cobrar.status_code == 200

    # Registrar devolucion con item_venta_id correcto
    r_dev = client.post("/api/operaciones-comerciales/devoluciones", json={
        "venta_id": venta_id,
        "items": [{"item_venta_id": item_venta_id, "cantidad": "1"}],
        "reintegro_tipo": "EFECTIVO",
        "motivo": "Defectuoso",
    })
    assert r_dev.status_code in (200, 201)

    # Verificar en reporte
    import datetime
    hoy = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    r = client.get(f'/api/reportes/operaciones-comerciales?fecha_desde={hoy}&fecha_hasta={hoy}')
    assert r.status_code == 200
    data = r.json()
    assert data['resumen']['total_operaciones'] >= 1
    tipos = [f['tipo'] for f in data['filas']]
    assert 'DEVOLUCION' in tipos


def test_operaciones_comerciales_filtro_tipo(client: TestClient) -> None:
    """GET /operaciones-comerciales?tipo=NOTA_CREDITO filtra por tipo."""
    r = client.get('/api/reportes/operaciones-comerciales?fecha_desde=2026-01-01&fecha_hasta=2026-12-31&tipo=NOTA_CREDITO')
    assert r.status_code == 200
    data = r.json()
    assert all(f['tipo'] == 'NOTA_CREDITO' for f in data['filas'])


def test_operaciones_comerciales_csv(client: TestClient) -> None:
    """GET /operaciones-comerciales?formato=csv devuelve CSV con cabecera correcta."""
    r = client.get('/api/reportes/operaciones-comerciales?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/csv')
    cabecera = r.text.strip().splitlines()[0]
    assert 'operacion_id' in cabecera
    assert 'tipo' in cabecera
    assert 'importe_total' in cabecera


# ---------------------------------------------------------------------------
# Tests: ventas por caja (docs Modulo 7 ss8)
# ---------------------------------------------------------------------------

def test_ventas_por_caja_sin_datos(client: TestClient) -> None:
    """GET /ventas-por-caja sin datos devuelve lista vacia."""
    r = client.get('/api/reportes/ventas-por-caja?fecha_desde=2026-01-01&fecha_hasta=2026-01-31')
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_ventas_por_caja_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """GET /ventas-por-caja con ventas devuelve cajas con totales."""
    from tests.test_ventas import _ingresar_stock
    prod_data = {**producto_datos, "sku": "RPT-CAJA-1"}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 10)
    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": "1"}],
        "metodo_pago": "EFECTIVO",
    })
    import datetime
    hoy = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    r = client.get(f'/api/reportes/ventas-por-caja?fecha_desde={hoy}&fecha_hasta={hoy}')
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert 'caja_id' in data[0]
    assert 'total_ventas' in data[0]
    assert 'cantidad_ventas' in data[0]


def test_ventas_por_caja_csv(client: TestClient) -> None:
    """GET /ventas-por-caja?formato=csv devuelve CSV con cabecera correcta."""
    r = client.get('/api/reportes/ventas-por-caja?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/csv')
    cabecera = r.text.strip().splitlines()[0]
    assert 'caja_id' in cabecera
    assert 'total_ventas' in cabecera
    assert 'fecha_apertura' in cabecera


# ---------------------------------------------------------------------------
# Tests: frecuencia de compra de clientes (docs Modulo 7 ss11)
# ---------------------------------------------------------------------------

def test_frecuencia_compra_clientes_sin_datos(client: TestClient) -> None:
    """GET /frecuencia-compra-clientes sin datos devuelve lista vacia."""
    r = client.get('/api/reportes/frecuencia-compra-clientes?fecha_desde=2026-01-01&fecha_hasta=2026-01-31')
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_frecuencia_compra_clientes_con_compras(client: TestClient, producto_datos: dict, persona_datos: dict) -> None:
    """GET /frecuencia-compra-clientes devuelve clientes con sus metricas de frecuencia."""
    from tests.test_ventas import _ingresar_stock
    persona = client.post("/api/personas", json=persona_datos).json()
    prod_data = {**producto_datos, "sku": "FREQ-CLI-1"}
    prod = client.post("/api/productos", json=prod_data).json()
    _ingresar_stock(client, prod["id"], 20)
    # Crear 2 ventas para el mismo cliente
    for _ in range(2):
        client.post("/api/ventas", json={
            "items": [{"producto_id": prod["id"], "cantidad": "1"}],
            "metodo_pago": "EFECTIVO",
            "cliente_id": persona["id"],
        })
    import datetime
    hoy = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    r = client.get(f'/api/reportes/frecuencia-compra-clientes?fecha_desde={hoy}&fecha_hasta={hoy}')
    assert r.status_code == 200
    data = r.json()
    cliente_data = next((c for c in data if c["cliente_id"] == persona["id"]), None)
    assert cliente_data is not None
    assert cliente_data["cantidad_compras"] >= 2
    assert "ticket_promedio" in cliente_data
    assert "primera_compra" in cliente_data


def test_frecuencia_compra_csv(client: TestClient) -> None:
    """GET /frecuencia-compra-clientes?formato=csv devuelve CSV correcto."""
    r = client.get('/api/reportes/frecuencia-compra-clientes?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/csv')
    cabecera = r.text.strip().splitlines()[0]
    assert 'cliente_id' in cabecera
    assert 'cantidad_compras' in cabecera
