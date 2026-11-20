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
    sin_tareas_plan: "Sin tareas. Pídele a Claude que las agregue.",
    nuevo_plan: "Nuevo plan",
    nuevo_plan_sub: "Se guarda en tu hoja. Después pídele a Claude que agregue las tareas.",
    plan_campos: { nombre: "Nombre", nombre_en: "Nombre en inglés (opcional)", inicio: "Inicio", semanas: "Semanas" },
    semanas_n: (n) => (n === 1 ? "1 semana" : `${n} semanas`),
    termina: "Termina el {f}.",
    crear: "Crear plan",
    creando: "Creando...",
    error_crear: "No se creó: {e}",
    archivados: "Archivados",
    nueva_tarea: "Nueva tarea",
    agregar_tarea: "Agregar tarea",
    tarea_campos: { titulo: "Título", frecuencia: "Frecuencia", veces: "Cuántas veces en la semana", dia: "Qué día", meta: "Meta (opcional)", detalle: "Detalle (opcional)" },
    frecuencias: { una_vez: "1 vez", diaria: "Diaria", dias_habiles: "L a V", semanal: "Semanal", veces: "Veces" },
    dias_largos: ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
    agregando: "Agregando...",
    error_tarea: "No se agregó: {e}",
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
    sin_tareas_plan: "No tasks yet. Ask Claude to add them.",
    nuevo_plan: "New plan",
    nuevo_plan_sub: "It is saved to your sheet. Then ask Claude to add the tasks.",
    plan_campos: { nombre: "Name", nombre_en: "English name (optional)", inicio: "Start", semanas: "Weeks" },
    semanas_n: (n) => (n === 1 ? "1 week" : `${n} weeks`),
    termina: "Ends on {f}.",
    crear: "Create plan",
    creando: "Creating...",
    error_crear: "Not created: {e}",
    archivados: "Archived",
    nueva_tarea: "New task",
    agregar_tarea: "Add task",
    tarea_campos: { titulo: "Title", frecuencia: "Frequency", veces: "How many times this week", dia: "Which day", meta: "Goal (optional)", detalle: "Details (optional)" },
    frecuencias: { una_vez: "Once", diaria: "Daily", dias_habiles: "Mon to Fri", semanal: "Weekly", veces: "Times" },
    dias_largos: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    agregando: "Adding...",
    error_tarea: "Not added: {e}",
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
  textosPlan();
  textosTarea();
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
    // Tarea recién creada: se abre su panel para ponerle fecha y hora
    if (abrirTrasCargar && buscarTarea(abrirTrasCargar)[0]) {
      const id = abrirTrasCargar;
      abrirTrasCargar = null;
      if (!tareaAbierta) abrirPanel(id);
    }
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
    const opcion = (p) => {
      const op = crear("option", "", p.nombre);
      op.value = p.id;
      op.selected = p.id === datos.plan.id;
      return op;
    };
    for (const p of datos.planes.filter((p) => p.activo)) sel.append(opcion(p));
    const archivados = datos.planes.filter((p) => !p.activo);
    if (archivados.length) {
      const grupo = crear("optgroup");
      grupo.label = t("archivados");
      for (const p of archivados) grupo.append(opcion(p));
      sel.append(grupo);
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
  // 1 a 4 semanas: 2 x 2. Más semanas: se agregan columnas (hasta 4) y luego filas.
  const n = Math.max(datos.semanas.length, 1);
  const columnas = n <= 4 ? 2 : Math.min(4, Math.ceil(n / 2));
  cont.style.setProperty("--columnas", columnas);
  cont.style.setProperty("--filas", Math.max(Math.ceil(n / columnas), n <= 4 ? 2 : 1));
  const planSinTareas = datos.semanas.every((s) => !s.tareas.length);
  for (const s of datos.semanas) {
    const caja = crear("section", "semana" + (s.actual ? " actual" : ""));
    const cabeza = crear("div", "semana-cabeza");
    cabeza.append(crear("h2", "", `${t("semana")} ${s.numero}`), crear("span", "semana-rango", s.rango));
    if (s.actual) {
      const clave = { por_empezar: "proxima", terminado: "ultima" }[datos.estado_plan] || "esta";
      cabeza.append(crear("span", "etiqueta", t(clave)));
    }
    const mas = crear("button", "boton-mas", "+");
    mas.type = "button";
    mas.title = `${t("agregar_tarea")}: ${t("semana")} ${s.numero}`;
    mas.setAttribute("aria-label", mas.title);
    mas.addEventListener("click", () => abrirNuevaTarea(s.numero));
    cabeza.append(mas);
    caja.append(cabeza);
    if (s.enfoque) caja.append(crear("p", "semana-enfoque", s.enfoque));
    if (s.nota) caja.append(crear("p", "semana-nota", s.nota));

    const lista = crear("ul", "tareas");
    for (const tarea of s.tareas) lista.append(dibujarTarea(tarea));
    if (!s.tareas.length) lista.append(crear("li", "semana-nota", t(planSinTareas ? "sin_tareas_plan" : "sin_tareas")));
    caja.append(lista);
    cont.append(caja);
  }
  if (foco) {
    const igual = [...cont.querySelectorAll("[aria-label]")].find((el) => el.getAttribute("aria-label") === foco);
    if (igual) igual.focus();
  }
  // Si el panel está abierto y no hay cambios sin guardar, se pone al día con la hoja
  if (tareaAbierta && !haySinGuardar()) llenarPanel(tareaAbierta);
  ajustarTamano();
}

// Compacta la pantalla solo si algún cuadrante no cabe, en dos niveles
function ajustarTamano() {
  const cuerpo = document.body;
  const desborda = () => [...document.querySelectorAll(".tareas")].some((u) => u.scrollHeight - u.clientHeight > 1);
  cuerpo.classList.remove("apretado-1", "apretado-2");
  if (innerWidth <= 760 || !desborda()) return;   // en ventana angosta la página ya hace scroll
  cuerpo.classList.add("apretado-1");
  if (desborda()) cuerpo.classList.add("apretado-2");
}

let esperaTamano = null;
function programarAjuste() {
  clearTimeout(esperaTamano);
  esperaTamano = setTimeout(ajustarTamano, 120);
}
window.addEventListener("resize", programarAjuste);
// Además vigila el tamaño real de la página (cubre casos en que no llega el evento resize)
if ("ResizeObserver" in window) new ResizeObserver(programarAjuste).observe(document.documentElement);

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

// ---------- Plan nuevo ----------

function fechaIso(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function proximoLunes() {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  const faltan = (8 - d.getDay()) % 7 || 7; // getDay: 0 domingo, 1 lunes
  d.setDate(d.getDate() + faltan);
  return fechaIso(d);
}

function mostrarFinPlan() {
  const inicio = $("p-inicio").value;
  const semanas = Number($("p-semanas").value);
  if (!inicio || !semanas) { $("p-fin").textContent = ""; return; }
  const fin = new Date(inicio + "T12:00:00");
  fin.setDate(fin.getDate() + 7 * semanas - 1);
  const texto = fin.toLocaleDateString(idioma, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  $("p-fin").textContent = t("termina").replace("{f}", texto);
}

function textosPlan() {
  const c = t("plan_campos");
  $("plan-titulo").textContent = t("nuevo_plan");
  $("plan-sub").textContent = t("nuevo_plan_sub");
  $("l-plan-nombre").textContent = c.nombre;
  $("l-plan-nombre-en").textContent = c.nombre_en;
  $("l-plan-inicio").textContent = c.inicio;
  $("l-plan-semanas").textContent = c.semanas;
  $("p-crear").textContent = t("crear");
  $("nuevo-plan").title = t("nuevo_plan");
  $("nuevo-plan").setAttribute("aria-label", t("nuevo_plan"));
  $("plan-cerrar").setAttribute("aria-label", t("cerrar"));
  const sel = $("p-semanas");
  const elegido = sel.value || "4";
  sel.replaceChildren();
  for (let i = 1; i <= 8; i++) {
    const op = crear("option", "", t("semanas_n")(i));
    op.value = String(i);
    sel.append(op);
  }
  sel.value = elegido;
  mostrarFinPlan();
}

function abrirNuevoPlan() {
  $("plan-form").reset();
  $("p-semanas").value = "4";
  $("p-inicio").value = proximoLunes();
  $("plan-mensaje").textContent = "";
  $("plan-mensaje").classList.remove("error");
  $("p-crear").disabled = false;
  mostrarFinPlan();
  $("fondo-plan").hidden = false;
  $("p-nombre").focus();
}

function cerrarNuevoPlan() {
  $("fondo-plan").hidden = true;
}

async function crearPlan(e) {
  e.preventDefault();
  const mensaje = $("plan-mensaje");
  mensaje.classList.remove("error");
  mensaje.textContent = t("creando");
  $("p-crear").disabled = true;
  try {
    const r = await enviar("/api/plan", {
      nombre: $("p-nombre").value.trim(),
      nombre_en: $("p-nombre-en").value.trim(),
      inicio: $("p-inicio").value,
      semanas: Number($("p-semanas").value),
    });
    guardar("plan", r.plan_id);   // la pantalla pasa al plan nuevo
    cerrarNuevoPlan();
    cargar(true);
  } catch (err) {
    mensaje.classList.add("error");
    mensaje.textContent = t("error_crear").replace("{e}", err.message);
    $("p-crear").disabled = false;
  }
}

// ---------- Tarea nueva ----------

let semanaNuevaTarea = null;
let abrirTrasCargar = null;   // id de una tarea recién creada, para abrir su panel

function frecuenciaElegida() {
  const b = $("t-frecuencia").querySelector('[aria-pressed="true"]');
  return b ? b.dataset.valor : "una_vez";
}

function elegirFrecuencia(valor) {
  for (const b of $("t-frecuencia").querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.valor === valor));
  $("c-t-veces").hidden = valor !== "veces";
  $("c-t-dia").hidden = valor !== "semanal";
}

function textosTarea() {
  const c = t("tarea_campos");
  $("tarea-titulo").textContent = t("nueva_tarea");
  $("l-t-titulo").textContent = c.titulo;
  $("l-t-frecuencia").textContent = c.frecuencia;
  $("t-frecuencia").setAttribute("aria-label", c.frecuencia);
  $("l-t-veces").textContent = c.veces;
  $("l-t-dia").textContent = c.dia;
  $("l-t-meta").textContent = c.meta;
  $("l-t-detalle").textContent = c.detalle;
  $("t-crear").textContent = t("agregar_tarea");
  $("tarea-cerrar").setAttribute("aria-label", t("cerrar"));
  for (const b of $("t-frecuencia").querySelectorAll("button")) b.textContent = t("frecuencias")[b.dataset.valor];
  const sel = $("t-dia");
  const elegido = sel.value || "0";
  sel.replaceChildren();
  t("dias_largos").forEach((nombre, i) => {
    const op = crear("option", "", nombre);
    op.value = String(i);
    sel.append(op);
  });
  sel.value = elegido;
}

function abrirNuevaTarea(numero) {
  semanaNuevaTarea = numero;
  $("tarea-form").reset();
  $("t-veces").value = "5";
  $("t-dia").value = "0";
  elegirFrecuencia("una_vez");
  $("tarea-sub").textContent = `${t("semana")} ${numero}, ${datos.plan.nombre}`;
  $("tarea-mensaje").textContent = "";
  $("tarea-mensaje").classList.remove("error");
  $("t-crear").disabled = false;
  $("fondo-tarea").hidden = false;
  $("t-titulo").focus();
}

function cerrarNuevaTarea() {
  $("fondo-tarea").hidden = true;
}

async function crearTarea(e) {
  e.preventDefault();
  const mensaje = $("tarea-mensaje");
  mensaje.classList.remove("error");
  mensaje.textContent = t("agregando");
  $("t-crear").disabled = true;
  const frecuencia = frecuenciaElegida();
  try {
    const r = await enviar("/api/tarea", {
      plan_id: datos.plan.id,
      semana: semanaNuevaTarea,
      titulo: $("t-titulo").value.trim(),
      frecuencia,
      veces: frecuencia === "veces" ? Number($("t-veces").value) : null,
      dia: frecuencia === "semanal" ? Number($("t-dia").value) : null,
      meta: $("t-meta").value.trim(),
      detalle: $("t-detalle").value.trim(),
    });
    cerrarNuevaTarea();
    abrirTrasCargar = r.tarea_id;   // al llegar los datos se abre su panel
  } catch (err) {
    mensaje.classList.add("error");
    mensaje.textContent = t("error_tarea").replace("{e}", err.message);
    $("t-crear").disabled = false;
  }
}

// ---------- Eventos ----------

$("panel-cerrar").addEventListener("click", () => cerrarPanel());
$("fondo-panel").addEventListener("click", (e) => { if (e.target === $("fondo-panel")) cerrarPanel(); });
$("tarea-cerrar").addEventListener("click", cerrarNuevaTarea);
$("fondo-tarea").addEventListener("click", (e) => { if (e.target === $("fondo-tarea")) cerrarNuevaTarea(); });
$("tarea-form").addEventListener("submit", crearTarea);
$("t-frecuencia").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (b) elegirFrecuencia(b.dataset.valor);
});
$("nuevo-plan").addEventListener("click", abrirNuevoPlan);
$("plan-cerrar").addEventListener("click", cerrarNuevoPlan);
$("fondo-plan").addEventListener("click", (e) => { if (e.target === $("fondo-plan")) cerrarNuevoPlan(); });
$("plan-form").addEventListener("submit", crearPlan);
$("p-inicio").addEventListener("input", mostrarFinPlan);
$("p-semanas").addEventListener("change", mostrarFinPlan);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("fondo-tarea").hidden) cerrarNuevaTarea();
  if (e.key === "Escape" && !$("fondo-plan").hidden) cerrarNuevoPlan();
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
