"""Tests del API Integraciones."""
from fastapi.testclient import TestClient


def test_estado_integraciones(client: TestClient) -> None:
    """GET estado devuelve estructura de integraciones por tipo."""
    r = client.get("/api/integraciones/estado")
    assert r.status_code == 200
    data = r.json()
    assert "facturacion_electronica" in data
    assert "pasarelas_pago" in data
    assert data["facturacion_electronica"]["activo"] is False
    assert "mensaje" in data["facturacion_electronica"]
    # Todos los tipos del catálogo deben tener estado
    assert "hardware_pos" in data
    assert "mensajeria" in data


def test_listar_tipos_integracion(client: TestClient) -> None:
    """GET tipos devuelve catálogo de tipos de integración soportados."""
    r = client.get("/api/integraciones/tipos")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    codigos = [t["codigo"] for t in data]
    assert "facturacion_electronica" in codigos
    assert "pasarelas_pago" in codigos
    for t in data:
        assert "codigo" in t
        assert "nombre" in t
        assert "descripcion" in t


def test_configurar_activo_ok(client: TestClient) -> None:
    """PATCH {tipo}/activo con activo=true actualiza estado y GET estado lo refleja."""
    r = client.patch(
        "/api/integraciones/facturacion_electronica/activo",
        json={"activo": True},
    )
    assert r.status_code == 200
    assert r.json() == {"tipo_codigo": "facturacion_electronica", "activo": True}
    estado = client.get("/api/integraciones/estado").json()
    assert estado["facturacion_electronica"]["activo"] is True
    assert "Activo" in estado["facturacion_electronica"]["mensaje"]


def test_configurar_activo_desactivar(client: TestClient) -> None:
    """PATCH activo=false deja la integración desactivada."""
    client.patch("/api/integraciones/hardware_pos/activo", json={"activo": True})
    r = client.patch("/api/integraciones/hardware_pos/activo", json={"activo": False})
    assert r.status_code == 200
    assert r.json()["activo"] is False
    estado = client.get("/api/integraciones/estado").json()
    assert estado["hardware_pos"]["activo"] is False


def test_configurar_activo_tipo_invalido_404(client: TestClient) -> None:
    """PATCH con tipo_codigo inexistente devuelve 404."""
    r = client.patch(
        "/api/integraciones/tipo_inexistente/activo",
        json={"activo": True},
    )
    assert r.status_code == 404


def test_configurar_activo_sin_body_422(client: TestClient) -> None:
    """PATCH sin 'activo' en el body devuelve 422."""
    r = client.patch("/api/integraciones/mensajeria/activo", json={})
    assert r.status_code == 422


def test_obtener_config_vacio(client: TestClient) -> None:
    """GET {tipo}/config sin config guardada devuelve 200 y objeto vacío."""
    r = client.get("/api/integraciones/pasarelas_pago/config")
    assert r.status_code == 200
    assert r.json() == {}


def test_obtener_config_tipo_invalido_404(client: TestClient) -> None:
    """GET config con tipo inexistente devuelve 404."""
    r = client.get("/api/integraciones/tipo_falso/config")
    assert r.status_code == 404


def test_guardar_config_y_obtener(client: TestClient) -> None:
    """PUT config guarda y GET devuelve el mismo objeto."""
    payload = {"api_key": "sk_test_123", "ambiente": "sandbox"}
    r = client.put("/api/integraciones/facturacion_electronica/config", json=payload)
    assert r.status_code == 200
    assert r.json() == payload
    r2 = client.get("/api/integraciones/facturacion_electronica/config")
    assert r2.status_code == 200
    assert r2.json() == payload


def test_guardar_config_actualiza(client: TestClient) -> None:
    """PUT config sobre tipo ya configurado actualiza."""
    client.put("/api/integraciones/mensajeria/config", json={"provider": "whatsapp"})
    r = client.put("/api/integraciones/mensajeria/config", json={"provider": "email", "smtp": "smtp.ejemplo.com"})
    assert r.status_code == 200
    assert r.json()["provider"] == "email"
    r2 = client.get("/api/integraciones/mensajeria/config")
    assert r2.json()["smtp"] == "smtp.ejemplo.com"


def test_guardar_config_tipo_invalido_404(client: TestClient) -> None:
    """PUT config con tipo inexistente devuelve 404."""
    r = client.put("/api/integraciones/inexistente/config", json={"key": "value"})
    assert r.status_code == 404


# --- Logs de integración ---


def test_listar_logs_vacio(client: TestClient) -> None:
    """GET logs sin registros devuelve lista vacía."""
    r = client.get("/api/integraciones/logs")
    assert r.status_code == 200
    assert r.json() == []


def test_registrar_log_ok(client: TestClient) -> None:
    """POST logs con tipo_codigo válido devuelve 200 y el log creado."""
    payload = {
        "tipo_codigo": "facturacion_electronica",
        "exito": False,
        "mensaje": "Error de conexión AFIP",
    }
    r = client.post("/api/integraciones/logs", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] is not None
    assert data["tipo_codigo"] == "facturacion_electronica"
    assert data["exito"] is False
    assert data["mensaje"] == "Error de conexión AFIP"
    assert data["detalle"] is None
    assert "created_at" in data


def test_registrar_log_con_detalle(client: TestClient) -> None:
    """POST logs con detalle opcional guarda el detalle."""
    payload = {
        "tipo_codigo": "pasarelas_pago",
        "exito": True,
        "mensaje": "Pago confirmado",
        "detalle": "ref_123",
    }
    r = client.post("/api/integraciones/logs", json=payload)
    assert r.status_code == 200
    assert r.json()["detalle"] == "ref_123"


def test_listar_logs_incluye_registrado(client: TestClient) -> None:
    """GET logs después de POST devuelve el log en la lista."""
    client.post(
        "/api/integraciones/logs",
        json={"tipo_codigo": "mensajeria", "exito": True, "mensaje": "Email enviado"},
    )
    r = client.get("/api/integraciones/logs")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    found = next((x for x in items if x["mensaje"] == "Email enviado"), None)
    assert found is not None
    assert found["tipo_codigo"] == "mensajeria"
    assert found["exito"] is True


def test_listar_logs_filtro_tipo(client: TestClient) -> None:
    """GET logs?tipo_codigo=X devuelve solo logs de ese tipo."""
    client.post(
        "/api/integraciones/logs",
        json={"tipo_codigo": "hardware_pos", "exito": False, "mensaje": "Impresora offline"},
    )
    client.post(
        "/api/integraciones/logs",
        json={"tipo_codigo": "mensajeria", "exito": True, "mensaje": "SMS ok"},
    )
    r = client.get("/api/integraciones/logs?tipo_codigo=hardware_pos")
    assert r.status_code == 200
    items = r.json()
    assert all(x["tipo_codigo"] == "hardware_pos" for x in items)


def test_registrar_log_tipo_invalido_404(client: TestClient) -> None:
    """POST logs con tipo_codigo no soportado devuelve 404."""
    r = client.post(
        "/api/integraciones/logs",
        json={"tipo_codigo": "tipo_falso", "exito": False, "mensaje": "Error"},
    )
    assert r.status_code == 404


def test_registrar_log_sin_exito_422(client: TestClient) -> None:
    """POST logs sin 'exito' devuelve 422."""
    r = client.post(
        "/api/integraciones/logs",
        json={"tipo_codigo": "facturacion_electronica", "mensaje": "Error"},
    )
    assert r.status_code == 422


def test_registrar_log_sin_mensaje_422(client: TestClient) -> None:
    """POST logs sin 'mensaje' devuelve 422."""
    r = client.post(
        "/api/integraciones/logs",
        json={"tipo_codigo": "facturacion_electronica", "exito": False},
    )
    assert r.status_code == 422


def test_resumen_integraciones_estructura(client: TestClient) -> None:
    """GET resumen devuelve estructura con resumen y por_tipo para todos los tipos."""
    r_tipos = client.get("/api/integraciones/tipos")
    assert r_tipos.status_code == 200
    tipos = r_tipos.json()
    codigos = [t["codigo"] for t in tipos]

    r = client.get("/api/integraciones/resumen")
    assert r.status_code == 200
    data = r.json()
    assert "resumen" in data and "por_tipo" in data
    assert data["resumen"]["total_tipos"] == len(codigos)
    for codigo in codigos:
        assert codigo in data["por_tipo"]
        entry = data["por_tipo"][codigo]
        assert "activo" in entry
        assert "configurado" in entry
        assert "ultimo_log_exito" in entry
        assert "ultimo_log_mensaje" in entry
        assert "ultimo_log_fecha" in entry


def test_resumen_integraciones_refleja_activo_y_ultimo_log(client: TestClient) -> None:
    """Resumen refleja activo/configurado y el último log por tipo."""
    # Activar facturación electrónica y guardar config
    client.patch("/api/integraciones/facturacion_electronica/activo", json={"activo": True})
    client.put(
        "/api/integraciones/facturacion_electronica/config",
        json={"api_key": "xyz", "ambiente": "prod"},
    )
    # Registrar log de éxito
    client.post(
        "/api/integraciones/logs",
        json={
            "tipo_codigo": "facturacion_electronica",
            "exito": True,
            "mensaje": "Conexión OK",
        },
    )
    r = client.get("/api/integraciones/resumen")
    assert r.status_code == 200
    entry = r.json()["por_tipo"]["facturacion_electronica"]
    assert entry["activo"] is True
    assert entry["configurado"] is True
    assert entry["ultimo_log_exito"] is True
    assert entry["ultimo_log_mensaje"] == "Conexión OK"
    assert entry["ultimo_log_fecha"] is not None


def test_probar_conexion_tipo_invalido_404(client: TestClient) -> None:
    """POST {tipo}/probar con tipo inválido devuelve 404."""
    r = client.post("/api/integraciones/tipo_inexistente/probar")
    assert r.status_code == 404


def test_probar_conexion_sin_config_devuelve_sin_configuracion(client: TestClient) -> None:
    """POST {tipo}/probar sin config previa devuelve exito=false y registra log visible en resumen."""
    r = client.post("/api/integraciones/pasarelas_pago/probar")
    assert r.status_code == 200
    assert r.json()["tipo_codigo"] == "pasarelas_pago"
    assert r.json()["exito"] is False
    assert r.json()["motivo"] == "sin_configuracion"

    resumen = client.get("/api/integraciones/resumen").json()
    entry = resumen["por_tipo"]["pasarelas_pago"]
    assert entry["ultimo_log_exito"] is False
    assert "Sin configuración" in (entry["ultimo_log_mensaje"] or "")


def test_probar_conexion_con_config_ok_registra_log_exitoso(client: TestClient) -> None:
    """POST {tipo}/probar con config previa devuelve ok y registra log de éxito visible en resumen."""
    client.put("/api/integraciones/facturacion_electronica/config", json={"api_key": "k", "ambiente": "sandbox"})
    r = client.post("/api/integraciones/facturacion_electronica/probar")
    assert r.status_code == 200
    assert r.json()["exito"] is True
    assert r.json()["motivo"] == "ok"

    resumen = client.get("/api/integraciones/resumen").json()
    entry = resumen["por_tipo"]["facturacion_electronica"]
    assert entry["configurado"] is True
    assert entry["ultimo_log_exito"] is True
    assert "Prueba de conexión exitosa" in (entry["ultimo_log_mensaje"] or "")


# --- Dispositivos POS (docs Módulo 8 §5 Hardware POS) ---


def test_listar_dispositivos_pos_devuelve_lista(client: TestClient) -> None:
    """GET /integraciones/dispositivos devuelve 200 y lista de dispositivos con codigo, nombre, descripcion."""
    r = client.get("/api/integraciones/dispositivos")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    for d in data:
        assert "codigo" in d
        assert "nombre" in d
        assert "descripcion" in d


def test_listar_dispositivos_pos_incluye_impresora_lector_balanza(client: TestClient) -> None:
    """GET /integraciones/dispositivos incluye impresora, lector_barras y balanza."""
    r = client.get("/api/integraciones/dispositivos")
    assert r.status_code == 200
    codigos = [d["codigo"] for d in r.json()]
    assert "impresora" in codigos
    assert "lector_barras" in codigos
    assert "balanza" in codigos


# --- Flujo alternativo sin impresora (docs Módulo 8 §6) ---


def test_flujo_alternativo_sin_impresora_devuelve_estructura(client: TestClient) -> None:
    """GET /integraciones/flujo-alternativo-sin-impresora devuelve 200 con activo, descripcion, pasos y beneficios."""
    r = client.get("/api/integraciones/flujo-alternativo-sin-impresora")
    assert r.status_code == 200
    data = r.json()
    assert data.get("activo") is True
    assert "descripcion" in data
    assert "pasos" in data
    assert "beneficios" in data
    assert len(data["pasos"]) >= 5
    assert all("orden" in p and "accion" in p and "titulo" in p for p in data["pasos"])


def test_flujo_alternativo_sin_impresora_pasos_ordenados(client: TestClient) -> None:
    """Los pasos del flujo incluyen solicitar DNI, buscar/crear cliente, email y enviar comprobante."""
    r = client.get("/api/integraciones/flujo-alternativo-sin-impresora")
    assert r.status_code == 200
    acciones = [p["accion"] for p in r.json()["pasos"]]
    assert "solicitar_dni" in acciones
    assert "solicitar_email" in acciones
    assert "enviar_comprobante_digital" in acciones


# ---------------------------------------------------------------------------
# Tests: estado de dispositivo (docs Módulo 8 §5-6)
# ---------------------------------------------------------------------------

def test_estado_dispositivo_sin_config_no_disponible(client: TestClient) -> None:
    """GET /dispositivos/{codigo}/estado sin hardware_pos configurado → disponible=False."""
    r = client.get("/api/integraciones/dispositivos/impresora/estado")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "impresora"
    assert "disponible" in data
    assert data["disponible"] is False


def test_estado_dispositivo_codigo_invalido_404(client: TestClient) -> None:
    """GET /dispositivos/{codigo}/estado con código no existente devuelve 404."""
    r = client.get("/api/integraciones/dispositivos/telefax/estado")
    assert r.status_code == 404


def test_estado_dispositivo_con_hardware_pos_activo(client: TestClient) -> None:
    """Con hardware_pos activo, el dispositivo aparece como disponible."""
    client.patch("/api/integraciones/hardware_pos/activo", json={"activo": True})
    r = client.get("/api/integraciones/dispositivos/lector_barras/estado")
    assert r.status_code == 200
    assert r.json()["disponible"] is True


def test_estado_dispositivo_config_explicita_false(client: TestClient) -> None:
    """Si la config marca el dispositivo explícitamente como False → no disponible."""
    client.patch("/api/integraciones/hardware_pos/activo", json={"activo": True})
    client.put("/api/integraciones/hardware_pos/config", json={"balanza": False, "impresora": True})

    r_bal = client.get("/api/integraciones/dispositivos/balanza/estado")
    assert r_bal.status_code == 200
    assert r_bal.json()["disponible"] is False

    r_imp = client.get("/api/integraciones/dispositivos/impresora/estado")
    assert r_imp.status_code == 200
    assert r_imp.json()["disponible"] is True


def test_estado_todos_dispositivos_pos(client: TestClient) -> None:
    """Los tres dispositivos (impresora, lector_barras, balanza) responden a estado."""
    for codigo in ("impresora", "lector_barras", "balanza"):
        r = client.get(f"/api/integraciones/dispositivos/{codigo}/estado")
        assert r.status_code == 200
        data = r.json()
        assert data["codigo"] == codigo
        assert "disponible" in data
        assert "motivo" in data


# ---------------------------------------------------------------------------
# Tests: flujo alternativo ejecutar (docs Módulo 8 §6)
# ---------------------------------------------------------------------------

def _crear_venta_minima(client) -> int:
    """Helper: crea producto + stock + venta y retorna venta_id."""
    r_prod = client.post(
        "/api/productos",
        json={"sku": "INT-V1", "nombre": "Prod Integración", "precio_venta": "10", "activo": True},
    )
    assert r_prod.status_code == 201
    prod_id = r_prod.json()["id"]
    client.post("/api/inventario/ingresar", json={"producto_id": prod_id, "cantidad": "5", "ubicacion": "GONDOLA"})
    r_venta = client.post(
        "/api/ventas",
        json={"items": [{"producto_id": prod_id, "cantidad": "1"}], "descuento": "0", "metodo_pago": "EFECTIVO"},
    )
    assert r_venta.status_code == 200
    return r_venta.json()["venta_id"]


def test_flujo_alternativo_ejecutar_crea_cliente_nuevo(client: TestClient) -> None:
    """POST /flujo-alternativo.../ejecutar con DNI nuevo crea persona+cliente y registra log."""
    venta_id = _crear_venta_minima(client)
    r = client.post(
        "/api/integraciones/flujo-alternativo-sin-impresora/ejecutar",
        json={
            "venta_id": venta_id,
            "documento_cliente": "ALT-DOC-001",
            "email": "cliente@test.com",
            "nombre_cliente": "Carlos",
            "apellido_cliente": "Ruiz",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["exito"] is True
    assert data["venta_id"] == venta_id
    assert data["email"] == "cliente@test.com"
    assert data["accion_cliente"] == "creado"
    assert data["cliente_id"] is not None
    assert data["persona_id"] is not None

    # Verificar que el log de mensajería quedó registrado
    logs = client.get("/api/integraciones/logs?tipo_codigo=mensajeria").json()
    assert any(str(venta_id) in (lg.get("mensaje") or "") for lg in logs)


def test_flujo_alternativo_ejecutar_cliente_existente(client: TestClient) -> None:
    """Si el DNI ya existe como persona, el flujo lo encuentra en lugar de crear."""
    # Crear persona con DNI conocido
    r_pers = client.post(
        "/api/personas",
        json={"nombre": "Ana", "apellido": "García", "documento": "EXIST-DOC-002", "activo": True},
    )
    assert r_pers.status_code == 201
    persona_id_orig = r_pers.json()["id"]

    venta_id = _crear_venta_minima(client)
    r = client.post(
        "/api/integraciones/flujo-alternativo-sin-impresora/ejecutar",
        json={
            "venta_id": venta_id,
            "documento_cliente": "EXIST-DOC-002",
            "email": "ana@test.com",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["exito"] is True
    assert data["persona_id"] == persona_id_orig
    assert data["accion_cliente"] in ("encontrado", "cliente_creado_para_persona_existente")


def test_flujo_alternativo_ejecutar_venta_inexistente(client: TestClient) -> None:
    """Si la venta no existe, el flujo retorna exito=False con motivo 'venta_no_encontrada'."""
    r = client.post(
        "/api/integraciones/flujo-alternativo-sin-impresora/ejecutar",
        json={
            "venta_id": 999999,
            "documento_cliente": "DOC-XYZ",
            "email": "x@test.com",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["exito"] is False
    assert data["motivo"] == "venta_no_encontrada"


# ---------------------------------------------------------------------------
# Tests: enviar comprobante digital (docs Módulo 8 §8)
# ---------------------------------------------------------------------------

def test_enviar_comprobante_digital_ok(client: TestClient) -> None:
    """POST /mensajeria/enviar-comprobante con venta existente registra log y retorna exito=True."""
    venta_id = _crear_venta_minima(client)
    r = client.post(
        "/api/integraciones/mensajeria/enviar-comprobante",
        json={"venta_id": venta_id, "email": "dest@test.com", "tipo_comprobante": "factura"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["exito"] is True
    assert data["motivo"] == "enviado"
    assert data["venta_id"] == venta_id
    assert data["email"] == "dest@test.com"
    assert data["tipo_comprobante"] == "factura"
    assert "mensaje" in data

    # Verificar log registrado en mensajería
    logs = client.get("/api/integraciones/logs?tipo_codigo=mensajeria").json()
    assert any(str(venta_id) in (lg.get("mensaje") or "") for lg in logs)


def test_enviar_comprobante_digital_venta_inexistente(client: TestClient) -> None:
    """POST /mensajeria/enviar-comprobante con venta inexistente retorna exito=False."""
    r = client.post(
        "/api/integraciones/mensajeria/enviar-comprobante",
        json={"venta_id": 999999, "email": "x@test.com"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["exito"] is False
    assert data["motivo"] == "venta_no_encontrada"

    # Debe quedar log de fallo
    logs = client.get("/api/integraciones/logs?tipo_codigo=mensajeria").json()
    assert any(lg["exito"] is False for lg in logs)


def test_enviar_comprobante_digital_mensajeria_activa_vs_simulada(client: TestClient) -> None:
    """Con mensajería activa el mensaje no lleva [SIM]; sin activar sí lo incluye."""
    venta_id = _crear_venta_minima(client)

    # Sin activar mensajería → mensaje lleva [SIM]
    r1 = client.post(
        "/api/integraciones/mensajeria/enviar-comprobante",
        json={"venta_id": venta_id, "email": "a@b.com"},
    )
    assert "[SIM]" in r1.json()["mensaje"]

    # Activar mensajería
    client.patch("/api/integraciones/mensajeria/activo", json={"activo": True})
    r2 = client.post(
        "/api/integraciones/mensajeria/enviar-comprobante",
        json={"venta_id": venta_id, "email": "a@b.com"},
    )
    assert "[SIM]" not in r2.json()["mensaje"]


# ---------------------------------------------------------------------------
# Tests: estadisticas de logs (metricas de exito/fallo)
# ---------------------------------------------------------------------------

def test_estadisticas_logs_vacio(client: TestClient) -> None:
    """GET /logs/estadisticas sin logs previos devuelve dict vacio."""
    r = client.get("/api/integraciones/logs/estadisticas")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_estadisticas_logs_con_registros(client: TestClient) -> None:
    """GET /logs/estadisticas refleja correctamente exitosos y fallos."""
    client.post("/api/integraciones/logs", json={"tipo_codigo": "mensajeria", "exito": True, "mensaje": "ok1"})
    client.post("/api/integraciones/logs", json={"tipo_codigo": "mensajeria", "exito": True, "mensaje": "ok2"})
    client.post("/api/integraciones/logs", json={"tipo_codigo": "mensajeria", "exito": False, "mensaje": "fallo1"})
    r = client.get("/api/integraciones/logs/estadisticas")
    assert r.status_code == 200
    data = r.json()
    assert "mensajeria" in data
    stats = data["mensajeria"]
    assert stats["total"] >= 3
    assert stats["exitosos"] >= 2
    assert stats["fallos"] >= 1
    assert "tasa_exito_pct" in stats


def test_estadisticas_logs_filtro_tipo(client: TestClient) -> None:
    """GET /logs/estadisticas?tipo_codigo filtra por tipo."""
    client.post("/api/integraciones/logs", json={"tipo_codigo": "hardware_pos", "exito": True, "mensaje": "hw ok"})
    r = client.get("/api/integraciones/logs/estadisticas?tipo_codigo=hardware_pos")
    assert r.status_code == 200
    data = r.json()
    assert "hardware_pos" in data
    assert "mensajeria" not in data


# ---------------------------------------------------------------------------
# Tests: exportacion contable (docs Modulo 8 ss10)
# ---------------------------------------------------------------------------

def test_exportacion_contable_sin_datos(client: TestClient) -> None:
    """GET /contable/exportar sin datos devuelve estructura vacia."""
    r = client.get("/api/integraciones/contable/exportar")
    assert r.status_code == 200
    data = r.json()
    assert "ventas" in data
    assert "movimientos_caja" in data
    assert "resumen_ventas" in data
    assert "resumen_caja" in data
    assert "exportado_en" in data


def test_exportacion_contable_con_venta(client: TestClient) -> None:
    """GET /contable/exportar con venta existente la incluye en el resultado."""
    venta_id = _crear_venta_minima(client)
    r = client.get("/api/integraciones/contable/exportar")
    assert r.status_code == 200
    data = r.json()
    ids_ventas = [v["id"] for v in data["ventas"]]
    assert venta_id in ids_ventas
    assert data["resumen_ventas"]["cantidad"] >= 1


def test_exportacion_contable_fechas_invalidas(client: TestClient) -> None:
    """GET /contable/exportar con fecha_desde > fecha_hasta retorna 400."""
    r = client.get("/api/integraciones/contable/exportar?fecha_desde=2025-12-31&fecha_hasta=2025-01-01")
    assert r.status_code == 400


def test_exportacion_contable_registra_log(client: TestClient) -> None:
    """GET /contable/exportar registra log de integracion_contable."""
    client.get("/api/integraciones/contable/exportar")
    logs = client.get("/api/integraciones/logs?tipo_codigo=integracion_contable").json()
    assert len(logs) >= 1
    assert logs[0]["exito"] is True


# ---------------------------------------------------------------------------
# Tests: API externa (docs Modulo 8 ss11)
# ---------------------------------------------------------------------------

def test_resumen_api_externa_estructura(client: TestClient) -> None:
    """GET /api-externa/resumen devuelve estructura esperada."""
    r = client.get("/api/integraciones/api-externa/resumen")
    assert r.status_code == 200
    data = r.json()
    assert "inventario" in data
    assert "ventas_hoy" in data
    assert "sistema" in data
    assert "total_productos_activos" in data["inventario"]
    assert "cantidad" in data["ventas_hoy"]


def test_datos_producto_externo_ok(client: TestClient) -> None:
    """GET /api-externa/productos/{id} devuelve datos del producto."""
    prod_r = client.post("/api/productos", json={"sku": "PRODEXT01", "nombre": "Prod externo", "precio_venta": 99.5})
    assert prod_r.status_code == 201
    prod_id = prod_r.json()["id"]
    r = client.get(f"/api/integraciones/api-externa/productos/{prod_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == prod_id
    assert data["sku"] == "PRODEXT01"
    assert "precio" in data
    assert "stock_actual" in data


def test_datos_producto_externo_404(client: TestClient) -> None:
    """GET /api-externa/productos/{id} con producto inexistente retorna 404."""
    r = client.get("/api/integraciones/api-externa/productos/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests: backups (docs Modulo 8 ss12)
# ---------------------------------------------------------------------------

def test_estado_backup_inicial(client: TestClient) -> None:
    """GET /backup/estado devuelve estructura de estado del backup."""
    r = client.get("/api/integraciones/backup/estado")
    assert r.status_code == 200
    data = r.json()
    assert "estado" in data
    assert "total_backups" in data
    assert "historial" in data


def test_ejecutar_backup_manual(client: TestClient) -> None:
    """POST /backup/ejecutar sin body ejecuta backup manual y retorna exito=True."""
    r = client.post("/api/integraciones/backup/ejecutar")
    assert r.status_code == 200
    data = r.json()
    assert data["exito"] is True
    assert data["frecuencia"] == "manual"
    assert "timestamp" in data


def test_ejecutar_backup_frecuencia_daily(client: TestClient) -> None:
    """POST /backup/ejecutar con frecuencia=daily ejecuta backup diario."""
    r = client.post("/api/integraciones/backup/ejecutar", json={"frecuencia": "daily"})
    assert r.status_code == 200
    data = r.json()
    assert data["exito"] is True
    assert data["frecuencia"] == "daily"


def test_ejecutar_backup_frecuencia_invalida(client: TestClient) -> None:
    """POST /backup/ejecutar con frecuencia invalida retorna 400."""
    r = client.post("/api/integraciones/backup/ejecutar", json={"frecuencia": "anual_invalida"})
    assert r.status_code == 400


def test_estado_backup_refleja_ejecutado(client: TestClient) -> None:
    """GET /backup/estado tras ejecutar backup refleja el cambio."""
    client.post("/api/integraciones/backup/ejecutar", json={"frecuencia": "weekly"})
    r = client.get("/api/integraciones/backup/estado")
    data = r.json()
    assert data["estado"] == "ok"
    assert data["total_backups"] >= 1


# ---------------------------------------------------------------------------
# Tests: datos fiscales de venta (docs Modulo 8 ss4)
# ---------------------------------------------------------------------------

def test_datos_fiscales_venta_ok(client: TestClient) -> None:
    """GET /fiscal/venta/{id} devuelve datos fiscales de la venta."""
    venta_id = _crear_venta_minima(client)
    r = client.get(f"/api/integraciones/fiscal/venta/{venta_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["venta_id"] == venta_id
    assert "total" in data
    assert "items" in data
    assert "emisor" in data
    assert "tipo_comprobante" in data


def test_datos_fiscales_venta_404(client: TestClient) -> None:
    """GET /fiscal/venta/{id} con venta inexistente retorna 404."""
    r = client.get("/api/integraciones/fiscal/venta/999999")
    assert r.status_code == 404


def test_datos_fiscales_venta_emisor_con_credenciales(client: TestClient) -> None:
    """GET /fiscal/venta/{id} incluye credenciales fiscales de configuracion."""
    client.put("/api/configuracion/integraciones", json={
        "credenciales_fiscales": {"cuit": "30123456789", "punto_venta": 3, "modo_produccion": False}
    })
    venta_id = _crear_venta_minima(client)
    r = client.get(f"/api/integraciones/fiscal/venta/{venta_id}")
    assert r.status_code == 200
    emisor = r.json()["emisor"]
    assert emisor["cuit"] == "30123456789"
    assert emisor["punto_venta"] == 3


# ---------------------------------------------------------------------------
# Tests: reconciliacion de pagos (docs Modulo 8 ss7)
# ---------------------------------------------------------------------------

def test_reconciliar_pagos_sin_ventas(client: TestClient) -> None:
    """POST /pasarela/reconciliar con pagos que no coinciden con ventas."""
    body = {
        "tipo_pasarela": "mercadopago",
        "pagos": [
            {"referencia_externa": "REF001", "monto": 99999.99, "estado": "aprobado"}
        ]
    }
    r = client.post("/api/integraciones/pasarela/reconciliar", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["tipo_pasarela"] == "mercadopago"
    assert data["total_pagos"] == 1
    assert len(data["sin_coincidencia"]) == 1
    assert data["resumen"]["conciliados"] == 0


def test_reconciliar_pagos_con_coincidencia(client: TestClient) -> None:
    """POST /pasarela/reconciliar reconcilia pagos que coinciden con ventas por monto."""
    venta_id = _crear_venta_minima(client)
    venta_data = client.get(f"/api/ventas/{venta_id}").json()
    total_venta = venta_data.get("total", 0)
    body = {
        "tipo_pasarela": "getnet",
        "pagos": [
            {"referencia_externa": "GETNET-001", "monto": total_venta, "estado": "aprobado"}
        ]
    }
    r = client.post("/api/integraciones/pasarela/reconciliar", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["resumen"]["conciliados"] >= 0
    assert "tasa_conciliacion_pct" in data["resumen"]


def test_reconciliar_pagos_pasarela_invalida(client: TestClient) -> None:
    """POST /pasarela/reconciliar con pasarela no soportada retorna 400."""
    body = {
        "tipo_pasarela": "pasarela_desconocida_xyz",
        "pagos": [
            {"referencia_externa": "R1", "monto": 100.0, "estado": "aprobado"}
        ]
    }
    r = client.post("/api/integraciones/pasarela/reconciliar", json=body)
    assert r.status_code == 400


def test_reconciliar_pagos_registra_log(client: TestClient) -> None:
    """POST /pasarela/reconciliar registra log en pasarelas_pago."""
    body = {
        "tipo_pasarela": "stripe",
        "pagos": [
            {"referencia_externa": "STRIPE-999", "monto": 50000.0, "estado": "aprobado"}
        ]
    }
    client.post("/api/integraciones/pasarela/reconciliar", json=body)
    logs = client.get("/api/integraciones/logs?tipo_codigo=pasarelas_pago").json()
    assert len(logs) >= 1
