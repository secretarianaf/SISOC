# Cambio: Tablero Becas Progresar · Curso obligatorio

## Alcance

El equipo de Datos seguía con un Power BI externo a los titulares de Becas
Progresar y su paso por el curso obligatorio "Proyecto de vida y economía
personal" de Formando Capital Humano. Se agrega una pantalla de SISOC,
`/dashboard/progresar-curso-obligatorio/`, con datos agregados (sin personas).

- Dueño: `sisoc_core/dashboard` (el módulo del menú "Tableros"). Progresar no
  tiene vertical en SISOC y el tablero solo lee dos tablas: no justifica un
  servicio nuevo.
- Datos: los de Progresar no viven en SISOC. Una carga diaria del equipo de
  Datos los deja agregados en dos tablas de la base,
  `bi_progresar_curso_obligatorio_resumen` y `_evolucion`, que SISOC solo lee
  con modelos `managed=False` (`ProgresarCursoResumen`,
  `ProgresarCursoEvolucion`). Ver
  `docs/registro/decisiones/2026-11-13-tableros-leen-tablas-bi-del-equipo-de-datos.md`.
- Migración `dashboard/0005_tablero_progresar_curso`: registra los dos modelos
  y dos llaves nuevas: `dashboard.view_tablero_progresar_curso` (ver el
  tablero, recortado a las provincias del usuario) y
  `dashboard.view_tablero_progresar_curso_nacional` (ver todo el país). **No
  crea ni modifica tablas** (`managed=False`).
- Service: `src/backends/sisoc_core/dashboard/services/tablero_progresar_curso/impl.py`
  (ORM). Vista `TableroProgresarCursoView` (delgada), template
  `tablero_progresar_curso.html` sobre `includes/main.html`, Chart.js, datos por
  `json_script` (CSP: sin scripts inline). JS y CSS en
  `static/custom/{js,css}/tablero_progresar_curso.*`, todo bajo `.tpc-tablero`.
- Patrón seguido: el tablero de Celiaquía (`celiaquia/tablero/`): service +
  vista delgada + permiso propio + `json_script`.
- El fondo usa el azul secundario de Poncho solo en esta pantalla, como
  `poncho_listados.css` (`.app-main:has(...)`).

Para que aparezca en el menú "Tableros" se carga una entrada con
`ruta_interna = /dashboard/progresar-curso-obligatorio/` y permisos
`dashboard.view_tablero_progresar_curso` y
`dashboard.view_tablero_progresar_curso_nacional`.

## Comportamiento

Bloques: tarjetas (titulares, inscriptos por estado del curso, rindieron);
tarjetas de seguimiento (inscriptos esta semana, inscriptos que no avanzan,
aprobados en menos de una hora); inscriptos y aprobados acumulados por día;
inscripción y resultados por jurisdicción; inscriptos por edad y género; tasa de
inscripción por edad y género. Filtros de jurisdicción y línea (por defecto
Progresar Obligatorio).

Alcance por usuario (se aplica en el servidor, antes de mandar los datos):

- superusuario o llave `..._nacional`: todo el país;
- el resto: solo las provincias completas de su alcance territorial (perfil
  "usuario provincial", `users.territorial_scope`,
  `provincia_lookup="provincia_id"`);
- sin provincia completa (no provincial, sin alcance, o solo municipio o
  localidad, que estas tablas no tienen): aviso "sin jurisdicción", sin datos.
  Así, un alta incompleta no muestra datos de más.

Si las tablas no existen o no se pueden leer (por ejemplo en QA u
homologación sin la carga), la pantalla muestra "Todavía no hay datos
cargados" en lugar de fallar. Sin login: al login; sin la llave: 403.

"Actualizado" es la fecha de la última carga (`MAX(fecha_carga)`); si tiene más
de un día se marca en ámbar. La carga guarda la hora de Argentina sin zona y se
muestra tal cual (sin convertir).

## Verificación

- `pytest src/backends/sisoc_core/dashboard/`: 33 pasan (llave nacional, alta
  incompleta sin perfil provincial, una y varias provincias, sin jurisdicción,
  solo municipio, superusuario, sin datos, sin tablas, sin login, sin la llave,
  sin datos personales en la respuesta). Con `test_urls_no_500` y
  `DJANGO_DEBUG=False`: 918 pasan (antes de las dos llaves).
- `black`, `djlint` y `pylint` (10/10) sin observaciones; `makemigrations
  --check` sin cambios; `url_registry.json` regenerado.
- Verificación visual en el entorno local con los totales agregados de la
  carga real (sin personas): usuario con la llave, usuario provincial y
  usuario sin la llave (403 y sin entrada en el menú). Confirmada por quien
  pidió el tablero. Con las dos llaves, además: usuario con la llave común sin
  perfil provincial (no ve datos).
