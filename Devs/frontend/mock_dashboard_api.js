// API simulada para Módulo 1 (Dashboard) — funciona 100% sin backend.
// Contratos: shape de respuestas alineado con lo que consume `app.js`.
(function () {
  const PRODUCTS = [
    { nombre: "Fideos Spaghetti Verizzia 500g", sku: "FDS-500-SPAG" },
    { nombre: "Salsa Tomate Tradicional", sku: "SLV-TOM-200" },
    { nombre: "Aceite de Oliva 1L", sku: "ACE-OLV-1L" },
    { nombre: "Yerba Mate 500g", sku: "YRB-MAT-500" },
    { nombre: "Azúcar 1kg", sku: "AZC-1KG" },
    { nombre: "Harina 1kg", sku: "HRN-1KG" },
    { nombre: "Arroz Largo Fino 1kg", sku: "RZZ-1KG" },
    { nombre: "Lentejas 500g", sku: "LNT-500" },
    { nombre: "Leche Entera 1L", sku: "LCH-ENT-1L" },
    { nombre: "Queso Sardo 300g", sku: "QSO-SAR-300" },
    { nombre: "Jamón Cocido 200g", sku: "JMN-COC-200" },
    { nombre: "Fiambres Especial 1kg", sku: "FIM-ESP-1KG" },
    { nombre: "Galletitas Dulces 300g", sku: "GLL-DUL-300" },
    { nombre: "Cereal Corn Flakes 600g", sku: "CRL-CFN-600" },
    { nombre: "Café Molido 250g", sku: "CAF-MOL-250" },
    { nombre: "Detergente Líquido 1L", sku: "DTG-LIQ-1L" },
    { nombre: "Papel Higiénico Pack", sku: "PPL-HIG-PK" },
    { nombre: "Jugo Durazno 1L", sku: "JGO-DUR-1L" },
    { nombre: "Agua Mineral 2L", sku: "AGU-MIN-2L" },
    { nombre: "Yogur Bebible 1L", sku: "YGR-BEB-1L" },
  ];

  // ---- Mocks POS (Módulo 2) ----
  // Estos datos son suficientes para que la pantalla POS funcione sin backend.
  const POS_PRODUCTS = PRODUCTS.map((p, idx) => {
    const id = idx + 1;
    const precio_venta = Math.round((2700 + idx * 155 + (idx % 5) * 280) / 10) * 10;
    const codigo_barra = `${p.sku}-BAR`;
    const stock_minimo = Math.round(8 + (idx % 7) * 2);
    // stock actual: algunos quedarán bajo para validar alertas/errores
    const stock_actual = Math.max(0, Math.round(stock_minimo * (0.25 + (idx % 6) * 0.14)));
    return {
      id,
      nombre: p.nombre,
      sku: p.sku,
      codigo_barra,
      precio_venta,
      stock_actual,
      stock_minimo,
      activo: true,
    };
  });

  // Personas/Clientes (solo subset necesario para POS + cuentas corrientes).
  const POS_CLIENTS = [
    {
      cliente_id: 201,
      persona_id: 301,
      nombre: "Victoria",
      apellido: "Perez",
      documento: "32911452",
      telefono: "1123456789",
      limite_credito: 120000,
      saldo: 25000,
      activo: true,
    },
    {
      cliente_id: 202,
      persona_id: 302,
      nombre: "Juan",
      apellido: "Gomez",
      documento: "30111452",
      telefono: "1144556677",
      limite_credito: 80000,
      saldo: 52000,
      activo: true,
    },
    {
      cliente_id: 203,
      persona_id: 303,
      nombre: "Maria",
      apellido: "Rodriguez",
      documento: "27911252",
      telefono: "1199887766",
      limite_credito: 200000,
      saldo: 0,
      activo: true,
    },
  ];

  let POS_CLIENTE_SEQ = POS_CLIENTS.reduce((a, c) => Math.max(a, c.cliente_id), 200) + 1;
  let POS_PERSONA_SEQ = POS_CLIENTS.reduce((a, c) => Math.max(a, c.persona_id), 300) + 1;

  const POS_CONFIG = {
    empresa: { nombre: "La Casona" },
    sucursales: [
      { id: 1, nombre: "Sucursal Centro", direccion: "Av. Principal 123", telefono: "411-0000", activo: true },
      { id: 2, nombre: "Sucursal Norte", direccion: "Ruta 9 Km 5", telefono: "411-1111", activo: false },
    ],
    parametros_dashboard: {
      objetivo_diario: 500000,
      punto_equilibrio_diario: 320000,
    },
  };

  // Ventas registradas en memoria (para que `POST /api/ventas` + `GET /api/ventas/{id}` funcione).
  let POS_VENTA_SEQ = 1000;
  const POS_VENTAS = new Map(); // id -> venta

  function posFindProductById(id) {
    return POS_PRODUCTS.find((p) => Number(p.id) === Number(id)) || null;
  }

  function posFindProductBySkuOrBarcode(code) {
    const c = String(code || "").trim();
    return POS_PRODUCTS.find((p) => String(p.sku) === c || String(p.codigo_barra) === c) || null;
  }

  function posFindClientByClienteId(cliente_id) {
    return POS_CLIENTS.find((c) => Number(c.cliente_id) === Number(cliente_id)) || null;
  }

  function posFindClientByPersonaId(persona_id) {
    return POS_CLIENTS.find((c) => Number(c.persona_id) === Number(persona_id)) || null;
  }

  function posDisponibleCliente(cliente) {
    if (!cliente) return null;
    const limite = Number(cliente.limite_credito ?? 0);
    const saldo = Number(cliente.saldo ?? 0);
    return limite - saldo;
  }

  // Seed pseudo-aleatorio determinista por tick (permite que el refresco muestre cambios).
  let tick = 0;
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a += 0x6d2b79f5;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function fmtDate(d) {
    // ISO corto (YYYY-MM-DD) como lo suelen mostrar los wireframes/SSOT.
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function todayLocal() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }

  function buildVentasPorHora(rand) {
    // Distribución típica: sube al mediodía y baja hacia la tarde.
    const horas = [];
    for (let h = 0; h < 24; h++) {
      const x = h;
      const peso =
        // campana simple alrededor de 12 y otra alrededor de 19
        Math.exp(-Math.pow((x - 12) / 3.2, 2)) * 1.0 +
        Math.exp(-Math.pow((x - 19) / 3.8, 2)) * 0.75 +
        // base de operación
        0.18;
      const vari = 0.85 + rand() * 0.35;
      const cantidad = Math.round(8 + peso * 18 * vari);
      const importeProm = 2800 + rand() * 2600; // importe por ticket (no por unidad)
      const total = Math.round(cantidad * importeProm * (0.92 + rand() * 0.22) / 100) * 100;
      horas.push({
        hora: String(h).padStart(2, "0") + ":00",
        cantidad,
        total,
      });
    }
    return horas;
  }

  function buildAlerts(rand, dias) {
    // stock bajo: parte del catálogo con stock por debajo del mínimo
    const indices = [...Array(PRODUCTS.length).keys()];
    // shuffle simple
    indices.sort(() => rand() - 0.5);
    const stockBajoCount = clamp(Math.floor(4 + rand() * 10), 1, 15);
    const stockBajo = indices.slice(0, stockBajoCount).map((i) => {
      const p = PRODUCTS[i];
      const stock_minimo = Math.round(5 + rand() * 30);
      const stock_actual = Math.round(rand() * (stock_minimo - 1));
      return {
        nombre: p.nombre,
        sku: p.sku,
        stock_actual,
        stock_minimo,
      };
    });

    // vencimientos: generar lotes con días restantes entre 0..dias (o cercano)
    const vencimientosCount = clamp(Math.floor(2 + rand() * 7), 1, 12);
    const base = todayLocal();
    const proximosVencer = indices.slice(stockBajoCount, stockBajoCount + vencimientosCount).map((i, idx) => {
      const p = PRODUCTS[i];
      const dias_restantes = clamp(Math.floor(1 + rand() * dias), 1, dias);
      const fecha = new Date(base.getTime() + dias_restantes * 24 * 60 * 60 * 1000);
      const lote_codigo = `LOTE-${String(idx + 1).padStart(2, "0")}-${fecha.getMonth() + 1}${fecha.getDate()}`;
      return {
        producto_nombre: p.nombre,
        lote_codigo,
        fecha_vencimiento: fmtDate(fecha),
        dias_restantes,
      };
    });

    return { stockBajo, proximosVencer };
  }

  function buildDashboard(rand, diasVencimiento) {
    const ventasHora = buildVentasPorHora(rand);
    const ventas_del_dia = ventasHora.reduce((a, r) => a + (r.cantidad || 0), 0);
    const total_ventas_del_dia = ventasHora.reduce((a, r) => a + (r.total || 0), 0);
    const ticket_promedio = ventas_del_dia > 0 ? total_ventas_del_dia / ventas_del_dia : 0;

    const valor_inventario = Math.round((8_000_000 + rand() * 5_000_000) / 100) * 100;
    const saldo_caja_teorico = Math.round(total_ventas_del_dia * (0.86 + rand() * 0.15) / 100) * 100;
    const { stockBajo, proximosVencer } = buildAlerts(rand, diasVencimiento);

    const stock_bajo = stockBajo.length;
    const proximos_vencer = proximosVencer.length;

    const objetivo_diario = 500_000; // ejemplo (en la vida real: ParametroSistema)
    const punto_equilibrio_diario = 320_000;
    const ganancia_actual = total_ventas_del_dia - punto_equilibrio_diario;
    const cumplimiento_objetivo_diario_pct = objetivo_diario ? Math.round((total_ventas_del_dia / objetivo_diario) * 10000) / 100 : null;
    const cumplimiento_punto_equilibrio_diario_pct = punto_equilibrio_diario
      ? Math.round((total_ventas_del_dia / punto_equilibrio_diario) * 10000) / 100
      : null;

    const now = new Date();
    const minutosHoy = now.getHours() * 60 + now.getMinutes();
    const ritmo = minutosHoy > 0 ? total_ventas_del_dia / minutosHoy : 0;
    const minutosMax = 24 * 60;
    const pronTotal = Math.round(ritmo * minutosMax * (0.95 + rand() * 0.1) / 100) * 100;
    const pronPctObj = objetivo_diario ? Math.round((pronTotal / objetivo_diario) * 10000) / 100 : null;

    const saludEstado = ganancia_actual >= 0 ? "verde" : ganancia_actual > -punto_equilibrio_diario * 0.25 ? "amarillo" : "rojo";

    const salud = {
      estado: saludEstado,
      ingresos_actuales: total_ventas_del_dia,
      punto_equilibrio: punto_equilibrio_diario,
      objetivo_diario,
    };

    const promedios = {
      ultimos_7_dias: Math.round((total_ventas_del_dia * (0.85 + rand() * 0.25)) / 100) * 100,
      este_dia_semana: Math.round((total_ventas_del_dia * (0.8 + rand() * 0.3)) / 100) * 100,
    };

    return {
      ventas_del_dia,
      total_ventas_del_dia,
      ticket_promedio,
      productos_stock_bajo: stock_bajo,
      valor_inventario,
      saldo_caja_teorico,
      alerts: { stockBajo, proximosVencer },
      panel: {
        salud,
        ganancia_actual,
        promedios,
        pronostico: {
          total_hoy: pronTotal,
          porcentaje_cumplimiento_objetivo_diario_pct: pronPctObj,
        },
        punto_equilibrio_diario,
        cumplimiento_punto_equilibrio_diario_pct,
        objetivo_diario,
        cumplimiento_objetivo_diario_pct: cumplimiento_objetivo_diario_pct,
      },
      ventasHora,
    };
  }

  function buildComparativos(rand, todayMetrics) {
    const ventasAyer = Math.max(1, Math.round(todayMetrics.total_ventas_del_dia * (0.78 + rand() * 0.25)));
    const ticketAyer = Math.max(1, Math.round(todayMetrics.ticket_promedio * (0.82 + rand() * 0.25)));

    const productos_stock_bajo_ayer = clamp(Math.round(todayMetrics.productos_stock_bajo * (0.8 + rand() * 0.3)), 0, 40);
    const valor_inventario_ayer = Math.round(todayMetrics.valor_inventario * (0.9 + rand() * 0.2));

    const mkRow = (kpi, valor, valorAnterior) => {
      const varPct = valorAnterior ? ((valor - valorAnterior) / valorAnterior) * 100 : 0;
      return {
        kpi,
        valor,
        valor_anterior: valorAnterior,
        variacion_pct: Math.round(varPct * 100) / 100,
      };
    };

    return [
      mkRow("Ventas del día", todayMetrics.ventas_del_dia, Math.round(todayMetrics.ventas_del_dia * (0.78 + rand() * 0.25))),
      mkRow("Total vendido", todayMetrics.total_ventas_del_dia, ventasAyer),
      mkRow("Ticket promedio", Math.round(todayMetrics.ticket_promedio), Math.round(ticketAyer)),
      mkRow("Stock bajo", todayMetrics.productos_stock_bajo, productos_stock_bajo_ayer),
      mkRow("Valor inventario", todayMetrics.valor_inventario, valor_inventario_ayer),
      mkRow("Saldo teórico caja", todayMetrics.saldo_caja_teorico, Math.round(todayMetrics.saldo_caja_teorico * (0.86 + rand() * 0.25))),
    ];
  }

  async function fetchJson(url) {
    tick += 1;
    const parsed = (() => {
      try {
        return new URL(url);
      } catch {
        return new URL(url, "http://localhost");
      }
    })();

    const pathname = parsed.pathname || "";
    const search = parsed.searchParams;

    // Endpoint matching por PATH (base puede ser cualquier host).
    const rand = mulberry32(0xC0FFEE ^ (tick * 2654435761));
    // Simular latencia para ver el estado de loading en UI.
    await delay(220 + Math.floor(rand() * 180));

    // Dashboard: alertas-operativas?dias_vencimiento=
    if (pathname === "/api/dashboard/alertas-operativas") {
      const dias = Number.parseInt(String(search.get("dias_vencimiento") || "30"), 10) || 30;
      const metrics = buildDashboard(rand, dias);
      return {
        tesoreria: {
          caja_abierta: rand() > 0.12,
          caja_id: rand() > 0.12 ? 120 + Math.floor(rand() * 20) : null,
          saldo_caja_teorico: metrics.saldo_caja_teorico,
        },
        inventario: {
          resumen: {
            stock_bajo: metrics.alerts.stockBajo.length,
            proximos_vencer: metrics.alerts.proximosVencer.length,
          },
          stock_bajo: metrics.alerts.stockBajo,
          proximos_vencer: metrics.alerts.proximosVencer,
        },
      };
    }

    // Dashboard: indicadores
    if (pathname === "/api/dashboard/indicadores") {
      const metrics = buildDashboard(rand, 30);
      return {
        ventas_del_dia: metrics.ventas_del_dia,
        total_ventas_del_dia: metrics.total_ventas_del_dia,
        ticket_promedio: Math.round(metrics.ticket_promedio),
        productos_stock_bajo: metrics.productos_stock_bajo,
        valor_inventario: metrics.valor_inventario,
        saldo_caja_teorico: metrics.saldo_caja_teorico,
      };
    }

    // Dashboard: indicadores-comparativos
    if (pathname === "/api/dashboard/indicadores-comparativos") {
      const metrics = buildDashboard(rand, 30);
      const rows = buildComparativos(rand, metrics);
      return rows;
    }

    // Dashboard: ventas-por-hora
    if (pathname === "/api/dashboard/ventas-por-hora") {
      const metrics = buildDashboard(rand, 30);
      return metrics.ventasHora;
    }

    // Dashboard: productos-stock-bajo
    if (pathname === "/api/dashboard/productos-stock-bajo") {
      const metrics = buildDashboard(rand, 30);
      return metrics.alerts.stockBajo;
    }

    // Dashboard: productos-proximos-vencer?dias=
    if (pathname === "/api/dashboard/productos-proximos-vencer") {
      const dias = Number.parseInt(String(search.get("dias") || "30"), 10) || 30;
      const metrics = buildDashboard(rand, dias);
      // recortar por dias en caso de exceso
      return metrics.alerts.proximosVencer
        .filter((x) => (Number(x.dias_restantes) || 0) <= dias)
        .slice(0, 50);
    }

    // Dashboard: panel-lateral
    if (pathname === "/api/dashboard/panel-lateral") {
      const metrics = buildDashboard(rand, 30);
      return metrics.panel;
    }

    // -------------------------
    // POS (Módulo 2) - GET
    // -------------------------

    // Catálogo de productos (para cargar posCatalogo).
    if (pathname === "/api/productos") {
      const activoOnly = String(search.get("activo_only") || "").toLowerCase() === "true";
      const productos = activoOnly ? POS_PRODUCTS.filter((p) => p.activo) : POS_PRODUCTS;
      return productos.slice(0, 500);
    }

    // Obtener producto por SKU (o código interno / barcode).
    if (pathname.startsWith("/api/productos/por-sku/")) {
      const sku = decodeURIComponent(pathname.split("/").pop() || "");
      const p = posFindProductBySkuOrBarcode(sku);
      if (!p) throw new Error("404");
      return {
        id: p.id,
        sku: p.sku,
        nombre: p.nombre,
        codigo_barra: p.codigo_barra,
        precio_venta: p.precio_venta,
      };
    }

    if (pathname === "/api/configuracion/empresa") {
      return POS_CONFIG.empresa;
    }

    if (pathname === "/api/configuracion/sucursales") {
      const soloActivas = String(search.get("solo_activas") || "").toLowerCase() === "true";
      const items = soloActivas ? POS_CONFIG.sucursales.filter((s) => s.activo) : POS_CONFIG.sucursales;
      return items.slice(0, 200);
    }

    if (pathname.startsWith("/api/configuracion/sucursales/")) {
      const id = Number(pathname.split("/").pop());
      const s = POS_CONFIG.sucursales.find((x) => Number(x.id) === id);
      if (!s) throw new Error("404");
      return s;
    }

    if (pathname === "/api/configuracion/parametros/dashboard") {
      return POS_CONFIG.parametros_dashboard;
    }

    // Búsqueda de clientes para selector en POS.
    if (pathname === "/api/personas/clientes/buscar") {
      const q = String(search.get("q") || "").toLowerCase().trim();
      const limite = Number.parseInt(String(search.get("limite") || "20"), 10) || 20;
      const results = POS_CLIENTS.filter((c) => {
        if (!q) return true;
        const nombreCompleto = `${c.apellido} ${c.nombre}`.toLowerCase();
        const doc = String(c.documento || "").toLowerCase();
        return nombreCompleto.includes(q) || doc.includes(q);
      })
        .slice(0, limite)
        .map((c) => ({
          cliente_id: c.cliente_id,
          persona_id: c.persona_id,
          apellido: c.apellido,
          nombre: c.nombre,
          documento: c.documento,
          telefono: c.telefono,
          limite_credito: c.limite_credito,
        }));
      return results;
    }

    // Resumen de cuenta corriente para un cliente (utilizado por posSeleccionarCliente).
    if (pathname.startsWith("/api/tesoreria/cuentas-corrientes/clientes/") && pathname.endsWith("/resumen")) {
      const parts = pathname.split("/");
      const cliente_id = parts[parts.length - 2];
      const cliente = posFindClientByClienteId(cliente_id);
      if (!cliente) throw new Error("404");
      const saldo = Number(cliente.saldo || 0);
      const limite_credito = Number(cliente.limite_credito || 0);
      const disponible = limite_credito - saldo;
      return { saldo, limite_credito, disponible };
    }

    // Ticket/venta para impresión y vista de POS.
    if (pathname.startsWith("/api/ventas/")) {
      const id = Number(pathname.split("/").pop());
      const venta = POS_VENTAS.get(id) || null;
      if (!venta) throw new Error("404");
      return venta;
    }

    throw new Error(`MockDashboardApi: endpoint no soportado: ${pathname}${parsed.search}`);
  }

  // -------------------------
  // POS (Módulo 2) - POST
  // -------------------------
  function mockFetchResponse(status, payload) {
    const ok = status >= 200 && status < 300;
    return {
      ok,
      status,
      statusText: ok ? "OK" : "Mock Error",
      async text() {
        if (payload === undefined) return "";
        if (typeof payload === "string") return payload;
        return JSON.stringify(payload);
      },
    };
  }

  // Override de fetch para soportar POST del POS sin backend.
  window.fetch = async function (url, init) {
    const method = String(init?.method || "GET").toUpperCase();
    const parsed = (() => {
      try {
        return new URL(url);
      } catch {
        return new URL(url, "http://localhost");
      }
    })();
    const pathname = parsed.pathname || "";

    const bodyText = init?.body ? String(init.body) : "";
    let body = null;
    if (bodyText) {
      try {
        body = JSON.parse(bodyText);
      } catch {
        body = null;
      }
    }

    // Alta rápida de cliente (posAltaRapidaCliente).
    if (method === "POST" && pathname === "/api/personas/clientes/alta-rapida") {
      const nombre = String(body?.nombre || "").trim();
      const apellido = String(body?.apellido || "").trim();
      const documento = String(body?.documento || "").trim();
      const telefono = body?.telefono ?? null;
      const limite_credito = Number(body?.limite_credito ?? 0) || 0;

      const cliente_id = POS_CLIENTE_SEQ++;
      const persona_id = POS_PERSONA_SEQ++;

      POS_CLIENTS.push({
        cliente_id,
        persona_id,
        nombre: nombre || "Cliente",
        apellido: apellido || "",
        documento: documento || String(persona_id),
        telefono: telefono,
        limite_credito,
        saldo: 0,
        activo: true,
      });

      return mockFetchResponse(200, {
        cliente_id,
        persona_id,
        nombre: nombre || "Cliente",
        apellido: apellido || "",
        documento: documento || String(persona_id),
        telefono: telefono,
        limite_credito,
      });
    }

    // Registrar venta (posCobrar -> POST /api/ventas).
    if (method === "POST" && pathname === "/api/ventas") {
      const items = Array.isArray(body?.items) ? body.items : [];
      const descuento = Number(body?.descuento || 0) || 0;
      const metodo_pago = String(body?.metodo_pago || "").trim();
      const clientePersonaId = body?.cliente_id != null ? Number(body.cliente_id) : null;

      if (items.length === 0) {
        return mockFetchResponse(400, { detail: "La venta debe tener al menos un ítem." });
      }

      // Validación stock + subtotal.
      let subtotal = 0;
      const ventaItems = [];
      for (const it of items) {
        const producto_id = Number(it?.producto_id);
        const cantidad = Number(it?.cantidad || 0) || 0;
        const precio_unitario = Number(it?.precio_unitario || 0) || 0;
        const producto = posFindProductById(producto_id);
        if (!producto) {
          return mockFetchResponse(404, { detail: "Producto no encontrado." });
        }
        if (cantidad <= 0) {
          return mockFetchResponse(400, { detail: "Cantidad inválida." });
        }
        if (producto.stock_actual < cantidad) {
          return mockFetchResponse(400, { detail: "stock insuficiente" });
        }

        const lineSubtotal = cantidad * precio_unitario;
        subtotal += lineSubtotal;
        ventaItems.push({
          producto_id,
          nombre_producto: producto.nombre,
          cantidad,
          precio_unitario,
          subtotal: lineSubtotal,
        });
      }

      const total = Math.max(0, subtotal - Math.max(0, descuento));

      // Validación de crédito (solo para cuenta corriente).
      let cliente = null;
      if (metodo_pago === "CUENTA_CORRIENTE") {
        cliente = clientePersonaId != null ? posFindClientByPersonaId(clientePersonaId) : null;
        if (!cliente) {
          return mockFetchResponse(400, { detail: "Cliente no válido para cuenta corriente." });
        }
        const disponible = posDisponibleCliente(cliente);
        if (total > disponible) {
          return mockFetchResponse(400, { detail: "límite de crédito excedido" });
        }
      }

      // Aplicar side-effects: actualizar stock y deuda.
      for (const vIt of ventaItems) {
        const prod = posFindProductById(vIt.producto_id);
        if (prod) prod.stock_actual = Math.max(0, prod.stock_actual - vIt.cantidad);
      }
      if (cliente && metodo_pago === "CUENTA_CORRIENTE") {
        cliente.saldo = Number(cliente.saldo || 0) + total;
      }

      const venta_id = POS_VENTA_SEQ++;
      const creado_en = new Date().toISOString();
      const venta = {
        id: venta_id,
        creado_en,
        items: ventaItems.map((x) => ({
          nombre_producto: x.nombre_producto,
          cantidad: x.cantidad,
          precio_unitario: x.precio_unitario,
          subtotal: x.subtotal,
        })),
        subtotal,
        descuento: Math.max(0, descuento),
        total,
        metodo_pago,
      };
      POS_VENTAS.set(venta_id, venta);

      return mockFetchResponse(200, { venta_id, total });
    }

    // Cualquier otro endpoint no modelado en este prototipo.
    return mockFetchResponse(404, { detail: `Mock fetch: endpoint no soportado (${method} ${pathname})` });
  };

  window.MockDashboardApi = {
    fetchJson,
    // útil para depuración manual
    _getTick: () => tick,
  };
})();

