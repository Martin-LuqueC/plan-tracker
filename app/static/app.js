// Plan Tracker: dibuja el tablero con los datos de /api/datos y guarda los cambios en la hoja.
// Se refresca sola cada 15 segundos y con el botón Actualizar.

const REFRESCO_MS = 15000;

const TEXTOS = {
  es: {
    cargando: "Cargando tu plan...",
    avance: "Avance de la semana",
    actualizar: "Actualizar",
    semana: "Semana",
    proxima: "Próxima",
    esta: "Esta semana",
    ultima: "Última",
    sin_tareas: "Sin tareas.",
    cumplidas: "{a} de {b} cumplidas",
    por_dias: "Se completa marcando los días ({a} de {b})",
    marcar: "Marcar como hecha",
    desmarcar: "Volver a pendiente",
    meta: "Meta",
    campos: { estado: "Estado", detalle: "Detalle", notas: "Notas", fecha: "Fecha", hora: "Hora", duracion: "Duración (min)" },
    estados: { pendiente: "Pendiente", en_curso: "En curso", hecho: "Hecho" },
    guardar: "Guardar",
    guardando: "Guardando...",
    guardado: "Guardado en la hoja",
    sin_cambios: "",
    descartar: "Tienes cambios sin guardar. ¿Cerrar sin guardar?",
    cerrar: "Cerrar",
    error: "No se pudo actualizar: {e} Reintento en unos segundos.",
    sin_servidor: "Plan Tracker está cerrado. Abre \"Abrir Plan Tracker\" de nuevo y esta ventana se pondrá al día sola.",
    error_guardar: "No se guardó: {e}",
    agendar: "Agendar en Calendar",
    reagendar: "Actualizar en Calendar",
    agendando: "Agendando...",
    agendado: "Listo en Calendar.",
    ver_evento: "Ver en Calendar",
    error_agendar: "No se agendó: {e}",
  },
  en: {
    cargando: "Loading your plan...",
    avance: "Week progress",
    actualizar: "Refresh",
    semana: "Week",
    proxima: "Next",
    esta: "This week",
    ultima: "Last",
    sin_tareas: "No tasks.",
    cumplidas: "{a} of {b} done",
    por_dias: "Completed by checking off days ({a} of {b})",
    marcar: "Mark as done",
    desmarcar: "Back to pending",
    meta: "Goal",
    campos: { estado: "Status", detalle: "Details", notas: "Notes", fecha: "Date", hora: "Time", duracion: "Duration (min)" },
    estados: { pendiente: "Pending", en_curso: "In progress", hecho: "Done" },
    guardar: "Save",
    guardando: "Saving...",
    guardado: "Saved to the sheet",
    sin_cambios: "",
    descartar: "You have unsaved changes. Close without saving?",
    cerrar: "Close",
    error: "Could not refresh: {e} Retrying in a few seconds.",
    sin_servidor: "Plan Tracker is closed. Run \"Abrir Plan Tracker\" again and this window will catch up on its own.",
    error_guardar: "Not saved: {e}",
    agendar: "Add to Calendar",
    reagendar: "Update in Calendar",
    agendando: "Scheduling...",
    agendado: "Done in Calendar.",
    ver_evento: "Open in Calendar",
    error_agendar: "Not scheduled: {e}",
  },
};

let datos = null;
let tareaAbierta = null;
let original = null;        // valores del panel al abrirlo, para saber si hay cambios
let idioma = leer("idioma") === "en" ? "en" : "es";
let pidiendo = false;
let enEspera = null;        // si piden actualizar mientras otra consulta está en curso
let escrituras = 0;         // cambios enviados a la hoja que aún no terminan

const $ = (id) => document.getElementById(id);
const t = (clave) => TEXTOS[idioma][clave];
const conNumeros = (texto, a, b) => texto.replace("{a}", a).replace("{b}", b);

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

// Preferencias guardadas en este navegador (si no se puede, no pasa nada)
function leer(clave) {
  try { return localStorage.getItem(clave) || ""; } catch { return ""; }
}
function guardar(clave, valor) {
  try { localStorage.setItem(clave, valor); } catch { /* sin almacenamiento */ }
}

function avisar(texto) {
  $("aviso").textContent = texto;
  $("aviso").hidden = !texto;
}

// ---------- Textos fijos ----------

function textosFijos() {
  document.documentElement.lang = idioma;
  $("actualizar-texto").textContent = t("actualizar");
  $("panel-cerrar").setAttribute("aria-label", t("cerrar"));
  for (const b of document.querySelectorAll(".idiomas button")) {
    b.setAttribute("aria-pressed", String(b.dataset.idioma === idioma));
  }
  const campos = t("campos");
  $("l-estado").textContent = campos.estado;
  $("l-detalle").textContent = campos.detalle;
  $("l-notas").textContent = campos.notas;
  $("l-fecha").textContent = campos.fecha;
  $("l-hora").textContent = campos.hora;
  $("l-duracion").textContent = campos.duracion;
  $("f-estado").setAttribute("aria-label", campos.estado);
  for (const b of $("f-estado").querySelectorAll("button")) b.textContent = t("estados")[b.dataset.valor];
  $("f-guardar").textContent = t("guardar");
  etiquetaAgendar(tareaAbierta && datos ? buscarTarea(tareaAbierta)[0] : null);
  if (!datos) $("cuadrantes").replaceChildren(crear("p", "semana-nota", t("cargando")));
}

// ---------- Lectura ----------

async function cargar(forzar = false) {
  if (pidiendo || escrituras > 0) {
    enEspera = { forzar: forzar || (enEspera && enEspera.forzar) };
    return;
  }
  pidiendo = true;
  $("actualizar").classList.add("girando");
  const params = new URLSearchParams({ idioma });
  const plan = leer("plan");
  if (plan) params.set("plan", plan);
  if (forzar) params.set("forzar", "1");
  try {
    const r = await fetch("/api/datos?" + params);
    const json = await r.json();
    if (json.error) throw new Error(json.error);
    // Si cambió el idioma o hay un cambio guardándose, estos datos ya no sirven
    if (json.idioma !== idioma || escrituras > 0) { enEspera = enEspera || { forzar: true }; return; }
    datos = json;
    avisar("");
    dibujar();
    // Enlace directo a una tarea: http://localhost:5050/#tarea=ID abre su panel
    const enlace = location.hash.match(/^#tarea=(.+)$/);
    if (enlace && !tareaAbierta) {
      history.replaceState(null, "", location.pathname);
      abrirPanel(decodeURIComponent(enlace[1]));
    }
    $("actualizado").textContent = new Date().toLocaleTimeString(idioma, { hour: "2-digit", minute: "2-digit" });
  } catch (e) {
    // TypeError = no hubo respuesta: el servidor está apagado
    avisar(e instanceof TypeError ? t("sin_servidor") : t("error").replace("{e}", e.message));
  } finally {
    pidiendo = false;
    $("actualizar").classList.remove("girando");
    if (enEspera && escrituras === 0) {
      const siguiente = enEspera;
      enEspera = null;
      cargar(siguiente.forzar);
    }
  }
}

// ---------- Escritura ----------

async function enviar(url, cuerpo) {
  escrituras++;
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
    const json = await r.json().catch(() => ({}));
    if (!r.ok || json.error) throw new Error(json.error || `HTTP ${r.status}`);
    return json;
  } finally {
    escrituras--;
    if (escrituras === 0) { enEspera = null; cargar(true); } // trae la hoja ya actualizada
  }
}

function recalcular(tarea) {
  if (tarea.recurrente) {
    const marcados = tarea.dias.filter((d) => d.marcado).length;
    tarea.cumplidas = tarea.estado === "hecho" ? tarea.meta_semanal : Math.min(marcados, tarea.meta_semanal);
  } else {
    tarea.cumplidas = tarea.estado === "hecho" ? 1 : 0;
  }
  tarea.completa = tarea.cumplidas >= tarea.meta_semanal;
}

async function cambiarEstado(tarea) {
  const nuevo = tarea.estado === "hecho" ? "pendiente" : "hecho";
  const antes = tarea.estado;
  tarea.estado = nuevo;               // se ve al instante
  recalcular(tarea);
  dibujar();
  try {
    await enviar(`/api/tarea/${encodeURIComponent(tarea.id)}`, { cambios: { estado: nuevo } });
  } catch (e) {
    tarea.estado = antes;
    recalcular(tarea);
    dibujar();
    avisar(t("error_guardar").replace("{e}", e.message));
  }
}

async function cambiarDia(tarea, dia) {
  dia.marcado = !dia.marcado;          // se ve al instante
  recalcular(tarea);
  dibujar();
  try {
    await enviar("/api/marca", { tarea_id: tarea.id, fecha: dia.fecha, marcado: dia.marcado });
  } catch (e) {
    dia.marcado = !dia.marcado;
    recalcular(tarea);
    dibujar();
    avisar(t("error_guardar").replace("{e}", e.message));
  }
}

// ---------- Dibujo ----------

function dibujarBarra() {
  const caja = $("plan");
  caja.replaceChildren();
  if (datos.planes.length > 1) {
    const sel = crear("select");
    sel.setAttribute("aria-label", "Plan");
    for (const p of datos.planes) {
      const op = crear("option", "", p.nombre);
      op.value = p.id;
      op.selected = p.id === datos.plan.id;
      sel.append(op);
    }
    sel.addEventListener("change", () => { guardar("plan", sel.value); cargar(); });
    caja.append(sel);
  } else {
    caja.textContent = datos.plan.nombre;
  }
  $("dia").textContent = datos.texto_dia;
  $("avance-texto").textContent = `${t("avance")} ${datos.avance_semana}%`;
  $("avance-relleno").style.width = datos.avance_semana + "%";
}

function dibujarTarea(tarea) {
  const li = crear("li", "tarea" + (tarea.completa ? " completa" : ""));

  // Casilla: se marca a mano en las tareas de una vez; en las recurrentes se llena con los días
  const casilla = crear(tarea.recurrente ? "span" : "button", "casilla");
  if (tarea.completa) casilla.classList.add("hecha");
  else if (tarea.estado === "en_curso") casilla.classList.add("en-curso");
  if (tarea.recurrente) {
    casilla.title = conNumeros(t("por_dias"), tarea.cumplidas, tarea.meta_semanal);
  } else {
    casilla.type = "button";
    casilla.title = tarea.estado === "hecho" ? t("desmarcar") : t("marcar");
    casilla.setAttribute("aria-label", `${casilla.title}: ${tarea.titulo}`);
    casilla.setAttribute("aria-pressed", String(tarea.estado === "hecho"));
    casilla.addEventListener("click", () => cambiarEstado(tarea));
  }
  li.append(casilla);

  const titulo = crear("button", "titulo", tarea.titulo);
  titulo.type = "button";
  titulo.title = tarea.titulo;
  titulo.addEventListener("click", () => abrirPanel(tarea.id));
  li.append(titulo);

  const dias = crear("span", "dias");
  for (const d of tarea.dias) {
    const boton = crear("button", "dia", d.letra);
    boton.type = "button";
    if (!d.toca) boton.classList.add("no-toca");
    if (d.marcado) boton.classList.add("marcado");
    if (datos.hoy === d.fecha) boton.classList.add("hoy");
    boton.title = d.nombre;
    boton.setAttribute("aria-label", `${d.nombre}: ${tarea.titulo}`);
    boton.setAttribute("aria-pressed", String(d.marcado));
    boton.addEventListener("click", () => cambiarDia(tarea, d));
    dias.append(boton);
  }
  li.append(dias);

  li.append(crear("span", "frecuencia", tarea.frecuencia));
  return li;
}

function dibujar() {
  if (!datos) return;
  dibujarBarra();
  // Conserva el foco del teclado al redibujar
  const foco = document.activeElement && document.activeElement.closest(".cuadrantes")
    ? document.activeElement.getAttribute("aria-label") : null;

  const cont = $("cuadrantes");
  cont.replaceChildren();
  for (const s of datos.semanas) {
    const caja = crear("section", "semana" + (s.actual ? " actual" : ""));
    const cabeza = crear("div", "semana-cabeza");
    cabeza.append(crear("h2", "", `${t("semana")} ${s.numero}`), crear("span", "semana-rango", s.rango));
    if (s.actual) {
      const clave = { por_empezar: "proxima", terminado: "ultima" }[datos.estado_plan] || "esta";
      cabeza.append(crear("span", "etiqueta", t(clave)));
    }
    caja.append(cabeza);
    if (s.enfoque) caja.append(crear("p", "semana-enfoque", s.enfoque));
    if (s.nota) caja.append(crear("p", "semana-nota", s.nota));

    const lista = crear("ul", "tareas");
    for (const tarea of s.tareas) lista.append(dibujarTarea(tarea));
    if (!s.tareas.length) lista.append(crear("li", "semana-nota", t("sin_tareas")));
    caja.append(lista);
    cont.append(caja);
  }
  if (foco) {
    const igual = [...cont.querySelectorAll("[aria-label]")].find((el) => el.getAttribute("aria-label") === foco);
    if (igual) igual.focus();
  }
  // Si el panel está abierto y no hay cambios sin guardar, se pone al día con la hoja
  if (tareaAbierta && !haySinGuardar()) llenarPanel(tareaAbierta);
}

// ---------- Panel de detalle ----------

function buscarTarea(id) {
  for (const s of datos.semanas) for (const tarea of s.tareas) if (tarea.id === id) return [tarea, s];
  return [null, null];
}

function estadoElegido() {
  const b = $("f-estado").querySelector('[aria-pressed="true"]');
  return b ? b.dataset.valor : "pendiente";
}

function elegirEstado(valor) {
  for (const b of $("f-estado").querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.valor === valor));
}

function valoresPanel() {
  return {
    estado: estadoElegido(),
    detalle: $("f-detalle").value.trim(),
    notas: $("f-notas").value.trim(),
    fecha: $("f-fecha").value,
    hora: $("f-hora").value,
    duracion_min: $("f-duracion").value.trim(),
  };
}

function haySinGuardar() {
  if (!original) return false;
  const ahora = valoresPanel();
  return Object.keys(ahora).some((c) => ahora[c] !== original[c]);
}

function actualizarBotonGuardar() {
  $("f-guardar").disabled = !haySinGuardar();
}

function llenarPanel(id) {
  const [tarea, s] = buscarTarea(id);
  if (!tarea) { cerrarPanel(true); return false; }
  $("panel-titulo").textContent = tarea.titulo;
  const sub = [`${t("semana")} ${s.numero}`, tarea.frecuencia];
  if (tarea.recurrente) sub.push(conNumeros(t("cumplidas"), tarea.cumplidas, tarea.meta_semanal));
  $("panel-sub").textContent = sub.join(", ");
  $("panel-meta").textContent = tarea.meta ? `${t("meta")}: ${tarea.meta}` : "";

  elegirEstado(tarea.estado);
  $("f-detalle").value = tarea.detalle;
  $("f-notas").value = tarea.notas;
  $("f-fecha").value = tarea.fecha;
  $("f-hora").value = tarea.hora;
  $("f-duracion").value = tarea.duracion_min;
  etiquetaAgendar(tarea);
  original = valoresPanel();
  actualizarBotonGuardar();
  return true;
}

function abrirPanel(id) {
  tareaAbierta = id;
  mostrarMensaje("");
  if (!llenarPanel(id)) return;
  $("fondo-panel").hidden = false;
  $("f-notas").focus();
}

function cerrarPanel(forzar = false) {
  if (!forzar && haySinGuardar() && !confirm(t("descartar"))) return;
  tareaAbierta = null;
  original = null;
  $("fondo-panel").hidden = true;
}

function mostrarMensaje(texto, esError = false, enlace = "") {
  const mensaje = $("panel-mensaje");
  mensaje.classList.toggle("error", esError);
  mensaje.textContent = texto;
  if (enlace) {
    const a = crear("a", "", t("ver_evento"));
    a.href = enlace;
    a.target = "_blank";
    a.rel = "noopener";
    mensaje.append(" ", a);
  }
}

// Guarda lo que cambió en el panel. Devuelve true si quedó todo guardado.
async function guardarCambios() {
  if (!haySinGuardar()) return true;
  const [tarea] = buscarTarea(tareaAbierta);
  if (!tarea) return false;
  const ahora = valoresPanel();
  const cambios = {};
  for (const c of Object.keys(ahora)) if (ahora[c] !== original[c]) cambios[c] = ahora[c];

  mostrarMensaje(t("guardando"));
  $("f-guardar").disabled = true;
  try {
    await enviar(`/api/tarea/${encodeURIComponent(tarea.id)}`, { cambios });
    Object.assign(tarea, cambios);   // se ve al instante; la hoja ya está actualizada
    recalcular(tarea);
    original = ahora;
    mostrarMensaje(t("guardado"));
    dibujar();
    return true;
  } catch (err) {
    mostrarMensaje(t("error_guardar").replace("{e}", err.message), true);
    return false;
  } finally {
    actualizarBotonGuardar();
  }
}

async function guardarPanel(e) {
  e.preventDefault();
  await guardarCambios();
}

async function agendarPanel() {
  const boton = $("f-agendar");
  boton.disabled = true;
  try {
    if (!(await guardarCambios())) return;   // primero se guarda lo que escribiste
    const [tarea] = buscarTarea(tareaAbierta);
    if (!tarea) return;
    mostrarMensaje(t("agendando"));
    try {
      const r = await enviar(`/api/tarea/${encodeURIComponent(tarea.id)}/agendar`, {});
      tarea.evento_id = tarea.evento_id || "nuevo";
      etiquetaAgendar(tarea);
      mostrarMensaje(t("agendado"), false, r.enlace);
    } catch (err) {
      mostrarMensaje(t("error_agendar").replace("{e}", err.message), true);
    }
  } finally {
    boton.disabled = false;
  }
}

function etiquetaAgendar(tarea) {
  $("f-agendar-texto").textContent = tarea && tarea.evento_id ? t("reagendar") : t("agendar");
}

// ---------- Eventos ----------

$("panel-cerrar").addEventListener("click", () => cerrarPanel());
$("fondo-panel").addEventListener("click", (e) => { if (e.target === $("fondo-panel")) cerrarPanel(); });
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("fondo-panel").hidden) cerrarPanel();
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !$("fondo-panel").hidden) $("panel-form").requestSubmit();
});
$("panel-form").addEventListener("submit", guardarPanel);
$("f-agendar").addEventListener("click", agendarPanel);
$("panel-form").addEventListener("input", () => { $("panel-mensaje").textContent = ""; actualizarBotonGuardar(); });
$("f-estado").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  elegirEstado(b.dataset.valor);
  $("panel-mensaje").textContent = "";
  actualizarBotonGuardar();
});
$("actualizar").addEventListener("click", () => cargar(true));
for (const b of document.querySelectorAll(".idiomas button")) {
  b.addEventListener("click", () => {
    if (b.dataset.idioma === idioma) return;
    idioma = b.dataset.idioma;
    guardar("idioma", idioma);
    textosFijos();
    cargar();
  });
}
window.addEventListener("focus", () => cargar());

textosFijos();
cargar(true);
setInterval(cargar, REFRESCO_MS);
