"""Tests de auditoría de eventos (consumidores)."""

from fastapi.testclient import TestClient


def test_movimiento_cuenta_corriente_persiste_evento_auditoria(
    client: TestClient,
    persona_datos: dict,
) -> None:
    """Registrar movimiento de cuenta corriente debe persistir evento auditado."""
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
        json={"tipo": "VENTA", "monto": 123.0, "descripcion": "Venta test audit"},
    )
    assert r_mov.status_code == 201

    r_evt = client.get(
        "/api/auditoria/eventos",
        params={
            "nombre": "MovimientoCuentaCorrienteRegistrado",
            "modulo": "tesoreria",
            "entidad_id": cliente_id,
            "limite": 10,
        },
    )
    assert r_evt.status_code == 200
    items = r_evt.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert items[0]["nombre"] == "MovimientoCuentaCorrienteRegistrado"
    assert items[0]["modulo"] == "tesoreria"
    assert items[0]["entidad_id"] == cliente_id
    assert items[0]["payload"]["cliente_id"] == cliente_id
    assert items[0]["payload"]["tipo"] == "VENTA"
    assert items[0]["payload"]["monto"] == 123.0


def test_movimiento_caja_persiste_evento_auditoria(client: TestClient) -> None:
    """Registrar movimiento de caja debe persistir MovimientoCajaRegistrado."""
    # Abrir caja
    r_abrir = client.post("/api/caja/abrir", json={"saldo_inicial": 100.0})
    assert r_abrir.status_code == 200
    caja_id = r_abrir.json()["id"]

    # Registrar movimiento
    r_mov = client.post(
        f"/api/caja/{caja_id}/movimientos",
        json={"tipo": "INGRESO", "monto": 50.0, "referencia": "Ingreso audit"},
    )
    assert r_mov.status_code == 200

    r_evt = client.get(
        "/api/auditoria/eventos",
        params={
            "nombre": "MovimientoCajaRegistrado",
            "modulo": "tesoreria",
            "entidad_id": caja_id,
            "limite": 10,
        },
    )
    assert r_evt.status_code == 200
    items = r_evt.json()
    assert len(items) >= 1
    assert items[0]["nombre"] == "MovimientoCajaRegistrado"
    assert items[0]["payload"]["caja_id"] == caja_id
    assert items[0]["payload"]["tipo"] == "INGRESO"
    assert items[0]["payload"]["monto"] == 50.0


def test_caja_abierta_y_cerrada_persisten_eventos_auditoria(client: TestClient) -> None:
    """Abrir/cerrar caja deben persistir CajaAbierta y CajaCerrada."""
    r_abrir = client.post("/api/caja/abrir", json={"saldo_inicial": 100.0})
    assert r_abrir.status_code == 200
    caja_id = r_abrir.json()["id"]

    r_cerrar = client.post(
        f"/api/caja/{caja_id}/cerrar",
        json={"saldo_final": 150.0, "supervisor_autorizado": True},
    )
    assert r_cerrar.status_code == 200

    r_evt_abrir = client.get(
        "/api/auditoria/eventos",
        params={"nombre": "CajaAbierta", "modulo": "tesoreria", "entidad_id": caja_id, "limite": 10},
    )
    assert r_evt_abrir.status_code == 200
    items_abrir = r_evt_abrir.json()
    assert len(items_abrir) >= 1
    assert items_abrir[0]["nombre"] == "CajaAbierta"
    assert items_abrir[0]["payload"]["caja_id"] == caja_id

    r_evt_cerrar = client.get(
        "/api/auditoria/eventos",
        params={"nombre": "CajaCerrada", "modulo": "tesoreria", "entidad_id": caja_id, "limite": 10},
    )
    assert r_evt_cerrar.status_code == 200
    items_cerrar = r_evt_cerrar.json()
    assert len(items_cerrar) >= 1
    assert items_cerrar[0]["nombre"] == "CajaCerrada"
    assert items_cerrar[0]["payload"]["caja_id"] == caja_id


def test_ingreso_y_gasto_persisten_eventos_auditoria_finanzas(client: TestClient) -> None:
    """Registrar ingreso/gasto debe persistir IngresoRegistrado/GastoRegistrado en auditoría."""
    # Crear cuenta financiera
    r_cuenta = client.post(
        "/api/finanzas/cuentas",
        json={"nombre": "Cuenta Auditoria", "tipo": "CAJA", "saldo_inicial": "0"},
    )
    assert r_cuenta.status_code == 201
    cuenta_id = r_cuenta.json()["id"]

    # Ingreso
    r_ingreso = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "ingreso", "monto": "10.0", "descripcion": "Ingreso audit"},
    )
    assert r_ingreso.status_code == 201
    ingreso_tx_id = r_ingreso.json()["id"]

    r_evt_ingreso = client.get(
        "/api/auditoria/eventos",
        params={
            "nombre": "IngresoRegistrado",
            "modulo": "finanzas",
            "entidad_id": ingreso_tx_id,
            "limite": 10,
        },
    )
    assert r_evt_ingreso.status_code == 200
    items_ingreso = r_evt_ingreso.json()
    assert len(items_ingreso) >= 1
    assert items_ingreso[0]["nombre"] == "IngresoRegistrado"
    assert items_ingreso[0]["payload"]["transaccion_id"] == ingreso_tx_id

    # Gasto
    r_gasto = client.post(
        f"/api/finanzas/cuentas/{cuenta_id}/transacciones",
        json={"tipo": "gasto", "monto": "3.5", "descripcion": "Gasto audit"},
    )
    assert r_gasto.status_code == 201
    gasto_tx_id = r_gasto.json()["id"]

    r_evt_gasto = client.get(
        "/api/auditoria/eventos",
        params={
            "nombre": "GastoRegistrado",
            "modulo": "finanzas",
            "entidad_id": gasto_tx_id,
            "limite": 10,
        },
    )
    assert r_evt_gasto.status_code == 200
    items_gasto = r_evt_gasto.json()
    assert len(items_gasto) >= 1
    assert items_gasto[0]["nombre"] == "GastoRegistrado"
    assert items_gasto[0]["payload"]["transaccion_id"] == gasto_tx_id

