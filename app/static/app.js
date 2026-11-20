// Plan Tracker: dibuja el tablero con los datos de /api/datos.
// Fase 3: solo lectura. Se refresca solo cada 45 segundos.

const REFRESCO_MS = 45000;
let datos = null;
let tareaAbierta = null;

const $ = (id) => document.getElementById(id);

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

function planGuardado() {
  try { return localStorage.getItem("plan") || ""; } catch { return ""; }
}
function guardarPlan(id) {
  try { localStorage.setItem("plan", id); } catch { /* sin almacenamiento, no pasa nada */ }
}

async function cargar(forzar = false) {
  const params = new URLSearchParams();
  const plan = planGuardado();
  if (plan) params.set("plan", plan);
  if (forzar) params.set("forzar", "1");
  try {
    const r = await fetch("/api/datos?" + params);
    const json = await r.json();
    if (json.error) throw new Error(json.error);
    datos = json;
    $("aviso").hidden = true;
    dibujar();
    const ahora = new Date();
    $("actualizado").textContent = ahora.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
  } catch (e) {
    $("aviso").textContent = "No se pudo actualizar: " + e.message + " Reintento en unos segundos.";
    $("aviso").hidden = false;
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
    sel.addEventListener("change", () => { guardarPlan(sel.value); cargar(); });
    caja.append(sel);
  } else {
    caja.textContent = datos.plan.nombre;
  }
  $("dia").textContent = datos.texto_dia;
  $("avance-texto").textContent = `Avance de la semana ${datos.avance_semana}%`;
  $("avance-relleno").style.width = datos.avance_semana + "%";
}

function dibujarTarea(t) {
  const li = crear("li", "tarea" + (t.completa ? " completa" : ""));

  const casilla = crear("span", "casilla");
  if (t.completa) casilla.classList.add("hecha");
  else if (t.estado === "en_curso") casilla.classList.add("en-curso");
  casilla.title = t.recurrente ? `${t.cumplidas} de ${t.meta_semanal}` : t.estado.replace("_", " ");
  li.append(casilla);

  const titulo = crear("button", "titulo", t.titulo);
  titulo.title = t.titulo;
  titulo.addEventListener("click", () => abrirPanel(t.id));
  li.append(titulo);

  const dias = crear("span", "dias");
  for (const d of t.dias) {
    const caja = crear("span", "dia", d.letra);
    if (!d.toca) caja.classList.add("no-toca");
    if (d.marcado) caja.classList.add("marcado");
    if (datos.hoy === d.fecha) caja.classList.add("hoy");
    caja.title = d.fecha;
    dias.append(caja);
  }
  li.append(dias);

  li.append(crear("span", "frecuencia", t.frecuencia));
  return li;
}

function dibujar() {
  dibujarBarra();
  const cont = $("cuadrantes");
  cont.replaceChildren();
  for (const s of datos.semanas) {
    const caja = crear("section", "semana" + (s.actual ? " actual" : ""));
    const cabeza = crear("div", "semana-cabeza");
    cabeza.append(crear("h2", "", `Semana ${s.numero}`), crear("span", "semana-rango", s.rango));
    if (s.actual) {
      const texto = datos.estado_plan === "por_empezar" ? "Próxima" : datos.estado_plan === "terminado" ? "Última" : "Esta semana";
      cabeza.append(crear("span", "etiqueta", texto));
    }
    caja.append(cabeza);
    if (s.enfoque) caja.append(crear("p", "semana-enfoque", s.enfoque));
    if (s.nota) caja.append(crear("p", "semana-nota", s.nota));

    const lista = crear("ul", "tareas");
    for (const t of s.tareas) lista.append(dibujarTarea(t));
    if (!s.tareas.length) lista.append(crear("li", "semana-nota", "Sin tareas."));
    caja.append(lista);
    cont.append(caja);
  }
  if (tareaAbierta) abrirPanel(tareaAbierta); // mantiene el panel al día tras refrescar
}

function buscarTarea(id) {
  for (const s of datos.semanas) for (const t of s.tareas) if (t.id === id) return [t, s];
  return [null, null];
}

function abrirPanel(id) {
  const [t, s] = buscarTarea(id);
  if (!t) { cerrarPanel(); return; }
  tareaAbierta = id;
  $("panel-titulo").textContent = t.titulo;
  const sub = [`Semana ${s.numero}`, t.frecuencia];
  if (t.recurrente) sub.push(`${t.cumplidas} de ${t.meta_semanal} cumplidas`);
  $("panel-sub").textContent = sub.join(", ");

  const filas = [
    ["Meta", t.meta],
    ["Detalle", t.detalle],
    ["Notas", t.notas],
    ["Fecha", t.fecha_texto],
    ["Hora", t.hora],
    ["Duración", t.duracion_min ? `${t.duracion_min} min` : ""],
  ];
  const dl = $("panel-datos");
  dl.replaceChildren();
  for (const [nombre, valor] of filas) {
    dl.append(crear("dt", "", nombre));
    dl.append(crear("dd", valor ? "" : "vacio", valor || "Sin dato"));
  }
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
window.addEventListener("focus", () => cargar());

cargar(true);
setInterval(cargar, REFRESCO_MS);
