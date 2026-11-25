# Plan Tracker

Instrucciones del proyecto para Claude Code. Léelas completas antes de cada sesión.

## Cómo trabajar con el usuario

- Explícale cada paso en español, en lenguaje simple: qué vas a hacer, por qué, y qué tiene que hacer el usuario (qué botón tocar, qué copiar, dónde). Antes de pedirle que ejecute algo, dile qué debería ver si salió bien.
- Avanza por fases pequeñas. Al terminar cada fase, verifica que funcione ejecutándolo, haz commit a GitHub con un mensaje claro y dile qué sigue.
- En textos de la interfaz y en tus explicaciones no uses guiones largos ni guiones como separadores.

## Computadora del usuario

- Windows, Microsoft Surface con procesador ARM64. Python 3.14 instalado.
- Usa solo librerías de Python puro o con soporte comprobado para Windows ARM64. Evita pandas, numpy, pyarrow, Streamlit y cualquier cosa que tenga que compilarse. Si una instalación falla, explica el error y busca una alternativa.
- Repositorio en GitHub. Nunca subas credenciales: `credentials.json`, `token.json` y `.env` van en `.gitignore` desde el primer commit.

## Qué es el programa

Una aplicación de escritorio para seguir planes de trabajo por semanas. El primero es un "Plan de 30 días" (4 semanas). Después vendrán otros planes, así que todo debe soportar varios planes.

El usuario la tiene abierta todo el día en su segunda pantalla. Tiene que ser muy simple visualmente.

### Arquitectura

- **Datos en una hoja de Google Sheets** llamada "Plan Tracker". Es el lugar compartido: Claude, desde cualquier chat de claude.ai, también lee y escribe esa hoja con su conector de Google Sheets. El programa nunca guarda datos solo en local; la hoja es la fuente de verdad.
- **Programa en Python con Flask**: un servidor local pequeño que sirve una página HTML simple. Se abre en una ventana propia de Chrome con `--app=http://localhost:PUERTO`, sin pestañas ni barra de direcciones, mediante un archivo `Abrir Plan Tracker.cmd`.
- **Google Calendar**: el programa puede crear o actualizar un evento a partir de una tarea con fecha y hora.
- **Autenticación de Google**: OAuth de aplicación de escritorio con `credentials.json` (lo descarga el usuario desde Google Cloud) y `token.json` generado la primera vez. Permisos: Sheets y Calendar. Librerías: `google-api-python-client`, `google-auth-oauthlib`.
- La página se refresca sola cada 30 a 60 segundos para mostrar cambios que Claude haya hecho en la hoja desde un chat.

### Estructura de la hoja (pestañas)

No cambies nombres de pestañas ni de columnas sin avisar al usuario: Claude en los chats depende de ellos.

- `Planes`: id, nombre, inicio (AAAA-MM-DD), fin, activo (SI/NO), nombre_en, color
  - color: paleta de colores del plan en la app: `carolina` (por defecto si está vacía) | `bosque` | `borgona` | `ambar` | `violeta` | `petroleo`. El usuario la elige con el círculo de colores junto al nombre del plan; Claude también puede cambiarla escribiendo uno de esos valores.
- `Semanas`: plan_id, numero, inicio, fin, enfoque, nota, enfoque_en, nota_en
  - El usuario también puede agregar tareas desde la app (botón + de cada semana): reciben id `sN-palabras-del-titulo` y van al final de su semana (orden = el mayor + 10).
  - Los planes creados desde la app tienen id `pAAAAMMDD` (fecha de inicio) y semanas de 7 días sin enfoque ni tareas: cuando el usuario pida completarlo, Claude agrega enfoques, notas y tareas en la hoja. Un plan con `activo` = NO aparece como archivado en el selector.
  - Las columnas `_en` son la versión en inglés que la app muestra cuando el usuario elige EN. Al crear o cambiar un plan, un enfoque o una nota, llena también su versión `_en`; si queda vacía, la app muestra el texto en español. Las tareas no tienen versión en inglés.
- `Tareas`: id, plan_id, semana, orden, titulo, frecuencia, veces, dia, meta, detalle, estado, fecha, hora, duracion_min, notas, evento_id
  - frecuencia: `una_vez` | `diaria` | `dias_habiles` | `semanal` | `veces`
  - veces: número, solo para `veces`. dia: 0 lunes a 6 domingo, solo para `semanal`
  - estado: `pendiente` | `en_curso` | `hecho`
  - evento_id: id del evento en Google Calendar, vacío si no tiene
- `Marcas`: tarea_id, fecha (un renglón por cada día cumplido de una tarea recurrente)
- `Metricas`: plan_id, semana, conversaciones, agencias, envios, entrevistas, postulaciones
- `Cambios`: fecha_hora, origen (app | claude), texto

### Diseño de la pantalla

Una sola pantalla. En planes de hasta 4 semanas, sin scroll a tamaño normal de ventana (si un cuadrante no cabe, la app compacta letra y espacios sola):

- Barra superior delgada: nombre del plan (selector si hay varios), "Semana N, día X de 7" y el avance de la semana.
- Debajo, 4 cuadrantes iguales en 2 por 2, uno por semana. La semana actual resaltada.
- Planes de más de 4 semanas: en la barra aparece un botón para elegir la vista, "4 semanas" u "N semanas" (todas). La vista se guarda por plan y la de 4 es la vista por defecto.
  - Vista de 4: cada semana mide lo mismo que en un plan de 4 semanas (2 por 2) y las demás se ven con scroll. El scroll encaja por filas completas (scroll snap), avanza de a una fila (2 semanas) y siempre muestra 4 semanas enteras. Al abrir el plan, la fila de la semana actual queda arriba; si no hay suficientes semanas debajo, se ven las últimas 4. Al refrescar no se mueve el scroll.
  - Vista de todas: todas las semanas en una cuadrícula sin scroll (hasta 4 columnas).
- En cada cuadrante, una línea por tarea: casilla para marcar, título, y a la derecha la frecuencia en texto corto ("1 vez", "L a V", "5 veces"). Las tareas recurrentes muestran 7 casillas pequeñas L M M J V S D para marcar cada día.
- Clic en el título abre un panel pequeño con detalle, notas, fecha, hora y el botón "Agendar en Calendar".
- Nada más en pantalla: sin barras laterales, sin gráficos, sin decoración. Tipografía legible, mucho espacio, colores sobrios y un solo color de acento por paleta.
- Cada plan tiene su paleta (fondo oscuro y un color de acento), elegida con el círculo de colores junto al nombre del plan, para distinguir los planes de un vistazo.

## Fases

1. Preparar el proyecto: carpetas, entorno virtual, `.gitignore`, `requirements.txt`, primer commit y conexión al repositorio de GitHub.
2. Conectar con Google: autenticación OAuth y leer la hoja "Plan Tracker". Mostrar en consola las tareas de la semana 1 para confirmar que funciona.
3. Pantalla de solo lectura: los 4 cuadrantes con los datos reales de la hoja.
4. Edición: marcar tareas y días, editar detalle y notas. Cada cambio se escribe en la hoja y se registra en `Cambios`.
5. Google Calendar: botón "Agendar" que crea o actualiza el evento y guarda `evento_id`.
6. Lanzador: `Abrir Plan Tracker.cmd` que arranca el servidor y abre la ventana, y opción de que arranque al iniciar Windows.
7. Varios planes: selector de plan y forma de crear un plan nuevo.
