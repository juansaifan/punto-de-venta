"""Tests de la API de inventario (stock)."""
from fastapi.testclient import TestClient


def test_obtener_stock_sin_registro(client: TestClient, producto_datos: dict) -> None:
    """Obtener stock de un producto sin registro devuelve cantidad 0."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    r = client.get(f"/api/inventario/productos/{producto_id}/stock")
    assert r.status_code == 200
    assert float(r.json()["cantidad"]) == 0


def test_ingresar_stock_ok(client: TestClient, producto_datos: dict) -> None:
    """Ingresar stock actualiza la cantidad."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    r = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "5.5"},
    )
    assert r.status_code == 200
    stock = client.get(f"/api/inventario/productos/{producto_id}/stock")
    assert stock.status_code == 200
    assert float(stock.json()["cantidad"]) == 5.5


def test_ingresar_stock_acumula(client: TestClient, producto_datos: dict) -> None:
    """Múltiples ingresos acumulan cantidad."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "3"},
    )
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "2"},
    )
    stock = client.get(f"/api/inventario/productos/{producto_id}/stock")
    assert stock.status_code == 200
    assert float(stock.json()["cantidad"]) == 5


def test_distribucion_stock_por_ubicacion(client: TestClient, producto_datos: dict) -> None:
    """GET /api/inventario/distribucion devuelve producto+ubicación+cantidad con filtros."""
    crear = client.post("/api/productos", json={**producto_datos, "sku": "TEST-DIST"})
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "2", "ubicacion": "GONDOLA"},
    )
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "5", "ubicacion": "DEPOSITO"},
    )

    dist = client.get(
        "/api/inventario/distribucion",
        params={"producto_id": producto_id},
    )
    assert dist.status_code == 200
    data = dist.json()
    assert len(data) >= 2
    assert any(x["ubicacion"] == "GONDOLA" and float(x["cantidad"]) == 2.0 for x in data)
    assert any(x["ubicacion"] == "DEPOSITO" and float(x["cantidad"]) == 5.0 for x in data)

    dist_dep = client.get(
        "/api/inventario/distribucion",
        params={"producto_id": producto_id, "ubicacion": "DEPOSITO"},
    )
    assert dist_dep.status_code == 200
    data_dep = dist_dep.json()
    assert len(data_dep) >= 1
    assert all(x["ubicacion"] == "DEPOSITO" for x in data_dep)
    assert any(float(x["cantidad"]) == 5.0 for x in data_dep)


def test_listar_movimientos_vacio(client: TestClient) -> None:
    """Listar movimientos sin datos devuelve lista vacía."""
    r = client.get("/api/inventario/movimientos")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_movimientos_despues_de_ingreso(client: TestClient, producto_datos: dict) -> None:
    """Listar movimientos incluye los generados por ingresar stock."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10"},
    )
    r = client.get("/api/inventario/movimientos")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) >= 1
    mov = next(m for m in datos if m["producto_id"] == producto_id)
    assert mov["tipo"] == "COMPRA"
    assert float(mov["cantidad"]) == 10
    assert "id" in mov
    assert "fecha" in mov


def test_listar_movimientos_filtro_por_producto(client: TestClient, producto_datos: dict) -> None:
    """Filtro producto_id devuelve solo movimientos de ese producto."""
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "5"},
    )
    r = client.get(f"/api/inventario/movimientos?producto_id={producto_id}")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) >= 1
    for m in datos:
        assert m["producto_id"] == producto_id


def test_listar_movimientos_filtro_por_tipo(client: TestClient, producto_datos: dict) -> None:
    """Filtro tipo=COMPRA devuelve solo movimientos de tipo COMPRA."""
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "3"},
    )
    r = client.get("/api/inventario/movimientos", params={"tipo": "COMPRA"})
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) >= 1
    for m in datos:
        assert m["tipo"] == "COMPRA"


# --- Categorías de productos ---


def test_listar_categorias_vacio(client: TestClient) -> None:
    """Listar categorías sin datos devuelve lista vacía."""
    r = client.get("/api/inventario/categorias")
    assert r.status_code == 200
    assert r.json() == []


def test_crear_categoria_ok(client: TestClient) -> None:
    """Crear categoría devuelve 201 y el recurso con codigo y nombre."""
    r = client.post(
        "/api/inventario/categorias",
        json={"codigo": "BEB", "nombre": "Bebidas", "descripcion": "Bebidas varias"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["codigo"] == "BEB"
    assert data["nombre"] == "Bebidas"
    assert data["descripcion"] == "Bebidas varias"
    assert data["categoria_padre_id"] is None


def test_obtener_categoria_por_id(client: TestClient) -> None:
    """Obtener categoría por ID devuelve el recurso."""
    crear = client.post(
        "/api/inventario/categorias",
        json={"codigo": "LAC", "nombre": "Lácteos"},
    )
    cat_id = crear.json()["id"]
    r = client.get(f"/api/inventario/categorias/{cat_id}")
    assert r.status_code == 200
    assert r.json()["codigo"] == "LAC"
    assert r.json()["nombre"] == "Lácteos"


def test_obtener_categoria_404(client: TestClient) -> None:
    """Obtener categoría inexistente devuelve 404."""
    r = client.get("/api/inventario/categorias/99999")
    assert r.status_code == 404


def test_crear_categoria_codigo_duplicado_409(client: TestClient) -> None:
    """Crear categoría con código ya existente devuelve 409."""
    client.post("/api/inventario/categorias", json={"codigo": "X", "nombre": "X"})
    r = client.post("/api/inventario/categorias", json={"codigo": "X", "nombre": "Otra"})
    assert r.status_code == 409
    assert "ya existe" in r.json()["detail"].lower()


def test_categoria_con_padre(client: TestClient) -> None:
    """Crear categoría con categoria_padre_id asigna la jerarquía."""
    padre = client.post(
        "/api/inventario/categorias",
        json={"codigo": "BEB", "nombre": "Bebidas"},
    )
    assert padre.status_code == 201
    padre_id = padre.json()["id"]
    r = client.post(
        "/api/inventario/categorias",
        json={"codigo": "GAS", "nombre": "Gaseosas", "categoria_padre_id": padre_id},
    )
    assert r.status_code == 201
    assert r.json()["categoria_padre_id"] == padre_id


def test_actualizar_categoria_ok(client: TestClient) -> None:
    """PATCH categoría actualiza nombre y descripcion."""
    crear = client.post(
        "/api/inventario/categorias",
        json={"codigo": "Y", "nombre": "Original", "descripcion": "Antes"},
    )
    cat_id = crear.json()["id"]
    r = client.patch(
        f"/api/inventario/categorias/{cat_id}",
        json={"nombre": "Actualizado", "descripcion": "Después"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nombre"] == "Actualizado"
    assert data["descripcion"] == "Después"
    assert data["codigo"] == "Y"


def test_actualizar_categoria_sin_campos_422(client: TestClient) -> None:
    """PATCH categoría sin ningún campo devuelve 422."""
    crear = client.post(
        "/api/inventario/categorias",
        json={"codigo": "Z", "nombre": "Z"},
    )
    cat_id = crear.json()["id"]
    r = client.patch(f"/api/inventario/categorias/{cat_id}", json={})
    assert r.status_code == 422


def test_crear_lote_ok(client: TestClient, producto_datos: dict) -> None:
    """POST productos/{id}/lotes crea lote con cantidad y fecha_vencimiento."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    r = client.post(
        f"/api/inventario/productos/{producto_id}/lotes",
        json={"cantidad": 10, "fecha_vencimiento": "2026-12-31"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["producto_id"] == producto_id
    assert data["cantidad"] == 10.0
    assert data["fecha_vencimiento"] == "2026-12-31"
    assert "id" in data


def test_crear_lote_producto_inexistente_404(client: TestClient) -> None:
    """POST lotes con producto_id inexistente devuelve 404."""
    r = client.post(
        "/api/inventario/productos/99999/lotes",
        json={"cantidad": 1, "fecha_vencimiento": "2026-06-01"},
    )
    assert r.status_code == 404


def test_crear_lote_sin_fecha_vencimiento_422(client: TestClient, producto_datos: dict) -> None:
    """POST lotes sin fecha_vencimiento devuelve 422."""
    crear = client.post("/api/productos", json=producto_datos)
    producto_id = crear.json()["id"]
    r = client.post(
        f"/api/inventario/productos/{producto_id}/lotes",
        json={"cantidad": 1},
    )
    assert r.status_code == 422


def test_alertas_stock_bajo_y_proximos_vencer(client: TestClient, producto_datos: dict) -> None:
    """GET /inventario/alertas detecta stock bajo y lotes próximos a vencer."""
    from datetime import date, timedelta

    # Producto con stock mínimo 5 y stock actual 2 => stock bajo
    producto_datos2 = {**producto_datos, "sku": "TEST-ALERT", "stock_minimo": "5"}
    crear = client.post("/api/productos", json=producto_datos2)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    client.post("/api/inventario/ingresar", json={"producto_id": producto_id, "cantidad": "2"})

    # Lote próximo a vencer en 3 días
    fv = (date.today() + timedelta(days=3)).isoformat()
    r_lote = client.post(
        f"/api/inventario/productos/{producto_id}/lotes",
        json={"cantidad": 10, "fecha_vencimiento": fv},
    )
    assert r_lote.status_code == 201

    r = client.get("/api/inventario/alertas", params={"dias_vencimiento": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["resumen"]["stock_bajo"] >= 1
    assert any(x["producto_id"] == producto_id for x in data["stock_bajo"])
    assert data["resumen"]["proximos_vencer"] >= 1
    assert any(x["producto_id"] == producto_id for x in data["proximos_vencer"])


def test_alertas_emitir_eventos_persiste_en_auditoria(client: TestClient, producto_datos: dict) -> None:
    """emitir_eventos=true debe dejar trazas en /api/auditoria/eventos."""
    from datetime import date, timedelta

    producto_datos2 = {**producto_datos, "sku": "TEST-ALERT-EVT", "stock_minimo": "1"}
    crear = client.post("/api/productos", json=producto_datos2)
    producto_id = crear.json()["id"]
    client.post("/api/inventario/ingresar", json={"producto_id": producto_id, "cantidad": "0.5"})

    fv = (date.today() + timedelta(days=1)).isoformat()
    client.post(
        f"/api/inventario/productos/{producto_id}/lotes",
        json={"cantidad": 1, "fecha_vencimiento": fv},
    )

    r = client.get("/api/inventario/alertas", params={"dias_vencimiento": 7, "emitir_eventos": "true"})
    assert r.status_code == 200

    r_aud = client.get("/api/auditoria/eventos", params={"modulo": "inventario", "limite": 50})
    assert r_aud.status_code == 200
    nombres = [e["nombre"] for e in r_aud.json()]
    assert "StockBajoDetectado" in nombres
    assert "LotesProximosAVencerDetectados" in nombres


def test_transferir_stock_mueve_cantidad_y_registra_movimientos(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Transferir stock entre ubicaciones registra dos movimientos tipo TRANSFERENCIA y actualiza stock."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    # Stock inicial en DEPOSITO
    r_ing = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10", "ubicacion": "DEPOSITO"},
    )
    assert r_ing.status_code == 200

    # Transferencia DEPOSITO -> GONDOLA
    r_transfer = client.post(
        "/api/inventario/transferir",
        json={
            "producto_id": producto_id,
            "cantidad": "4",
            "origen": "DEPOSITO",
            "destino": "GONDOLA",
            "referencia": "Transferencia test",
        },
    )
    assert r_transfer.status_code == 200, r_transfer.json()

    # Stock final
    st_deposito = client.get(
        f"/api/inventario/productos/{producto_id}/stock",
        params={"ubicacion": "DEPOSITO"},
    ).json()["cantidad"]
    st_gondola = client.get(
        f"/api/inventario/productos/{producto_id}/stock",
        params={"ubicacion": "GONDOLA"},
    ).json()["cantidad"]
    assert float(st_deposito) == 6.0
    assert float(st_gondola) == 4.0

    # Históricos por filtro de ubicacion
    movs_dep = client.get(
        "/api/inventario/movimientos",
        params={
            "producto_id": producto_id,
            "tipo": "TRANSFERENCIA",
            "ubicacion": "DEPOSITO",
        },
    ).json()
    movs_gon = client.get(
        "/api/inventario/movimientos",
        params={
            "producto_id": producto_id,
            "tipo": "TRANSFERENCIA",
            "ubicacion": "GONDOLA",
        },
    ).json()

    assert len(movs_dep) >= 1
    assert len(movs_gon) >= 1
    assert any(float(m["cantidad"]) < 0 for m in movs_dep)
    assert any(float(m["cantidad"]) > 0 for m in movs_gon)


def test_revertir_movimiento_inventario_restaurar_stock(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """POST /api/inventario/movimientos/{id}/revertir revierte stock y registra REVERSION."""
    crear = client.post("/api/productos", json={**producto_datos, "sku": "TEST-REV"})
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    # Estado inicial: stock GONDOLA = 0
    r_stock0 = client.get(
        f"/api/inventario/productos/{producto_id}/stock",
        params={"ubicacion": "GONDOLA"},
    )
    assert r_stock0.status_code == 200
    assert float(r_stock0.json()["cantidad"]) == 0.0

    # Generar un movimiento de entrada (COMPRA) con ingresar_stock
    r_ing = client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10", "ubicacion": "GONDOLA"},
    )
    assert r_ing.status_code == 200

    # Obtener el movimiento más reciente COMPRA (con limit=1)
    movs = client.get(
        "/api/inventario/movimientos",
        params={
            "producto_id": producto_id,
            "tipo": "COMPRA",
            "limite": 1,
        },
    ).json()
    assert len(movs) == 1
    mov = movs[0]
    cantidad_ingresada = float(mov["cantidad"])
    assert cantidad_ingresada > 0

    # Stock ahora debe ser 10
    r_stock1 = client.get(
        f"/api/inventario/productos/{producto_id}/stock",
        params={"ubicacion": "GONDOLA"},
    )
    assert float(r_stock1.json()["cantidad"]) == cantidad_ingresada

    # Revertir
    r_rev = client.post(
        f"/api/inventario/movimientos/{mov['id']}/revertir",
        json={"referencia": "Revert test"},
    )
    assert r_rev.status_code == 200
    data_rev = r_rev.json()
    assert data_rev["tipo"] == "REVERSION"
    assert float(data_rev["cantidad"]) == -cantidad_ingresada

    # Stock debe volver al inicial
    r_stock2 = client.get(
        f"/api/inventario/productos/{producto_id}/stock",
        params={"ubicacion": "GONDOLA"},
    )
    assert float(r_stock2.json()["cantidad"]) == 0.0

    # Debe existir el movimiento REVERSION en el histórico
    movs_rev = client.get(
        "/api/inventario/movimientos",
        params={
            "producto_id": producto_id,
            "tipo": "REVERSION",
            "limite": 5,
        },
    ).json()
    assert any(m["id"] == data_rev["id"] for m in movs_rev)


def test_revertir_movimiento_inventario_404(client: TestClient) -> None:
    """Revertir un movimiento inexistente devuelve 404."""
    r = client.post("/api/inventario/movimientos/999999/revertir", json={})
    assert r.status_code == 404


def test_conteo_manual_ajusta_disminucion_y_registra_movimiento_ajuste(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """POST /api/inventario/conteos/manual ajusta stock y crea movimiento tipo AJUSTE con diferencia negativa."""
    crear = client.post("/api/productos", json={**producto_datos, "sku": "TEST-CONT1"})
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10", "ubicacion": "GONDOLA"},
    )

    r = client.post(
        "/api/inventario/conteos/manual",
        json={
            "items": [
                {
                    "producto_id": producto_id,
                    "ubicacion": "GONDOLA",
                    "cantidad_contada": "7",
                }
            ],
            "referencia": "Conteo manual - disminución",
        },
    )
    assert r.status_code == 200, r.json()
    data = r.json()
    movs = data["movimientos"]
    assert len(movs) == 1
    assert movs[0]["tipo"] == "AJUSTE"
    assert float(movs[0]["cantidad"]) == -3.0

    st = client.get(
        f"/api/inventario/productos/{producto_id}/stock",
        params={"ubicacion": "GONDOLA"},
    )
    assert st.status_code == 200
    assert float(st.json()["cantidad"]) == 7.0


def test_conteo_manual_ajusta_aumento_y_registra_movimiento_ajuste(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """POST /api/inventario/conteos/manual ajusta stock y crea movimiento tipo AJUSTE con diferencia positiva."""
    crear = client.post("/api/productos", json={**producto_datos, "sku": "TEST-CONT2"})
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "2", "ubicacion": "GONDOLA"},
    )

    r = client.post(
        "/api/inventario/conteos/manual",
        json={
            "items": [
                {
                    "producto_id": producto_id,
                    "ubicacion": "GONDOLA",
                    "cantidad_contada": "5",
                }
            ]
        },
    )
    assert r.status_code == 200, r.json()
    data = r.json()
    movs = data["movimientos"]
    assert len(movs) == 1
    assert movs[0]["tipo"] == "AJUSTE"
    assert float(movs[0]["cantidad"]) == 3.0

    st = client.get(
        f"/api/inventario/productos/{producto_id}/stock",
        params={"ubicacion": "GONDOLA"},
    )
    assert st.status_code == 200
    assert float(st.json()["cantidad"]) == 5.0


def test_checklist_conteo_manual_incluye_stock_actual(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """GET /api/inventario/conteos/manual/checklist retorna productos con stock_actual y campos vacíos."""
    p1 = client.post("/api/productos", json={**producto_datos, "sku": "TEST-CHK1"})
    assert p1.status_code == 201
    producto_id1 = p1.json()["id"]

    p2 = client.post("/api/productos", json={**producto_datos, "sku": "TEST-CHK2", "nombre": "Producto 2"})
    assert p2.status_code == 201
    producto_id2 = p2.json()["id"]

    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id1, "cantidad": "3.25", "ubicacion": "GONDOLA"},
    )

    r = client.get("/api/inventario/conteos/manual/checklist", params={"ubicacion": "GONDOLA", "limite": 10})
    assert r.status_code == 200
    items = r.json()

    i1 = next(x for x in items if x["producto_id"] == producto_id1)
    i2 = next(x for x in items if x["producto_id"] == producto_id2)

    assert float(i1["stock_actual"]) == 3.25
    assert i1["cantidad_contada"] is None
    assert i1["verificado"] is False

    assert float(i2["stock_actual"]) == 0.0
    assert i2["cantidad_contada"] is None
    assert i2["verificado"] is False


def test_checklist_conteo_rotativo_filtra_por_dia_y_categoria(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """GET /api/inventario/conteos/rotativos/checklist usa mapeo día->categoría."""
    # Categorías requeridas por el mapeo base (BEB/LAC/ALM)
    r_beb = client.post(
        "/api/inventario/categorias",
        json={"codigo": "BEB", "nombre": "Bebidas"},
    )
    assert r_beb.status_code == 201
    beb_id = r_beb.json()["id"]

    r_lac = client.post(
        "/api/inventario/categorias",
        json={"codigo": "LAC", "nombre": "Lácteos"},
    )
    assert r_lac.status_code == 201
    lac_id = r_lac.json()["id"]

    r_alm = client.post(
        "/api/inventario/categorias",
        json={"codigo": "ALM", "nombre": "Almacén"},
    )
    assert r_alm.status_code == 201
    # alm_id no se usa explícitamente, pero asegura existencia del mapeo

    # Productos asignados a categorías distintas
    p1 = client.post("/api/productos", json={**producto_datos, "sku": "TEST-ROT1"})
    assert p1.status_code == 201
    prod1_id = p1.json()["id"]

    p2 = client.post(
        "/api/productos",
        json={**producto_datos, "sku": "TEST-ROT2", "nombre": "Producto rot 2"},
    )
    assert p2.status_code == 201
    prod2_id = p2.json()["id"]

    # Asignación de categorías (Bebidas y Lácteos)
    r1 = client.patch(
        f"/api/productos/{prod1_id}",
        json={"categoria_id": beb_id},
    )
    assert r1.status_code == 200

    r2 = client.patch(
        f"/api/productos/{prod2_id}",
        json={"categoria_id": lac_id},
    )
    assert r2.status_code == 200

    # Stock en GONDOLA
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": prod1_id, "cantidad": "3", "ubicacion": "GONDOLA"},
    )
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": prod2_id, "cantidad": "7", "ubicacion": "GONDOLA"},
    )

    # 2026-03-16 es lunes => Bebidas (BEB)
    r = client.get(
        "/api/inventario/conteos/rotativos/checklist",
        params={"fecha": "2026-03-16", "ubicacion": "GONDOLA", "limite": 100},
    )
    assert r.status_code == 200
    items = r.json()

    assert any(x["producto_id"] == prod1_id for x in items)
    assert not any(x["producto_id"] == prod2_id for x in items)

    i1 = next(x for x in items if x["producto_id"] == prod1_id)
    assert float(i1["stock_actual"]) == 3.0
    assert i1["cantidad_contada"] is None
    assert i1["verificado"] is False


def test_movimiento_manual_actualiza_stock_ajuste(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """POST /api/inventario/movimientos/manual actualiza stock con cantidad firmada."""
    crear = client.post("/api/productos", json={**producto_datos, "sku": "TEST-MAN1"})
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "5", "ubicacion": "GONDOLA"},
    )

    r_mov = client.post(
        "/api/inventario/movimientos/manual",
        json={
            "producto_id": producto_id,
            "tipo": "AJUSTE",
            "cantidad": "-2",
            "ubicacion": "GONDOLA",
            "referencia": "Ajuste manual -2",
        },
    )
    assert r_mov.status_code == 200, r_mov.json()
    data = r_mov.json()
    assert data["tipo"] == "AJUSTE"
    assert float(data["cantidad"]) == -2.0
    assert data["ubicacion"] == "GONDOLA"

    st = client.get(
        f"/api/inventario/productos/{producto_id}/stock",
        params={"ubicacion": "GONDOLA"},
    )
    assert st.status_code == 200
    assert float(st.json()["cantidad"]) == 3.0


def test_movimiento_manual_tipo_invalido_400(
    client: TestClient,
    producto_datos: dict,
) -> None:
    """Movimiento manual con tipo inválido devuelve 400."""
    crear = client.post("/api/productos", json={**producto_datos, "sku": "TEST-MAN2"})
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    r_mov = client.post(
        "/api/inventario/movimientos/manual",
        json={
            "producto_id": producto_id,
            "tipo": "TIPO_NO_EXISTE",
            "cantidad": "1",
            "ubicacion": "GONDOLA",
        },
    )
    assert r_mov.status_code == 400


def test_reposicion_automatica_transfiere_deposito_a_gondola(client: TestClient, producto_datos: dict) -> None:
    """POST /inventario/reposicion/ejecutar mueve stock DEPOSITO→GONDOLA si está habilitado."""
    # habilitar transferencias automáticas
    r_cfg = client.put("/api/configuracion/inventario", json={"transferencias_automaticas": True})
    assert r_cfg.status_code == 200

    # producto con mínimo 5; góndola 2; depósito 10 => transfiere 3
    p = client.post("/api/productos", json={**producto_datos, "sku": "TEST-REP", "stock_minimo": "5"})
    assert p.status_code == 201
    producto_id = p.json()["id"]

    client.post("/api/inventario/ingresar", json={"producto_id": producto_id, "cantidad": "2", "ubicacion": "GONDOLA"})
    client.post("/api/inventario/ingresar", json={"producto_id": producto_id, "cantidad": "10", "ubicacion": "DEPOSITO"})

    r = client.post("/api/inventario/reposicion/ejecutar")
    assert r.status_code == 200
    data = r.json()
    assert data["ejecutada"] is True
    assert any(x["producto_id"] == producto_id for x in data["transferencias"])

    st_g = float(client.get(f"/api/inventario/productos/{producto_id}/stock", params={"ubicacion": "GONDOLA"}).json()["cantidad"])
    st_d = float(client.get(f"/api/inventario/productos/{producto_id}/stock", params={"ubicacion": "DEPOSITO"}).json()["cantidad"])
    assert st_g == 5.0
    assert st_d == 7.0

    movs = client.get("/api/inventario/movimientos", params={"producto_id": producto_id, "tipo": "TRANSFERENCIA"}).json()
    assert any(m["ubicacion"] == "GONDOLA" and float(m["cantidad"]) == 3.0 for m in movs)
    assert any(m["ubicacion"] == "DEPOSITO" and float(m["cantidad"]) == -3.0 for m in movs)


def test_pedidos_automaticos_genera_solicitud_compra_si_no_alcanza_deposito(
    client: TestClient, producto_datos: dict
) -> None:
    """Si no alcanza depósito y pedidos_automaticos=true, genera solicitud de compra."""
    client.put(
        "/api/configuracion/inventario",
        json={"transferencias_automaticas": True, "pedidos_automaticos": True},
    )

    p = client.post(
        "/api/productos",
        json={**producto_datos, "sku": "TEST-PED", "stock_minimo": "5"},
    )
    producto_id = p.json()["id"]

    # góndola 0, depósito 1 => faltante 4 => solicitud
    client.post("/api/inventario/ingresar", json={"producto_id": producto_id, "cantidad": "1", "ubicacion": "DEPOSITO"})

    r = client.post("/api/inventario/reposicion/ejecutar")
    assert r.status_code == 200
    data = r.json()
    assert data["ejecutada"] is True
    assert any(x["producto_id"] == producto_id for x in data.get("pedidos", []))

    # consultar solicitudes
    r_list = client.get("/api/inventario/solicitudes-compra")
    assert r_list.status_code == 200
    assert len(r_list.json()) >= 1
    sol_id = r_list.json()[0]["id"]

    r_det = client.get(f"/api/inventario/solicitudes-compra/{sol_id}")
    assert r_det.status_code == 200
    sol = r_det.json()
    assert any(it["producto_id"] == producto_id and it["cantidad"] == 4.0 for it in sol["items"])


def test_convertir_solicitud_a_compra_marca_atendida_e_ingresa_stock(
    client: TestClient, producto_datos: dict, persona_datos: dict
) -> None:
    """POST solicitudes-compra/{id}/convertir-a-compra crea compra, ingresa stock y marca ATENDIDA."""
    # Config para generar solicitud
    client.put(
        "/api/configuracion/inventario",
        json={"transferencias_automaticas": True, "pedidos_automaticos": True},
    )

    # Crear proveedor (persona)
    prov = client.post("/api/personas", json=persona_datos)
    proveedor_id = prov.json()["id"]

    # Crear cuenta financiera para registrar gasto
    client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Compras", "tipo": "CAJA", "saldo_inicial": "0"},
    )

    # Crear producto con costo_actual
    prod = client.post(
        "/api/productos",
        json={**producto_datos, "sku": "TEST-CONV", "stock_minimo": "5", "costo_actual": "2.00"},
    )
    producto_id = prod.json()["id"]

    # Depósito 0 => faltante 5 => solicitud
    r = client.post("/api/inventario/reposicion/ejecutar")
    assert r.status_code == 200

    sol_list = client.get("/api/inventario/solicitudes-compra").json()
    assert len(sol_list) >= 1
    sol_id = sol_list[0]["id"]

    conv = client.post(
        f"/api/inventario/solicitudes-compra/{sol_id}/convertir-a-compra",
        json={"proveedor_id": proveedor_id},
    )
    assert conv.status_code == 201
    compra_id = conv.json()["compra"]["id"]

    # Solicitud marcada atendida
    sol_det = client.get(f"/api/inventario/solicitudes-compra/{sol_id}").json()
    assert sol_det["estado"] == "ATENDIDA"

    # Compra aparece en /api/compras
    compras = client.get("/api/compras").json()
    assert any(c["id"] == compra_id for c in compras)

    # Stock ingresado (góndola por defecto)
    st = float(client.get(f"/api/inventario/productos/{producto_id}/stock").json()["cantidad"])
    assert st == 5.0


# ---------------------------------------------------------------------------
# Tests: rotacion de stock (docs Modulo 5 ss11)
# ---------------------------------------------------------------------------

def test_rotacion_stock_sin_movimientos(client: TestClient, producto_datos: dict) -> None:
    """GET /rotacion sin movimientos devuelve lista vacia o sin_movimiento."""
    r = client.get("/api/inventario/rotacion?tipo_rotacion=alta")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_rotacion_stock_tipo_invalido(client: TestClient) -> None:
    """GET /rotacion con tipo invalido retorna 400."""
    r = client.get("/api/inventario/rotacion?tipo_rotacion=invalido_xyz")
    assert r.status_code == 400


def test_rotacion_stock_con_movimientos_alta(client: TestClient, producto_datos: dict) -> None:
    """GET /rotacion alta devuelve productos con mas movimientos primero."""
    prod = client.post("/api/productos", json={**producto_datos, "sku": "ROT-ALTA-01"})
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    # Generar varios movimientos
    client.post("/api/inventario/ingresar", json={"producto_id": prod_id, "cantidad": "10"})
    client.post("/api/inventario/ingresar", json={"producto_id": prod_id, "cantidad": "5"})
    r = client.get("/api/inventario/rotacion?tipo_rotacion=alta&limite=10")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "producto_id" in data[0]
        assert "cantidad_movimientos" in data[0]
        assert "clasificacion" in data[0]


def test_rotacion_stock_sin_movimiento(client: TestClient, producto_datos: dict) -> None:
    """GET /rotacion?tipo_rotacion=sin_movimiento devuelve productos sin movimientos."""
    prod = client.post("/api/productos", json={**producto_datos, "sku": "ROT-SIN-01"})
    assert prod.status_code == 201
    r = client.get("/api/inventario/rotacion?tipo_rotacion=sin_movimiento")
    assert r.status_code == 200
    data = r.json()
    ids = [item["producto_id"] for item in data]
    assert prod.json()["id"] in ids


# ---------------------------------------------------------------------------
# Tests: ranking de mermas (docs Modulo 5 ss11)
# ---------------------------------------------------------------------------

def test_ranking_mermas_sin_datos(client: TestClient) -> None:
    """GET /mermas/ranking sin mermas devuelve lista vacia."""
    r = client.get("/api/inventario/mermas/ranking")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_ranking_mermas_con_movimiento(client: TestClient, producto_datos: dict) -> None:
    """GET /mermas/ranking refleja mermas registradas."""
    prod = client.post("/api/productos", json={**producto_datos, "sku": "MERMA-01", "costo_actual": "5.00"})
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    # Ingresar stock primero
    client.post("/api/inventario/ingresar", json={"producto_id": prod_id, "cantidad": "20"})
    # Registrar merma
    client.post("/api/inventario/movimientos/manual", json={
        "producto_id": prod_id,
        "tipo": "MERMA",
        "cantidad": "-3",
        "ubicacion": "GONDOLA",
        "referencia": "Merma test"
    })
    r = client.get("/api/inventario/mermas/ranking")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert "total_merma" in data[0]
    assert "costo_estimado_merma" in data[0]


# ---------------------------------------------------------------------------
# Tests: lotes vencidos (docs Modulo 5 ss11)
# ---------------------------------------------------------------------------

def test_lotes_vencidos_sin_datos(client: TestClient) -> None:
    """GET /lotes/vencidos sin lotes vencidos devuelve lista vacia."""
    r = client.get("/api/inventario/lotes/vencidos")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_lotes_vencidos_con_lote_expirado(client: TestClient, producto_datos: dict) -> None:
    """GET /lotes/vencidos incluye lotes cuya fecha ya paso."""
    prod = client.post("/api/productos", json={**producto_datos, "sku": "VENC-01"})
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    # Crear lote con fecha pasada
    r_lote = client.post(
        f"/api/inventario/productos/{prod_id}/lotes",
        json={"cantidad": 5, "fecha_vencimiento": "2020-01-01"},
    )
    assert r_lote.status_code == 201
    r = client.get("/api/inventario/lotes/vencidos")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["dias_vencido"] > 0
    assert "nombre_producto" in data[0]


# ---------------------------------------------------------------------------
# Tests: lotes por producto (docs Modulo 5 ss11)
# ---------------------------------------------------------------------------

def test_lotes_por_producto_vacio(client: TestClient, producto_datos: dict) -> None:
    """GET /productos/{id}/lotes sin lotes devuelve lista vacia."""
    prod = client.post("/api/productos", json={**producto_datos, "sku": "LOTPROD-01"})
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    r = client.get(f"/api/inventario/productos/{prod_id}/lotes")
    assert r.status_code == 200
    assert r.json() == []


def test_lotes_por_producto_con_lotes(client: TestClient, producto_datos: dict) -> None:
    """GET /productos/{id}/lotes muestra todos los lotes del producto."""
    prod = client.post("/api/productos", json={**producto_datos, "sku": "LOTPROD-02"})
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    client.post(f"/api/inventario/productos/{prod_id}/lotes", json={"cantidad": 10, "fecha_vencimiento": "2030-12-31"})
    client.post(f"/api/inventario/productos/{prod_id}/lotes", json={"cantidad": 5, "fecha_vencimiento": "2020-06-15"})
    r = client.get(f"/api/inventario/productos/{prod_id}/lotes")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert "vencido" in data[0]
    assert "dias_para_vencer" in data[0]


def test_lotes_por_producto_solo_vigentes(client: TestClient, producto_datos: dict) -> None:
    """GET /productos/{id}/lotes?solo_vigentes=true filtra los ya vencidos."""
    prod = client.post("/api/productos", json={**producto_datos, "sku": "LOTPROD-03"})
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    client.post(f"/api/inventario/productos/{prod_id}/lotes", json={"cantidad": 10, "fecha_vencimiento": "2030-12-31"})
    client.post(f"/api/inventario/productos/{prod_id}/lotes", json={"cantidad": 5, "fecha_vencimiento": "2020-01-01"})
    r = client.get(f"/api/inventario/productos/{prod_id}/lotes?solo_vigentes=true")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["vencido"] is False


# ---------------------------------------------------------------------------
# Tests: historial por producto (docs Modulo 5 ss12)
# ---------------------------------------------------------------------------

def test_historial_producto_ok(client: TestClient, producto_datos: dict) -> None:
    """GET /productos/{id}/historial devuelve estructura completa."""
    prod = client.post("/api/productos", json={**producto_datos, "sku": "HIST-01"})
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    client.post("/api/inventario/ingresar", json={"producto_id": prod_id, "cantidad": "10"})
    r = client.get(f"/api/inventario/productos/{prod_id}/historial")
    assert r.status_code == 200
    data = r.json()
    assert "producto" in data
    assert "stock_por_ubicacion" in data
    assert "movimientos_recientes" in data
    assert "lotes" in data
    assert data["producto"]["id"] == prod_id


def test_historial_producto_404(client: TestClient) -> None:
    """GET /productos/{id}/historial con producto inexistente retorna 404."""
    r = client.get("/api/inventario/productos/999999/historial")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests: punto de reorden (docs Modulo 5 ss7)
# ---------------------------------------------------------------------------

def test_reorden_sin_productos_configurados(client: TestClient) -> None:
    """GET /reorden sin productos con punto_reorden devuelve lista vacia."""
    r = client.get("/api/inventario/reorden")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_reorden_detecta_producto_bajo_punto(client: TestClient, producto_datos: dict) -> None:
    """GET /reorden incluye producto cuyo stock esta por debajo del punto_reorden."""
    prod = client.post(
        "/api/productos",
        json={**producto_datos, "sku": "REORD-01", "punto_reorden": "10"},
    )
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    # Stock 0 < punto_reorden 10
    r = client.get("/api/inventario/reorden")
    assert r.status_code == 200
    data = r.json()
    ids = [item["producto_id"] for item in data]
    assert prod_id in ids


def test_reorden_excluye_producto_sobre_punto(client: TestClient, producto_datos: dict) -> None:
    """GET /reorden no incluye producto con stock >= punto_reorden."""
    prod = client.post(
        "/api/productos",
        json={**producto_datos, "sku": "REORD-02", "punto_reorden": "5"},
    )
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    # Ingresar stock sobre el punto_reorden
    client.post("/api/inventario/ingresar", json={"producto_id": prod_id, "cantidad": "20"})
    r = client.get("/api/inventario/reorden")
    assert r.status_code == 200
    ids = [item["producto_id"] for item in r.json()]
    assert prod_id not in ids


# ---------------------------------------------------------------------------
# Tests: valorizacion del inventario (docs Modulo 5 ss8)
# ---------------------------------------------------------------------------

def test_valorizacion_sin_stock(client: TestClient) -> None:
    """GET /valorizacion sin stock devuelve totales en 0."""
    r = client.get("/api/inventario/valorizacion")
    assert r.status_code == 200
    data = r.json()
    assert "total_valor_costo" in data
    assert "total_valor_venta" in data
    assert "margen_potencial" in data
    assert "detalle" in data


def test_valorizacion_con_stock_y_costo(client: TestClient, producto_datos: dict) -> None:
    """GET /valorizacion calcula correctamente valor_costo y valor_venta."""
    prod = client.post(
        "/api/productos",
        json={**producto_datos, "sku": "VALOR-01", "precio_venta": "100", "costo_actual": "60"},
    )
    assert prod.status_code == 201
    prod_id = prod.json()["id"]
    client.post("/api/inventario/ingresar", json={"producto_id": prod_id, "cantidad": "10"})
    r = client.get("/api/inventario/valorizacion")
    assert r.status_code == 200
    data = r.json()
    prod_val = next((p for p in data["detalle"] if p["producto_id"] == prod_id), None)
    assert prod_val is not None
    assert prod_val["valor_costo"] == 600.0
    assert prod_val["valor_venta"] == 1000.0


# ---------------------------------------------------------------------------
# Tests: DELETE /inventario/categorias/{id} — eliminar categoría
# ---------------------------------------------------------------------------

def test_eliminar_categoria_ok(client: TestClient) -> None:
    """Eliminar categoría sin productos ni subcategorías devuelve 204."""
    r = client.post("/api/inventario/categorias", json={"codigo": "DEL-CAT", "nombre": "Cat a eliminar"})
    assert r.status_code == 201
    cat_id = r.json()["id"]

    r = client.delete(f"/api/inventario/categorias/{cat_id}")
    assert r.status_code == 204

    # Ya no existe
    r2 = client.get(f"/api/inventario/categorias/{cat_id}")
    assert r2.status_code == 404


def test_eliminar_categoria_inexistente_404(client: TestClient) -> None:
    """Eliminar categoría que no existe devuelve 404."""
    r = client.delete("/api/inventario/categorias/999999")
    assert r.status_code == 404


def test_eliminar_categoria_con_productos_falla(client: TestClient, producto_datos: dict) -> None:
    """No se puede eliminar una categoría que tiene productos asociados."""
    # Crear categoría
    r_cat = client.post("/api/inventario/categorias", json={"codigo": "CAT-PROD", "nombre": "Categoría con productos"})
    cat_id = r_cat.json()["id"]

    # Crear producto en esa categoría
    client.post("/api/productos", json={
        **producto_datos,
        "sku": "PROD-CAT-DEL",
        "categoria_id": cat_id,
    })

    # Intento de eliminar debe fallar
    r = client.delete(f"/api/inventario/categorias/{cat_id}")
    assert r.status_code == 400
    assert "producto" in r.json()["detail"].lower()


def test_eliminar_categoria_con_subcategorias_falla(client: TestClient) -> None:
    """No se puede eliminar una categoría que tiene subcategorías."""
    r_padre = client.post("/api/inventario/categorias", json={"codigo": "CAT-PADRE", "nombre": "Padre"})
    padre_id = r_padre.json()["id"]

    client.post("/api/inventario/categorias", json={
        "codigo": "CAT-HIJO",
        "nombre": "Hijo",
        "categoria_padre_id": padre_id,
    })

    r = client.delete(f"/api/inventario/categorias/{padre_id}")
    assert r.status_code == 400
    assert "subcategor" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: POST /inventario/productos/importar — importación bulk
# ---------------------------------------------------------------------------

def test_importar_productos_crea_nuevos(client: TestClient) -> None:
    """Importar una lista de productos crea los nuevos y retorna contadores."""
    items = [
        {"sku": "IMP-001", "nombre": "Producto Importado A", "precio_venta": "100"},
        {"sku": "IMP-002", "nombre": "Producto Importado B", "precio_venta": "200", "costo_actual": "120"},
        {"sku": "IMP-003", "nombre": "Producto Importado C", "precio_venta": "300"},
    ]
    r = client.post("/api/inventario/productos/importar", json={"items": items})
    assert r.status_code == 201
    data = r.json()
    assert data["creados"] == 3
    assert data["actualizados"] == 0
    assert data["errores"] == []
    assert data["total_procesados"] == 3

    # Verificar que se crearon
    r2 = client.get("/api/productos/por-sku/IMP-001")
    assert r2.status_code == 200
    assert r2.json()["nombre"] == "Producto Importado A"


def test_importar_productos_actualiza_existentes(client: TestClient, producto_datos: dict) -> None:
    """Importar con actualizar_si_existe=true actualiza productos existentes."""
    client.post("/api/productos", json={**producto_datos, "sku": "IMP-UPDATE", "precio_venta": "50"})

    items = [{"sku": "IMP-UPDATE", "nombre": "Nombre Actualizado", "precio_venta": "75"}]
    r = client.post("/api/inventario/productos/importar", json={
        "items": items,
        "actualizar_si_existe": True,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["creados"] == 0
    assert data["actualizados"] == 1

    r2 = client.get("/api/productos/por-sku/IMP-UPDATE")
    assert float(r2.json()["precio_venta"]) == 75.0


def test_importar_productos_no_actualiza_si_desactivado(client: TestClient, producto_datos: dict) -> None:
    """Con actualizar_si_existe=false, SKUs existentes se registran como errores."""
    client.post("/api/productos", json={**producto_datos, "sku": "IMP-NOACT"})
    items = [{"sku": "IMP-NOACT", "nombre": "Intento", "precio_venta": "99"}]
    r = client.post("/api/inventario/productos/importar", json={
        "items": items,
        "actualizar_si_existe": False,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["creados"] == 0
    assert data["actualizados"] == 0
    assert len(data["errores"]) == 1
    assert "IMP-NOACT" in data["errores"][0]["sku"]


def test_importar_productos_con_errores_parciales(client: TestClient) -> None:
    """Items sin SKU o sin precio_venta generan error sin detener el resto."""
    items = [
        {"sku": "IMP-OK", "nombre": "OK", "precio_venta": "100"},
        {"nombre": "Sin SKU", "precio_venta": "100"},          # sin sku
        {"sku": "IMP-SIN-PRECIO", "nombre": "Sin precio"},     # sin precio_venta
    ]
    r = client.post("/api/inventario/productos/importar", json={"items": items})
    assert r.status_code == 201
    data = r.json()
    assert data["creados"] == 1
    assert len(data["errores"]) == 2


def test_importar_productos_lista_vacia_422(client: TestClient) -> None:
    """Importar lista vacía devuelve 422."""
    r = client.post("/api/inventario/productos/importar", json={"items": []})
    assert r.status_code == 422
