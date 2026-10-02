# 2026-09-23 - "Volver" unificado en todas las pantallas (#2460)

## Contexto
- El boton "Volver" estaba implementado pantalla por pantalla, con posicion y
  estilo distintos: margen derecho junto a las opciones de archivo, debajo de la
  carga de archivos, margen izquierdo, o directamente ausente.
- Relevamiento: de las **327 pantallas** (templates que extienden
  `includes/main.html`), **138 tenian algun "Volver"** con markup propio
  (41 `btn btn-secondary`, 7 `btn-sm btn-primary`, 5 `btn-outline-secondary`,
  `btn-cancel`, etc.), mas un tercer estilo (`poncho-volver`, pildora blanca) en
  el componente `search_bar.html`.
- Las referencias del issue diferian entre si: el detalle de comedores usaba
  azul arriba a la izquierda; la edicion de admisiones tecnicas, gris.
- "Que persistan los filtros" no funcionaba: `navigator.js` guardaba `lastUrl`
  solo si el link de origen tenia la clase `.link-handler`, cosa que casi ningun
  listado usa.

## Cambios aplicados
- `templates/components/back_button.html` (nuevo): markup canonico. Gris
  (`btn btn-secondary btn-sm`), con flecha, arriba a la izquierda.
- `templates/includes/main.html`: lo incluye **una sola vez**, antes del titulo
  de pagina, de modo que aparece en las 327 pantallas sin tocar cada template.
- `static/custom/js/volver.js` (nuevo): mantiene una pila de URLs visitadas en
  `sessionStorage` **con querystring**, asi "Volver" regresa al listado tal como
  estaba filtrado. Cascada de resolucion: pila de navegacion -> referrer del
  mismo origen -> `volver_url` que declare la vista -> `history.back()`.
  Se carga desde `scripts/mainscripts.html`.
- `core/context_processors.boton_volver` + alta en `config/settings.py`: define
  `ocultar_volver`, `volver_url` y `volver_texto` para que el componente nunca
  resuelva variables inexistentes (hay un test en VAT que falla si un render
  loguea "Exception while resolving variable").
- `static/custom/css/custom.css`: estilos de `.sisoc-volver-barra`/`.sisoc-volver`
  (se oculta al imprimir).
- **Limpieza**: se removieron **119 botones "Volver" de navegacion en 110
  templates**, junto con los wrappers que quedaron vacios. Incluye las variantes
  con etiqueta propia ("Volver al CDI", "Volver a la nomina", "Volver al
  listado", ...), que quedan cubiertas por el boton global.
- `templates/components/search_bar.html`: se saco la rama `back_url`/`back_text`
  (la pildora blanca `poncho-volver`) y el parametro de los 8 includes que lo
  pasaban.
- `core/views.inicio_view`: pasa `ocultar_volver=True` por ser la pantalla raiz.

## Decisiones y limites
- **Se conservan 31 "Volver" que funcionan como cancelar de un formulario** (los
  que conviven con un `type="submit"`): no son navegacion, son descartar la
  edicion, y sacarlos dejaria formularios sin salida junto a "Guardar". Queda
  pendiente, si UX lo pide, renombrarlos a "Cancelar".
- No se tocaron `templates/403.html`, `404.html` y `500.html`: ahi "volver al
  inicio" es un link dentro de un parrafo, no un boton.
- Tampoco el `prev_text='Volver'` de `components/pagination.html`, que es
  paginado, no navegacion.

## Impacto esperado
- Todas las pantallas muestran el mismo "Volver", gris, arriba a la izquierda.
- Al volver desde un detalle se recupera el listado con sus filtros aplicados,
  porque la pila guarda la URL completa.
- Entrar directo por URL (pestaña nueva, link compartido) cae al referrer o a la
  raiz: no hay pila previa que consultar.

## Validación
- `pytest -n auto`: 5453 passed, 14 skipped. Test nuevo
  `tests/test_boton_volver_unificado.py` (6), que incluye un test de arquitectura
  que falla si alguna pantalla vuelve a declarar su propio boton de navegacion.
- `tests/test_csv_export_architecture.py` sigue fallando, pero ya fallaba antes
  (rompe al decodificar un archivo `cp1252` de `xlwt`).
- `black` y `djlint --check` sobre lo tocado. Se descarto el reformateo masivo
  que `djlint --reformat` habia introducido en 4 templates que no estaban
  formateados de antes, para no mezclar formateo con el cambio funcional.

## Riesgos y rollback
- Riesgo principal: alguna pantalla dependia visualmente del boton removido
  (por ejemplo una fila de acciones que ahora queda con un solo elemento). El
  diff es de 89 inserciones / 473 borrados en 126 archivos: conviene una pasada
  visual por las pantallas mas usadas antes de mergear.
- Si una pantalla necesita un destino fijo, la vista pasa `volver_url`; si no
  debe mostrarlo, `ocultar_volver=True`.
- Rollback: revertir el commit. No hay migraciones.

## Segunda ronda de review (PR #2567)

### 1. El destino ya no sale solo del orden de navegacion (bloqueante)

La pila guardaba el orden en que se visitaron las pantallas, no la jerarquia.
Despues de un POST-redirect-GET a una URL nueva, el formulario quedaba como
"pantalla anterior" y el boton apuntaba ahi. Tres flujos rotos:

- **Alta**: listado -> crear -> POST -> detalle nuevo. "Volver" iba al alta vacia.
- **Borrado desde el detalle**: "Volver" iba al `confirm_delete` de un objeto que
  ya no existe, o sea un 404.
- **Edicion con `success_url` al listado**: "Volver" iba al formulario de edicion.

Se corrigio por partida doble:

- **Las pantallas transitorias no se apilan.** Quien lo decide es el servidor:
  `core.context_processors._es_pantalla_transitoria` mira la clase de la vista
  (`FormMixin` o `DeletionMixin`) y emite `data-volver-transitoria` en el
  `<script>`. Se dedujo de la clase en vez de pedirle a cada template que se
  marcara porque son ~200 formularios y uno sin marcar es un bug silencioso.
- **El destino jerarquico gana sobre la pila.** Si la vista declara
  `volver_url`, se usa ese; la pila solo aporta la querystring cuando alguna
  visita apunta al mismo path. Asi el destino es el correcto *y* se conservan
  los filtros, que era el requisito original del issue.

### 2. Destino jerarquico en la entrada directa (importante)

Con la pila y el referrer vacios (pestaña nueva, link de mail), el boton caia a
`history.back()`, que podia sacar al usuario de SISOC. Ahora:

- `history.back()` se elimino: el ultimo recurso es `/`.
- Se declaro `volver_url` en las vistas donde se habia sacado un boton
  contextual, con el mismo destino que tenia: VAT (curso, centro, comision,
  asistencia, wizard de comision e institucion), centro de familia, importar
  expedientes, ciudadanos y los tres `*_job_detail`.
- En `centrodeinfancia/views.py` el `back_url` que habia quedado muerto se
  renombro a `volver_url`: esa pantalla recupera el detalle del CDI como destino.

### 3. Se sacaron los "Volver" duplicados que quedaban (importante)

17 botones de navegacion en 16 templates, entre ellos
`ciudadanos/importacion_masiva_form.html`, que es uno de los ejemplos que cita
el issue y mostraba dos "Volver".

`VAT/.../nomina_form_edit.html` resulto ser un template muerto: ninguna vista lo
referencia.

### 4. El test de arquitectura ahora los detecta (importante)

Antes exigia la clase `btn`, asi que no veia `vat-back`, `sisoc-back-link` ni
`sisoc-wizard-back`; tampoco miraba `<button>`; y con una ventana de 400
caracteres cualquier `type="submit"` cercano eximia al boton, aunque estuviera
en otro form.

Ahora mira `<a>` y `<button>` con cualquier clase, y en vez de la heuristica por
distancia usa una **allowlist explicita** (`CANCELAR_DE_FORMULARIO`) de las 22
pantallas donde el "Volver" es el cancelar de un formulario. Un segundo test
falla si una entrada de la allowlist se queda sin su boton, para que no acumule
entradas muertas: de hecho encontro tres mientras se hacia este cambio.

### 5. Criterio unificado en los formularios (importante)

En `comedor_form.html` y `organizacion_form.html` el "Volver" de la barra sticky
se habia sacado en edicion y dejado en alta. Se saco en los dos: esa barra ya
tiene un "Cancelar" explicito al lado, asi que el "Volver" era navegacion
duplicada, no la salida del formulario. Se eliminaron los `{% if %}{% else %}
{% endif %}` vacios que quedaron ahi y en `centrodeinfancia_form.html`,
`destinatario_form`, `trabajador_form`, `nomina_form` y el `<div>` vacio de
`rendicion_cuentas_final_detail.html`.

### 6. Cobertura del JavaScript (importante)

`tests/js/volver.test.js`: 12 casos con `node:test` y `node:vm`, sin dependencias
nuevas, siguiendo el estilo de los tests JS que ya habia. Cubren los tres flujos
rotos, la pila, el zigzag, la recarga, el destino jerarquico con y sin
querystring, la entrada directa y el referrer externo.

El paso "Ejecutar pruebas de JavaScript" se sumo a `deploy_guard`. Se listan los
archivos en vez de la carpeta porque `tests/js/user_mobile_access.test.js` ya
venia fallando de antes (su stub de DOM no implementa `querySelector`) y sumarlo
pondria el CI en rojo por algo ajeno a este PR.

### 7. Formato mezclado con el cambio funcional (menor)

`includes/base.html`, `includes/sidebar/new_opciones.html` y
`components/data_table.html` no tenian ningun cambio funcional: se revirtieron
del todo y salen del diff.

Los reflows de `centrodeinfancia_detail`, `ciudadano_detail`,
`relevamientos/relevamiento_detail` y `datacalle/relevamiento_detail` **no se
pueden sacar**: los genera el paso "Run DJLint autofix" de `.github/workflows/lint.yml`,
que corre `djlint --reformat` sobre todo template modificado y commitea el
resultado. Mientras esos archivos formen parte del PR, el CI los va a reformatear.
Se verifico revirtiendolos y volviendo a correr djlint: los reintroduce.
