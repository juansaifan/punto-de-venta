"""Tests del API Finanzas."""
from fastapi.testclient import TestClient


def test_listar_cuentas_vacio(client: TestClient) -> None:
    """Listar cuentas sin datos devuelve lista vacía."""
    r = client.get("/api/finanzas/cuentas")
    assert r.status_code == 200
    assert r.json() == []


def test_obtener_cuenta_404(client: TestClient) -> None:
    """Obtener cuenta inexistente devuelve 404."""
    r = client.get("/api/finanzas/cuentas/99999")
    assert r.status_code == 404


def test_crear_cuenta_ok(client: TestClient) -> None:
    """Crear cuenta financiera devuelve 201 y la cuenta con saldo inicial."""
    payload = {"nombre": "Cuenta Caja", "tipo": "CAJA", "saldo_inicial": "150.50"}
    r = client.post("/api/finanzas/cuentas", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["nombre"] == "Cuenta Caja"
    assert data["tipo"] == "CAJA"
    assert data["saldo"] == 150.50


def test_listar_cuentas_incluye_creada(client: TestClient) -> None:
    """Después de crear una cuenta, listar la incluye."""
    payload = {"nombre": "Cuenta Banco", "tipo": "BANCO", "saldo_inicial": "0"}
    client.post("/api/finanzas/cuentas", json=payload)
    r = client.get("/api/finanzas/cuentas")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    nombres = [c["nombre"] for c in items]
    assert "Cuenta Banco" in nombres


def test_registrar_transaccion_ingreso_actualiza_saldo(client: TestClient) -> None:
    """Registrar un ingreso incrementa el saldo de la cuenta."""
    # Crear cuenta con saldo inicial 0
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Ingresos", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear.status_code == 201
    cuenta_id = crear.json()["id"]

    # Registrar ingreso de 100.50
    r_tx = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100.50", "descripcion": "Ingreso prueba"},
    )
    assert r_tx.status_code == 201
    tx = r_tx.json()
    assert tx["cuenta_id"] == cuenta_id
    assert tx["tipo"] == "ingreso"
    assert tx["monto"] == 100.50

    # Verificar saldo de la cuenta
    r_cuenta = client.get(f"/api/finanzas/cuentas/{cuenta_id}")
    assert r_cuenta.status_code == 200
    assert r_cuenta.json()["saldo"] == 100.50


def test_registrar_transaccion_gasto_actualiza_saldo(client: TestClient) -> None:
    """Registrar un gasto decrementa el saldo de la cuenta."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Gastos", "tipo": "CAJA", "saldo_inicial": "200"},
    )
    cuenta_id = crear.json()["id"]

    r_tx = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "50", "descripcion": "Gasto prueba"},
    )
    assert r_tx.status_code == 201

    r_cuenta = client.get(f"/api/finanzas/cuentas/{cuenta_id}")
    assert r_cuenta.status_code == 200
    assert r_cuenta.json()["saldo"] == 150.0


def test_registrar_transaccion_tipo_invalido_falla(client: TestClient) -> None:
    """Tipo distinto de ingreso/gasto devuelve 400."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Tipo Invalido", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]

    r_tx = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "otro", "monto": "10"},
    )
    assert r_tx.status_code == 400


def test_registrar_transaccion_cuenta_inexistente_404(client: TestClient) -> None:
    """Registrar transacción en cuenta inexistente devuelve 404."""
    r_tx = client.post(
        "/api/finanzas/cuentas/99999/transacciones",
        json={"tipo": "ingreso", "monto": "10"},
    )
    assert r_tx.status_code == 404


def test_listar_transacciones_por_cuenta_devuelve_registros(client: TestClient) -> None:
    """Listar transacciones de una cuenta devuelve las registradas."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Movimientos", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear.status_code == 201
    cuenta_id = crear.json()["id"]

    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100", "descripcion": "Ingreso 1"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "30", "descripcion": "Gasto 1"},
    )

    r = client.get(f"/api/finanzas/cuentas/{cuenta_id}/transacciones")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 2
    tipos = {t["tipo"] for t in datos}
    assert tipos == {"ingreso", "gasto"}


def test_listar_transacciones_filtrado_por_tipo(client: TestClient) -> None:
    """El filtro tipo=ingreso devuelve solo ingresos."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Filtro Tipo", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]

    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "50"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "20"},
    )

    r = client.get(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        params={"tipo": "ingreso"},
    )
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 1
    assert datos[0]["tipo"] == "ingreso"


def test_listar_transacciones_cuenta_inexistente_404(client: TestClient) -> None:
    """Listar transacciones de una cuenta inexistente devuelve 404."""
    r = client.get("/api/finanzas/cuentas/99999/transacciones")
    assert r.status_code == 404


def test_transacciones_global_csv_sin_datos_devuelve_solo_cabecera(client: TestClient) -> None:
    """GET /finanzas/transacciones?formato=csv sin datos devuelve solo cabecera CSV."""
    r = client.get("/api/finanzas/transacciones?formato=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert len(lineas) == 1
    assert (
        lineas[0]
        == "id,cuenta_id,nombre_cuenta,tipo,monto,fecha,descripcion,conciliada"
    )


def test_transacciones_global_csv_con_datos_devuelve_fila(client: TestClient) -> None:
    """GET /finanzas/transacciones?formato=csv con movimientos devuelve cabecera + filas."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Historial CSV", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear.status_code == 201
    cuenta_id = crear.json()["id"]
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "10", "descripcion": "Ingreso CSV"},
    )

    r = client.get("/api/finanzas/transacciones?formato=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert lineas[0] == "id,cuenta_id,nombre_cuenta,tipo,monto,fecha,descripcion,conciliada"
    assert len(lineas) >= 2


def test_ingresos_endpoint_filtra_solo_ingresos(client: TestClient) -> None:
    """GET /finanzas/ingresos devuelve solo transacciones tipo ingreso."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Ingresos", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "10"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "3"},
    )
    r = client.get("/api/finanzas/ingresos")
    assert r.status_code == 200
    datos = r.json()
    assert all(x["tipo"] == "ingreso" for x in datos)


def test_egresos_endpoint_filtra_solo_gastos(client: TestClient) -> None:
    """GET /finanzas/egresos devuelve solo transacciones tipo gasto."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Egresos", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "10"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "3"},
    )
    r = client.get("/api/finanzas/egresos")
    assert r.status_code == 200
    datos = r.json()
    assert all(x["tipo"] == "gasto" for x in datos)


def test_ingresos_csv_sin_datos_devuelve_solo_cabecera(client: TestClient) -> None:
    """GET /finanzas/ingresos?formato=csv sin datos devuelve solo cabecera CSV."""
    r = client.get("/api/finanzas/ingresos?formato=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert len(lineas) == 1
    assert lineas[0] == "id,cuenta_id,nombre_cuenta,tipo,monto,fecha,descripcion,conciliada"


def test_egresos_csv_sin_datos_devuelve_solo_cabecera(client: TestClient) -> None:
    """GET /finanzas/egresos?formato=csv sin datos devuelve solo cabecera CSV."""
    r = client.get("/api/finanzas/egresos?formato=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert len(lineas) == 1
    assert lineas[0] == "id,cuenta_id,nombre_cuenta,tipo,monto,fecha,descripcion,conciliada"


def test_margen_producto_finanzas_vacio(client: TestClient) -> None:
    """Rentabilidad margen-producto sin ventas devuelve lista vacía."""
    r = client.get(
        "/api/finanzas/rentabilidad/margen-producto?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_margen_producto_finanzas_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Rentabilidad margen-producto responde total_vendido y costos/márgenes."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    precio_venta = float(crear.json()["precio_venta"])
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
    venta = client.get(f"/api/ventas/{r_venta.json()['venta_id']}").json()
    fecha_venta = venta["creado_en"][:10]

    r = client.get(
        f"/api/finanzas/rentabilidad/margen-producto?fecha_desde={fecha_venta}&fecha_hasta={fecha_venta}"
    )
    assert r.status_code == 200
    items = r.json()
    fila = next((x for x in items if x["producto_id"] == producto_id), None)
    assert fila is not None
    total_esperado = 2 * precio_venta
    assert fila["total_vendido"] == total_esperado
    # producto_datos no envía costo_actual, por defecto 0
    assert fila["total_costo"] == 0.0
    assert fila["margen_bruto"] == total_esperado
    assert fila["margen_pct"] == 100.0


def test_margen_producto_finanzas_orden_invalido_400(client: TestClient) -> None:
    """Rentabilidad margen-producto con orden_por inválido devuelve 400."""
    r = client.get(
        "/api/finanzas/rentabilidad/margen-producto?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&orden_por=invalid"
    )
    assert r.status_code == 400


def test_margen_categoria_finanzas_vacio(client: TestClient) -> None:
    """Rentabilidad margen-categoria sin ventas devuelve lista vacía."""
    r = client.get(
        "/api/finanzas/rentabilidad/margen-categoria?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
    )
    assert r.status_code == 200
    assert r.json() == []


def test_margen_categoria_finanzas_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """Rentabilidad margen-categoria responde total_vendido y margen."""
    from tests.test_ventas import _ingresar_stock

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    precio_venta = float(crear.json()["precio_venta"])
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
    venta = client.get(f"/api/ventas/{r_venta.json()['venta_id']}").json()
    fecha_venta = venta["creado_en"][:10]

    r = client.get(
        f"/api/finanzas/rentabilidad/margen-categoria?fecha_desde={fecha_venta}&fecha_hasta={fecha_venta}"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    fila = items[0]
    assert "categoria_id" in fila
    assert "categoria_nombre" in fila
    assert fila["total_vendido"] == 2 * precio_venta
    assert fila["total_costo"] == 0.0
    assert fila["margen_bruto"] == 2 * precio_venta
    assert fila["margen_pct"] == 100.0


def test_resumen_cuenta_sin_movimientos(client: TestClient) -> None:
    """El resumen de una cuenta sin movimientos refleja solo el saldo inicial."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Resumen", "tipo": "CAJA", "saldo_inicial": "200"},
    )
    assert crear.status_code == 201
    cuenta = crear.json()
    cuenta_id = cuenta["id"]

    r = client.get(f"/api/finanzas/cuentas/{cuenta_id}/resumen")
    assert r.status_code == 200
    data = r.json()
    assert data["cuenta_id"] == cuenta_id
    assert data["saldo_actual"] == 200.0
    assert data["total_ingresos"] == 0.0
    assert data["total_gastos"] == 0.0
    assert data["balance_movimientos"] == 0.0


def test_resumen_cuenta_con_ingresos_y_gastos(client: TestClient) -> None:
    """El resumen de cuenta muestra correctamente ingresos, gastos y balance."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Resumen Movimientos", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]

    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100", "descripcion": "Ingreso A"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "50", "descripcion": "Ingreso B"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "30", "descripcion": "Gasto A"},
    )

    r = client.get(f"/api/finanzas/cuentas/{cuenta_id}/resumen")
    assert r.status_code == 200
    data = r.json()
    assert data["cuenta_id"] == cuenta_id
    assert data["saldo_actual"] == 120.0  # 100 + 50 - 30
    assert data["total_ingresos"] == 150.0
    assert data["total_gastos"] == 30.0
    assert data["balance_movimientos"] == 120.0


def test_resumen_cuenta_inexistente_404(client: TestClient) -> None:
    """El resumen de una cuenta inexistente devuelve 404."""
    r = client.get("/api/finanzas/cuentas/99999/resumen")
    assert r.status_code == 404


def test_evolucion_saldo_cuenta_devuelve_puntos_ordenados(client: TestClient) -> None:
    """La evolución de saldo devuelve puntos ordenados con saldo acumulado."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Evolución", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]

    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100", "descripcion": "Ingreso 1"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "40", "descripcion": "Gasto 1"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "10", "descripcion": "Ingreso 2"},
    )

    r = client.get(f"/api/finanzas/cuentas/{cuenta_id}/evolucion-saldo")
    assert r.status_code == 200
    puntos = r.json()
    assert len(puntos) == 3
    # Verificar orden cronológico por fecha (no estricta, pero creciente)
    fechas = [p["fecha"] for p in puntos]
    assert fechas == sorted(fechas)
    # Verificar saldo acumulado
    saldos = [p["saldo_despues"] for p in puntos]
    assert saldos == [100.0, 60.0, 70.0]


def test_evolucion_saldo_cuenta_inexistente_404(client: TestClient) -> None:
    """La evolución de saldo de una cuenta inexistente devuelve 404."""
    r = client.get("/api/finanzas/cuentas/99999/evolucion-saldo")
    assert r.status_code == 404


def test_registrar_ingreso_emite_evento_IngresoRegistrado(client: TestClient) -> None:
    """Al registrar un ingreso se emite el evento IngresoRegistrado (EVENTOS.md)."""
    from backend.events import subscribe, clear_handlers

    recibidos: list[dict] = []

    def handler(payload: dict) -> None:
        recibidos.append(payload)

    subscribe("IngresoRegistrado", handler)
    try:
        crear = client.post(
            "/api/finanzas/cuentas",
            json={"nombre": "Cuenta Evento", "tipo": "CAJA", "saldo_inicial": "0"},
        )
        assert crear.status_code == 201
        cuenta_id = crear.json()["id"]
        r_tx = client.post(
            f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
            json={"tipo": "ingreso", "monto": "75.25", "descripcion": "Ingreso evento"},
        )
        assert r_tx.status_code == 201
        tx = r_tx.json()
        assert len(recibidos) == 1
        payload = recibidos[0]
        assert payload["transaccion_id"] == tx["id"]
        assert payload["cuenta_id"] == cuenta_id
        assert payload["tipo"] == "ingreso"
        assert payload["monto"] == 75.25
        assert payload["descripcion"] == "Ingreso evento"
        assert "fecha" in payload
    finally:
        clear_handlers("IngresoRegistrado")


def test_registrar_gasto_emite_evento_GastoRegistrado(client: TestClient) -> None:
    """Al registrar un gasto se emite el evento GastoRegistrado (EVENTOS.md)."""
    from backend.events import subscribe, clear_handlers

    recibidos: list[dict] = []

    def handler(payload: dict) -> None:
        recibidos.append(payload)

    subscribe("GastoRegistrado", handler)
    try:
        crear = client.post(
            "/api/finanzas/cuentas",
            json={"nombre": "Cuenta Gasto Evento", "tipo": "CAJA", "saldo_inicial": "100"},
        )
        assert crear.status_code == 201
        cuenta_id = crear.json()["id"]
        r_tx = client.post(
            f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
            json={"tipo": "gasto", "monto": "25", "descripcion": "Gasto evento"},
        )
        assert r_tx.status_code == 201
        tx = r_tx.json()
        assert len(recibidos) == 1
        payload = recibidos[0]
        assert payload["transaccion_id"] == tx["id"]
        assert payload["cuenta_id"] == cuenta_id
        assert payload["tipo"] == "gasto"
        assert payload["monto"] == 25.0
        assert payload["descripcion"] == "Gasto evento"
        assert "fecha" in payload
    finally:
        clear_handlers("GastoRegistrado")


def test_conciliar_transaccion_ok(client: TestClient) -> None:
    """Marcar una transacción como conciliada actualiza conciliada y fecha_conciliacion."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Conciliar", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear.status_code == 201
    cuenta_id = crear.json()["id"]
    tx_post = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100", "descripcion": "Ingreso a conciliar"},
    )
    assert tx_post.status_code == 201
    transaccion_id = tx_post.json()["id"]

    r = client.patch(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones/{transaccion_id}/conciliar",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["conciliada"] is True
    assert data["fecha_conciliacion"] is not None

    r_list = client.get(f"/api/finanzas/cuentas/{cuenta_id}/transacciones")
    assert r_list.status_code == 200
    items = [t for t in r_list.json() if t["id"] == transaccion_id]
    assert len(items) == 1
    assert items[0]["conciliada"] is True
    assert items[0]["fecha_conciliacion"] is not None


def test_desconciliar_transaccion_ok(client: TestClient) -> None:
    """Desmarcar conciliación deja conciliada en False y fecha_conciliacion en null."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Desconciliar", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]
    tx_post = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "50", "descripcion": "Gasto"},
    )
    transaccion_id = tx_post.json()["id"]
    client.patch(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones/{transaccion_id}/conciliar",
    )

    r = client.patch(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones/{transaccion_id}/desconciliar",
    )
    assert r.status_code == 200
    assert r.json()["conciliada"] is False
    assert r.json()["fecha_conciliacion"] is None


def test_listar_transacciones_filtro_conciliada(client: TestClient) -> None:
    """El filtro conciliada=true/false devuelve solo las transacciones en ese estado."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Filtro Conc", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]
    tx1 = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "10"},
    )
    tx2 = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "20"},
    )
    transaccion_id_1 = tx1.json()["id"]
    client.patch(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones/{transaccion_id_1}/conciliar",
    )

    r_conc = client.get(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        params={"conciliada": "true"},
    )
    assert r_conc.status_code == 200
    datos_conc = r_conc.json()
    assert len(datos_conc) == 1
    assert datos_conc[0]["id"] == transaccion_id_1
    assert datos_conc[0]["conciliada"] is True

    r_sin = client.get(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        params={"conciliada": "false"},
    )
    assert r_sin.status_code == 200
    datos_sin = r_sin.json()
    assert len(datos_sin) == 1
    assert datos_sin[0]["id"] == tx2.json()["id"]
    assert datos_sin[0]["conciliada"] is False


def test_conciliar_transaccion_inexistente_404(client: TestClient) -> None:
    """Conciliar una transacción inexistente devuelve 404."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta 404", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]
    r = client.patch(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones/99999/conciliar",
    )
    assert r.status_code == 404


def test_conciliar_transaccion_otra_cuenta_404(client: TestClient) -> None:
    """Conciliar una transacción indicando otra cuenta devuelve 404."""
    c1 = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta A", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    c2 = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta B", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id_a = c1.json()["id"]
    cuenta_id_b = c2.json()["id"]
    tx_b = client.post(
        f"/api/finanzas/cuentas/{cuenta_id_b}/transacciones",
        json={"tipo": "ingreso", "monto": "5"},
    )
    transaccion_id_b = tx_b.json()["id"]

    r = client.patch(
        f"/api/finanzas/cuentas/{cuenta_id_a}/transacciones/{transaccion_id_b}/conciliar",
    )
    assert r.status_code == 404


def test_resumen_global_sin_cuentas(client: TestClient) -> None:
    """GET resumen-global sin cuentas devuelve saldo_total 0 y cantidad_cuentas 0."""
    r = client.get("/api/finanzas/resumen-global")
    assert r.status_code == 200
    data = r.json()
    assert data["saldo_total"] == 0.0
    assert data["total_ingresos"] == 0.0
    assert data["total_gastos"] == 0.0
    assert data["cantidad_cuentas"] == 0
    assert data["desde"] is None
    assert data["hasta"] is None


def test_resumen_global_con_cuentas(client: TestClient) -> None:
    """GET resumen-global con cuentas devuelve saldo_total y cantidad_cuentas."""
    client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "C1", "tipo": "CAJA", "saldo_inicial": "100"},
    )
    client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "C2", "tipo": "BANCO", "saldo_inicial": "50.50"},
    )
    r = client.get("/api/finanzas/resumen-global")
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad_cuentas"] == 2
    assert data["saldo_total"] == 150.50
    assert data["total_ingresos"] == 0.0
    assert data["total_gastos"] == 0.0


def test_resumen_global_con_rango_incluye_transacciones(client: TestClient) -> None:
    """GET resumen-global con desde/hasta incluye total_ingresos y total_gastos del rango."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Rango", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    cuenta_id = crear.json()["id"]
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "200", "descripcion": "Ingreso"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "30", "descripcion": "Gasto"},
    )
    # Sin params: total_ingresos/total_gastos son 0 (no se filtra por rango)
    r = client.get("/api/finanzas/resumen-global")
    assert r.status_code == 200
    assert r.json()["saldo_total"] == 170.0
    assert r.json()["total_ingresos"] == 0.0
    assert r.json()["total_gastos"] == 0.0
    # Con rango amplio (desde/hasta) debe sumar las transacciones
    r2 = client.get(
        "/api/finanzas/resumen-global?desde=2000-01-01T00:00:00&hasta=2030-12-31T23:59:59"
    )
    assert r2.status_code == 200
    assert r2.json()["total_ingresos"] == 200.0
    assert r2.json()["total_gastos"] == 30.0


def test_listar_transacciones_global_vacio(client: TestClient) -> None:
    """GET /finanzas/transacciones sin datos devuelve lista vacía."""
    r = client.get("/api/finanzas/transacciones")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_transacciones_global_incluye_todas_las_cuentas(client: TestClient) -> None:
    """GET /finanzas/transacciones devuelve transacciones de todas las cuentas con nombre_cuenta."""
    c1 = client.post("/api/finanzas/cuentas", json={"nombre": "Caja", "tipo": "CAJA", "saldo_inicial": "0"})
    c2 = client.post("/api/finanzas/cuentas", json={"nombre": "Banco", "tipo": "BANCO", "saldo_inicial": "0"})
    id1, id2 = c1.json()["id"], c2.json()["id"]
    client.post(f"/api/finanzas/cuentas/{id1}/transacciones", json={"tipo": "ingreso", "monto": "100"})
    client.post(f"/api/finanzas/cuentas/{id2}/transacciones", json={"tipo": "gasto", "monto": "25"})
    r = client.get("/api/finanzas/transacciones")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    nombres = {x["nombre_cuenta"] for x in data}
    assert "Caja" in nombres
    assert "Banco" in nombres
    montos = {x["monto"] for x in data}
    assert 100.0 in montos
    assert 25.0 in montos
    for x in data:
        assert "id" in x and "cuenta_id" in x and "tipo" in x and "fecha" in x and "conciliada" in x


def test_listar_transacciones_global_filtro_tipo(client: TestClient) -> None:
    """GET /finanzas/transacciones?tipo=ingreso devuelve solo ingresos."""
    c = client.post("/api/finanzas/cuentas", json={"nombre": "F", "tipo": "CAJA", "saldo_inicial": "0"})
    cid = c.json()["id"]
    client.post(f"/api/finanzas/cuentas/{cid}/transacciones", json={"tipo": "ingreso", "monto": "50"})
    client.post(f"/api/finanzas/cuentas/{cid}/transacciones", json={"tipo": "gasto", "monto": "10"})
    r = client.get("/api/finanzas/transacciones?tipo=ingreso")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["tipo"] == "ingreso"
    assert data[0]["monto"] == 50.0


def test_listar_transacciones_global_filtro_cuenta_id(client: TestClient) -> None:
    """GET /finanzas/transacciones?cuenta_id=X devuelve solo transacciones de esa cuenta."""
    c1 = client.post("/api/finanzas/cuentas", json={"nombre": "A", "tipo": "CAJA", "saldo_inicial": "0"})
    c2 = client.post("/api/finanzas/cuentas", json={"nombre": "B", "tipo": "CAJA", "saldo_inicial": "0"})
    id1, id2 = c1.json()["id"], c2.json()["id"]
    client.post(f"/api/finanzas/cuentas/{id1}/transacciones", json={"tipo": "ingreso", "monto": "1"})
    client.post(f"/api/finanzas/cuentas/{id2}/transacciones", json={"tipo": "ingreso", "monto": "2"})
    r = client.get(f"/api/finanzas/transacciones?cuenta_id={id2}")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["cuenta_id"] == id2
    assert data[0]["monto"] == 2.0


def test_listar_transacciones_global_tipo_invalido_400(client: TestClient) -> None:
    """GET /finanzas/transacciones?tipo=invalido devuelve 400."""
    r = client.get("/api/finanzas/transacciones?tipo=invalido")
    assert r.status_code == 400


def test_flujo_caja_sin_transacciones_devuelve_lista_vacia(client: TestClient) -> None:
    """GET /finanzas/flujo-caja sin transacciones devuelve lista vacía."""
    r = client.get("/api/finanzas/flujo-caja")
    assert r.status_code == 200
    assert r.json() == []


def test_flujo_caja_con_ingresos_y_egresos_por_dia(client: TestClient) -> None:
    """
    El flujo de caja agrupa por día e incluye ingresos, egresos, saldo_dia y saldo_acumulado.
    """
    # Crear cuenta y registrar movimientos en el mismo día
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Flujo", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear.status_code == 201
    cuenta_id = crear.json()["id"]

    # Dos ingresos y un gasto
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100", "descripcion": "Ingreso 1"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "50", "descripcion": "Ingreso 2"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "30", "descripcion": "Gasto 1"},
    )

    r = client.get("/api/finanzas/flujo-caja")
    assert r.status_code == 200
    datos = r.json()
    # Todos los movimientos son del mismo día → un único registro en el flujo
    assert len(datos) == 1
    fila = datos[0]
    assert "fecha" in fila
    assert fila["ingresos"] == 150.0
    assert fila["egresos"] == 30.0
    assert fila["saldo_dia"] == 120.0
    assert fila["saldo_acumulado"] == 120.0


def test_balances_mensuales_sin_transacciones_devuelve_lista_vacia(client: TestClient) -> None:
    """GET /finanzas/balances-mensuales sin transacciones devuelve lista vacía."""
    r = client.get("/api/finanzas/balances-mensuales")
    assert r.status_code == 200
    assert r.json() == []


def test_balances_mensuales_agrupan_por_mes_con_resultado_neto(client: TestClient) -> None:
    """
    Los balances mensuales agrupan ingresos y egresos por periodo YYYY-MM y calculan resultado_neto.
    """
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Balances", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear.status_code == 201
    cuenta_id = crear.json()["id"]

    # Registramos algunos movimientos (la fecha real será la actual; todos caen en el mismo mes)
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "50"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "30"},
    )

    r = client.get("/api/finanzas/balances-mensuales")
    assert r.status_code == 200
    data = r.json()
    # Todas las transacciones del mismo mes → un solo periodo
    assert len(data) == 1
    bal = data[0]
    assert "periodo" in bal
    assert bal["ingresos"] == 150.0
    assert bal["egresos"] == 30.0
    assert bal["resultado_neto"] == 120.0


def test_balances_mensuales_csv_sin_transacciones_devuelve_solo_cabecera(client: TestClient) -> None:
    """GET /finanzas/balances-mensuales?formato=csv sin transacciones devuelve solo la cabecera CSV."""
    r = client.get("/api/finanzas/balances-mensuales?formato=csv")
    assert r.status_code == 200
    body = r.text.strip().splitlines()
    # Solo cabecera sin filas de datos
    assert len(body) == 1
    assert body[0] == "periodo,ingresos,egresos,resultado_neto"


def test_balances_mensuales_csv_con_datos_tiene_fila(client: TestClient) -> None:
    """GET /finanzas/balances-mensuales?formato=csv con movimientos devuelve cabecera + al menos una fila."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Balances CSV", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear.status_code == 201
    cuenta_id = crear.json()["id"]

    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100"},
    )

    r = client.get("/api/finanzas/balances-mensuales?formato=csv")
    assert r.status_code == 200
    body = r.text.strip().splitlines()
    # Cabecera + al menos una fila
    assert len(body) >= 2
    assert body[0] == "periodo,ingresos,egresos,resultado_neto"


def test_indicadores_financieros_sin_movimientos_devuelve_ceros(client: TestClient) -> None:
    """GET /finanzas/indicadores sin datos devuelve totales en 0."""
    r = client.get("/api/finanzas/indicadores")
    assert r.status_code == 200
    data = r.json()
    assert data["total_ingresos"] == 0.0
    assert data["total_gastos"] == 0.0
    assert data["resultado_neto"] == 0.0
    assert data["cantidad_movimientos"] == 0


def test_indicadores_financieros_con_movimientos_calcula_resultado_y_promedio(client: TestClient) -> None:
    """Los indicadores financieros reflejan totales y promedio_diario coherentes."""
    crear = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Indicadores", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear.status_code == 201
    cuenta_id = crear.json()["id"]

    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "100"},
    )
    client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "40"},
    )

    r = client.get("/api/finanzas/indicadores?periodo=dia")
    assert r.status_code == 200
    data = r.json()
    assert data["total_ingresos"] == 100.0
    assert data["total_gastos"] == 40.0
    assert data["resultado_neto"] == 60.0
    # periodo=dia con rango por defecto → un solo día
    assert data["dias"] >= 1
    # Para un solo día, promedio_diario debe coincidir con resultado_neto
    if data["dias"] == 1:
        assert data["promedio_diario"] == 60.0
    assert data["cantidad_movimientos"] == 2


def test_indicadores_financieros_periodo_invalido_400(client: TestClient) -> None:
    """Periodo inválido en /finanzas/indicadores devuelve 400."""
    r = client.get("/api/finanzas/indicadores?periodo=anio")
    assert r.status_code == 400


def test_registrar_pago_cliente_crea_ingreso_y_movimiento_cuenta_corriente(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """
    POST /finanzas/pagos-cliente:
    - crea un ingreso en la cuenta financiera indicada
    - registra un movimiento PAGO en la cuenta corriente del cliente.
    """
    # Crear cuenta financiera
    crear_cuenta = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Cobros Clientes", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert crear_cuenta.status_code == 201
    cuenta_id = crear_cuenta.json()["id"]

    # Crear persona y rol cliente asociado
    crear_persona = client.post("/api/personas", json=persona_datos)
    assert crear_persona.status_code == 201
    persona_id = crear_persona.json()["id"]

    crear_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "CUENTA_CORRIENTE",
            "limite_credito": 1000.0,
        },
    )
    assert crear_cliente.status_code == 201
    cliente_id = crear_cliente.json()["id"]

    # Registrar pago de cliente
    r_pago = client.post(
        "/api/finanzas/pagos-cliente",
        json={
            "cuenta_id": cuenta_id,
            "cliente_id": cliente_id,
            "monto": "150.75",
            "descripcion": "Pago de prueba",
        },
    )
    assert r_pago.status_code == 201
    data = r_pago.json()
    assert data["cuenta_id"] == cuenta_id
    assert data["cliente_id"] == cliente_id
    assert data["monto"] == 150.75

    # La cuenta financiera debe reflejar el ingreso
    r_cuenta = client.get(f"/api/finanzas/cuentas/{cuenta_id}")
    assert r_cuenta.status_code == 200
    assert r_cuenta.json()["saldo"] == 150.75

    # La cuenta corriente del cliente debe registrar un PAGO (saldo negativo, ya que representa deuda)
    r_resumen = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen",
    )
    assert r_resumen.status_code == 200
    resumen = r_resumen.json()
    assert resumen["cliente_id"] == cliente_id
    # El pago disminuye la deuda; si solo hay un pago sin ventas, saldo debe ser <= 0
    assert float(resumen["saldo"]) <= 0.0

# ---------------------------------------------------------------------------
# Tests - nuevas funciones Modulo 4 (Finanzas) - brechas funcionales
# ---------------------------------------------------------------------------


def _crear_cuenta_con_tx(client, nombre="Cuenta Test", monto_ing=200, monto_gas=80):
    r_c = client.post("/api/finanzas/cuentas", json={"nombre": nombre, "tipo": "GENERAL", "saldo_inicial": "0"})
    cid = r_c.json()["id"]
    client.post(f"/api/finanzas/cuentas/{cid}/transacciones", json={"tipo": "ingreso", "monto": str(monto_ing), "descripcion": "Test ingreso"})
    client.post(f"/api/finanzas/cuentas/{cid}/transacciones", json={"tipo": "gasto", "monto": str(monto_gas), "descripcion": "Test gasto"})
    return cid


def test_balances_diarios_sin_datos(client) -> None:
    r = client.get("/api/finanzas/balances-diarios")
    assert r.status_code == 200
    assert r.json() == []


def test_balances_diarios_csv_sin_datos(client) -> None:
    r = client.get("/api/finanzas/balances-diarios?formato=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert lineas[0] == "periodo,ingresos,egresos,resultado_neto"
    assert len(lineas) == 1


def test_balances_diarios_con_transacciones(client) -> None:
    _crear_cuenta_con_tx(client, "CuentaDiaria")
    r = client.get("/api/finanzas/balances-diarios")
    assert r.status_code == 200
    filas = r.json()
    assert len(filas) >= 1
    f = filas[0]
    assert "periodo" in f
    assert "ingresos" in f
    assert "egresos" in f
    assert "resultado_neto" in f
    assert f["ingresos"] >= 200.0
    assert f["egresos"] >= 80.0
    assert abs(f["resultado_neto"] - (f["ingresos"] - f["egresos"])) < 0.01


def test_balances_anuales_sin_datos(client) -> None:
    r = client.get("/api/finanzas/balances-anuales")
    assert r.status_code == 200
    assert r.json() == []


def test_balances_anuales_csv_sin_datos(client) -> None:
    r = client.get("/api/finanzas/balances-anuales?formato=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert lineas[0] == "periodo,ingresos,egresos,resultado_neto"


def test_balances_anuales_con_transacciones(client) -> None:
    _crear_cuenta_con_tx(client, "CuentaAnual")
    r = client.get("/api/finanzas/balances-anuales")
    assert r.status_code == 200
    filas = r.json()
    assert len(filas) >= 1
    f = filas[0]
    assert len(f["periodo"]) == 4  # "YYYY"
    assert f["ingresos"] >= 200.0


def test_flujo_caja_agrupado_sin_datos(client) -> None:
    r = client.get("/api/finanzas/flujo-caja-agrupado?agrupacion=dia")
    assert r.status_code == 200
    assert r.json() == []


def test_flujo_caja_agrupado_agrupacion_invalida(client) -> None:
    r = client.get("/api/finanzas/flujo-caja-agrupado?agrupacion=hora")
    assert r.status_code == 400


def test_flujo_caja_agrupado_csv_sin_datos(client) -> None:
    r = client.get("/api/finanzas/flujo-caja-agrupado?agrupacion=mes&formato=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert lineas[0] == "periodo,ingresos,egresos,saldo_dia,saldo_acumulado"


def test_flujo_caja_agrupado_con_transacciones(client) -> None:
    _crear_cuenta_con_tx(client, "CuentaFlujo")
    r = client.get("/api/finanzas/flujo-caja-agrupado?agrupacion=dia")
    assert r.status_code == 200
    filas = r.json()
    assert len(filas) >= 1
    f = filas[0]
    assert "saldo_dia" in f
    assert "saldo_acumulado" in f
    assert abs(f["saldo_dia"] - (f["ingresos"] - f["egresos"])) < 0.01


def test_flujo_caja_agrupado_semana(client) -> None:
    _crear_cuenta_con_tx(client, "CuentaSemana")
    r = client.get("/api/finanzas/flujo-caja-agrupado?agrupacion=semana")
    assert r.status_code == 200
    filas = r.json()
    assert len(filas) >= 1
    assert "W" in filas[0]["periodo"]


def test_rentabilidad_periodo_sin_ventas(client) -> None:
    r = client.get("/api/finanzas/rentabilidad/periodo?fecha_desde=2026-01-01&fecha_hasta=2026-01-31")
    assert r.status_code == 200
    data = r.json()
    assert "resumen" in data
    assert data["resumen"]["total_ventas"] == 0.0
    assert data["filas"] == []


def test_rentabilidad_periodo_csv_sin_ventas(client) -> None:
    r = client.get("/api/finanzas/rentabilidad/periodo?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&formato=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.text.strip().splitlines()
    assert lineas[0] == "periodo,total_ventas,total_costo,gastos_operativos,margen_bruto,margen_bruto_pct,margen_neto,margen_neto_pct"


def test_rentabilidad_periodo_agrupacion_invalida(client) -> None:
    r = client.get("/api/finanzas/rentabilidad/periodo?fecha_desde=2026-01-01&fecha_hasta=2026-01-31&agrupacion=semana")
    assert r.status_code == 400


def test_rentabilidad_periodo_con_ventas(client, producto_datos) -> None:
    from tests.test_ventas import _ingresar_stock
    r_prod = client.post("/api/productos", json=producto_datos)
    pid = r_prod.json()["id"]
    _ingresar_stock(client, pid, 10)
    r_venta = client.post("/api/ventas", json={"items": [{"producto_id": pid, "cantidad": "2"}], "descuento": "0", "metodo_pago": "EFECTIVO"})
    assert r_venta.status_code == 200
    from datetime import datetime, timezone
    hoy = datetime.now(timezone.utc).date().isoformat()
    r = client.get(f"/api/finanzas/rentabilidad/periodo?fecha_desde={hoy}&fecha_hasta={hoy}")
    assert r.status_code == 200
    data = r.json()
    assert data["resumen"]["total_ventas"] > 0
    assert len(data["filas"]) >= 1
    assert "margen_bruto" in data["filas"][0]
    assert "margen_neto" in data["filas"][0]


def test_indicadores_avanzados_sin_datos(client) -> None:
    r = client.get("/api/finanzas/indicadores-avanzados")
    assert r.status_code == 200
    data = r.json()
    assert "saldo_total_cuentas" in data
    assert "liquidez" in data
    assert "margen_ganancia_pct" in data
    assert "ticket_promedio" in data
    assert data["total_ingresos"] == 0.0
    assert data["total_gastos"] == 0.0


def test_indicadores_avanzados_con_transacciones(client) -> None:
    _crear_cuenta_con_tx(client, "CuentaIndicadores", monto_ing=500, monto_gas=200)
    r = client.get("/api/finanzas/indicadores-avanzados")
    assert r.status_code == 200
    data = r.json()
    assert data["total_ingresos"] >= 500.0
    assert data["total_gastos"] >= 200.0
    assert data["resultado_neto"] >= 300.0
    assert data["margen_ganancia_pct"] > 0.0
    assert data["liquidez"] is not None


# ---------------------------------------------------------------------------
# Tendencias financieras (docs §12)
# ---------------------------------------------------------------------------

def test_tendencias_sin_datos_devuelve_lista_vacia(client) -> None:
    """Sin transacciones la lista de filas está vacía."""
    r = client.get("/api/finanzas/tendencias")
    assert r.status_code == 200
    data = r.json()
    assert data["filas"] == []
    assert data["agrupacion"] == "mes"


def test_tendencias_agrupacion_invalida_400(client) -> None:
    """Agrupación desconocida devuelve 400."""
    r = client.get("/api/finanzas/tendencias?agrupacion=trimestre")
    assert r.status_code == 400


def test_tendencias_con_transacciones_mensual(client) -> None:
    """Con ingresos y egresos devuelve al menos un período con datos correctos."""
    _crear_cuenta_con_tx(client, "CuentaTendencias", monto_ing=800, monto_gas=300)
    r = client.get("/api/finanzas/tendencias?agrupacion=mes&n_periodos=12")
    assert r.status_code == 200
    data = r.json()
    assert data["agrupacion"] == "mes"
    filas = data["filas"]
    assert len(filas) >= 1
    fila = filas[0]
    assert "periodo" in fila
    assert fila["ingresos"] >= 800.0
    assert fila["egresos"] >= 300.0
    assert fila["resultado_neto"] >= 500.0
    # Primer período no tiene variación anterior
    assert fila["variacion_ingresos_pct"] is None
    assert fila["variacion_egresos_pct"] is None


def test_tendencias_con_transacciones_diario(client) -> None:
    """Con agrupacion=dia devuelve filas con campo 'periodo' en formato YYYY-MM-DD."""
    _crear_cuenta_con_tx(client, "CuentaTendDiario", monto_ing=100, monto_gas=50)
    r = client.get("/api/finanzas/tendencias?agrupacion=dia")
    assert r.status_code == 200
    data = r.json()
    assert data["agrupacion"] == "dia"
    filas = data["filas"]
    assert len(filas) >= 1
    assert len(filas[0]["periodo"]) == 10  # YYYY-MM-DD


def test_tendencias_csv_sin_datos_devuelve_cabecera(client) -> None:
    """En formato CSV sin datos devuelve solo la cabecera."""
    r = client.get("/api/finanzas/tendencias?formato=csv")
    assert r.status_code == 200
    assert "periodo" in r.text
    assert "variacion_ingresos_pct" in r.text
    assert "variacion_egresos_pct" in r.text


def test_tendencias_csv_con_datos_tiene_filas(client) -> None:
    """En formato CSV con datos genera al menos una fila de datos."""
    _crear_cuenta_con_tx(client, "CuentaTendCSV", monto_ing=200, monto_gas=80)
    r = client.get("/api/finanzas/tendencias?agrupacion=mes&formato=csv")
    assert r.status_code == 200
    lineas = [l for l in r.text.strip().splitlines() if l.strip()]
    assert len(lineas) >= 2  # cabecera + al menos 1 fila de datos


def test_tendencias_n_periodos_limita_resultado(client) -> None:
    """El parámetro n_periodos limita el número de períodos devueltos."""
    _crear_cuenta_con_tx(client, "CuentaTendLimite", monto_ing=150, monto_gas=50)
    r = client.get("/api/finanzas/tendencias?agrupacion=mes&n_periodos=1")
    assert r.status_code == 200
    filas = r.json()["filas"]
    assert len(filas) <= 1


# ---------------------------------------------------------------------------
# Tests: Módulo 3 — CuentaFinanciera (estado, observaciones, tipos)
# ---------------------------------------------------------------------------

def test_crear_cuenta_con_estado_y_observaciones(client: TestClient) -> None:
    """Crear cuenta con observaciones y verificar estado 'activa' por defecto."""
    r = client.post("/api/finanzas/cuentas", json={
        "nombre": "Fondo Caja Chica",
        "tipo": "fondo_operativo",
        "saldo_inicial": "500",
        "observaciones": "Fondo para gastos menores",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["estado"] == "activa"
    assert data["observaciones"] == "Fondo para gastos menores"
    assert data["tipo"] == "fondo_operativo"


def test_actualizar_cuenta_estado_a_inactiva(client: TestClient) -> None:
    """PATCH /finanzas/cuentas/{id} — cambiar estado a inactiva."""
    r = client.post("/api/finanzas/cuentas", json={"nombre": "Cuenta Test Inact", "tipo": "GENERAL"})
    cuenta_id = r.json()["id"]

    r = client.patch(f"/api/finanzas/cuentas/{cuenta_id}", json={"estado": "inactiva"})
    assert r.status_code == 200
    assert r.json()["estado"] == "inactiva"


def test_actualizar_cuenta_nombre_y_observaciones(client: TestClient) -> None:
    """PATCH /finanzas/cuentas/{id} — actualizar nombre y observaciones."""
    r = client.post("/api/finanzas/cuentas", json={"nombre": "Cuenta Original"})
    cuenta_id = r.json()["id"]

    r = client.patch(f"/api/finanzas/cuentas/{cuenta_id}", json={
        "nombre": "Cuenta Actualizada",
        "observaciones": "Nueva observación",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["nombre"] == "Cuenta Actualizada"
    assert data["observaciones"] == "Nueva observación"


def test_actualizar_cuenta_estado_invalido(client: TestClient) -> None:
    """Estado inválido en PATCH devuelve 422."""
    r = client.post("/api/finanzas/cuentas", json={"nombre": "Cuenta Inv"})
    cuenta_id = r.json()["id"]
    r = client.patch(f"/api/finanzas/cuentas/{cuenta_id}", json={"estado": "suspendida"})
    assert r.status_code == 422


def test_actualizar_cuenta_no_existe_404(client: TestClient) -> None:
    """PATCH en cuenta inexistente devuelve 404."""
    r = client.patch("/api/finanzas/cuentas/999999", json={"nombre": "Nuevo nombre"})
    assert r.status_code == 404


def test_listar_cuentas_filtro_por_estado(client: TestClient) -> None:
    """GET /finanzas/cuentas?estado=inactiva devuelve solo las inactivas."""
    r1 = client.post("/api/finanzas/cuentas", json={"nombre": "Activa A"})
    r2 = client.post("/api/finanzas/cuentas", json={"nombre": "Inactiva B"})
    cuenta_inact_id = r2.json()["id"]
    client.patch(f"/api/finanzas/cuentas/{cuenta_inact_id}", json={"estado": "inactiva"})

    r = client.get("/api/finanzas/cuentas", params={"estado": "inactiva"})
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()]
    assert cuenta_inact_id in ids
    assert r1.json()["id"] not in ids


# ---------------------------------------------------------------------------
# Tests: Módulo 3 — Transferencias entre cuentas (§8 Tesorería)
# ---------------------------------------------------------------------------

def _cuenta_con_saldo(client, nombre: str, saldo: float) -> int:
    """Helper: crea una cuenta con saldo inicial y retorna su ID."""
    r = client.post("/api/finanzas/cuentas", json={"nombre": nombre, "saldo_inicial": str(saldo)})
    assert r.status_code == 201
    return r.json()["id"]


def test_transferir_entre_cuentas_ok(client: TestClient) -> None:
    """Transferencia exitosa: actualiza saldos de ambas cuentas."""
    id_a = _cuenta_con_saldo(client, "Cuenta A", 1000)
    id_b = _cuenta_con_saldo(client, "Cuenta B", 0)

    r = client.post("/api/finanzas/cuentas/transferir", json={
        "cuenta_origen_id": id_a,
        "cuenta_destino_id": id_b,
        "importe": "400",
        "motivo": "Traslado fondos",
    })
    assert r.status_code == 201, r.json()
    data = r.json()
    assert data["cuenta_origen_id"] == id_a
    assert data["cuenta_destino_id"] == id_b
    assert float(data["importe"]) == 400.0
    assert data["transaccion_egreso_id"] is not None
    assert data["transaccion_ingreso_id"] is not None

    # Verificar saldos actualizados
    r_a = client.get(f"/api/finanzas/cuentas/{id_a}")
    r_b = client.get(f"/api/finanzas/cuentas/{id_b}")
    assert r_a.json()["saldo"] == 600.0
    assert r_b.json()["saldo"] == 400.0


def test_transferir_saldo_insuficiente_400(client: TestClient) -> None:
    """Transferencia con saldo insuficiente en origen devuelve 400."""
    id_a = _cuenta_con_saldo(client, "Cuenta Sin Fondos", 50)
    id_b = _cuenta_con_saldo(client, "Cuenta Destino", 0)

    r = client.post("/api/finanzas/cuentas/transferir", json={
        "cuenta_origen_id": id_a,
        "cuenta_destino_id": id_b,
        "importe": "200",
    })
    assert r.status_code == 400
    assert "insuficiente" in r.json()["detail"].lower()


def test_transferir_misma_cuenta_400(client: TestClient) -> None:
    """Transferencia hacia la misma cuenta devuelve 400."""
    id_a = _cuenta_con_saldo(client, "Cuenta Misma", 500)
    r = client.post("/api/finanzas/cuentas/transferir", json={
        "cuenta_origen_id": id_a,
        "cuenta_destino_id": id_a,
        "importe": "100",
    })
    assert r.status_code == 400
    assert "distintas" in r.json()["detail"].lower()


def test_transferir_cuenta_origen_inexistente_404(client: TestClient) -> None:
    """Origen inexistente devuelve 404."""
    id_b = _cuenta_con_saldo(client, "Destino Exis", 0)
    r = client.post("/api/finanzas/cuentas/transferir", json={
        "cuenta_origen_id": 999999,
        "cuenta_destino_id": id_b,
        "importe": "100",
    })
    assert r.status_code == 404


def test_transferir_cuenta_destino_inexistente_404(client: TestClient) -> None:
    """Destino inexistente devuelve 404."""
    id_a = _cuenta_con_saldo(client, "Origen Exis", 500)
    r = client.post("/api/finanzas/cuentas/transferir", json={
        "cuenta_origen_id": id_a,
        "cuenta_destino_id": 999999,
        "importe": "100",
    })
    assert r.status_code == 404


def test_transferir_cuenta_inactiva_400(client: TestClient) -> None:
    """Transferencia desde/hacia cuenta inactiva devuelve 400."""
    id_a = _cuenta_con_saldo(client, "Cuenta Activa T", 500)
    id_b = _cuenta_con_saldo(client, "Cuenta Inactiva T", 0)
    client.patch(f"/api/finanzas/cuentas/{id_b}", json={"estado": "inactiva"})

    r = client.post("/api/finanzas/cuentas/transferir", json={
        "cuenta_origen_id": id_a,
        "cuenta_destino_id": id_b,
        "importe": "100",
    })
    assert r.status_code == 400
    assert "inactiva" in r.json()["detail"].lower()


def test_transferir_genera_transacciones_en_ambas_cuentas(client: TestClient) -> None:
    """La transferencia crea una transacción gasto en origen e ingreso en destino."""
    id_a = _cuenta_con_saldo(client, "Origen TX", 1000)
    id_b = _cuenta_con_saldo(client, "Destino TX", 200)

    client.post("/api/finanzas/cuentas/transferir", json={
        "cuenta_origen_id": id_a,
        "cuenta_destino_id": id_b,
        "importe": "300",
        "motivo": "Test transacciones",
    })

    # Ambas cuentas deben tener transacciones
    r_tx_a = client.get(f"/api/finanzas/transacciones?cuenta_id={id_a}")
    r_tx_b = client.get(f"/api/finanzas/transacciones?cuenta_id={id_b}")
    assert r_tx_a.status_code == 200
    assert r_tx_b.status_code == 200
    tipos_a = [t["tipo"] for t in r_tx_a.json()]
    tipos_b = [t["tipo"] for t in r_tx_b.json()]
    assert "gasto" in tipos_a
    assert "ingreso" in tipos_b