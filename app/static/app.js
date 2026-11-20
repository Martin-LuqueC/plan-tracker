// Plan Tracker: dibuja el tablero con los datos de /api/datos.
// Fase 3: solo lectura. Se refresca sola cada 15 segundos y con el botón Actualizar.

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
    campos: ["Meta", "Detalle", "Notas", "Fecha", "Hora", "Duración"],
    sin_dato: "Sin dato",
    min: "min",
    cerrar: "Cerrar",
    error: "No se pudo actualizar: {e} Reintento en unos segundos.",
    estados: { pendiente: "pendiente", en_curso: "en curso", hecho: "hecho" },
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
    campos: ["Goal", "Details", "Notes", "Date", "Time", "Duration"],
    sin_dato: "No data",
    min: "min",
    cerrar: "Close",
    error: "Could not refresh: {e} Retrying in a few seconds.",
    estados: { pendiente: "pending", en_curso: "in progress", hecho: "done" },
  },
};

let datos = null;
let tareaAbierta = null;
let idioma = leer("idioma") === "en" ? "en" : "es";
let pidiendo = false;

const $ = (id) => document.getElementById(id);
const t = (clave) => TEXTOS[idioma][clave];

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

function textosFijos() {
  document.documentElement.lang = idioma;
  $("actualizar-texto").textContent = t("actualizar");
  $("panel-cerrar").setAttribute("aria-label", t("cerrar"));
  for (const b of document.querySelectorAll(".idiomas button")) {
    b.setAttribute("aria-pressed", String(b.dataset.idioma === idioma));
  }
  if (!datos) $("cuadrantes").replaceChildren(crear("p", "semana-nota", t("cargando")));
}

let enEspera = null; // si piden actualizar mientras otra consulta está en curso

async function cargar(forzar = false) {
  if (pidiendo) {
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
    if (json.idioma !== idioma) { enEspera = enEspera || { forzar: false }; return; } // cambió el idioma a medio camino
    datos = json;
    $("aviso").hidden = true;
    dibujar();
    $("actualizado").textContent = new Date().toLocaleTimeString(idioma, { hour: "2-digit", minute: "2-digit" });
  } catch (e) {
    $("aviso").textContent = t("error").replace("{e}", e.message);
    $("aviso").hidden = false;
  } finally {
    pidiendo = false;
    $("actualizar").classList.remove("girando");
    if (enEspera) {
      const siguiente = enEspera;
      enEspera = null;
      cargar(siguiente.forzar);
    }
  }
}

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

  const casilla = crear("span", "casilla");
  if (tarea.completa) casilla.classList.add("hecha");
  else if (tarea.estado === "en_curso") casilla.classList.add("en-curso");
  casilla.title = tarea.recurrente
    ? t("cumplidas").replace("{a}", tarea.cumplidas).replace("{b}", tarea.meta_semanal)
    : t("estados")[tarea.estado] || tarea.estado;
  li.append(casilla);

  const titulo = crear("button", "titulo", tarea.titulo);
  titulo.type = "button";
  titulo.title = tarea.titulo;
  titulo.addEventListener("click", () => abrirPanel(tarea.id));
  li.append(titulo);

  const dias = crear("span", "dias");
  for (const d of tarea.dias) {
    const caja = crear("span", "dia", d.letra);
    if (!d.toca) caja.classList.add("no-toca");
    if (d.marcado) caja.classList.add("marcado");
    if (datos.hoy === d.fecha) caja.classList.add("hoy");
    caja.title = d.nombre;
    dias.append(caja);
  }
  li.append(dias);

  li.append(crear("span", "frecuencia", tarea.frecuencia));
  return li;
}

function dibujar() {
  dibujarBarra();
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
  if (tareaAbierta) abrirPanel(tareaAbierta); // mantiene el panel al día tras refrescar
}

function buscarTarea(id) {
  for (const s of datos.semanas) for (const tarea of s.tareas) if (tarea.id === id) return [tarea, s];
  return [null, null];
}

function abrirPanel(id) {
  const [tarea, s] = buscarTarea(id);
  if (!tarea) { cerrarPanel(); return; }
  tareaAbierta = id;
  $("panel-titulo").textContent = tarea.titulo;
  const sub = [`${t("semana")} ${s.numero}`, tarea.frecuencia];
  if (tarea.recurrente) sub.push(t("cumplidas").replace("{a}", tarea.cumplidas).replace("{b}", tarea.meta_semanal));
  $("panel-sub").textContent = sub.join(", ");

  const valores = [
    tarea.meta,
    tarea.detalle,
    tarea.notas,
    tarea.fecha_texto,
    tarea.hora,
    tarea.duracion_min ? `${tarea.duracion_min} ${t("min")}` : "",
  ];
  const dl = $("panel-datos");
  dl.replaceChildren();
  t("campos").forEach((nombre, i) => {
    dl.append(crear("dt", "", nombre));
    dl.append(crear("dd", valores[i] ? "" : "vacio", valores[i] || t("sin_dato")));
  });
  if ($("fondo-panel").hidden) {
    $("fondo-panel").hidden = false;
    $("panel-cerrar").focus();
  }
}

function cerrarPanel() {
  tareaAbierta = null;
  $("fondo-panel").hidden = true;
}

$("panel-cerrar").addEventListener("click", cerrarPanel);
$("fondo-panel").addEventListener("click", (e) => { if (e.target === $("fondo-panel")) cerrarPanel(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarPanel(); });
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
