//

const API_URL = "/api";
const API_TOKEN = "cibertec-demo-2026";
const HEADERS = { Authorization: `Bearer ${API_TOKEN}` };

function esRolLimitado() {
  return localStorage.getItem("cibertec_rol") === "Limitado";
}
function headersConRol(extra) {

  return {
    ...HEADERS,
    "X-Rol": localStorage.getItem("cibertec_rol") || "",
    "X-Usuario": encodeURIComponent(localStorage.getItem("cibertec_usuario") || ""),
    "X-Nombre-Usuario": encodeURIComponent(localStorage.getItem("cibertec_nombre") || ""),
    ...extra,
  };
}

// ===================================================================
// LOGIN (login.html)
// ===================================================================
function initLogin() {
  const form = document.getElementById("form-login");
  const error = document.getElementById("login-error");
  if (localStorage.getItem("cibertec_auth") === "ok") {
    window.location.href = "index.html";
    return;
  }
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    error.hidden = true;
    const usuario = document.getElementById("input-usuario").value.trim();
    const clave = document.getElementById("input-clave").value;
    const boton = form.querySelector("button[type=submit]");
    boton.disabled = true;
    try {
      const cuenta = await apiPost("/auth/login", { usuario, clave });
      localStorage.setItem("cibertec_auth", "ok");
      localStorage.setItem("cibertec_usuario", cuenta.usuario);
      localStorage.setItem("cibertec_nombre", cuenta.nombre_completo);
      localStorage.setItem("cibertec_rol", cuenta.rol);
      window.location.href = "index.html";
    } catch (err) {
      error.textContent = (err.data && err.data.error) || "Usuario o contraseña incorrectos.";
      error.hidden = false;
      boton.disabled = false;
    }
  });
}

// ===================================================================
// HELPERS DE API
// ===================================================================
async function apiGet(ruta) {
  const resp = await fetch(`${API_URL}${ruta}`, { headers: headersConRol() });
  if (!resp.ok) throw new Error(`${ruta} -> HTTP ${resp.status}`);
  return resp.json();
}
async function apiPost(ruta, body) {
  const resp = await fetch(`${API_URL}${ruta}`, {
    method: "POST", headers: headersConRol({ "Content-Type": "application/json" }), body: JSON.stringify(body || {}),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw Object.assign(new Error(data.error || `HTTP ${resp.status}`), { data, status: resp.status });
  return data;
}
async function apiPatch(ruta, body) {
  const resp = await fetch(`${API_URL}${ruta}`, {
    method: "PATCH", headers: headersConRol({ "Content-Type": "application/json" }), body: JSON.stringify(body || {}),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw Object.assign(new Error(data.error || `HTTP ${resp.status}`), { data, status: resp.status });
  return data;
}
async function apiDelete(ruta) {
  const resp = await fetch(`${API_URL}${ruta}`, { method: "DELETE", headers: headersConRol() });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw Object.assign(new Error(data.error || `HTTP ${resp.status}`), { data, status: resp.status });
  return data;
}
async function apiUpload(ruta, formData) {
  const resp = await fetch(`${API_URL}${ruta}`, { method: "POST", headers: headersConRol(), body: formData });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw Object.assign(new Error(data.error || `HTTP ${resp.status}`), { data, status: resp.status });
  return data;
}

function marcarConexion(ok, detalle) {
  const el = document.getElementById("estado-conexion");
  if (!el) return;
  el.className = `estado-conexion ${ok ? "ok" : "error"}`;
  el.textContent = ok ? "API conectada" : `Error de conexión: ${detalle}`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function descargarCSV(nombre, filas) {
  const csv = filas.map((f) => f.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = nombre;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

// ===================================================================
// GRÁFICOS (sin librerías externas)
// ===================================================================
function renderBarChart(el, datos, opts = {}) {
  const max = Math.max(1, ...datos.map((d) => d.valor));
  el.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "bar-chart";
  for (const d of datos) {
    const grupo = document.createElement("div");
    grupo.className = "grupo";
    const barra = document.createElement("div");
    barra.className = "barra";
    barra.style.height = `${Math.round((d.valor / max) * 170)}px`;
    if (opts.color) barra.style.background = opts.color;
    barra.innerHTML = `<span class="valor">${d.valor}</span>`;
    const etiqueta = document.createElement("div");
    etiqueta.className = "etiqueta";
    etiqueta.textContent = d.etiqueta;
    etiqueta.title = d.etiqueta;
    grupo.appendChild(barra);
    grupo.appendChild(etiqueta);
    wrap.appendChild(grupo);
  }
  el.appendChild(wrap);
}

const PALETA_DONUT = ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#64748b"];

function renderDonut(el, datos) {
  const total = datos.reduce((s, d) => s + d.valor, 0) || 1;
  const r = 52, cx = 60, cy = 60, grosor = 18;
  const circ = 2 * Math.PI * r;
  let acumulado = 0;
  let circulos = "";
  datos.forEach((d, i) => {
    const frac = d.valor / total;
    const largo = frac * circ;
    const color = d.color || PALETA_DONUT[i % PALETA_DONUT.length];
    circulos += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="${grosor}"
      stroke-dasharray="${largo} ${circ - largo}" stroke-dashoffset="${-acumulado}" transform="rotate(-90 ${cx} ${cy})"/>`;
    acumulado += largo;
  });
  const leyenda = datos.map((d, i) => {
    const color = d.color || PALETA_DONUT[i % PALETA_DONUT.length];
    const pct = ((d.valor / total) * 100).toFixed(1);
    return `<div class="fila"><i style="background:${color}"></i>${esc(d.etiqueta)} — ${d.valor} (${pct}%)</div>`;
  }).join("");
  el.innerHTML = `
    <div class="donut-wrap">
      <svg width="120" height="120" viewBox="0 0 120 120">${circulos}</svg>
      <div class="leyenda-donut">${leyenda || '<span class="vacio">Sin datos</span>'}</div>
    </div>`;
}

// ===================================================================
// MODAL
// ===================================================================
function abrirModal(html) {
  let overlay = document.getElementById("overlay-modal");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "overlay-modal";
    overlay.className = "overlay-modal";
    overlay.addEventListener("click", (e) => { if (e.target === overlay) cerrarModal(); });
    document.body.appendChild(overlay);
  }
  overlay.innerHTML = `<div class="modal">${html}</div>`;
  overlay.hidden = false;
}
function cerrarModal() {
  const overlay = document.getElementById("overlay-modal");
  if (overlay) overlay.hidden = true;
}

// ===================================================================
// DATOS DE REFERENCIA (catálogo compartido con el backend)
// ===================================================================
const TIPOS_PC = ["Desktop", "iMac", "Laptop", "Workstation"];
const CATEGORIAS = ["Avanzada", "Estándar"];

// ===================================================================
// ROUTER
// ===================================================================
const RUTA_POR_DEFECTO = "dashboard";

const RUTAS_SOLO_ADMIN = new Set(["rpa", "analitica", "usuarios", "bitacora", "configuracion"]);

async function router() {
  const ruta = (location.hash || `#${RUTA_POR_DEFECTO}`).slice(1);
  document.querySelectorAll("#nav-principal a").forEach((a) => {
    a.classList.toggle("activo", a.dataset.ruta === ruta);
  });
  const vista = document.getElementById("vista");

  // Control de acceso por rol: aunque el enlace esté oculto en el menú
  // para una cuenta "Limitado", se bloquea también la navegación
  // directa por hash (#rpa, #configuracion, etc.) — la interfaz nunca
  // depende solo de esconder el botón.
  if (RUTAS_SOLO_ADMIN.has(ruta) && esRolLimitado()) {
    vista.innerHTML = `
      <div class="card">
        <h2>Acceso restringido</h2>
        <p class="texto-muted">Esta sección requiere una cuenta con rol <strong>Administrador</strong>. Su cuenta (<strong>${esc(localStorage.getItem("cibertec_nombre") || "")}</strong>) tiene rol <strong>Limitado</strong>.</p>
      </div>`;
    marcarConexion(true);
    return;
  }

  const render = VISTAS[ruta] || VISTAS[RUTA_POR_DEFECTO];
  vista.innerHTML = '<p class="vacio">Cargando…</p>';
  try {
    await render(vista);
    marcarConexion(true);
  } catch (err) {
    console.error(err);
    marcarConexion(false, err.message);
    vista.innerHTML = `<div class="card"><p class="modal-error">No se pudo cargar esta sección: ${esc(err.message)}</p></div>`;
  }
}

// ===================================================================
// VISTA: DASHBOARD PRINCIPAL
// ===================================================================
async function vistaDashboard(vista) {
  const [ind, equipos, alertas, actividad] = await Promise.all([
    apiGet("/indicadores"),
    apiGet("/equipos"),
    apiGet("/alertas?estado=activa"),
    apiGet("/actividad-reciente?limite=8"),
  ]);

  const porTipo = {};
  for (const e of equipos) porTipo[e.tipo_pc] = (porTipo[e.tipo_pc] || 0) + 1;

  vista.innerHTML = `
    <div class="page-header">
      <h1>Dashboard Principal</h1>
      <p>Visión general del parque de equipos de las 7 sedes de CIBERTEC.</p>
    </div>
    <div class="grid-kpi">
      <div class="kpi"><div class="kpi-label">Total Activos</div><div class="kpi-valor">${ind.cantidad_equipos}</div></div>
      <div class="kpi kpi-ok"><div class="kpi-label">Activos Operativos</div><div class="kpi-valor">${ind.equipos_operativos}</div></div>
      <div class="kpi kpi-warn"><div class="kpi-label">Con fallas</div><div class="kpi-valor">${ind.equipos_con_fallas}</div></div>
      <div class="kpi kpi-danger"><div class="kpi-label">Faltantes (alertas)</div><div class="kpi-valor">${ind.equipos_faltantes_activos}</div></div>
      <div class="kpi"><div class="kpi-label">Con +7 años de uso</div><div class="kpi-valor">${ind.equipos_mas_7_anios}</div></div>
    </div>
    <div class="grid-2">
      <div class="card">
        <h2>Activos por sede</h2>
        <div id="chart-sede"></div>
      </div>
      <div class="card">
        <h2>Alertas inteligentes <span class="hint">(activas)</span></h2>
        <div class="lista-alertas" id="lista-alertas"></div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card">
        <h2>Distribución por tipo de equipo</h2>
        <div id="chart-tipo"></div>
      </div>
      <div class="card">
        <h2>Últimas actividades</h2>
        <div class="lista-actividad" id="lista-actividad"></div>
      </div>
    </div>
  `;

  renderBarChart(vista.querySelector("#chart-sede"), ind.por_sede.map((s) => ({ etiqueta: s.sede, valor: s.total_equipos })));
  const COLOR_TIPO_PC = { Desktop: "#d97706", iMac: "#0891b2", Laptop: "#7c3aed", Workstation: "#2563eb" };
  renderDonut(vista.querySelector("#chart-tipo"), TIPOS_PC.map((t) => ({ etiqueta: t, valor: porTipo[t] || 0, color: COLOR_TIPO_PC[t] })));

  const listaAlertas = vista.querySelector("#lista-alertas");
  const top = alertas.slice(0, 6);
  listaAlertas.innerHTML = top.length
    ? top.map((a) => {
        const clase = a.tipo_alerta === "fin_vida_util" ? "media" : "critica";
        return `<div class="item-alerta ${clase}">
          <span class="titulo">${esc(a.tipo_alerta.replace("_", " "))} — ${esc(a.codigo_activo_case)}</span>
          <span class="sub">${esc(a.nombre_sede)} · ${esc(a.codigo_aula)} · ${esc(a.fecha_generacion)}</span>
        </div>`;
      }).join("")
    : '<p class="vacio">Sin alertas activas.</p>';

  const listaAct = vista.querySelector("#lista-actividad");
  listaAct.innerHTML = actividad.length
    ? actividad.map((a) => {
        const esConciliacion = a.tipo === "conciliacion";
        const icono = esConciliacion
          ? '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>'
          : '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01"/><circle cx="12" cy="12" r="9"/></svg>';
        const titulo = esConciliacion ? `Conciliación registrada — ${esc(a.referencia)}` : `Alerta generada (${esc(a.detalle)}) — ${esc(a.referencia)}`;
        return `<div class="item-actividad"><div class="icono">${icono}</div><div><div class="titulo">${titulo}</div><div class="sub">${esc(a.sede)} · ${esc(a.fecha)}</div></div></div>`;
      }).join("")
    : '<p class="vacio">Sin actividad registrada todavía.</p>';
}

// ===================================================================
// VISTA: INVENTARIO (CRUD real de equipos)
// ===================================================================
const estadoInventario = { pagina: 1, porPagina: 50, filtroSede: "", filtroAmbiente: "", filtroTipo: "", busqueda: "" };

async function vistaInventario(vista) {
  const [sedes, equipos] = await Promise.all([apiGet("/sedes"), apiGet("/equipos")]);

  vista.innerHTML = `
    <div class="page-header-row">
      <div>
        <h1>Gestión de Inventario</h1>
        <p>${equipos.length} equipos registrados en el sistema.</p>
      </div>
      ${esRolLimitado() ? '<span class="badge media">Acceso de solo lectura</span>' : '<button class="btn btn-primario" id="btn-nuevo-activo">+ Nuevo Activo</button>'}
    </div>
    <div class="barra-filtros">
      <select id="f-sede"><option value="">Todas las sedes</option>${sedes.map((s) => `<option value="${esc(s.nombre)}">${esc(s.nombre)}</option>`).join("")}</select>
      <select id="f-tipo"><option value="">Todos los tipos</option>${TIPOS_PC.map((t) => `<option value="${t}">${t}</option>`).join("")}</select>
      <select id="f-estado"><option value="">Todos los estados</option><option value="Operativo">Operativo</option><option value="Inoperativo">Inoperativo</option></select>
      <input type="search" id="f-buscar" placeholder="Buscar por código, marca o modelo…">
    </div>
    <div class="card">
      <div class="tabla-wrap">
        <table>
          <thead><tr><th>Código</th><th>Tipo / Categoría</th><th>Marca</th><th>Modelo</th><th>Serie</th><th>Sede</th><th>Estado</th><th>Acciones</th></tr></thead>
          <tbody id="tbody-inventario"></tbody>
        </table>
      </div>
      <div class="paginacion" id="paginacion-inventario"></div>
    </div>
  `;

  let datos = equipos;

  function aplicarFiltros() {
    datos = equipos.filter((e) => {
      if (estadoInventario.filtroSede && e.nombre_sede !== estadoInventario.filtroSede) return false;
      if (estadoInventario.filtroTipo && e.tipo_pc !== estadoInventario.filtroTipo) return false;
      if (estadoInventario.filtroAmbiente && e.estado_case !== estadoInventario.filtroAmbiente) return false;
      if (estadoInventario.busqueda) {
        const q = estadoInventario.busqueda.toLowerCase();
        if (![e.codigo_activo_case, e.marca, e.modelo].some((v) => (v || "").toLowerCase().includes(q))) return false;
      }
      return true;
    });
    estadoInventario.pagina = 1;
    pintarTabla();
  }

  function pintarTabla() {
    const inicio = (estadoInventario.pagina - 1) * estadoInventario.porPagina;
    const pagina = datos.slice(inicio, inicio + estadoInventario.porPagina);
    const tbody = vista.querySelector("#tbody-inventario");
    tbody.innerHTML = pagina.length
      ? pagina.map((e) => `
        <tr>
          <td>${esc(e.codigo_activo_case)}</td>
          <td>${esc(e.tipo_pc)} · ${esc(e.categoria)}</td>
          <td>${esc(e.marca)}</td>
          <td>${esc(e.modelo)}</td>
          <td>${esc(e.service_tag_case)}</td>
          <td>${esc(e.nombre_sede)}</td>
          <td><span class="badge ${e.estado_case === "Operativo" ? "operativo" : "inoperativo"}">${esc(e.estado_case)}</span></td>
          <td class="acciones-tabla">
            <button class="btn-icono" data-accion="ver" data-id="${e.id_equipo}">Ver</button>
            ${esRolLimitado() ? "" : `
            <button class="btn-icono" data-accion="editar" data-id="${e.id_equipo}">Editar</button>
            <button class="btn-icono peligro" data-accion="eliminar" data-id="${e.id_equipo}">Eliminar</button>`}
          </td>
        </tr>`).join("")
      : '<tr><td colspan="8" class="vacio">Sin resultados para el filtro aplicado.</td></tr>';

    const totalPaginas = Math.max(1, Math.ceil(datos.length / estadoInventario.porPagina));
    const pag = vista.querySelector("#paginacion-inventario");
    pag.innerHTML = `
      <span>${datos.length} resultado(s) · página ${estadoInventario.pagina} de ${totalPaginas}</span>
      <button id="pag-prev" ${estadoInventario.pagina <= 1 ? "disabled" : ""}>‹ Anterior</button>
      <button id="pag-next" ${estadoInventario.pagina >= totalPaginas ? "disabled" : ""}>Siguiente ›</button>
    `;
    pag.querySelector("#pag-prev")?.addEventListener("click", () => { estadoInventario.pagina--; pintarTabla(); });
    pag.querySelector("#pag-next")?.addEventListener("click", () => { estadoInventario.pagina++; pintarTabla(); });

    tbody.querySelectorAll("[data-accion]").forEach((btn) => {
      btn.addEventListener("click", () => manejarAccionEquipo(btn.dataset.accion, Number(btn.dataset.id)));
    });
  }

  async function manejarAccionEquipo(accion, id) {
    const equipo = equipos.find((e) => e.id_equipo === id);
    if (!equipo) return;
    if (accion === "ver") return modalVerEquipo(equipo);
    if (accion === "editar") return modalFormEquipo(equipo, async (cambios) => {
      const actualizado = await apiPatch(`/equipos/${id}`, cambios);
      Object.assign(equipo, actualizado);
      cerrarModal();
      aplicarFiltros();
    });
    if (accion === "eliminar") {
      if (!confirm(`¿Eliminar el equipo ${equipo.codigo_activo_case}? Esta acción no se puede deshacer.`)) return;
      await apiDelete(`/equipos/${id}`);
      const idx = equipos.indexOf(equipo);
      equipos.splice(idx, 1);
      aplicarFiltros();
    }
  }

  function modalVerEquipo(e) {
    abrirModal(`
      <h3>Detalle del activo — ${esc(e.codigo_activo_case)}</h3>
      <table class="tabla-config">
        <tr><td>Tipo de equipo</td><td>${esc(e.tipo_pc)}</td></tr>
        <tr><td>Categoría</td><td>${esc(e.categoria)}</td></tr>
        <tr><td>Marca / Modelo</td><td>${esc(e.marca)} ${esc(e.modelo)}</td></tr>
        <tr><td>Service tag</td><td>${esc(e.service_tag_case)}</td></tr>
        <tr><td>Sede / Ambiente</td><td>${esc(e.nombre_sede)} — ${esc(e.codigo_aula)}</td></tr>
        <tr><td>Año de recepción</td><td>${esc(e.anio_recepcion)}</td></tr>
        <tr><td>Años de uso</td><td>${esc(e.anios_uso)}</td></tr>
        <tr><td>Modalidad</td><td>${esc(e.leasing_o_propio)}</td></tr>
        <tr><td>Estado del equipo</td><td>${esc(e.estado_case)}</td></tr>
        <tr><td>Estado del monitor</td><td>${esc(e.estado_monitor)}</td></tr>
        <tr><td>Prioridad de renovación</td><td>${esc(e.prioridad_renovacion || "—")}</td></tr>
      </table>
      <div class="modal-acciones" style="margin-top:18px;"><button class="btn btn-secundario" id="btn-cerrar-modal">Cerrar</button></div>
    `);
    document.getElementById("btn-cerrar-modal").addEventListener("click", cerrarModal);
  }

  function modalFormEquipo(equipo, onGuardar) {
    const editar = Boolean(equipo && equipo.id_equipo);
    const e = equipo || {};
    abrirModal(`
      <h3>${editar ? "Editar activo" : "Registrar nuevo activo"}</h3>
      <p class="modal-error" id="form-error" hidden></p>
      <form id="form-equipo">
        <div class="form-grid">
          <label>Código patrimonial<input name="codigo_activo_case" value="${esc(e.codigo_activo_case || "")}" ${editar ? "readonly" : "required"}></label>
          <label>Tipo de equipo<select name="tipo_pc">${TIPOS_PC.map((t) => `<option ${e.tipo_pc === t ? "selected" : ""}>${t}</option>`).join("")}</select></label>
          <label>Marca<input name="marca" value="${esc(e.marca || "")}" required></label>
          <label>Modelo<input name="modelo" value="${esc(e.modelo || "")}" required></label>
          <label>Categoría<select name="categoria">${CATEGORIAS.map((c) => `<option ${e.categoria === c ? "selected" : ""}>${c}</option>`).join("")}</select></label>
          <label>Modalidad<select name="leasing_o_propio"><option ${e.leasing_o_propio === "Propio" ? "selected" : ""}>Propio</option><option ${e.leasing_o_propio === "Leasing" ? "selected" : ""}>Leasing</option></select></label>
          <label>Año de recepción<input type="number" name="anio_recepcion" value="${esc(e.anio_recepcion ?? 2026)}"></label>
          <label>Años de uso<input type="number" name="anios_uso" value="${esc(e.anios_uso ?? 0)}"></label>
          <label>Estado del equipo<select name="estado_case"><option ${e.estado_case === "Operativo" || !editar ? "selected" : ""}>Operativo</option><option ${e.estado_case === "Inoperativo" ? "selected" : ""}>Inoperativo</option></select></label>
          <label>Sede<select name="id_sede">${sedes.map((s) => `<option value="${s.id_sede}">${esc(s.nombre)}</option>`).join("")}</select></label>
          <label class="span-2">Ambiente<select name="id_espacio"></select></label>
        </div>
        <div class="modal-acciones">
          <button type="button" class="btn btn-secundario" id="btn-cancelar-form">Cancelar</button>
          <button type="submit" class="btn btn-primario">Guardar</button>
        </div>
      </form>
    `);

    const form = document.getElementById("form-equipo");
    const selSede = form.querySelector('[name="id_sede"]');
    const selEspacio = form.querySelector('[name="id_espacio"]');

    async function cargarEspacios(idSedePreferido, idEspacioPreferido) {
      const idSede = idSedePreferido || Number(selSede.value);
      const espacios = await apiGet(`/espacios?id_sede=${idSede}`);
      selEspacio.innerHTML = espacios.map((es) => `<option value="${es.id_espacio}">${esc(es.codigo_aula)} (${esc(es.tipo_ambiente)})</option>`).join("");
      if (idEspacioPreferido) selEspacio.value = idEspacioPreferido;
    }

    if (editar) {
      const sedeActual = sedes.find((s) => s.nombre === e.nombre_sede);
      if (sedeActual) selSede.value = sedeActual.id_sede;
      cargarEspacios(sedeActual ? sedeActual.id_sede : sedes[0]?.id_sede, e.id_espacio);
    } else {
      cargarEspacios(sedes[0]?.id_sede);
    }
    selSede.addEventListener("change", () => cargarEspacios());

    document.getElementById("btn-cancelar-form").addEventListener("click", cerrarModal);
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(form);
      const cuerpo = Object.fromEntries(fd.entries());
      cuerpo.id_espacio = Number(cuerpo.id_espacio);
      cuerpo.anio_recepcion = Number(cuerpo.anio_recepcion);
      cuerpo.anios_uso = Number(cuerpo.anios_uso);
      delete cuerpo.id_sede;
      try {
        await onGuardar(cuerpo);
      } catch (err) {
        const el = document.getElementById("form-error");
        el.textContent = err.message;
        el.hidden = false;
      }
    });
  }

  vista.querySelector("#btn-nuevo-activo")?.addEventListener("click", () => {
    modalFormEquipo(null, async (cuerpo) => {
      const nuevo = await apiPost("/equipos", cuerpo);
      equipos.unshift(nuevo);
      cerrarModal();
      aplicarFiltros();
    });
  });
  vista.querySelector("#f-sede").addEventListener("change", (e) => { estadoInventario.filtroSede = e.target.value; aplicarFiltros(); });
  vista.querySelector("#f-tipo").addEventListener("change", (e) => { estadoInventario.filtroTipo = e.target.value; aplicarFiltros(); });
  vista.querySelector("#f-estado").addEventListener("change", (e) => { estadoInventario.filtroAmbiente = e.target.value; aplicarFiltros(); });
  vista.querySelector("#f-buscar").addEventListener("input", (e) => { estadoInventario.busqueda = e.target.value; aplicarFiltros(); });

  aplicarFiltros();
}

// ===================================================================
// VISTA: AUTOMATIZACIÓN RPA
// ===================================================================
async function vistaRPA(vista) {
  vista.innerHTML = `
    <div class="page-header">
      <h1>Inventario Automatizado RPA</h1>
      <p>Ejecuta en vivo la misma lógica del bot de conciliación (<code>rpa_bot/bot_conciliacion.py</code>) directamente desde el navegador.</p>
    </div>
    <div class="rpa-pasos">
      <div class="card">
        <h2>Paso 1: Robot de inventario</h2>
        <div class="rpa-icono-robot">
          <svg width="70" height="70" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.3">
            <rect x="5" y="7" width="14" height="11" rx="2"/><circle cx="9" cy="12" r="1.1" fill="#2563eb" stroke="none"/><circle cx="15" cy="12" r="1.1" fill="#2563eb" stroke="none"/>
            <path d="M12 7V4M9 4h6"/><path d="M3 12H1M23 12h-2"/>
          </svg>
        </div>
        <p class="texto-muted">Seleccione un archivo CSV con el conteo físico trimestral, o genere uno de ejemplo con la distribución real de CIBERTEC para la demostración.</p>
        <div class="dropzone">
          <input type="file" id="input-archivo-conteo" accept=".csv">
        </div>
        <button class="btn btn-secundario" id="btn-generar-conteo" style="width:100%;margin-bottom:8px;">Generar conteo de ejemplo (trimestre oct)</button>
        <p class="texto-muted" id="preview-conteo"></p>
      </div>

      <div class="card">
        <h2>Paso 2: Ejecutar robot</h2>
        <select id="sel-trimestre" style="margin-bottom:12px;padding:8px;border-radius:7px;border:1.5px solid var(--border);">
          <option value="oct">Trimestre: Octubre</option>
          <option value="ene">Trimestre: Enero</option>
          <option value="abr">Trimestre: Abril</option>
          <option value="jul">Trimestre: Julio</option>
        </select>
        <button class="btn btn-primario" id="btn-ejecutar-robot" style="width:100%;">Ejecutar Robot</button>
        <div class="paso-log" id="paso-log" hidden>
          <div class="paso" data-paso="0"><span class="check"></span> Conectando con la API…</div>
          <div class="paso" data-paso="1"><span class="check"></span> Leyendo archivo de conteo físico…</div>
          <div class="paso" data-paso="2"><span class="check"></span> Validando estructura y sedes…</div>
          <div class="paso" data-paso="3"><span class="check"></span> Comparando contra el registro maestro…</div>
          <div class="paso" data-paso="4"><span class="check"></span> Generando alertas y actualizando base de datos…</div>
          <div class="paso" data-paso="5"><span class="check"></span> Proceso completado</div>
        </div>
        <div id="resultado-robot"></div>
      </div>
    </div>
    <div class="card" style="margin-top:18px;">
      <h2>Bitácora del robot</h2>
      <div class="bitacora" id="bitacora-robot">En espera de ejecución…</div>
    </div>
  `;

  vista.querySelector("#btn-generar-conteo").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      const r = await apiPost("/rpa/generar-conteo", { trimestre: vista.querySelector("#sel-trimestre").value });
      vista.querySelector("#preview-conteo").textContent =
        `Archivo generado: ${r.total} registros (${r.con_discrepancia} con discrepancia esperada).`;
    } finally {
      e.target.disabled = false;
    }
  });

  vista.querySelector("#btn-ejecutar-robot").addEventListener("click", async () => {
    const btn = vista.querySelector("#btn-ejecutar-robot");
    const pasoLog = vista.querySelector("#paso-log");
    const resultadoEl = vista.querySelector("#resultado-robot");
    const bitacoraEl = vista.querySelector("#bitacora-robot");
    const archivoInput = vista.querySelector("#input-archivo-conteo");
    const trimestre = vista.querySelector("#sel-trimestre").value;

    btn.disabled = true;
    resultadoEl.innerHTML = "";
    pasoLog.hidden = false;
    bitacoraEl.textContent = "";
    const pasos = [...pasoLog.querySelectorAll(".paso")];
    pasos.forEach((p) => p.classList.remove("hecho", "activo"));

    const avance = animarPasos(pasos);

    try {
      let resultado;
      if (archivoInput.files.length) {
        const fd = new FormData();
        fd.append("archivo", archivoInput.files[0]);
        fd.append("trimestre", trimestre);
        resultado = await apiUpload("/rpa/ejecutar", fd);
      } else {
        resultado = await apiPost("/rpa/ejecutar", { trimestre });
      }
      await avance.completar();
      bitacoraEl.textContent = (resultado.bitacora || []).join("\n");
      const errores = (resultado.errores || []).length;
      resultadoEl.innerHTML = `<div class="banner-resultado ok">
        Proceso completado: ${resultado.conciliados} conciliados sin novedad, ${resultado.con_discrepancia} con discrepancia,
        ${resultado.alertas_generadas} alertas generadas${errores ? `, ${errores} error(es) controlado(s)` : ""}.
      </div>`;
    } catch (err) {
      avance.detener();
      bitacoraEl.textContent = `ERROR: ${err.message}`;
      resultadoEl.innerHTML = `<div class="banner-resultado error">${esc(err.message)}</div>`;
    } finally {
      btn.disabled = false;
    }
  });
}

function animarPasos(pasos) {
  let cancelado = false;
  let i = 0;
  const marcar = () => {
    if (cancelado || i >= pasos.length - 1) return;
    pasos[i].classList.add("hecho");
    i++;
    pasos[i]?.classList.add("activo");
  };
  pasos[0]?.classList.add("activo");
  const intervalo = setInterval(marcar, 380);
  return {
    completar: () => new Promise((resolve) => {
      clearInterval(intervalo);
      const terminar = setInterval(() => {
        if (i >= pasos.length - 1) {
          pasos[pasos.length - 1].classList.add("hecho");
          clearInterval(terminar);
          resolve();
        } else {
          marcar();
        }
      }, 220);
    }),
    detener: () => { cancelado = true; clearInterval(intervalo); },
  };
}

// ===================================================================
// VISTA: DASHBOARD INTELIGENTE (analítica CRISP-DM)
// ===================================================================
async function vistaAnalitica(vista) {
  const [equipos, alertas, priorizacion] = await Promise.all([
    apiGet("/equipos"), apiGet("/alertas"), apiGet("/priorizacion-renovacion?top=200"),
  ]);

  const porMarca = {};
  for (const e of equipos) porMarca[e.marca] = (porMarca[e.marca] || 0) + 1;
  const antiguedadPorSede = {};
  const conteoPorSede = {};
  for (const e of equipos) {
    antiguedadPorSede[e.nombre_sede] = (antiguedadPorSede[e.nombre_sede] || 0) + e.anios_uso;
    conteoPorSede[e.nombre_sede] = (conteoPorSede[e.nombre_sede] || 0) + 1;
  }
  const activas = alertas.filter((a) => a.estado === "activa");
  const criticas = activas.filter((a) => a.tipo_alerta !== "fin_vida_util").length;
  const advertencias = activas.filter((a) => a.tipo_alerta === "fin_vida_util").length;
  const atendidas = alertas.length - activas.length;

  const distribucionPrioridad = { Alta: 0, Media: 0, Baja: 0, "Sin calcular": 0 };
  for (const e of equipos) {
    const p = priorizacion.find((x) => x.codigo_activo_case === e.codigo_activo_case);
    distribucionPrioridad[p ? p.prioridad_renovacion : "Sin calcular"]++;
  }

  vista.innerHTML = `
    <div class="page-header-row">
      <div>
        <h1>Dashboard Analítico e Inteligente</h1>
        <p>Motor de priorización de renovación — modelo CRISP-DM (índice compuesto + KMeans de validación).</p>
      </div>
      <button class="btn btn-exito" id="btn-ejecutar-motor">Ejecutar motor de priorización</button>
    </div>
    <div id="resultado-motor"></div>
    <div class="grid-3">
      <div class="card"><h2>Alertas — estado general</h2>
        <div class="semaforo"><span class="luz rojo" title="Críticas"></span><span class="luz amarillo" title="Advertencia"></span><span class="luz verde" title="Atendidas"></span></div>
        <p class="texto-muted">${criticas} críticas · ${advertencias} advertencia (fin de vida útil) · ${atendidas} atendidas</p>
      </div>
      <div class="card"><h2>Equipos por marca</h2><div id="chart-marca"></div></div>
      <div class="card"><h2>Prioridad de renovación</h2><div id="chart-prioridad"></div></div>
    </div>
    <div class="grid-2">
      <div class="card"><h2>Antigüedad promedio por sede (años)</h2><div id="chart-antiguedad"></div></div>
      <div class="card"><h2>Equipos prioritarios para renovación</h2>
        <div class="tabla-wrap"><table>
          <thead><tr><th>Equipo</th><th>Sede</th><th>Años de uso</th><th>Prioridad</th></tr></thead>
          <tbody id="tbody-prioridad"></tbody>
        </table></div>
      </div>
    </div>
  `;

  renderBarChart(vista.querySelector("#chart-marca"),
    Object.entries(porMarca).sort((a, b) => b[1] - a[1]).map(([m, n]) => ({ etiqueta: m, valor: n })));
  renderDonut(vista.querySelector("#chart-prioridad"), [
    { etiqueta: "Alta", valor: distribucionPrioridad.Alta, color: "#dc2626" },
    { etiqueta: "Media", valor: distribucionPrioridad.Media, color: "#d97706" },
    { etiqueta: "Baja", valor: distribucionPrioridad.Baja, color: "#16a34a" },
    { etiqueta: "Sin calcular", valor: distribucionPrioridad["Sin calcular"], color: "#94a3b8" },
  ]);
  renderBarChart(vista.querySelector("#chart-antiguedad"),
    Object.keys(conteoPorSede).map((s) => ({ etiqueta: s, valor: Math.round((antiguedadPorSede[s] / conteoPorSede[s]) * 10) / 10 })),
    { color: "#7c3aed" });

  function pintarTablaPrioridad(lista) {
    const top = lista.filter((e) => e.prioridad_renovacion === "Alta").slice(0, 12);
    const tbody = vista.querySelector("#tbody-prioridad");
    tbody.innerHTML = top.length
      ? top.map((e) => `<tr><td>${esc(e.codigo_activo_case)}</td><td>${esc(e.nombre_sede)}</td><td>${esc(e.anios_uso)}</td><td><span class="badge alta">Alta</span></td></tr>`).join("")
      : '<tr><td colspan="4" class="vacio">Ejecute el motor de priorización para ver resultados.</td></tr>';
  }
  pintarTablaPrioridad(priorizacion);

  vista.querySelector("#btn-ejecutar-motor").addEventListener("click", async (e) => {
    const btn = e.target;
    btn.disabled = true;
    btn.textContent = "Calculando…";
    const resultadoEl = vista.querySelector("#resultado-motor");
    resultadoEl.innerHTML = "";
    try {
      const r = await apiPost("/analitica/ejecutar", {});
      resultadoEl.innerHTML = `<div class="banner-resultado ok">Motor ejecutado: ${r.equipos_actualizados} equipos actualizados
        (Alta: ${r.distribucion_prioridad.Alta || 0} · Media: ${r.distribucion_prioridad.Media || 0} · Baja: ${r.distribucion_prioridad.Baja || 0}).</div>`;
      pintarTablaPrioridad(r.top10.map((t) => ({ ...t })).concat(priorizacion).filter((v, i, arr) => arr.findIndex((x) => x.codigo_activo_case === v.codigo_activo_case) === i));
      renderDonut(vista.querySelector("#chart-prioridad"), [
        { etiqueta: "Alta", valor: r.distribucion_prioridad.Alta || 0, color: "#dc2626" },
        { etiqueta: "Media", valor: r.distribucion_prioridad.Media || 0, color: "#d97706" },
        { etiqueta: "Baja", valor: r.distribucion_prioridad.Baja || 0, color: "#16a34a" },
      ]);
    } catch (err) {
      resultadoEl.innerHTML = `<div class="banner-resultado error">${esc(err.message)}</div>`;
    } finally {
      btn.disabled = false;
      btn.textContent = "Ejecutar motor de priorización";
    }
  });
}

// ===================================================================
// VISTA: REPORTES
// ===================================================================
async function vistaReportes(vista) {
  vista.innerHTML = `
    <div class="page-header"><h1>Reportes</h1><p>Exporta los datos actuales del sistema en formato CSV.</p></div>
    <div class="grid-3">
      <div class="card"><h2>Inventario completo</h2><p class="texto-muted">Todos los equipos con su sede, estado y antigüedad.</p><button class="btn btn-primario" id="rep-inventario">Exportar CSV</button></div>
      <div class="card"><h2>Alertas activas</h2><p class="texto-muted">Listado vigente de alertas sin atender.</p><button class="btn btn-primario" id="rep-alertas">Exportar CSV</button></div>
      <div class="card"><h2>Priorización de renovación</h2><p class="texto-muted">Resultado del motor CRISP-DM por equipo.</p><button class="btn btn-primario" id="rep-priorizacion">Exportar CSV</button></div>
    </div>
  `;
  vista.querySelector("#rep-inventario").addEventListener("click", async () => {
    const equipos = await apiGet("/equipos");
    descargarCSV("inventario_cibertec.csv", [
      ["codigo_activo_case", "tipo_pc", "categoria", "marca", "modelo", "sede", "ambiente", "anios_uso", "estado_case"],
      ...equipos.map((e) => [e.codigo_activo_case, e.tipo_pc, e.categoria, e.marca, e.modelo, e.nombre_sede, e.codigo_aula, e.anios_uso, e.estado_case]),
    ]);
  });
  vista.querySelector("#rep-alertas").addEventListener("click", async () => {
    const alertas = await apiGet("/alertas?estado=activa");
    descargarCSV("alertas_activas_cibertec.csv", [
      ["sede", "aula", "codigo_activo_case", "tipo_pc", "tipo_alerta", "fecha_generacion"],
      ...alertas.map((a) => [a.nombre_sede, a.codigo_aula, a.codigo_activo_case, a.tipo_pc, a.tipo_alerta, a.fecha_generacion]),
    ]);
  });
  vista.querySelector("#rep-priorizacion").addEventListener("click", async () => {
    const p = await apiGet("/priorizacion-renovacion?top=2000");
    descargarCSV("priorizacion_renovacion_cibertec.csv", [
      ["codigo_activo_case", "sede", "tipo_pc", "anios_uso", "estado_case", "score_renovacion", "prioridad_renovacion"],
      ...p.map((e) => [e.codigo_activo_case, e.nombre_sede, e.tipo_pc, e.anios_uso, e.estado_case, e.score_renovacion, e.prioridad_renovacion]),
    ]);
  });
}

// ===================================================================
// VISTA: USUARIOS (cuentas de acceso al sistema + personal de campo)
// ===================================================================
async function vistaUsuarios(vista) {
  const [cuentas, asistentes] = await Promise.all([apiGet("/usuarios"), apiGet("/asistentes")]);
  vista.innerHTML = `
    <div class="page-header"><h1>Usuarios</h1>
    <p>Cuentas de acceso a esta interfaz y personal de campo responsable de la verificación física trimestral (RF-01/RF-02, Sprint 1).</p></div>
    <div class="card">
      <h2>Cuentas de acceso al sistema</h2>
      <p class="texto-muted">El rol <strong>Administrador</strong> tiene acceso completo (Inventario con alta/edición/baja, Automatización RPA, Dashboard Inteligente y Configuración). El rol <strong>Limitado</strong> solo puede consultar el Dashboard Principal, ver el Inventario (sin modificarlo) y exportar Reportes — tanto la interfaz como la API bloquean el resto (ver <code>backend/app/auth.py::require_admin</code>).</p>
      <div class="tabla-wrap"><table>
        <thead><tr><th>#</th><th>Nombre completo</th><th>Usuario</th><th>Rol</th><th>Estado</th></tr></thead>
        <tbody>${cuentas.map((u, i) => `
          <tr>
            <td>${i + 1}</td>
            <td>${esc(u.nombre_completo)}</td>
            <td><code>${esc(u.usuario)}</code></td>
            <td><span class="badge ${u.rol === "Administrador" ? "operativo" : "media"}">${esc(u.rol)}</span></td>
            <td><span class="badge ${u.activo ? "operativo" : "inoperativo"}">${u.activo ? "Activo" : "Inactivo"}</span></td>
          </tr>`).join("")}</tbody>
      </table></div>
    </div>
    <div class="card">
      <h2>Personal de campo (asistentes)</h2>
      <p class="texto-muted">Ejecutan la verificación física trimestral en cada sede; no inician sesión en esta interfaz.</p>
      <div class="tabla-wrap"><table>
        <thead><tr><th>#</th><th>Nombre</th><th>Sede asignada</th></tr></thead>
        <tbody>${asistentes.map((a, i) => `<tr><td>${i + 1}</td><td>${esc(a.nombre)}</td><td>${esc(a.sede_asignada)}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>
  `;
}

// ===================================================================
// VISTA: BITÁCORA DE CAMBIOS (auditoría — quién hizo qué y cuándo)
// ===================================================================
const ETIQUETA_ACCION = {
  alta: "Alta", edicion: "Edición", baja: "Baja", atencion: "Atención", ejecucion: "Ejecución",
};
const BADGE_ACCION = {
  alta: "operativo", edicion: "media", baja: "inoperativo", atencion: "operativo", ejecucion: "media",
};
const ETIQUETA_ENTIDAD = {
  equipo: "Equipo", alerta: "Alerta", priorizacion: "Priorización de renovación", rpa: "Bot RPA",
};

async function vistaBitacora(vista) {
  const registros = await apiGet("/bitacora?limite=300");

  vista.innerHTML = `
    <div class="page-header">
      <h1>Bitácora de cambios</h1>
      <p>Quién realizó cada alta, edición o baja de un equipo, atendió una alerta, o ejecutó el bot RPA
         y el motor de priorización — con fecha, hora y cuenta responsable.</p>
    </div>
    <div class="barra-filtros">
      <select id="f-bitacora-entidad">
        <option value="">Todas las entidades</option>
        ${Object.entries(ETIQUETA_ENTIDAD).map(([v, t]) => `<option value="${v}">${t}</option>`).join("")}
      </select>
      <input type="search" id="f-bitacora-usuario" placeholder="Buscar por usuario…">
    </div>
    <div class="card">
      <div class="tabla-wrap">
        <table>
          <thead><tr><th>Fecha y hora</th><th>Usuario</th><th>Rol</th><th>Acción</th><th>Entidad</th><th>Referencia</th><th>Detalle</th></tr></thead>
          <tbody id="tbody-bitacora"></tbody>
        </table>
      </div>
    </div>
  `;

  function pintar() {
    const filtroEntidad = vista.querySelector("#f-bitacora-entidad").value;
    const filtroUsuario = vista.querySelector("#f-bitacora-usuario").value.trim().toLowerCase();
    const filtrados = registros.filter((r) => {
      if (filtroEntidad && r.entidad !== filtroEntidad) return false;
      if (filtroUsuario && !(r.usuario || "").toLowerCase().includes(filtroUsuario)
          && !(r.nombre_usuario || "").toLowerCase().includes(filtroUsuario)) return false;
      return true;
    });
    const tbody = vista.querySelector("#tbody-bitacora");
    tbody.innerHTML = filtrados.length
      ? filtrados.map((r) => `
        <tr>
          <td>${esc(r.fecha_hora)}</td>
          <td>${esc(r.nombre_usuario || r.usuario)}${r.nombre_usuario ? ` <span class="texto-muted">(${esc(r.usuario)})</span>` : ""}</td>
          <td>${r.rol ? `<span class="badge ${r.rol === "Administrador" ? "operativo" : "media"}">${esc(r.rol)}</span>` : "—"}</td>
          <td><span class="badge ${BADGE_ACCION[r.accion] || "media"}">${esc(ETIQUETA_ACCION[r.accion] || r.accion)}</span></td>
          <td>${esc(ETIQUETA_ENTIDAD[r.entidad] || r.entidad)}</td>
          <td>${esc(r.referencia || "—")}</td>
          <td>${esc(r.detalle || "—")}</td>
        </tr>`).join("")
      : '<tr><td colspan="7" class="vacio">Sin registros para el filtro aplicado.</td></tr>';
  }

  vista.querySelector("#f-bitacora-entidad").addEventListener("change", pintar);
  vista.querySelector("#f-bitacora-usuario").addEventListener("input", pintar);
  pintar();
}

// ===================================================================
// VISTA: CONFIGURACIÓN
// ===================================================================
async function vistaConfiguracion(vista) {
  const salud = await apiGet("/salud").catch(() => ({ estado: "sin conexión" }));
  vista.innerHTML = `
    <div class="page-header"><h1>Configuración</h1><p>Información del sistema y del entorno de ejecución del prototipo.</p></div>
    <div class="grid-2">
      <div class="card">
        <h2>Estado del sistema</h2>
        <table class="tabla-config">
          <tr><td>Servicio</td><td>${esc(salud.servicio || "—")}</td></tr>
          <tr><td>Estado de la API</td><td><span class="badge operativo">${esc(salud.estado)}</span></td></tr>
          <tr><td>Token de autenticación (RNF-03)</td><td><code>Bearer cibertec-demo-2026</code></td></tr>
          <tr><td>Motor de base de datos</td><td>SQLite (backend/data/inventario_cibertec.db)</td></tr>
          <tr><td>Framework backend</td><td>Flask 3</td></tr>
        </table>
      </div>
      <div class="card">
        <h2>Catálogo único de sedes</h2>
        <p class="texto-muted">Resuelve nombres alternativos detectados en el archivo institucional (Sprint 1, Restricciones).</p>
        <div>${["Arequipa", "Breña", "Callao", "Independencia", "Lima Centro", "San Juan de Lurigancho", "Trujillo"].map((s) => `<span class="chip">${s}</span>`).join("")}</div>
        <p class="texto-muted" style="margin-top:12px;">Alias conocidos: <strong>"Sede Norte"</strong> → Independencia · <strong>"Sede Bellavista"</strong> → Callao</p>
      </div>
    </div>
    <div class="card">
      <h2>Sesión</h2>
      <p class="texto-muted">Conectado como <strong>${esc(localStorage.getItem("cibertec_nombre") || "—")}</strong> (usuario <code>${esc(localStorage.getItem("cibertec_usuario") || "—")}</code>), rol <span class="badge operativo">${esc(localStorage.getItem("cibertec_rol") || "Administrador")}</span>.</p>
      <button class="btn btn-secundario" id="btn-cerrar-sesion-config">Cerrar sesión</button>
    </div>
  `;
  vista.querySelector("#btn-cerrar-sesion-config").addEventListener("click", cerrarSesion);
}

// ===================================================================
// VISTA: AYUDA
// ===================================================================
async function vistaAyuda(vista) {
  vista.innerHTML = `
    <div class="page-header"><h1>Ayuda</h1><p>Guía rápida del sistema para la sustentación.</p></div>
    <div class="card">
      <div class="ayuda-seccion">
        <h3>¿Qué hace cada sección?</h3>
        <p><strong>Dashboard Principal:</strong> indicadores generales del parque de equipos y alertas recientes.</p>
        <p><strong>Inventario:</strong> alta, edición, baja y búsqueda de equipos — CRUD real contra la base de datos.</p>
        <p><strong>Automatización RPA:</strong> ejecuta en vivo la conciliación trimestral (misma lógica que el bot de terminal <code>rpa_bot/bot_conciliacion.py</code>).</p>
        <p><strong>Dashboard Inteligente:</strong> motor analítico CRISP-DM que prioriza qué equipos renovar primero.</p>
        <p><strong>Reportes:</strong> exportación de datos en CSV.</p>
        <p><strong>Bitácora de cambios:</strong> quién realizó cada alta, edición o baja de un equipo, atendió una alerta, o ejecutó el bot RPA y el motor de priorización, con fecha, hora y cuenta responsable.</p>
      </div>
      <div class="ayuda-seccion">
        <h3>Cuentas y roles de acceso</h3>
        <p>Cada persona inicia sesión con su propia cuenta (ver sección «Usuarios»). El rol <strong>Administrador</strong> ve las 9 secciones; el rol <strong>Limitado</strong> solo ve Dashboard Principal, Inventario (solo lectura), Reportes y Ayuda — Automatización RPA, Dashboard Inteligente, Usuarios, Bitácora de cambios y Configuración quedan ocultas y también bloqueadas por la API si se intenta acceder directamente.</p>
      </div>
      <div class="ayuda-seccion">
        <h3>Demostración completa (opcional, desde terminal)</h3>
        <p>Para mostrar el bot y el motor analítico como procesos externos (equivalentes a un flujo real de UiPath / un notebook de análisis), use, con el servidor corriendo:</p>
        <p><code>python rpa_bot/generar_input_conteo.py</code> → <code>python rpa_bot/bot_conciliacion.py</code> → <code>python analitica/motor_priorizacion.py</code></p>
      </div>
      <div class="ayuda-seccion">
        <h3>Correspondencia con los Sprints de la investigación</h3>
        <p>Ver <code>README.md</code> del proyecto y los documentos en <code>docs/</code> para el detalle de cada Sprint (1 a 6) y su relación con este sistema.</p>
      </div>
    </div>
  `;
}

// ===================================================================
// TABLA DE RUTAS
// ===================================================================
const VISTAS = {
  dashboard: vistaDashboard,
  inventario: vistaInventario,
  rpa: vistaRPA,
  analitica: vistaAnalitica,
  reportes: vistaReportes,
  usuarios: vistaUsuarios,
  bitacora: vistaBitacora,
  configuracion: vistaConfiguracion,
  ayuda: vistaAyuda,
};

function cerrarSesion() {
  localStorage.removeItem("cibertec_auth");
  localStorage.removeItem("cibertec_usuario");
  localStorage.removeItem("cibertec_nombre");
  localStorage.removeItem("cibertec_rol");
  window.location.href = "login.html";
}

// ===================================================================
// ARRANQUE
// ===================================================================
function initApp() {
  if (localStorage.getItem("cibertec_auth") !== "ok") {
    window.location.href = "login.html";
    return;
  }
  const nombre = localStorage.getItem("cibertec_nombre") || localStorage.getItem("cibertec_usuario") || "Usuario CIBERTEC";
  const rol = localStorage.getItem("cibertec_rol") || "Administrador";
  const topbarNombre = document.getElementById("topbar-nombre");
  if (topbarNombre) topbarNombre.textContent = nombre;
  const topbarRol = document.getElementById("topbar-rol");
  if (topbarRol) {
    topbarRol.textContent = rol;
    topbarRol.className = `badge ${rol === "Administrador" ? "operativo" : "media"}`;
  }
  const iniciales = nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("") || "CI";
  const avatar = document.querySelector(".avatar");
  if (avatar) avatar.textContent = iniciales;

  // Una cuenta "Limitado" no ve en el menú las secciones administrativas
  // (además del bloqueo de navegación directa por hash en router() y
  // del rechazo 403 del backend si de todos modos se llama a la API).
  if (esRolLimitado()) {
    document.querySelectorAll("[data-solo-admin]").forEach((el) => { el.style.display = "none"; });
  }

  document.getElementById("btn-logout").addEventListener("click", cerrarSesion);
  window.addEventListener("hashchange", router);
  router();
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.classList.contains("pagina-login")) {
    initLogin();
  } else if (document.getElementById("vista")) {
    initApp();
  }
});
