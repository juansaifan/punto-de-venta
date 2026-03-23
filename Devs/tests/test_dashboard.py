"""Tests del API Dashboard."""
from fastapi.testclient import TestClient


def test_indicadores_ok(client: TestClient) -> None:
    """GET indicadores devuelve estructura esperada."""
    r = client.get("/api/dashboard/indicadores")
    assert r.status_code == 200
    data = r.json()
    assert "fecha" in data
    assert "ventas_del_dia" in data
    assert "total_ventas_del_dia" in data
    assert "ticket_promedio" in data
    assert "caja_abierta" in data
    assert "saldo_caja_teorico" in data
    assert "productos_stock_bajo" in data
    assert "valor_inventario" in data
    assert isinstance(data["valor_inventario"], (int, float))
    # saldo_caja_teorico puede ser None si no hay caja abierta o numérico si existe
    assert (data["saldo_caja_teorico"] is None) or isinstance(
        data["saldo_caja_teorico"], (int, float)
    )


def test_ventas_por_hora_sin_parametro(client: TestClient) -> None:
    """GET ventas-por-hora sin fecha devuelve 24 horas (hoy)."""
    r = client.get("/api/dashboard/ventas-por-hora")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 24
    for i, punto in enumerate(data):
        assert punto["hora"] == f"{i:02d}"
        assert "cantidad_ventas" in punto
        assert "total_vendido" in punto
        assert isinstance(punto["cantidad_ventas"], int)
        assert isinstance(punto["total_vendido"], (int, float))


def test_ventas_por_hora_con_fecha_sin_ventas(client: TestClient) -> None:
    """GET ventas-por-hora con fecha sin ventas devuelve 24 horas en cero."""
    r = client.get("/api/dashboard/ventas-por-hora?fecha=2026-01-15")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 24
    for punto in data:
        assert punto["cantidad_ventas"] == 0
        assert punto["total_vendido"] == 0.0


def test_ventas_por_hora_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """GET ventas-por-hora con fecha que tiene ventas devuelve al menos una hora con datos."""
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
    venta = client.get(f"/api/ventas/{r_venta.json()['venta_id']}").json()
    fecha_venta = venta["creado_en"][:10]

    r = client.get(f"/api/dashboard/ventas-por-hora?fecha={fecha_venta}")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 24
    total_ventas = sum(p["cantidad_ventas"] for p in data)
    total_importe = sum(p["total_vendido"] for p in data)
    assert total_ventas >= 1
    assert total_importe >= 0


def test_productos_stock_bajo_vacio(client: TestClient, producto_datos: dict) -> None:
    """Productos con stock por encima del mínimo no aparecen en alertas."""
    # producto_datos tiene stock_minimo 2; si ingresamos 10, no debe aparecer
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "10"},
    )
    r = client.get("/api/dashboard/productos-stock-bajo")
    assert r.status_code == 200
    lista = r.json()
    ids_bajo = [p["producto_id"] for p in lista]
    assert producto_id not in ids_bajo


def test_productos_stock_bajo_incluye_productos_debajo_minimo(
    client: TestClient, producto_datos: dict
) -> None:
    """Productos con stock <= stock_minimo aparecen en alertas."""
    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    # stock_minimo es 2 en producto_datos; no ingresar o ingresar 1
    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "1"},
    )
    r = client.get("/api/dashboard/productos-stock-bajo")
    assert r.status_code == 200
    lista = r.json()
    found = next((p for p in lista if p["producto_id"] == producto_id), None)
    assert found is not None
    assert found["stock_actual"] == 1.0
    assert found["stock_minimo"] == 2.0
    assert found["nombre"] == producto_datos["nombre"]


def test_indicadores_comparativos_estructura(client: TestClient) -> None:
    """GET indicadores-comparativos devuelve todos los indicadores más comparativa vs día anterior."""
    r = client.get("/api/dashboard/indicadores-comparativos")
    assert r.status_code == 200
    data = r.json()
    assert "fecha" in data
    assert "ventas_del_dia" in data
    assert "total_ventas_del_dia" in data
    assert "ticket_promedio" in data
    assert "comparativa" in data
    comp = data["comparativa"]
    assert "fecha_anterior" in comp
    assert "ventas_del_dia_anterior" in comp
    assert "total_ventas_del_dia_anterior" in comp
    assert "ticket_promedio_anterior" in comp
    assert "variacion_pct_cantidad_ventas" in comp
    assert "variacion_pct_total_ventas" in comp
    assert "variacion_pct_ticket_promedio" in comp


def test_indicadores_comparativos_con_fecha(client: TestClient) -> None:
    """GET indicadores-comparativos con fecha devuelve comparativa para esa fecha vs anterior."""
    r = client.get("/api/dashboard/indicadores-comparativos?fecha=2026-01-20")
    assert r.status_code == 200
    data = r.json()
    assert data["fecha"] == "2026-01-20"
    assert data["comparativa"]["fecha_anterior"] == "2026-01-19"


def test_indicadores_comparativos_variacion_sin_ventas_anteriores(client: TestClient) -> None:
    """Cuando el día anterior tiene 0 ventas, variacion_pct puede ser None."""
    # Fecha sin ventas en 2026-01-18 ni 2026-01-17; al menos variacion puede ser None
    r = client.get("/api/dashboard/indicadores-comparativos?fecha=2026-01-18")
    assert r.status_code == 200
    data = r.json()
    assert data["ventas_del_dia"] == 0
    assert data["comparativa"]["ventas_del_dia_anterior"] == 0
    # Con ambos 0, variacion no definible
    assert data["comparativa"]["variacion_pct_cantidad_ventas"] is None
    assert data["comparativa"]["variacion_pct_total_ventas"] is None


def test_productos_proximos_vencer_vacio(client: TestClient) -> None:
    """GET productos-proximos-vencer sin lotes devuelve lista vacía."""
    r = client.get("/api/dashboard/productos-proximos-vencer")
    assert r.status_code == 200
    assert r.json() == []


def test_productos_proximos_vencer_incluye_lote_en_rango(
    client: TestClient, producto_datos: dict
) -> None:
    """GET productos-proximos-vencer devuelve lotes con vencimiento en los próximos días."""
    from datetime import date, timedelta

    crear = client.post("/api/productos", json=producto_datos)
    assert crear.status_code == 201
    producto_id = crear.json()["id"]
    fecha_cerca = (date.today() + timedelta(days=10)).isoformat()
    lotes = client.post(
        f"/api/inventario/productos/{producto_id}/lotes",
        json={"cantidad": 5, "fecha_vencimiento": fecha_cerca},
    )
    assert lotes.status_code == 201
    r = client.get("/api/dashboard/productos-proximos-vencer?dias=30")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    found = next((x for x in data if x["producto_id"] == producto_id and x["lote_id"] == lotes.json()["id"]), None)
    assert found is not None
    assert found["cantidad"] == 5.0
    assert found["fecha_vencimiento"] == fecha_cerca
    assert found["dias_restantes"] == 10
    assert found["nombre"] == producto_datos["nombre"]


def test_alertas_operativas_con_inventario_y_tesoreria(client: TestClient, producto_datos: dict) -> None:
    """GET /dashboard/alertas-operativas consolida inventario y tesorería."""
    from datetime import date, timedelta

    # Abrir caja para tesorería
    abrir = client.post("/api/caja/abrir", json={"saldo_inicial": "0"})
    assert abrir.status_code == 200

    # Crear producto con stock bajo + lote próximo a vencer
    crear = client.post(
        "/api/productos",
        json={**producto_datos, "sku": "DASH-ALERT", "stock_minimo": "5"},
    )
    assert crear.status_code == 201
    producto_id = crear.json()["id"]

    client.post(
        "/api/inventario/ingresar",
        json={"producto_id": producto_id, "cantidad": "2", "ubicacion": "GONDOLA"},
    )
    fecha_cerca = (date.today() + timedelta(days=3)).isoformat()
    client.post(
        f"/api/inventario/productos/{producto_id}/lotes",
        json={"cantidad": 1, "fecha_vencimiento": fecha_cerca},
    )

    r = client.get("/api/dashboard/alertas-operativas", params={"dias_vencimiento": 10})
    assert r.status_code == 200
    data = r.json()

    assert "inventario" in data and "tesoreria" in data
    assert data["tesoreria"]["caja_abierta"] is True
    assert data["tesoreria"]["caja_id"] is not None

    inv = data["inventario"]
    assert inv["resumen"]["stock_bajo"] >= 1
    assert any(x["producto_id"] == producto_id for x in inv["stock_bajo"])
    assert inv["resumen"]["proximos_vencer"] >= 1
    assert any(x["producto_id"] == producto_id for x in inv["proximos_vencer"])


def test_alertas_operativas_flags_excluyen_secciones(client: TestClient) -> None:
    """Flags incluir_* permiten excluir secciones."""
    r = client.get(
        "/api/dashboard/alertas-operativas",
        params={"incluir_inventario": "false", "incluir_tesoreria": "false"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["inventario"] is None
    assert data["tesoreria"] is None


def test_panel_lateral_dashboard_devuelve_estructura_basica(client: TestClient) -> None:
    """GET /dashboard/panel-lateral devuelve salud/promedios/pronostico."""
    r = client.get("/api/dashboard/panel-lateral")
    assert r.status_code == 200
    data = r.json()
    assert "fecha" in data
    assert "salud" in data and "estado" in data["salud"]
    assert "promedios" in data
    assert "pronostico" in data


def test_panel_lateral_refleja_parametros_dashboard(client: TestClient) -> None:
    """panel-lateral expone objetivo/punto equilibrio desde ParametroSistema.dashboard."""
    payload = {"objetivo_diario": 1000, "punto_equilibrio_diario": 600}
    r_set = client.put("/api/configuracion/parametros/dashboard", json=payload)
    assert r_set.status_code == 200

    r = client.get("/api/dashboard/panel-lateral")
    assert r.status_code == 200
    data = r.json()

    assert data["objetivo_diario"] == payload["objetivo_diario"]
    assert data["punto_equilibrio_diario"] == payload["punto_equilibrio_diario"]
    # Sin ventas, total_hoy=0 < punto_equilibrio => ROJO
    assert data["salud"]["estado"] == "ROJO"
    assert data["ganancia_actual"] == -payload["punto_equilibrio_diario"]
    assert data["cumplimiento_punto_equilibrio_diario_pct"] == 0.0
    assert data["cumplimiento_objetivo_diario_pct"] == 0.0


# ────────────────────────────────────────────────────────────
# Tests: §4.7 Objetivos semanal y mensual
# ────────────────────────────────────────────────────────────

def test_panel_lateral_objetivos_semanal_mensual(client: TestClient) -> None:
    """Panel lateral expone objetivos semanal y mensual y calcula cumplimiento."""
    payload = {
        "objetivo_diario": 1000,
        "objetivo_semanal": 7000,
        "objetivo_mensual": 30000,
        "punto_equilibrio_diario": 500,
    }
    r_set = client.put("/api/configuracion/parametros/dashboard", json=payload)
    assert r_set.status_code == 200

    r = client.get("/api/dashboard/panel-lateral")
    assert r.status_code == 200
    data = r.json()

    assert data["objetivo_semanal"] == payload["objetivo_semanal"]
    assert data["objetivo_mensual"] == payload["objetivo_mensual"]
    # Con ingresos = 0, cumplimiento debe ser 0.0
    assert data["cumplimiento_objetivo_semanal_pct"] == 0.0
    assert data["cumplimiento_objetivo_mensual_pct"] == 0.0
    # Campos de ingresos acumulados deben existir
    assert "ingresos_semana_actual" in data
    assert "ingresos_mes_actual" in data
    assert isinstance(data["ingresos_semana_actual"], (int, float))
    assert isinstance(data["ingresos_mes_actual"], (int, float))


def test_panel_lateral_objetivos_nulos_sin_config(client: TestClient) -> None:
    """Sin configuración de objetivos, los campos son None."""
    r = client.get("/api/dashboard/panel-lateral")
    assert r.status_code == 200
    data = r.json()
    # Sin config, los objetivos deben ser None
    assert data["objetivo_semanal"] is None
    assert data["objetivo_mensual"] is None
    assert data["cumplimiento_objetivo_semanal_pct"] is None
    assert data["cumplimiento_objetivo_mensual_pct"] is None


# ────────────────────────────────────────────────────────────
# Tests: §4.2 Promedios con tickets
# ────────────────────────────────────────────────────────────

def test_panel_lateral_estructura_promedios(client: TestClient) -> None:
    """panel-lateral incluye ingresos y tickets promedio en la sección promedios."""
    r = client.get("/api/dashboard/panel-lateral")
    assert r.status_code == 200
    data = r.json()
    promedios = data["promedios"]
    assert "ingresos_ultimos_7_dias" in promedios
    assert "tickets_ultimos_7_dias" in promedios
    assert "ingresos_este_dia_semana" in promedios
    assert isinstance(promedios["tickets_ultimos_7_dias"], (int, float))


# ────────────────────────────────────────────────────────────
# Tests: §4.8 Margen promedio del día
# ────────────────────────────────────────────────────────────

def test_margen_dia_sin_ventas(client: TestClient) -> None:
    """GET /dashboard/margen-dia sin ventas devuelve margen_bruto 0 y pct None."""
    r = client.get("/api/dashboard/margen-dia?fecha=2026-01-01")
    assert r.status_code == 200
    data = r.json()
    assert data["margen_bruto"] == 0.0
    assert data["total_ingresos"] == 0.0
    assert data["margen_pct"] is None
    assert data["fecha"] == "2026-01-01"


def test_margen_dia_con_ventas(client: TestClient, producto_datos: dict) -> None:
    """GET /dashboard/margen-dia con ventas refleja margen bruto correcto."""
    from tests.test_ventas import _ingresar_stock

    # Crear producto con costo y precio conocidos para validar margen
    datos = {**producto_datos, "sku": "MARGEN-TEST", "precio_venta": "100.00", "costo_actual": "60.00"}
    crear = client.post("/api/productos", json=datos)
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
    venta = client.get(f"/api/ventas/{r_venta.json()['venta_id']}").json()
    fecha_venta = venta["creado_en"][:10]

    r = client.get(f"/api/dashboard/margen-dia?fecha={fecha_venta}")
    assert r.status_code == 200
    data = r.json()
    # margen_bruto = (100 - 60) * 2 = 80
    assert data["margen_bruto"] == 80.0
    assert data["total_ingresos"] == 200.0
    assert data["margen_pct"] == 40.0


def test_panel_lateral_incluye_margen_dia(client: TestClient) -> None:
    """Panel lateral incluye sección margen_dia con campos requeridos (§4.8)."""
    r = client.get("/api/dashboard/panel-lateral")
    assert r.status_code == 200
    data = r.json()
    assert "margen_dia" in data
    margen = data["margen_dia"]
    assert "margen_bruto" in margen
    assert "margen_pct" in margen
    assert "tendencia_vs_ayer_pct" in margen


# ---------------------------------------------------------------------------
# Tests: top productos (docs Modulo 1 ss3.1)
# ---------------------------------------------------------------------------

def _crear_venta_dashboard(client, sku: str, precio: str, cantidad: str = "1") -> None:
    prod = client.post("/api/productos", json={"sku": sku, "nombre": f"Prod {sku}", "precio_venta": precio, "costo_actual": "1"}).json()
    client.post("/api/inventario/ingresar", json={"producto_id": prod["id"], "cantidad": "50"})
    client.post("/api/ventas", json={
        "items": [{"producto_id": prod["id"], "cantidad": cantidad}],
        "metodo_pago": "EFECTIVO",
    })
    return prod


def test_top_productos_sin_ventas(client: TestClient) -> None:
    """GET /top-productos sin ventas devuelve lista vacia."""
    r = client.get("/api/dashboard/top-productos")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_top_productos_con_ventas(client: TestClient) -> None:
    """GET /top-productos devuelve productos ordenados por total facturado."""
    _crear_venta_dashboard(client, "TOP-A", "500", "2")
    _crear_venta_dashboard(client, "TOP-B", "100", "1")
    r = client.get("/api/dashboard/top-productos?limite=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2
    assert data[0]["total_facturado"] >= data[1]["total_facturado"]
    assert "posicion" in data[0]
    assert "nombre" in data[0]
    assert "unidades_vendidas" in data[0]


def test_top_productos_limite(client: TestClient) -> None:
    """GET /top-productos con limite=1 devuelve solo 1 resultado."""
    _crear_venta_dashboard(client, "TOP-LIM-A", "200")
    _crear_venta_dashboard(client, "TOP-LIM-B", "300")
    r = client.get("/api/dashboard/top-productos?limite=1")
    assert r.status_code == 200
    assert len(r.json()) <= 1


# ---------------------------------------------------------------------------
# Tests: tendencias de ventas (docs Modulo 1 ss3.1)
# ---------------------------------------------------------------------------

def test_tendencias_diario(client: TestClient) -> None:
    """GET /tendencias?periodo=diario devuelve N dias."""
    r = client.get("/api/dashboard/tendencias?periodo=diario&cantidad_periodos=7")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 7
    assert "total_ventas" in data[0]
    assert "cantidad_ventas" in data[0]
    assert "etiqueta" in data[0]


def test_tendencias_semanal(client: TestClient) -> None:
    """GET /tendencias?periodo=semanal devuelve N semanas."""
    r = client.get("/api/dashboard/tendencias?periodo=semanal&cantidad_periodos=4")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4
    assert "ticket_promedio" in data[0]


def test_tendencias_mensual(client: TestClient) -> None:
    """GET /tendencias?periodo=mensual devuelve N meses."""
    r = client.get("/api/dashboard/tendencias?periodo=mensual&cantidad_periodos=3")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert "etiqueta" in data[0]


def test_tendencias_periodo_invalido(client: TestClient) -> None:
    """GET /tendencias con periodo invalido retorna 400."""
    r = client.get("/api/dashboard/tendencias?periodo=anual")
    assert r.status_code == 400
