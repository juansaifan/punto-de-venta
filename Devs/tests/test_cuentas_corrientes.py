"""Tests del submódulo Tesorería / Cuentas Corrientes de Clientes."""

from fastapi.testclient import TestClient


def test_registrar_movimiento_emite_evento_MovimientoCuentaCorrienteRegistrado(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """Registrar un movimiento emite el evento MovimientoCuentaCorrienteRegistrado."""
    from backend.events import clear_handlers, subscribe

    recibidos: list[dict] = []

    def handler(payload: dict) -> None:
        recibidos.append(payload)

    subscribe("MovimientoCuentaCorrienteRegistrado", handler)
    try:
        r_persona = client.post("/api/personas", json=persona_datos)
        assert r_persona.status_code == 201
        persona_id = r_persona.json()["id"]

        r_cliente = client.post(
            "/api/personas/clientes",
            json={
                "persona_id": persona_id,
                "segmento": "frecuente",
                "condicion_pago": "30 días",
                "limite_credito": 500.0,
            },
        )
        assert r_cliente.status_code == 201
        cliente_id = r_cliente.json()["id"]

        r_mov = client.post(
            f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
            json={"tipo": "VENTA", "monto": 123.0, "descripcion": "Venta test evento"},
        )
        assert r_mov.status_code == 201
        mov = r_mov.json()

        assert len(recibidos) == 1
        payload = recibidos[0]
        assert payload["movimiento_id"] == mov["id"]
        assert payload["cuenta_id"] == mov["cuenta_id"]
        assert payload["cliente_id"] == cliente_id
        assert payload["tipo"] == "VENTA"
        assert payload["monto"] == 123.0
        assert payload["descripcion"] == "Venta test evento"
        assert "fecha" in payload
        assert payload["saldo_despues"] == 123.0
    finally:
        clear_handlers("MovimientoCuentaCorrienteRegistrado")


def test_cuenta_corriente_resumen_sin_movimientos(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """Resumen de cuenta corriente sin movimientos devuelve saldo 0 y respeta límite de crédito."""
    # Crear persona y cliente con límite de crédito
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "30 días",
            "limite_credito": 500.0,
        },
    )
    assert r_cliente.status_code == 201
    cliente_id = r_cliente.json()["id"]

    r_resumen = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    )
    assert r_resumen.status_code == 200
    data = r_resumen.json()
    assert data["cliente_id"] == cliente_id
    assert data["saldo"] == 0.0
    assert data["limite_credito"] == 500.0
    assert data["disponible"] == 500.0


def test_cuenta_corriente_registrar_venta_y_pago_actualiza_saldo(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """Registrar VENTA aumenta saldo y registrar PAGO lo reduce."""
    r_persona = client.post("/api/personas", json=persona_datos)
    assert r_persona.status_code == 201
    persona_id = r_persona.json()["id"]

    r_cliente = client.post(
        "/api/personas/clientes",
        json={
            "persona_id": persona_id,
            "segmento": "frecuente",
            "condicion_pago": "30 días",
            "limite_credito": 1000.0,
        },
    )
    assert r_cliente.status_code == 201
    cliente_id = r_cliente.json()["id"]

    # Registrar una venta a crédito
    r_mov_venta = client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "VENTA", "monto": 200.0, "descripcion": "Venta a crédito"},
    )
    assert r_mov_venta.status_code == 201

    r_resumen = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    )
    assert r_resumen.status_code == 200
    data = r_resumen.json()
    assert data["saldo"] == 200.0
    assert data["disponible"] == 800.0

    # Registrar un pago parcial
    r_mov_pago = client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "PAGO", "monto": 50.0, "descripcion": "Pago parcial"},
    )
    assert r_mov_pago.status_code == 201

    r_resumen2 = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen"
    )
    assert r_resumen2.status_code == 200
    data2 = r_resumen2.json()
    assert data2["saldo"] == 150.0
    assert data2["disponible"] == 850.0

    # Listar movimientos debe devolver al menos los dos movimientos registrados
    r_movs = client.get(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos"
    )
    assert r_movs.status_code == 200
    movimientos = r_movs.json()
    assert len(movimientos) >= 2
    tipos = {m["tipo"] for m in movimientos}
    assert "VENTA" in tipos
    assert "PAGO" in tipos


def test_cuenta_corriente_cliente_inexistente_404(client: TestClient) -> None:
    """Operaciones sobre cuenta corriente de cliente inexistente devuelven 404."""
    r_resumen = client.get(
        "/api/tesoreria/cuentas-corrientes/clientes/99999/resumen"
    )
    assert r_resumen.status_code == 404

    r_mov = client.post(
        "/api/tesoreria/cuentas-corrientes/clientes/99999/movimientos",
        json={"tipo": "VENTA", "monto": 100.0},
    )
    assert r_mov.status_code == 404


# ────────────────────────────────────────────────────────────
# Tests: tipos adicionales (NOTA_CREDITO, NOTA_DEBITO)
# ────────────────────────────────────────────────────────────

def test_nota_debito_aumenta_saldo(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """NOTA_DEBITO incrementa el saldo de la cuenta corriente."""
    r_persona = client.post("/api/personas", json=persona_datos)
    persona_id = r_persona.json()["id"]
    r_cliente = client.post(
        "/api/personas/clientes",
        json={"persona_id": persona_id, "limite_credito": 1000.0},
    )
    cliente_id = r_cliente.json()["id"]

    r_mov = client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "NOTA_DEBITO", "monto": 150.0, "descripcion": "Nota de débito por interés"},
    )
    assert r_mov.status_code == 201
    assert r_mov.json()["tipo"] == "NOTA_DEBITO"

    r_resumen = client.get(f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen")
    assert float(r_resumen.json()["saldo"]) == 150.0


def test_nota_credito_reduce_saldo(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """NOTA_CREDITO reduce el saldo de la cuenta corriente."""
    r_persona = client.post("/api/personas", json=persona_datos)
    persona_id = r_persona.json()["id"]
    r_cliente = client.post(
        "/api/personas/clientes",
        json={"persona_id": persona_id, "limite_credito": 1000.0},
    )
    cliente_id = r_cliente.json()["id"]

    # Primero crear deuda
    client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "VENTA", "monto": 300.0},
    )

    # Aplicar nota de crédito
    r_nc = client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "NOTA_CREDITO", "monto": 100.0, "descripcion": "Descuento por devolución"},
    )
    assert r_nc.status_code == 201
    assert r_nc.json()["tipo"] == "NOTA_CREDITO"

    r_resumen = client.get(f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/resumen")
    assert float(r_resumen.json()["saldo"]) == 200.0


def test_tipo_invalido_cc_devuelve_400(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """Tipo de movimiento inválido en CC devuelve 400."""
    r_persona = client.post("/api/personas", json=persona_datos)
    persona_id = r_persona.json()["id"]
    r_cliente = client.post("/api/personas/clientes", json={"persona_id": persona_id})
    cliente_id = r_cliente.json()["id"]

    r = client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "TIPO_INVALIDO", "monto": 50.0},
    )
    assert r.status_code == 400


# ────────────────────────────────────────────────────────────
# Tests: listado global de cuentas corrientes
# ────────────────────────────────────────────────────────────

def test_listar_cuentas_corrientes_vacio(client: TestClient) -> None:
    """Listar cuentas corrientes sin datos devuelve lista vacía."""
    r = client.get("/api/tesoreria/cuentas-corrientes")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_cuentas_corrientes_con_saldo(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """Listar cuentas corrientes refleja las cuentas creadas con saldo."""
    r_persona = client.post("/api/personas", json=persona_datos)
    persona_id = r_persona.json()["id"]
    r_cliente = client.post(
        "/api/personas/clientes",
        json={"persona_id": persona_id, "limite_credito": 500.0},
    )
    cliente_id = r_cliente.json()["id"]

    # Registrar venta para generar saldo
    client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "VENTA", "monto": 200.0},
    )

    r = client.get("/api/tesoreria/cuentas-corrientes")
    assert r.status_code == 200
    cuentas = r.json()
    assert len(cuentas) >= 1
    cuenta = next((c for c in cuentas if c["cliente_id"] == cliente_id), None)
    assert cuenta is not None
    assert float(cuenta["saldo"]) == 200.0
    assert float(cuenta["limite_credito"]) == 500.0
    assert float(cuenta["disponible"]) == 300.0


def test_listar_cuentas_corrientes_filtro_solo_con_saldo(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """El filtro solo_con_saldo=true excluye cuentas sin deuda."""
    r_persona = client.post("/api/personas", json=persona_datos)
    persona_id = r_persona.json()["id"]
    r_cliente = client.post("/api/personas/clientes", json={"persona_id": persona_id})
    cliente_id = r_cliente.json()["id"]

    # Registrar y cancelar la deuda completamente (saldo = 0)
    client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "VENTA", "monto": 100.0},
    )
    client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "PAGO", "monto": 100.0},
    )

    r = client.get("/api/tesoreria/cuentas-corrientes?solo_con_saldo=true")
    assert r.status_code == 200
    cuentas = r.json()
    # Este cliente no debe aparecer (saldo == 0)
    assert all(float(c["saldo"]) > 0 for c in cuentas)


# ---------------------------------------------------------------------------
# Tests: aging de cuentas corrientes (docs Modulo 3 ss5)
# ---------------------------------------------------------------------------

def test_aging_sin_deuda(client: TestClient) -> None:
    """GET /aging sin deudas devuelve estructura vacia correcta."""
    r = client.get("/api/tesoreria/cuentas-corrientes/aging")
    assert r.status_code == 200
    data = r.json()
    assert "fecha_corte" in data
    assert "total_deuda" in data
    assert "resumen_por_tramo" in data
    assert "detalle" in data
    assert data["total_deuda"] == 0.0


def test_aging_con_deuda_activa(client: TestClient, persona_datos: dict) -> None:
    """GET /aging con deudas refleja correctamente los tramos."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post("/api/personas/clientes", json={"persona_id": p["id"]}).json()
    cliente_id = cli["id"]
    client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "VENTA", "monto": 300.0},
    )
    r = client.get("/api/tesoreria/cuentas-corrientes/aging")
    assert r.status_code == 200
    data = r.json()
    assert data["total_deuda"] > 0
    assert any(
        len(v) > 0 for v in data["detalle"].values()
    ), "Debe haber al menos un cliente en algún tramo"


# ---------------------------------------------------------------------------
# Tests: reporte de deudores (docs Modulo 3 ss5)
# ---------------------------------------------------------------------------

def test_deudores_sin_datos(client: TestClient) -> None:
    """GET /deudores sin deudas devuelve lista vacia."""
    r = client.get("/api/tesoreria/cuentas-corrientes/deudores")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_deudores_con_deuda(client: TestClient, persona_datos: dict) -> None:
    """GET /deudores incluye cliente con saldo > 0 con estructura completa."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post("/api/personas/clientes", json={"persona_id": p["id"], "limite_credito": "500"}).json()
    cliente_id = cli["id"]
    client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos",
        json={"tipo": "VENTA", "monto": 200.0},
    )
    r = client.get("/api/tesoreria/cuentas-corrientes/deudores")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    deudor = next((d for d in data if d["cliente_id"] == cliente_id), None)
    assert deudor is not None
    assert deudor["saldo"] == 200.0
    assert deudor["limite_credito"] == 500.0
    assert deudor["disponible"] == 300.0
    assert "dias_desde_ultima_venta" in deudor
    assert "dias_desde_ultimo_pago" in deudor


def test_deudores_filtro_saldo_minimo(client: TestClient, persona_datos: dict) -> None:
    """GET /deudores?saldo_minimo filtra por saldo minimo."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post("/api/personas/clientes", json={"persona_id": p["id"]}).json()
    client.post(
        f"/api/tesoreria/cuentas-corrientes/clientes/{cli['id']}/movimientos",
        json={"tipo": "VENTA", "monto": 50.0},
    )
    r_alto = client.get("/api/tesoreria/cuentas-corrientes/deudores?saldo_minimo=100")
    assert r_alto.status_code == 200
    assert not any(d["saldo"] < 100 for d in r_alto.json())


# ---------------------------------------------------------------------------
# Tests: estadisticas de pagos por cliente (docs Modulo 3 ss10)
# ---------------------------------------------------------------------------

def test_estadisticas_pagos_cliente_sin_cuenta(client: TestClient, persona_datos: dict) -> None:
    """GET estadisticas-pagos sin cuenta corriente devuelve totales en 0."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post("/api/personas/clientes", json={"persona_id": p["id"]}).json()
    r = client.get(f"/api/tesoreria/cuentas-corrientes/clientes/{cli['id']}/estadisticas-pagos")
    assert r.status_code == 200
    data = r.json()
    assert data["total_ventas_cc"] == 0.0
    assert data["total_pagos_cc"] == 0.0
    assert data["cantidad_pagos"] == 0


def test_estadisticas_pagos_cliente_con_movimientos(client: TestClient, persona_datos: dict) -> None:
    """GET estadisticas-pagos refleja ventas y pagos registrados."""
    p = client.post("/api/personas", json=persona_datos).json()
    cli = client.post("/api/personas/clientes", json={"persona_id": p["id"]}).json()
    cliente_id = cli["id"]
    client.post(f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos", json={"tipo": "VENTA", "monto": 300.0})
    client.post(f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/movimientos", json={"tipo": "PAGO", "monto": 100.0})
    r = client.get(f"/api/tesoreria/cuentas-corrientes/clientes/{cliente_id}/estadisticas-pagos")
    assert r.status_code == 200
    data = r.json()
    assert data["total_ventas_cc"] == 300.0
    assert data["total_pagos_cc"] == 100.0
    assert data["cantidad_ventas"] == 1
    assert data["cantidad_pagos"] == 1
    assert data["saldo_actual"] == 200.0
    assert data["promedio_pago"] == 100.0


def test_estadisticas_pagos_cliente_404(client: TestClient) -> None:
    """GET estadisticas-pagos con cliente inexistente retorna 404."""
    r = client.get("/api/tesoreria/cuentas-corrientes/clientes/999999/estadisticas-pagos")
    assert r.status_code == 404

