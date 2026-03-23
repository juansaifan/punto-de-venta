"""Tests de la API de Tesorería (caja)."""
from fastapi.testclient import TestClient


def test_listar_cajas_vacio(client: TestClient) -> None:
    """Listar cajas sin datos devuelve lista vacía."""
    r = client.get("/api/caja")
    assert r.status_code == 200
    assert r.json() == []


def test_caja_abierta_sin_caja(client: TestClient) -> None:
    """Obtener caja abierta cuando no hay ninguna devuelve null."""
    r = client.get("/api/caja/abierta")
    assert r.status_code == 200
    assert r.json() is None


def test_abrir_caja_ok(client: TestClient) -> None:
    """Abrir caja con saldo inicial devuelve la caja creada."""
    r = client.post(
        "/api/caja/abrir",
        json={"saldo_inicial": "100.50"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] is not None
    assert float(data["saldo_inicial"]) == 100.50
    assert data["fecha_cierre"] is None


def test_abrir_segunda_caja_falla(client: TestClient) -> None:
    """No puede abrirse otra caja si ya hay una abierta (409)."""
    client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    r = client.post("/api/caja/abrir", json={"saldo_inicial": "50"})
    assert r.status_code == 409
    assert "abierta" in r.json()["detail"].lower()


def test_obtener_caja_abierta_ok(client: TestClient) -> None:
    """Tras abrir caja, GET /caja/abierta la devuelve."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "200"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]
    r = client.get("/api/caja/abierta")
    assert r.status_code == 200
    assert r.json()["id"] == caja_id
    assert float(r.json()["saldo_inicial"]) == 200


def test_cerrar_caja_ok(client: TestClient) -> None:
    """Cerrar caja registra fecha_cierre y saldo_final."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    caja_id = abrir.json()["id"]
    r = client.post(
        f"/api/caja/{caja_id}/cerrar",
        json={"saldo_final": "150.75", "supervisor_autorizado": True},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fecha_cierre"] is not None
    assert float(data["saldo_final"]) == 150.75


def test_cerrar_caja_inexistente_404(client: TestClient) -> None:
    """Cerrar caja inexistente devuelve 404."""
    r = client.post("/api/caja/99999/cerrar", json={})
    assert r.status_code == 404


def test_cerrar_caja_ya_cerrada_falla(client: TestClient) -> None:
    """Cerrar una caja ya cerrada devuelve 400."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = abrir.json()["id"]
    client.post(
        f"/api/caja/{caja_id}/cerrar",
        json={"saldo_final": "0", "supervisor_autorizado": False},
    )
    r = client.post(f"/api/caja/{caja_id}/cerrar", json={})
    assert r.status_code == 400
    assert "cerrada" in r.json()["detail"].lower()


def test_listar_cajas_incluye_abiertas_y_cerradas(client: TestClient) -> None:
    """Listar cajas incluye las creadas (abiertas y cerradas)."""
    client.post("/api/caja/abrir", json={"saldo_inicial": "10"})
    caja1_id = client.get("/api/caja/abierta").json()["id"]
    client.post(f"/api/caja/{caja1_id}/cerrar", json={"saldo_final": "10"})
    client.post("/api/caja/abrir", json={"saldo_inicial": "20"})
    r = client.get("/api/caja")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_registrar_movimiento_ingreso_ok(client: TestClient) -> None:
    """Registrar un ingreso en caja abierta devuelve el movimiento."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    caja_id = abrir.json()["id"]
    r = client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "50.00", "referencia": "Venta mostrador"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["caja_id"] == caja_id
    assert data["tipo"] == "INGRESO"
    assert float(data["monto"]) == 50.0
    assert data["referencia"] == "Venta mostrador"


def test_registrar_movimiento_caja_cerrada_falla(client: TestClient) -> None:
    """No se puede registrar movimiento en caja cerrada (400)."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = abrir.json()["id"]
    client.post(
        f"/api/caja/{caja_id}/cerrar",
        json={"saldo_final": "0", "supervisor_autorizado": False},
    )
    r = client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "10"},
    )
    assert r.status_code == 400
    assert "cerrada" in r.json()["detail"].lower()


def test_listar_movimientos_caja(client: TestClient) -> None:
    """Listar movimientos de una caja devuelve los registrados."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = abrir.json()["id"]
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "20", "referencia": "A"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "5", "referencia": "B"},
    )
    r = client.get(f"/api/caja/{caja_id}/movimientos")
    assert r.status_code == 200
    movs = r.json()
    assert len(movs) == 2


def test_resumen_caja_sin_movimientos(client: TestClient) -> None:
    """El resumen de caja sin movimientos refleja solo el saldo_inicial."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    caja_id = abrir.json()["id"]

    r = client.get(f"/api/caja/{caja_id}/resumen")
    assert r.status_code == 200
    data = r.json()
    assert data["caja_id"] == caja_id
    assert float(data["saldo_inicial"]) == 100.0
    assert float(data["total_ingresos"]) == 0.0
    assert float(data["total_egresos"]) == 0.0
    assert float(data["saldo_teorico"]) == 100.0


def test_resumen_caja_con_ingresos_y_egresos(client: TestClient) -> None:
    """El resumen de caja considera ingresos y egresos para el saldo_teorico."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "50"})
    caja_id = abrir.json()["id"]

    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": "30"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "VENTA", "monto": "20"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "10"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "RETIRO", "monto": "5"},
    )

    r = client.get(f"/api/caja/{caja_id}/resumen")
    assert r.status_code == 200
    data = r.json()
    assert data["caja_id"] == caja_id
    assert float(data["saldo_inicial"]) == 50.0
    assert float(data["total_ingresos"]) == 50.0  # 30 + 20
    assert float(data["total_egresos"]) == 15.0  # 10 + 5
    assert float(data["saldo_teorico"]) == 85.0  # 50 + 50 - 15


def test_resumen_caja_con_cierre_calcula_diferencia(
    client: TestClient,
) -> None:
    """Cuando la caja está cerrada, el resumen incluye diferencia saldo_final - saldo_teorico."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    assert abrir.status_code == 200
    caja_id = abrir.json()["id"]

    # saldo_teorico = 100 + (VENTA 20) - (GASTO 5) = 115
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "VENTA", "monto": "20", "referencia": "Venta"},
    )
    client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "GASTO", "monto": "5", "referencia": "Gasto"},
    )

    # cierro con diferencia +3
    cerrar = client.post(
        f"/api/caja/{caja_id}/cerrar",
        json={"saldo_final": "118", "supervisor_autorizado": True},
    )
    assert cerrar.status_code == 200

    r = client.get(f"/api/caja/{caja_id}/resumen")
    assert r.status_code == 200
    data = r.json()
    assert float(data["saldo_teorico"]) == 115.0
    assert float(data["saldo_final"]) == 118.0
    assert float(data["diferencia"]) == 3.0


def test_resumen_caja_inexistente_404(client: TestClient) -> None:
    """El resumen de una caja inexistente devuelve 404."""
    r = client.get("/api/caja/99999/resumen")
    assert r.status_code == 404


def test_abrir_caja_emite_CajaAbierta(client: TestClient) -> None:
    """Al abrir caja se emite el evento CajaAbierta (EVENTOS.md)."""
    from backend.events import subscribe, clear_handlers

    recibidos: list[dict] = []

    def handler(payload: dict) -> None:
        recibidos.append(payload)

    subscribe("CajaAbierta", handler)
    try:
        r = client.post("/api/caja/abrir", json={"saldo_inicial": "75.25"})
        assert r.status_code == 200
        data = r.json()
        assert len(recibidos) == 1
        payload = recibidos[0]
        assert payload["caja_id"] == data["id"]
        assert payload["saldo_inicial"] == 75.25
        assert "fecha_apertura" in payload
    finally:
        clear_handlers("CajaAbierta")


def test_cerrar_caja_emite_CajaCerrada(client: TestClient) -> None:
    """Al cerrar caja se emite el evento CajaCerrada (EVENTOS.md)."""
    from backend.events import subscribe, clear_handlers

    recibidos: list[dict] = []

    def handler(payload: dict) -> None:
        recibidos.append(payload)

    subscribe("CajaCerrada", handler)
    try:
        abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
        caja_id = abrir.json()["id"]
        r = client.post(
            f"/api/caja/{caja_id}/cerrar",
            json={"saldo_final": "120", "supervisor_autorizado": True},
        )
        assert r.status_code == 200
        assert len(recibidos) == 1
        payload = recibidos[0]
        assert payload["caja_id"] == caja_id
        assert payload["saldo_inicial"] == 100.0
        assert payload["saldo_final"] == 120.0
        assert "fecha_cierre" in payload
    finally:
        clear_handlers("CajaCerrada")


# ────────────────────────────────────────────────────────────
# Tests: filtro por tipo en movimientos de caja
# ────────────────────────────────────────────────────────────

def test_listar_movimientos_filtro_tipo(client: TestClient) -> None:
    """Filtrar movimientos de caja por tipo devuelve solo los del tipo indicado."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    caja_id = abrir.json()["id"]

    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "INGRESO", "monto": "30"})
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "GASTO", "monto": "10"})
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "INGRESO", "monto": "20"})

    r = client.get(f"/api/caja/{caja_id}/movimientos?tipo=INGRESO")
    assert r.status_code == 200
    movs = r.json()
    assert len(movs) == 2
    assert all(m["tipo"] == "INGRESO" for m in movs)


def test_listar_movimientos_filtro_tipo_gasto(client: TestClient) -> None:
    """Filtrar por GASTO devuelve solo gastos."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = abrir.json()["id"]

    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "INGRESO", "monto": "50"})
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "GASTO", "monto": "15"})

    r = client.get(f"/api/caja/{caja_id}/movimientos?tipo=GASTO")
    assert r.status_code == 200
    movs = r.json()
    assert len(movs) == 1
    assert movs[0]["tipo"] == "GASTO"


# ────────────────────────────────────────────────────────────
# Tests: resumen global de cajas
# ────────────────────────────────────────────────────────────

def test_resumen_global_cajas_sin_datos(client: TestClient) -> None:
    """Resumen global sin cajas devuelve ceros."""
    r = client.get("/api/caja/resumen-global")
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad_cajas_total"] == 0
    assert data["cantidad_cajas_abiertas"] == 0
    assert float(data["total_ingresos_historico"]) == 0.0


def test_resumen_global_cajas_con_datos(client: TestClient) -> None:
    """Resumen global refleja cajas y movimientos registrados."""
    # Abrir caja 1 con movimientos y cerrar
    abrir1 = client.post("/api/caja/abrir", json={"saldo_inicial": "100"})
    caja1_id = abrir1.json()["id"]
    client.post(f"/api/caja/{caja1_id}/movimientos", json={"tipo": "INGRESO", "monto": "50"})
    client.post(f"/api/caja/{caja1_id}/movimientos", json={"tipo": "GASTO", "monto": "20"})
    client.post(f"/api/caja/{caja1_id}/cerrar", json={"saldo_final": "130", "supervisor_autorizado": True})

    # Abrir caja 2 (queda abierta)
    client.post("/api/caja/abrir", json={"saldo_inicial": "200"})

    r = client.get("/api/caja/resumen-global")
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad_cajas_total"] == 2
    assert data["cantidad_cajas_abiertas"] == 1
    assert data["cantidad_cajas_cerradas"] == 1
    assert float(data["total_ingresos_historico"]) == 50.0
    assert float(data["total_egresos_historico"]) == 20.0
    assert float(data["saldo_neto_historico"]) == 30.0


# ────────────────────────────────────────────────────────────
# Tests: historial global de movimientos
# ────────────────────────────────────────────────────────────

def test_movimientos_global_lista_todos(client: TestClient) -> None:
    """El endpoint global lista movimientos de todas las cajas."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = abrir.json()["id"]
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "INGRESO", "monto": "100"})
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "GASTO", "monto": "40"})

    r = client.get("/api/caja/movimientos-global")
    assert r.status_code == 200
    movs = r.json()
    assert len(movs) >= 2


def test_movimientos_global_filtro_tipo(client: TestClient) -> None:
    """El historial global acepta filtro por tipo."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = abrir.json()["id"]
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "INGRESO", "monto": "10"})
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "RETIRO", "monto": "5"})

    r = client.get("/api/caja/movimientos-global?tipo=RETIRO")
    assert r.status_code == 200
    movs = r.json()
    assert len(movs) >= 1
    assert all(m["tipo"] == "RETIRO" for m in movs)


# ────────────────────────────────────────────────────────────
# Tests: exportación CSV de movimientos de caja
# ────────────────────────────────────────────────────────────

def test_exportar_movimientos_csv_ok(client: TestClient) -> None:
    """Exportar movimientos de caja devuelve CSV con cabecera y filas."""
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    caja_id = abrir.json()["id"]
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "INGRESO", "monto": "75", "referencia": "Ref A"})
    client.post(f"/api/caja/{caja_id}/movimientos", json={"tipo": "GASTO", "monto": "25"})

    r = client.get(f"/api/caja/{caja_id}/movimientos/exportar")
    assert r.status_code == 200
    content = r.text
    lines = content.strip().split("\n")
    assert lines[0] == "id,fecha,tipo,monto,medio_pago,referencia"
    assert len(lines) == 3  # cabecera + 2 movimientos


def test_exportar_movimientos_csv_caja_inexistente(client: TestClient) -> None:
    """Exportar movimientos de caja inexistente devuelve 404."""
    r = client.get("/api/caja/99999/movimientos/exportar")
    assert r.status_code == 404
