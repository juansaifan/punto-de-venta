function $(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  $(id).textContent = value;
}

function showError(err) {
  const box = $("errorBox");
  box.hidden = false;
  $("errorText").textContent = String(err?.stack || err?.message || err);
}

function clearError() {
  $("errorBox").hidden = true;
  $("errorText").textContent = "";
}

function normalizeBaseUrl(raw) {
  const v = String(raw || "").trim().replace(/\/+$/, "");
  return v || "http://localhost:8000";
}

async function fetchJson(url) {
  // Esta UI debe funcionar sin backend: para el Módulo 1 usamos mocks.
  if (window.MockDashboardApi?.fetchJson) {
    return await window.MockDashboardApi.fetchJson(url);
  }

  // Fallback (no esperado en modo “mock”).
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    throw new Error(`HTTP ${r.status} ${r.statusText}\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  return data;
}

function setDashboardLoading(loading) {
  const msg = loading ? "Cargando..." : "—";

  // KPIs caja / alertas
  setText("cajaAbierta", msg);
  setText("cajaId", msg);
  setText("saldoTeorico", msg);
  setText("stockBajo", loading ? "..." : 0);
  setText("proxVencer", loading ? "..." : 0);
  setText("stockBajoDetalle", loading ? "[]" : "[]");
  setText("proxVencerDetalle", loading ? "[]" : "[]");

  // KPIs indicadores
  setText("kpiVentasDia", loading ? "..." : 0);
  setText("kpiTotalDia", loading ? "..." : 0);
  setText("kpiTicket", loading ? "..." : 0);
  setText("kpiStockBajo", loading ? "..." : 0);
  setText("kpiValorInv", loading ? "..." : 0);
  setText("kpiSaldoCaja", msg);
  setText("indicadoresJson", loading ? "{...}" : "{}");

  // Tablas: comparativos / ventas por hora / alertas detalle
  const setTableLoading = (bodyId, cols) => {
    const body = $(bodyId);
    if (!body) return;
    body.innerHTML = `<tr><td colspan="${cols}" class="muted">${loading ? "Cargando..." : "—"}</td></tr>`;
  };
  setTableLoading("kpiComparativosBody", 4);
  setTableLoading("ventasHoraBody", 4);
  setTableLoading("alertStockBajoBody", 4);
  setTableLoading("alertVencerBody", 4);

  // Panel lateral
  setText("plSalud", msg);
  setText("plProm7", msg);
  setText("plPromDow", msg);
  setText("plPron", msg);
  setText("plPe", msg);
  setText("plObj", msg);
  setText("plJson", loading ? "{...}" : "{}");

  const btn = $("refresh");
  if (btn) btn.disabled = loading;
}

function setTab(tab) {
  const tabs = Array.from(document.querySelectorAll(".tab"));
  for (const t of tabs) t.classList.toggle("active", t.dataset.tab === tab);

  // resumen = cards por defecto (caja + alertas)
  const indicadores = $("indicadoresCard");
  indicadores.hidden = tab !== "indicadores";
  const pl = $("panelLateralCard");
  if (pl) pl.hidden = tab !== "indicadores";

  const pos = $("posCard");
  pos.hidden = tab !== "pos";

  const cfg = $("configCard");
  cfg.hidden = tab !== "config";

  if (tab === "pos") {
    initPosIfNeeded().catch(showError);
    $("posBuscar")?.focus();
  }
  if (tab === "config") {
    initConfigIfNeeded().catch(showError);
  }
}

async function refreshResumen(base, dias) {
  const url = `${base}/api/dashboard/alertas-operativas?dias_vencimiento=${encodeURIComponent(dias)}`;
  const data = await fetchJson(url);

  const t = data.tesoreria || {};
  setText("cajaAbierta", t.caja_abierta ? "Sí" : "No");
  setText("cajaId", t.caja_id ?? "—");
  setText("saldoTeorico", t.saldo_caja_teorico ?? "—");

  const inv = data.inventario || {};
  const res = inv.resumen || {};
  setText("stockBajo", res.stock_bajo ?? 0);
  setText("proxVencer", res.proximos_vencer ?? 0);
  setText("stockBajoDetalle", JSON.stringify(inv.stock_bajo || [], null, 2));
  setText("proxVencerDetalle", JSON.stringify(inv.proximos_vencer || [], null, 2));
}

async function refreshIndicadores(base) {
  const url = `${base}/api/dashboard/indicadores`;
  const data = await fetchJson(url);

  setText("kpiVentasDia", data.ventas_del_dia ?? 0);
  setText("kpiTotalDia", data.total_ventas_del_dia ?? 0);
  setText("kpiTicket", data.ticket_promedio ?? 0);
  setText("kpiStockBajo", data.productos_stock_bajo ?? 0);
  setText("kpiValorInv", data.valor_inventario ?? 0);
  setText("kpiSaldoCaja", data.saldo_caja_teorico ?? "—");
  setText("indicadoresJson", JSON.stringify(data, null, 2));
}

function renderComparativos(data) {
  const body = $("kpiComparativosBody");
  if (!body) return;
  const rows = Array.isArray(data) ? data : [];
  if (rows.length === 0) {
    body.innerHTML = '<tr><td colspan="4" class="muted">Sin datos</td></tr>';
    return;
  }
  body.innerHTML = rows
    .map((r) => {
      const kpi = r.kpi ?? "—";
      const hoy = r.valor ?? 0;
      const ant = r.valor_anterior ?? 0;
      const varPct = r.variacion_pct;
      let badge = "—";
      if (typeof varPct === "number") {
        const cls = varPct >= 0 ? "up" : "down";
        const s = `${varPct >= 0 ? "+" : ""}${varPct.toFixed(2)}%`;
        badge = `<span class="badge ${cls}">${s}</span>`;
      }
      return `<tr><td>${kpi}</td><td>${hoy}</td><td>${ant}</td><td>${badge}</td></tr>`;
    })
    .join("");
}

async function refreshIndicadoresComparativos(base) {
  const data = await fetchJson(`${base}/api/dashboard/indicadores-comparativos`);
  // svc retorna dict con keys por KPI o lista? normalizamos a lista
  if (Array.isArray(data)) {
    renderComparativos(data);
    return;
  }
  const rows = [];
  if (data && typeof data === "object") {
    for (const [kpi, v] of Object.entries(data)) {
      if (v && typeof v === "object") rows.push({ kpi, ...v });
    }
  }
  renderComparativos(rows);
}

function renderVentasPorHora(rows) {
  const body = $("ventasHoraBody");
  if (!Array.isArray(rows) || rows.length === 0) {
    body.innerHTML = '<tr><td colspan="4" class="muted">Sin datos</td></tr>';
    return;
  }

  const maxTotal = Math.max(
    0,
    ...rows.map((r) => Number(r.total || 0)).filter((n) => Number.isFinite(n))
  );
  const html = rows
    .map((r) => {
      const hora = r.hora ?? "—";
      const cantidad = r.cantidad ?? 0;
      const total = r.total ?? 0;
      const pct =
        maxTotal > 0 ? Math.max(0, Math.min(100, (Number(total || 0) / maxTotal) * 100)) : 0;
      return `<tr><td>${hora}</td><td>${cantidad}</td><td>${total}</td><td><div class="bar"><div style="width:${pct.toFixed(1)}%"></div></div></td></tr>`;
    })
    .join("");
  body.innerHTML = html;
}

async function refreshVentasPorHora(base) {
  const url = `${base}/api/dashboard/ventas-por-hora`;
  const data = await fetchJson(url);
  renderVentasPorHora(data || []);
}

function renderStockBajoTabla(items) {
  const body = $("alertStockBajoBody");
  if (!body) return;
  const rows = Array.isArray(items) ? items : [];
  if (rows.length === 0) {
    body.innerHTML = '<tr><td colspan="4" class="muted">Sin alertas</td></tr>';
    return;
  }
  body.innerHTML = rows
    .slice(0, 50)
    .map((p) => {
      return `<tr><td>${escapeHtml(p.nombre ?? "")}</td><td>${escapeHtml(p.sku ?? "")}</td><td>${p.stock_actual ?? "—"}</td><td>${p.stock_minimo ?? "—"}</td></tr>`;
    })
    .join("");
}

function renderVencerTabla(items) {
  const body = $("alertVencerBody");
  if (!body) return;
  const rows = Array.isArray(items) ? items : [];
  if (rows.length === 0) {
    body.innerHTML = '<tr><td colspan="4" class="muted">Sin alertas</td></tr>';
    return;
  }
  body.innerHTML = rows
    .slice(0, 50)
    .map((x) => {
      return `<tr><td>${escapeHtml(x.producto_nombre ?? "")}</td><td>${escapeHtml(x.lote_codigo ?? "")}</td><td>${escapeHtml(x.fecha_vencimiento ?? "")}</td><td>${x.dias_restantes ?? "—"}</td></tr>`;
    })
    .join("");
}

async function refreshAlertasDetalle(base) {
  const dias = Number.parseInt($("diasVenc")?.textContent || "30", 10) || 30;
  const [sb, pv] = await Promise.all([
    fetchJson(`${base}/api/dashboard/productos-stock-bajo`),
    fetchJson(`${base}/api/dashboard/productos-proximos-vencer?dias=${encodeURIComponent(dias)}`),
  ]);
  renderStockBajoTabla(sb);
  renderVencerTabla(pv);
}

async function refresh() {
  clearError();
  const base = normalizeBaseUrl($("apiBase").value);
  const dias = Number.parseInt($("diasVenc").textContent || "30", 10) || 30;

  setDashboardLoading(true);
  try {
    await Promise.all([
      refreshResumen(base, dias),
      refreshIndicadores(base),
      refreshIndicadoresComparativos(base),
      refreshVentasPorHora(base),
      refreshAlertasDetalle(base),
      refreshPanelLateral(base),
    ]);

    // En esta iteración la UI está centrada en Dashboard (mocks).
    // POS/Configuración quedan desactivados desde la navegación.
    if (!$("posCard")?.hidden) {
      await refreshPosCatalogo(base);
      renderPos();
    }
    if (!$("configCard")?.hidden) {
      await refreshConfigEmpresa(base);
      await refreshConfigSucursales(base);
    }
  } finally {
    setDashboardLoading(false);
  }
}

async function refreshPanelLateral(base) {
  const data = await fetchJson(`${base}/api/dashboard/panel-lateral`);
  const salud = data?.salud || {};
  const estado = salud.estado ?? "—";
  const ganancia = data?.ganancia_actual;
  const gananciaTxt =
    ganancia == null ? "" : ` · Ganancia: $ ${money(ganancia)}`;
  setText("plSalud", `${estado}${gananciaTxt}`);
  setText("plProm7", data?.promedios?.ultimos_7_dias ?? "—");
  setText("plPromDow", data?.promedios?.este_dia_semana ?? "—");
  const pron = data?.pronostico || {};
  const pronTotal = pron?.total_hoy;
  const pronPctObj = pron?.porcentaje_cumplimiento_objetivo_diario_pct;
  const pronTxt =
    pronTotal == null
      ? "—"
      : ` $ ${money(pronTotal)}${pronPctObj == null ? "" : ` · Cumpl obj: ${pronPctObj} %`}`;
  setText("plPron", pronTxt);

  const pe = data?.punto_equilibrio_diario;
  const pePct = data?.cumplimiento_punto_equilibrio_diario_pct;
  setText(
    "plPe",
    pe == null ? "—" : `$ ${money(pe)}${pePct == null ? "" : ` · ${pePct} %`}`
  );

  const obj = data?.objetivo_diario;
  const objPct = data?.cumplimiento_objetivo_diario_pct;
  setText(
    "plObj",
    obj == null ? "—" : `$ ${money(obj)}${objPct == null ? "" : ` · ${objPct} %`}`
  );
  setText("plJson", JSON.stringify(data, null, 2));
}

// ---- Configuración (Empresa / Sucursales) ----
let configInited = false;
const POS_SUCURSAL_ID_KEY = "pos_sucursal_id";

function setCfgMsg(id, text) {
  const el = $(id);
  if (el) el.textContent = text || "";
}

async function initConfigIfNeeded() {
  if (configInited) return;
  configInited = true;

  $("cfgEmpresaCargar").addEventListener("click", () => refreshConfigEmpresa(normalizeBaseUrl($("apiBase").value)).catch(showError));
  $("cfgEmpresaGuardar").addEventListener("click", () => guardarConfigEmpresa().catch(showError));
  $("cfgSucRefrescar").addEventListener("click", () => refreshConfigSucursales(normalizeBaseUrl($("apiBase").value)).catch(showError));
  $("cfgSucCrear").addEventListener("click", () => crearSucursal().catch(showError));
  $("cfgPosSucursalGuardar").addEventListener("click", () => guardarPosSucursal().catch(showError));
  $("cfgPosSucursalRefrescar").addEventListener("click", () => refreshConfigPosSucursales(normalizeBaseUrl($("apiBase").value)).catch(showError));

  $("cfgParamRefrescarClaves").addEventListener("click", () => refreshConfigParamClaves(normalizeBaseUrl($("apiBase").value)).catch(showError));
  $("cfgParamCargar").addEventListener("click", () => cargarParametro().catch(showError));
  $("cfgParamGuardar").addEventListener("click", () => guardarParametro().catch(showError));

  $("cfgDashCargar")?.addEventListener("click", () => refreshDashboardParametros(normalizeBaseUrl($("apiBase").value)).catch(showError));
  $("cfgDashGuardar")?.addEventListener("click", () => guardarDashboardParametros().catch(showError));

  $("cfgMpCrear").addEventListener("click", () => crearMedioPago().catch(showError));
  $("cfgMpRefrescar").addEventListener("click", () => refreshMediosPago(normalizeBaseUrl($("apiBase").value)).catch(showError));

  $("cfgUsrCrear").addEventListener("click", () => crearUsuario().catch(showError));
  $("cfgUsrRefrescar").addEventListener("click", () => refreshAccesos(normalizeBaseUrl($("apiBase").value)).catch(showError));
  $("cfgRolCrear").addEventListener("click", () => crearRol().catch(showError));
  $("cfgRolRefrescar").addEventListener("click", () => refreshAccesos(normalizeBaseUrl($("apiBase").value)).catch(showError));
  $("cfgPermCrear").addEventListener("click", () => crearPermiso().catch(showError));
  $("cfgPermRefrescar").addEventListener("click", () => refreshAccesos(normalizeBaseUrl($("apiBase").value)).catch(showError));

  await refreshConfigEmpresa(normalizeBaseUrl($("apiBase").value));
  await refreshConfigSucursales(normalizeBaseUrl($("apiBase").value));
  await refreshConfigPosSucursales(normalizeBaseUrl($("apiBase").value));
  await refreshConfigParamClaves(normalizeBaseUrl($("apiBase").value));
  await refreshMediosPago(normalizeBaseUrl($("apiBase").value));
  await refreshAccesos(normalizeBaseUrl($("apiBase").value));
  await refreshDashboardParametros(normalizeBaseUrl($("apiBase").value));
}

function empresaPayloadFromForm() {
  return {
    nombre: $("cfgEmpresaNombre").value || null,
    razon_social: $("cfgEmpresaRazon").value || null,
    cuit: $("cfgEmpresaCuit").value || null,
    condicion_fiscal: $("cfgEmpresaFiscal").value || null,
    direccion: $("cfgEmpresaDir").value || null,
    telefono: $("cfgEmpresaTel").value || null,
    email: $("cfgEmpresaEmail").value || null,
    logo_url: $("cfgEmpresaLogo").value || null,
  };
}

function fillEmpresaForm(emp) {
  $("cfgEmpresaNombre").value = emp?.nombre ?? "";
  $("cfgEmpresaRazon").value = emp?.razon_social ?? "";
  $("cfgEmpresaCuit").value = emp?.cuit ?? "";
  $("cfgEmpresaFiscal").value = emp?.condicion_fiscal ?? "";
  $("cfgEmpresaDir").value = emp?.direccion ?? "";
  $("cfgEmpresaTel").value = emp?.telefono ?? "";
  $("cfgEmpresaEmail").value = emp?.email ?? "";
  $("cfgEmpresaLogo").value = emp?.logo_url ?? "";
}

async function refreshConfigEmpresa(base) {
  try {
    const emp = await fetchJson(`${base}/api/configuracion/empresa`);
    fillEmpresaForm(emp);
    setCfgMsg("cfgEmpresaMsg", "Empresa cargada.");
  } catch (e) {
    // 404 si no configurado
    fillEmpresaForm(null);
    setCfgMsg("cfgEmpresaMsg", "Empresa no configurada (completá al menos Nombre y guardá).");
  }
}

async function guardarConfigEmpresa() {
  const base = normalizeBaseUrl($("apiBase").value);
  const payload = empresaPayloadFromForm();
  const r = await fetch(`${base}/api/configuracion/empresa`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    setCfgMsg("cfgEmpresaMsg", "No se pudo guardar empresa.");
    throw new Error(`Guardar empresa (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  fillEmpresaForm(data);
  setCfgMsg("cfgEmpresaMsg", "Empresa guardada.");
  // refrescar cache POS
  posEmpresa = data;
}

async function refreshConfigSucursales(base) {
  const body = $("cfgSucBody");
  if (!body) return;
  const sucs = await fetchJson(`${base}/api/configuracion/sucursales?solo_activas=false&limite=100&offset=0`);
  if (!Array.isArray(sucs) || sucs.length === 0) {
    body.innerHTML = '<tr><td colspan="6" class="muted">Sin sucursales</td></tr>';
    setCfgMsg("cfgSucMsg", "");
    return;
  }
  body.innerHTML = sucs
    .map((s) => {
      return `
        <tr data-id="${s.id}">
          <td>${s.id}</td>
          <td><input class="input" data-f="nombre" value="${escapeHtml(s.nombre ?? "")}" /></td>
          <td><input class="input" data-f="direccion" value="${escapeHtml(s.direccion ?? "")}" /></td>
          <td><input class="input" data-f="telefono" value="${escapeHtml(s.telefono ?? "")}" /></td>
          <td>
            <select class="input select" data-f="activo">
              <option value="true" ${s.activo ? "selected" : ""}>Sí</option>
              <option value="false" ${!s.activo ? "selected" : ""}>No</option>
            </select>
          </td>
          <td><button class="btn" data-act="save">Guardar</button></td>
        </tr>
      `;
    })
    .join("");

  for (const tr of body.querySelectorAll("tr[data-id]")) {
    tr.querySelector('[data-act="save"]').addEventListener("click", () => {
      const id = Number(tr.getAttribute("data-id"));
      guardarSucursalFila(id, tr).catch(showError);
    });
  }
  setCfgMsg("cfgSucMsg", `Sucursales: ${sucs.length}`);
}

async function refreshConfigPosSucursales(base) {
  const sel = $("cfgPosSucursal");
  if (!sel) return;
  const sucs = await fetchJson(`${base}/api/configuracion/sucursales?solo_activas=true&limite=200&offset=0`);
  const items = Array.isArray(sucs) ? sucs : [];
  if (items.length === 0) {
    sel.innerHTML = '<option value="">(Sin sucursales activas)</option>';
    setCfgMsg("cfgPosSucursalMsg", "No hay sucursales activas.");
    return;
  }
  const saved = localStorage.getItem(POS_SUCURSAL_ID_KEY) || "";
  sel.innerHTML = items
    .map((s) => `<option value="${s.id}" ${String(s.id) === saved ? "selected" : ""}>${escapeHtml(s.nombre)} (#${s.id})</option>`)
    .join("");
  setCfgMsg("cfgPosSucursalMsg", saved ? `Seleccionada: #${saved}` : "Elegí una sucursal para el POS.");
}

async function guardarPosSucursal() {
  const id = String($("cfgPosSucursal").value || "").trim();
  if (!id) {
    setCfgMsg("cfgPosSucursalMsg", "Seleccioná una sucursal.");
    return;
  }
  localStorage.setItem(POS_SUCURSAL_ID_KEY, id);
  setCfgMsg("cfgPosSucursalMsg", `Sucursal POS guardada: #${id}`);
  await refreshPosEmpresaSucursal(normalizeBaseUrl($("apiBase").value));
}

async function refreshConfigParamClaves(base) {
  const sel = $("cfgParamClave");
  if (!sel) return;
  const data = await fetchJson(`${base}/api/configuracion/parametros`);
  const claves = Array.isArray(data?.claves) ? data.claves : [];
  if (claves.length === 0) {
    sel.innerHTML = '<option value="">(Sin claves)</option>';
    setCfgMsg("cfgParamMsg", "No hay claves de parámetros.");
    return;
  }
  const cur = sel.value;
  sel.innerHTML = claves.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
  if (cur && claves.includes(cur)) sel.value = cur;
  setCfgMsg("cfgParamMsg", `Claves: ${claves.length}`);
}

async function cargarParametro() {
  const base = normalizeBaseUrl($("apiBase").value);
  const clave = String($("cfgParamClave").value || "").trim();
  if (!clave) {
    setCfgMsg("cfgParamMsg", "Seleccioná una clave.");
    return;
  }
  const data = await fetchJson(`${base}/api/configuracion/parametros/${encodeURIComponent(clave)}`);
  $("cfgParamJson").value = JSON.stringify(data || {}, null, 2);
  setCfgMsg("cfgParamMsg", `Parámetro cargado: ${clave}`);
}

async function guardarParametro() {
  const base = normalizeBaseUrl($("apiBase").value);
  const clave = String($("cfgParamClave").value || "").trim();
  if (!clave) {
    setCfgMsg("cfgParamMsg", "Seleccioná una clave.");
    return;
  }
  let obj = null;
  try {
    obj = JSON.parse($("cfgParamJson").value || "{}");
  } catch {
    setCfgMsg("cfgParamMsg", "JSON inválido.");
    return;
  }
  const r = await fetch(`${base}/api/configuracion/parametros/${encodeURIComponent(clave)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(obj),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    setCfgMsg("cfgParamMsg", "No se pudo guardar parámetro.");
    throw new Error(`Guardar parámetro (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  $("cfgParamJson").value = JSON.stringify(data || {}, null, 2);
  setCfgMsg("cfgParamMsg", `Parámetro guardado: ${clave}`);
}

// Parámetros específicos de Dashboard (ParametroSistema.dashboard)
async function refreshDashboardParametros(base) {
  const msg = $("cfgDashMsg");
  try {
    const data = await fetchJson(`${base}/api/configuracion/parametros/dashboard`);
    const objetivo = data?.objetivo_diario ?? "";
    const pe = data?.punto_equilibrio_diario ?? "";
    $("cfgDashObjetivo").value = objetivo === null || objetivo === undefined ? "" : String(objetivo);
    $("cfgDashPuntoEquilibrio").value = pe === null || pe === undefined ? "" : String(pe);
    if (msg) msg.textContent = "Parámetros de dashboard cargados.";
  } catch {
    if (msg) msg.textContent = "No se pudo cargar parámetros de dashboard.";
  }
}

async function guardarDashboardParametros() {
  const base = normalizeBaseUrl($("apiBase").value);
  const objRaw = String($("cfgDashObjetivo").value || "").trim();
  const peRaw = String($("cfgDashPuntoEquilibrio").value || "").trim();

  const payload = {};
  if (objRaw) payload.objetivo_diario = Number(objRaw.replace(",", "."));
  if (peRaw) payload.punto_equilibrio_diario = Number(peRaw.replace(",", "."));

  // Permitir vacío (borra valores enviados) pero en este caso payload puede quedar vacío.
  const invalid = Object.values(payload).some((v) => !Number.isFinite(v));
  if (invalid) {
    setCfgMsg("cfgDashMsg", "Valores inválidos. Usá números (ej: 500000).");
    return;
  }

  const r = await fetch(`${base}/api/configuracion/parametros/dashboard`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    setCfgMsg("cfgDashMsg", "No se pudo guardar parámetros de dashboard.");
    throw new Error(`Guardar dashboard (HTTP ${r.status})`);
  }
  if (data && typeof data === "object") {
    $("cfgDashObjetivo").value = data.objetivo_diario ?? $("cfgDashObjetivo").value;
    $("cfgDashPuntoEquilibrio").value = data.punto_equilibrio_diario ?? $("cfgDashPuntoEquilibrio").value;
  }
  setCfgMsg("cfgDashMsg", "Parámetros de dashboard guardados.");

  // Si el POS está abierto, refrescar valores para tickets
  try {
    await refreshPosDashboardParametros(base);
  } catch {
    // no bloquear
  }
}

async function refreshMediosPago(base) {
  const body = $("cfgMpBody");
  if (!body) return;
  const items = await fetchJson(`${base}/api/configuracion/medios-pago?solo_activos=false&limite=200&offset=0`);
  const lista = Array.isArray(items) ? items : [];
  if (lista.length === 0) {
    body.innerHTML = '<tr><td colspan="7" class="muted">Sin medios de pago</td></tr>';
    setCfgMsg("cfgMpMsg", "");
    return;
  }
  body.innerHTML = lista
    .map((m) => {
      return `
        <tr data-id="${m.id}">
          <td>${m.id}</td>
          <td>${escapeHtml(m.codigo)}</td>
          <td><input class="input" data-f="nombre" value="${escapeHtml(m.nombre ?? "")}" /></td>
          <td>
            <select class="input select" data-f="activo">
              <option value="true" ${m.activo ? "selected" : ""}>Sí</option>
              <option value="false" ${!m.activo ? "selected" : ""}>No</option>
            </select>
          </td>
          <td><input class="input" data-f="comision" value="${escapeHtml(String(m.comision ?? 0))}" /></td>
          <td><input class="input" data-f="dias" value="${escapeHtml(String(m.dias_acreditacion ?? 0))}" /></td>
          <td><button class="btn" data-act="save">Guardar</button></td>
        </tr>
      `;
    })
    .join("");
  for (const tr of body.querySelectorAll("tr[data-id]")) {
    tr.querySelector('[data-act="save"]').addEventListener("click", () => {
      const id = Number(tr.getAttribute("data-id"));
      guardarMedioPagoFila(id, tr).catch(showError);
    });
  }
  setCfgMsg("cfgMpMsg", `Medios de pago: ${lista.length}`);
}

async function crearMedioPago() {
  const base = normalizeBaseUrl($("apiBase").value);
  const codigo = String($("cfgMpCodigo").value || "").trim();
  const nombre = String($("cfgMpNombre").value || "").trim();
  const comision = Number(String($("cfgMpComision").value || "0").replace(",", "."));
  const dias = Number.parseInt(String($("cfgMpDias").value || "0"), 10) || 0;
  const activo = $("cfgMpActivo").value === "true";
  if (!codigo || !nombre) {
    setCfgMsg("cfgMpMsg", "Código y nombre son obligatorios.");
    return;
  }
  const r = await fetch(`${base}/api/configuracion/medios-pago`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      codigo,
      nombre,
      activo,
      comision: Number.isFinite(comision) ? comision : 0,
      dias_acreditacion: dias,
    }),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    setCfgMsg("cfgMpMsg", "No se pudo crear medio de pago.");
    throw new Error(`Crear medio pago (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  $("cfgMpCodigo").value = "";
  $("cfgMpNombre").value = "";
  $("cfgMpComision").value = "";
  $("cfgMpDias").value = "";
  setCfgMsg("cfgMpMsg", "Medio de pago creado.");
  await refreshMediosPago(base);
}

async function guardarMedioPagoFila(id, tr) {
  const base = normalizeBaseUrl($("apiBase").value);
  const nombre = tr.querySelector('[data-f="nombre"]').value;
  const activo = tr.querySelector('[data-f="activo"]').value === "true";
  const comision = Number(String(tr.querySelector('[data-f="comision"]').value || "0").replace(",", "."));
  const dias = Number.parseInt(String(tr.querySelector('[data-f="dias"]').value || "0"), 10) || 0;
  const r = await fetch(`${base}/api/configuracion/medios-pago/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      nombre,
      activo,
      comision: Number.isFinite(comision) ? comision : 0,
      dias_acreditacion: dias,
    }),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    setCfgMsg("cfgMpMsg", "No se pudo guardar medio de pago.");
    throw new Error(`Guardar medio pago (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  setCfgMsg("cfgMpMsg", `Medio de pago ${id} guardado.`);
}

async function refreshAccesos(base) {
  // roles y permisos primero para combos/asignaciones
  const roles = await fetchJson(`${base}/api/configuracion/roles?limite=200&offset=0`);
  const permisos = await fetchJson(`${base}/api/configuracion/permisos?limite=500&offset=0`);
  const usuarios = await fetchJson(`${base}/api/configuracion/usuarios?limite=200&offset=0`);

  const rolesList = Array.isArray(roles) ? roles : [];
  const permisosList = Array.isArray(permisos) ? permisos : [];
  const usuariosList = Array.isArray(usuarios) ? usuarios : [];

  // usuarios table
  const ub = $("cfgUsrBody");
  if (ub) {
    if (usuariosList.length === 0) {
      ub.innerHTML = '<tr><td colspan="5" class="muted">Sin usuarios</td></tr>';
    } else {
      ub.innerHTML = usuariosList
        .map((u) => {
          const opts = [`<option value="">(sin rol)</option>`]
            .concat(rolesList.map((r) => `<option value="${r.id}" ${String(r.id) === String(u.rol_id ?? "") ? "selected" : ""}>${escapeHtml(r.codigo)} (#${r.id})</option>`))
            .join("");
          return `
            <tr data-id="${u.id}">
              <td>${u.id}</td>
              <td>${escapeHtml(u.nombre)}</td>
              <td>
                <select class="input select" data-f="activo">
                  <option value="true" ${u.activo ? "selected" : ""}>Sí</option>
                  <option value="false" ${!u.activo ? "selected" : ""}>No</option>
                </select>
              </td>
              <td><select class="input select" data-f="rol">${opts}</select></td>
              <td><button class="btn" data-act="save">Guardar</button></td>
            </tr>
          `;
        })
        .join("");
      for (const tr of ub.querySelectorAll("tr[data-id]")) {
        tr.querySelector('[data-act="save"]').addEventListener("click", () => {
          const id = Number(tr.getAttribute("data-id"));
          guardarUsuarioFila(id, tr).catch(showError);
        });
      }
    }
  }

  // roles-permisos table
  const rb = $("cfgRolPermBody");
  if (rb) {
    if (rolesList.length === 0) {
      rb.innerHTML = '<tr><td colspan="4" class="muted">Sin roles</td></tr>';
    } else {
      rb.innerHTML = rolesList
        .map((r) => {
          return `
            <tr data-id="${r.id}">
              <td>${escapeHtml(r.codigo)} (#${r.id})</td>
              <td class="muted" data-f="cur">—</td>
              <td><input class="input" data-f="ids" placeholder="1,2,3" /></td>
              <td><button class="btn" data-act="asignar">Asignar</button></td>
            </tr>
          `;
        })
        .join("");
      // cargar permisos actuales por rol (N llamadas, simple)
      for (const tr of rb.querySelectorAll("tr[data-id]")) {
        const rolId = Number(tr.getAttribute("data-id"));
        try {
          const ps = await fetchJson(`${base}/api/configuracion/roles/${encodeURIComponent(rolId)}/permisos`);
          const cur = Array.isArray(ps) ? ps : [];
          tr.querySelector('[data-f="cur"]').textContent =
            cur.length === 0 ? "—" : cur.map((p) => `${p.codigo}(#${p.id})`).join(", ");
        } catch {
          tr.querySelector('[data-f="cur"]').textContent = "Error al cargar";
        }
        tr.querySelector('[data-act="asignar"]').addEventListener("click", () => {
          asignarPermisosRol(rolId, tr).catch(showError);
        });
      }
    }
  }

  setCfgMsg("cfgAccMsg", `Usuarios: ${usuariosList.length} · Roles: ${rolesList.length} · Permisos: ${permisosList.length}`);
}

async function crearUsuario() {
  const base = normalizeBaseUrl($("apiBase").value);
  const nombre = String($("cfgUsrNombre").value || "").trim();
  if (!nombre) {
    setCfgMsg("cfgAccMsg", "Nombre de usuario obligatorio.");
    return;
  }
  const r = await fetch(`${base}/api/configuracion/usuarios`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ nombre }),
  });
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!r.ok) {
    setCfgMsg("cfgAccMsg", "No se pudo crear usuario.");
    throw new Error(`Crear usuario (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  $("cfgUsrNombre").value = "";
  setCfgMsg("cfgAccMsg", "Usuario creado.");
  await refreshAccesos(base);
}

async function guardarUsuarioFila(id, tr) {
  const base = normalizeBaseUrl($("apiBase").value);
  const activo = tr.querySelector('[data-f="activo"]').value === "true";
  const rolRaw = String(tr.querySelector('[data-f="rol"]').value || "").trim();
  const rol_id = rolRaw ? Number.parseInt(rolRaw, 10) : null;
  const r = await fetch(`${base}/api/configuracion/usuarios/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ activo, rol_id }),
  });
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!r.ok) {
    setCfgMsg("cfgAccMsg", "No se pudo guardar usuario.");
    throw new Error(`Guardar usuario (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  setCfgMsg("cfgAccMsg", `Usuario ${id} guardado.`);
}

async function crearRol() {
  const base = normalizeBaseUrl($("apiBase").value);
  const codigo = String($("cfgRolCodigo").value || "").trim();
  const nombre = String($("cfgRolNombre").value || "").trim();
  if (!codigo || !nombre) {
    setCfgMsg("cfgAccMsg", "Código y nombre del rol obligatorios.");
    return;
  }
  const r = await fetch(`${base}/api/configuracion/roles`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ codigo, nombre }),
  });
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!r.ok) {
    setCfgMsg("cfgAccMsg", "No se pudo crear rol.");
    throw new Error(`Crear rol (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  $("cfgRolCodigo").value = "";
  $("cfgRolNombre").value = "";
  setCfgMsg("cfgAccMsg", "Rol creado.");
  await refreshAccesos(base);
}

async function crearPermiso() {
  const base = normalizeBaseUrl($("apiBase").value);
  const codigo = String($("cfgPermCodigo").value || "").trim();
  const nombre = String($("cfgPermNombre").value || "").trim();
  const descripcion = String($("cfgPermDesc").value || "").trim();
  if (!codigo || !nombre) {
    setCfgMsg("cfgAccMsg", "Código y nombre del permiso obligatorios.");
    return;
  }
  const r = await fetch(`${base}/api/configuracion/permisos`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ codigo, nombre, descripcion }),
  });
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!r.ok) {
    setCfgMsg("cfgAccMsg", "No se pudo crear permiso.");
    throw new Error(`Crear permiso (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  $("cfgPermCodigo").value = "";
  $("cfgPermNombre").value = "";
  $("cfgPermDesc").value = "";
  setCfgMsg("cfgAccMsg", "Permiso creado.");
  await refreshAccesos(base);
}

async function asignarPermisosRol(rolId, tr) {
  const base = normalizeBaseUrl($("apiBase").value);
  const raw = String(tr.querySelector('[data-f="ids"]').value || "").trim();
  const ids = raw
    ? raw.split(",").map((x) => Number.parseInt(x.trim(), 10)).filter((n) => Number.isFinite(n))
    : [];
  const r = await fetch(`${base}/api/configuracion/roles/${encodeURIComponent(rolId)}/permisos`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ permiso_ids: ids }),
  });
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!r.ok) {
    setCfgMsg("cfgAccMsg", "No se pudo asignar permisos.");
    throw new Error(`Asignar permisos (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  setCfgMsg("cfgAccMsg", `Permisos asignados al rol #${rolId}.`);
  await refreshAccesos(base);
}

async function crearSucursal() {
  const base = normalizeBaseUrl($("apiBase").value);
  const nombre = String($("cfgSucNombre").value || "").trim();
  const direccion = String($("cfgSucDir").value || "").trim() || null;
  const telefono = String($("cfgSucTel").value || "").trim() || null;
  const activo = $("cfgSucActivo").value === "true";
  if (!nombre) {
    setCfgMsg("cfgSucMsg", "El nombre de sucursal es obligatorio.");
    return;
  }
  const r = await fetch(`${base}/api/configuracion/sucursales`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ nombre, direccion, telefono, activo }),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    setCfgMsg("cfgSucMsg", "No se pudo crear sucursal.");
    throw new Error(`Crear sucursal (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  $("cfgSucNombre").value = "";
  $("cfgSucDir").value = "";
  $("cfgSucTel").value = "";
  setCfgMsg("cfgSucMsg", "Sucursal creada.");
  await refreshConfigSucursales(base);
  // refrescar cache POS de sucursal (primer activa)
  await refreshPosEmpresaSucursal(base);
}

async function guardarSucursalFila(id, tr) {
  const base = normalizeBaseUrl($("apiBase").value);
  const nombre = tr.querySelector('[data-f="nombre"]').value;
  const direccion = tr.querySelector('[data-f="direccion"]').value;
  const telefono = tr.querySelector('[data-f="telefono"]').value;
  const activo = tr.querySelector('[data-f="activo"]').value === "true";
  const r = await fetch(`${base}/api/configuracion/sucursales/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ nombre, direccion, telefono, activo }),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    setCfgMsg("cfgSucMsg", "No se pudo guardar sucursal.");
    throw new Error(`Guardar sucursal (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  setCfgMsg("cfgSucMsg", `Sucursal ${id} guardada.`);
  await refreshPosEmpresaSucursal(base);
}

// ---- POS (inspirado en pos-market: búsqueda + código + carrito + atajos) ----
let posInited = false;
let posBaseUrl = "http://localhost:8000";
let posCatalogo = [];
let posResultados = [];
let posCarrito = [];
let posClienteSel = null; // {cliente_id, persona_id, nombre, apellido, ...}
let posClienteResumenCC = null; // {saldo, limite_credito, disponible}
let posEmpresa = null;
let posSucursal = null;
let posDashboardParametros = { objetivo_diario: null, punto_equilibrio_diario: null };

function money(v) {
  const n = Number(v || 0);
  if (!Number.isFinite(n)) return "0";
  return n.toFixed(2);
}

function moneyOpt(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(2);
}

function setMsg(text) {
  const el = $("posMsg");
  if (el) el.textContent = text || "";
}

function setClienteMsg(text) {
  const el = $("posClienteCC");
  if (el) el.textContent = text || "";
}

function renderClienteSel() {
  const el = $("posClienteSel");
  if (!el) return;
  if (!posClienteSel) {
    el.textContent = "Sin cliente";
  } else {
    el.textContent = `${posClienteSel.apellido || ""} ${posClienteSel.nombre || ""}`.trim();
  }
}

async function initPosIfNeeded() {
  if (posInited) return;
  posInited = true;

  $("posBuscar").addEventListener("input", () => {
    posBuscar($("posBuscar").value);
  });
  $("posBuscar").addEventListener("keydown", (e) => {
    if (e.key === "Enter") posBuscar($("posBuscar").value);
  });
  $("posCodigo").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      posAgregarPorCodigo($("posCodigo").value).catch(showError);
    }
  });

  $("posCobrar").addEventListener("click", () => posCobrar().catch(showError));
  $("posCancelar").addEventListener("click", () => posCancelar());
  $("posDescuento").addEventListener("input", () => renderPos());
  $("posMedioPago").addEventListener("change", () => renderPos());
  $("posImprimirTicket").addEventListener("click", () => posImprimirTicket());
  $("posLimpiarTicket").addEventListener("click", () => posLimpiarTicket());

  $("posClienteBuscar").addEventListener("input", () => {
    posBuscarCliente($("posClienteBuscar").value).catch(showError);
  });
  $("posClienteAltaApellido").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      posAltaRapidaCliente().catch(showError);
    }
  });
  $("posClienteAltaLimite").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      posAltaRapidaCliente().catch(showError);
    }
  });

  window.addEventListener("keydown", (e) => {
    if ($("posCard")?.hidden) return;
    if (e.key === "F2") {
      e.preventDefault();
      $("posBuscar").focus();
    } else if (e.key === "F4") {
      e.preventDefault();
      posCobrar().catch(showError);
    } else if (e.key === "Escape") {
      e.preventDefault();
      posCancelar();
    }
  });

  posBaseUrl = normalizeBaseUrl($("apiBase").value);
  await refreshPosCatalogo(posBaseUrl);
  await refreshPosEmpresaSucursal(posBaseUrl);
  await refreshPosDashboardParametros(posBaseUrl);
  renderClienteSel();
  posBuscar("");
  renderPos();
}

async function refreshPosCatalogo(base) {
  posBaseUrl = base;
  if (posCatalogo.length > 0) return;
  // No hay query de búsqueda en backend; cacheamos y filtramos en el cliente.
  const url = `${base}/api/productos?activo_only=true&limite=500&offset=0`;
  posCatalogo = (await fetchJson(url)) || [];
}

async function refreshPosEmpresaSucursal(base) {
  // Empresa puede no estar configurada, no bloquear POS
  try {
    posEmpresa = await fetchJson(`${base}/api/configuracion/empresa`);
  } catch {
    posEmpresa = null;
  }
  const preferida = localStorage.getItem(POS_SUCURSAL_ID_KEY);
  if (preferida) {
    try {
      posSucursal = await fetchJson(`${base}/api/configuracion/sucursales/${encodeURIComponent(preferida)}`);
      return;
    } catch {
      // fallback a primera activa
    }
  }
  try {
    const sucs = await fetchJson(`${base}/api/configuracion/sucursales?solo_activas=true&limite=1&offset=0`);
    posSucursal = Array.isArray(sucs) && sucs.length > 0 ? sucs[0] : null;
  } catch {
    posSucursal = null;
  }
}

async function refreshPosDashboardParametros(base) {
  try {
    const cfg = await fetchJson(`${base}/api/configuracion/parametros/dashboard`);
    posDashboardParametros = {
      objetivo_diario: cfg?.objetivo_diario ?? null,
      punto_equilibrio_diario: cfg?.punto_equilibrio_diario ?? null,
    };
  } catch {
    posDashboardParametros = { objetivo_diario: null, punto_equilibrio_diario: null };
  }
}

async function posBuscarCliente(q) {
  const texto = String(q || "").trim();
  const box = $("posClienteResultados");
  if (!box) return;
  if (!texto) {
    box.innerHTML = "";
    return;
  }
  const url = `${posBaseUrl}/api/personas/clientes/buscar?q=${encodeURIComponent(texto)}&limite=20&offset=0`;
  const data = (await fetchJson(url)) || [];
  if (!Array.isArray(data) || data.length === 0) {
    box.innerHTML = '<div class="custRow"><div class="muted">Sin resultados</div><div></div></div>';
    return;
  }
  box.innerHTML = data
    .map((c) => {
      const name = `${c.apellido || ""} ${c.nombre || ""}`.trim();
      const doc = c.documento ? `Doc: ${c.documento}` : "Sin doc";
      const lim = c.limite_credito != null ? `Límite: $ ${money(c.limite_credito)}` : "Sin límite";
      return `
        <div class="custRow" data-cliente-id="${c.cliente_id}">
          <div>
            <div class="name">${name}</div>
            <div class="meta">${doc} · ${lim}</div>
          </div>
          <div class="price">Seleccionar</div>
        </div>
      `;
    })
    .join("");

  for (const row of box.querySelectorAll(".custRow[data-cliente-id]")) {
    row.addEventListener("click", () => {
      const id = Number(row.getAttribute("data-cliente-id"));
      const sel = data.find((x) => Number(x.cliente_id) === id);
      posSeleccionarCliente(sel).catch(showError);
    });
  }
}

async function posSeleccionarCliente(sel) {
  posClienteSel = sel || null;
  posClienteResumenCC = null;
  renderClienteSel();
  setClienteMsg("");
  if (!posClienteSel) return;
  try {
    const url = `${posBaseUrl}/api/tesoreria/cuentas-corrientes/clientes/${encodeURIComponent(
      posClienteSel.cliente_id
    )}/resumen`;
    posClienteResumenCC = await fetchJson(url);
    const s = posClienteResumenCC;
    const parts = [
      `Saldo: $ ${money(s.saldo ?? 0)}`,
      s.limite_credito == null ? "Límite: —" : `Límite: $ ${money(s.limite_credito)}`,
      s.disponible == null ? "Disponible: —" : `Disponible: $ ${money(s.disponible)}`,
    ];
    setClienteMsg(parts.join(" · "));
  } catch (e) {
    setClienteMsg("No se pudo obtener resumen de cuenta corriente.");
  }
  renderPos();
}

async function posAltaRapidaCliente() {
  const nombre = String($("posClienteAltaNombre").value || "").trim();
  const apellido = String($("posClienteAltaApellido").value || "").trim();
  const documento = String($("posClienteAltaDocumento").value || "").trim() || null;
  const telefono = String($("posClienteAltaTelefono").value || "").trim() || null;
  const limiteRaw = String($("posClienteAltaLimite").value || "").trim();
  const limite = limiteRaw ? Number(limiteRaw.replace(",", ".")) : null;
  if (!nombre || !apellido) {
    setClienteMsg("Para alta rápida: completar nombre y apellido (Enter en apellido).");
    return;
  }
  const url = `${posBaseUrl}/api/personas/clientes/alta-rapida`;
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      nombre,
      apellido,
      documento,
      telefono,
      limite_credito: Number.isFinite(limite) ? limite : null,
    }),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    throw new Error(`Alta rápida cliente (HTTP ${r.status})\n${typeof data === "string" ? data : JSON.stringify(data)}`);
  }
  $("posClienteAltaNombre").value = "";
  $("posClienteAltaApellido").value = "";
  $("posClienteAltaDocumento").value = "";
  $("posClienteAltaTelefono").value = "";
  $("posClienteAltaLimite").value = "";
  $("posClienteBuscar").value = "";
  $("posClienteResultados").innerHTML = "";
  await posSeleccionarCliente(data);
}

function posLimpiarTicket() {
  setText("posTicket", "{}");
  const html = $("posTicketHtml");
  if (html) html.innerHTML = "";
}

function escapeHtml(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function posRenderTicketHtml(venta) {
  const box = $("posTicketHtml");
  if (!box) return;
  if (!venta || !venta.id) {
    box.innerHTML = "";
    return;
  }
  const empresa = posEmpresa?.nombre || "Punto de Venta";
  const sucursal = posSucursal?.nombre || "—";
  const objetivo = posDashboardParametros?.objetivo_diario;
  const puntoEquilibrio = posDashboardParametros?.punto_equilibrio_diario;
  const cliente = posClienteSel
    ? `${posClienteSel.apellido || ""} ${posClienteSel.nombre || ""}`.trim()
    : "—";
  const items = Array.isArray(venta.items) ? venta.items : [];
  const filas = items
    .map((it) => {
      const nombre = escapeHtml(it.nombre_producto || "");
      const cant = money(it.cantidad || 0);
      const pu = money(it.precio_unitario || 0);
      const sub = money(it.subtotal || 0);
      return `<tr><td>${nombre}</td><td>${cant}</td><td>$ ${pu}</td><td>$ ${sub}</td></tr>`;
    })
    .join("");

  box.innerHTML = `
    <h3>${escapeHtml(empresa)} — Ticket #${escapeHtml(venta.id)}</h3>
    <div class="row"><div class="muted">Sucursal</div><div>${escapeHtml(sucursal)}</div></div>
    <div class="row"><div class="muted">Fecha</div><div>${escapeHtml(venta.creado_en || "")}</div></div>
    <div class="row"><div class="muted">Cliente</div><div>${escapeHtml(cliente)}</div></div>
    <div class="row"><div class="muted">Medio de pago</div><div>${escapeHtml(venta.metodo_pago || "")}</div></div>
    <div class="hr"></div>
    <table>
      <thead><tr><th>Producto</th><th>Cant.</th><th>P.Unit</th><th>Subtotal</th></tr></thead>
      <tbody>${filas || `<tr><td colspan="4" class="muted">—</td></tr>`}</tbody>
    </table>
    <div class="hr"></div>
    <div class="row"><div class="muted">Subtotal</div><div>$ ${money(venta.subtotal || 0)}</div></div>
    <div class="row"><div class="muted">Descuento</div><div>$ ${money(venta.descuento || 0)}</div></div>
    <div class="row total"><div>Total</div><div>$ ${money(venta.total || 0)}</div></div>
    <div class="hr"></div>
    <div class="row"><div class="muted">Objetivo diario</div><div>$ ${escapeHtml(moneyOpt(objetivo))}</div></div>
    <div class="row"><div class="muted">Punto equilibrio</div><div>$ ${escapeHtml(moneyOpt(puntoEquilibrio))}</div></div>
  `;
}

function posImprimirTicket() {
  const html = $("posTicketHtml")?.innerHTML || "";
  if (!html.trim()) {
    setMsg("No hay ticket para imprimir.");
    return;
  }
  const w = window.open("", "_blank", "noopener,noreferrer,width=520,height=700");
  if (!w) {
    setMsg("No se pudo abrir la ventana de impresión (bloqueador de popups).");
    return;
  }
  w.document.write(`
    <!doctype html>
    <html><head><meta charset="utf-8" />
      <title>Ticket</title>
      <style>
        body{font-family:system-ui,Segoe UI,Roboto,Arial;margin:16px;}
        h3{margin:0 0 8px;}
        .muted{color:#555}
        .row{display:flex;justify-content:space-between;gap:10px;margin:2px 0}
        .hr{height:1px;background:#ddd;margin:10px 0}
        table{width:100%;border-collapse:collapse}
        th,td{padding:8px 6px;border-bottom:1px solid #eee;text-align:left;font-size:13px}
        th{color:#444}
        .total{font-size:16px;font-weight:800}
      </style>
    </head><body>${html}</body></html>
  `);
  w.document.close();
  w.focus();
  w.print();
  w.close();
}

function posBuscar(texto) {
  const q = String(texto || "").trim().toLowerCase();
  if (!q) {
    posResultados = posCatalogo.slice(0, 80);
  } else {
    posResultados = posCatalogo
      .filter((p) => {
        const nombre = String(p.nombre || "").toLowerCase();
        const sku = String(p.sku || "").toLowerCase();
        const codigo = String(p.codigo_barra || "").toLowerCase();
        return nombre.includes(q) || sku.includes(q) || codigo.includes(q);
      })
      .slice(0, 80);
  }
  renderPosResultados();
}

function posAgregarProducto(p) {
  posAgregarProductoConCantidad(p, 1);
}

async function posAgregarPorCodigo(raw) {
  const codigoRaw = String(raw || "").trim();
  if (!codigoRaw) return;
  // cantidad rápida: "3*SKU"
  let codigo = codigoRaw;
  let multiplicador = 1;
  const m = codigoRaw.match(/^(\d+(?:[.,]\d+)?)\s*\*\s*(.+)$/);
  if (m) {
    const n = Number(m[1].replace(",", "."));
    multiplicador = Number.isFinite(n) && n > 0 ? n : 1;
    codigo = String(m[2] || "").trim();
  }
  if (!codigo) return;
  setMsg("");

  // 1) Intentar SKU directo (endpoint dedicado)
  try {
    const p = await fetchJson(
      `${posBaseUrl}/api/productos/por-sku/${encodeURIComponent(codigo)}`
    );
    posAgregarProductoConCantidad(p, multiplicador);
    $("posCodigo").value = "";
    $("posCodigo").focus();
    return;
  } catch (_) {
    // ignorar (puede ser 404)
  }

  // 2) Buscar por codigo_barra en catálogo local
  const p2 = posCatalogo.find(
    (p) => String(p.codigo_barra || "").trim() === codigo
  );
  if (p2) {
    posAgregarProductoConCantidad(p2, multiplicador);
    $("posCodigo").value = "";
    $("posCodigo").focus();
    return;
  }

  setMsg("Producto no encontrado por SKU ni código de barra.");
}

function posAgregarProductoConCantidad(p, cantidad) {
  if (!p) return;
  const qty = Number(cantidad || 1);
  const q = Number.isFinite(qty) && qty > 0 ? qty : 1;
  const id = p.id;
  const existente = posCarrito.find((it) => it.id === id);
  if (existente) {
    existente.cantidad = Number(existente.cantidad || 0) + q;
  } else {
    posCarrito.push({
      id,
      sku: p.sku,
      nombre: p.nombre,
      precio_venta: Number(p.precio_venta || 0),
      cantidad: q,
    });
  }
  setMsg("");
  renderPos();
}

function posCambiarCantidad(id, delta) {
  const it = posCarrito.find((x) => x.id === id);
  if (!it) return;
  it.cantidad = Math.max(0, Number(it.cantidad || 0) + delta);
  posCarrito = posCarrito.filter((x) => x.cantidad > 0);
  renderPos();
}

function posCancelar() {
  posCarrito = [];
  $("posDescuento").value = "0";
  $("posCodigo").value = "";
  setMsg("Venta cancelada.");
  posLimpiarTicket();
  renderPos();
}

function posTotales() {
  const subtotal = posCarrito.reduce(
    (acc, it) => acc + Number(it.precio_venta || 0) * Number(it.cantidad || 0),
    0
  );
  const desc = Number(String($("posDescuento").value || "0").replace(",", "."));
  const descuento = Number.isFinite(desc) ? Math.max(0, desc) : 0;
  const total = Math.max(0, subtotal - descuento);
  return { subtotal, descuento, total };
}

async function posCobrar() {
  if (posCarrito.length === 0) {
    setMsg("El carrito está vacío.");
    return;
  }
  const { descuento } = posTotales();
  const metodo = $("posMedioPago").value || "EFECTIVO";
  if (metodo === "CUENTA_CORRIENTE" && !posClienteSel) {
    setMsg("Para cobrar a cuenta corriente, primero seleccioná un cliente.");
    return;
  }
  // Confirmación mínima (checkout)
  const { total } = posTotales();
  if (metodo === "CUENTA_CORRIENTE" && posClienteResumenCC?.disponible != null) {
    const disp = Number(posClienteResumenCC.disponible || 0);
    if (total > disp) {
      const ok = confirm(
        `El total ($ ${money(total)}) excede el disponible ($ ${money(disp)}). Puede fallar por límite.\n¿Desea intentar igual?`
      );
      if (!ok) return;
    }
  } else {
    const ok = confirm(`Confirmar cobro por $ ${money(total)} (${metodo})`);
    if (!ok) return;
  }
  const items = posCarrito.map((it) => ({
    producto_id: it.id,
    cantidad: it.cantidad,
    precio_unitario: it.precio_venta,
  }));

  const url = `${posBaseUrl}/api/ventas`;
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      items,
      descuento,
      metodo_pago: metodo,
      cliente_id: posClienteSel ? posClienteSel.persona_id : null,
    }),
  });
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!r.ok) {
    const detail =
      typeof data === "string"
        ? data
        : (data && (data.detail || JSON.stringify(data))) || "";
    const msg = String(detail || "").toLowerCase();
    if (msg.includes("límite") || msg.includes("limite") || msg.includes("credito")) {
      setMsg("No se pudo registrar la venta: límite de crédito excedido.");
      return;
    }
    if (msg.includes("stock") || msg.includes("insuficiente")) {
      setMsg("No se pudo registrar la venta: stock insuficiente.");
      return;
    }
    setMsg(`No se pudo registrar la venta (HTTP ${r.status}).`);
    throw new Error(`Error al cobrar (HTTP ${r.status})\n${detail}`);
  }

  setMsg(`Venta registrada. ID: ${data?.venta_id ?? "—"} Total: ${money(data?.total ?? 0)}`);
  posCarrito = [];
  $("posCodigo").value = "";
  renderPos();
  // ticket mínimo
  if (data?.venta_id) {
    try {
      const v = await fetchJson(`${posBaseUrl}/api/ventas/${encodeURIComponent(data.venta_id)}`);
      setText("posTicket", JSON.stringify(v, null, 2));
      posRenderTicketHtml(v);
    } catch {
      // ignore
    }
  }
  // refrescar dashboard (caja/indicadores) tras registrar venta
  refresh().catch(showError);
}

function renderPosResultados() {
  const box = $("posResultados");
  const count = $("posResultadosCount");
  if (!box || !count) return;
  count.textContent = String(posResultados.length);

  if (posResultados.length === 0) {
    box.innerHTML = '<div class="posRow"><div class="muted">Sin resultados</div><div></div></div>';
    return;
  }

  box.innerHTML = posResultados
    .map((p) => {
      const name = p.nombre || "Producto";
      const sku = p.sku || "—";
      const cod = p.codigo_barra || "—";
      const price = money(p.precio_venta || 0);
      return `
        <div class="posRow" data-id="${p.id}">
          <div>
            <div class="name">${name}</div>
            <div class="meta">SKU: ${sku} · Código: ${cod}</div>
          </div>
          <div class="price">$ ${price}</div>
        </div>
      `;
    })
    .join("");

  for (const row of box.querySelectorAll(".posRow[data-id]")) {
    row.addEventListener("click", () => {
      const id = Number(row.dataset.id);
      const p = posResultados.find((x) => x.id === id);
      posAgregarProducto(p);
    });
  }
}

function renderPosCarrito() {
  const box = $("posCarrito");
  const count = $("posCarritoCount");
  if (!box || !count) return;
  count.textContent = String(posCarrito.reduce((a, it) => a + it.cantidad, 0));

  if (posCarrito.length === 0) {
    box.innerHTML = '<div class="cartRow"><div class="muted">Carrito vacío</div><div></div></div>';
    return;
  }

  box.innerHTML = posCarrito
    .map((it) => {
      const subtotal = money(Number(it.precio_venta || 0) * Number(it.cantidad || 0));
      return `
        <div class="cartRow" data-id="${it.id}">
          <div>
            <div class="top">
              <div class="name">${it.nombre || "Producto"}</div>
              <div class="price">$ ${money(it.precio_venta || 0)}</div>
            </div>
            <div class="meta">SKU: ${it.sku || "—"} · Subtotal: $ ${subtotal}</div>
            <div class="controls">
              <button class="qtyBtn" data-act="minus">−</button>
              <div class="qtyVal">${money(it.cantidad)}</div>
              <button class="qtyBtn" data-act="plus">+</button>
              <button class="qtyBtn" data-act="del">×</button>
            </div>
          </div>
          <div></div>
        </div>
      `;
    })
    .join("");

  for (const row of box.querySelectorAll(".cartRow[data-id]")) {
    const id = Number(row.dataset.id);
    row.querySelector('[data-act="minus"]').addEventListener("click", () => posCambiarCantidad(id, -1));
    row.querySelector('[data-act="plus"]').addEventListener("click", () => posCambiarCantidad(id, +1));
    row.querySelector('[data-act="del"]').addEventListener("click", () => {
      posCarrito = posCarrito.filter((x) => x.id !== id);
      renderPos();
    });
  }
}

function renderPos() {
  if ($("posCard")?.hidden) return;
  renderPosResultados();
  renderPosCarrito();
  const { subtotal, descuento, total } = posTotales();
  setText("posSubtotal", `$ ${money(subtotal)}`);
  setText("posTotal", `$ ${money(total)}`);

  // hint de crédito si corresponde
  const metodo = $("posMedioPago").value || "EFECTIVO";
  if (metodo === "CUENTA_CORRIENTE") {
    if (!posClienteSel) {
      setClienteMsg("Seleccioná un cliente para operar a crédito.");
    } else if (posClienteResumenCC && posClienteResumenCC.disponible != null) {
      const disp = Number(posClienteResumenCC.disponible || 0);
      if (total > disp) {
        setClienteMsg(`Atención: total $ ${money(total)} excede disponible $ ${money(disp)} (puede fallar por límite).`);
      }
    }
  }
}

window.addEventListener("DOMContentLoaded", () => {
  for (const btn of document.querySelectorAll(".tab")) {
    btn.addEventListener("click", () => setTab(btn.dataset.tab));
  }
  setTab("resumen");

  $("refresh").addEventListener("click", () => refresh().catch(showError));

  let timer = null;
  function resetAutoRefresh() {
    if (timer) clearInterval(timer);
    timer = null;
    const every = Number.parseInt($("refreshEvery").value, 10) || 0;
    if (every > 0) {
      timer = setInterval(() => refresh().catch(showError), every * 1000);
    }
  }
  $("refreshEvery").addEventListener("change", resetAutoRefresh);
  resetAutoRefresh();

  refresh().catch(showError);
});

