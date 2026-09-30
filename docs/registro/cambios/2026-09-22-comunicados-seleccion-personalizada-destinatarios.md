# 2026-09-22 - Comunicados: seleccion personalizada de destinatarios (#2505)

## Contexto
- El selector de destinatarios del formulario de comunicados serializaba **todo**
  el universo de comedores/organizaciones en un `<select multiple>` oculto y solo
  permitia filtrar por nombre en el cliente. No habia forma de combinar criterios
  ni de seleccionar "todos los que matchean".
- El issue pide ademas que los filtros coincidan con los de los listados. Comedores
  ya tenia filtros combinables (`core/services/advanced_filters` +
  `comedores/services/filter_config`); **Organizaciones no tenia ninguno**: su
  listado solo filtraba por texto libre.
- El orden de las secciones del formulario tampoco era el pedido.

## Cambios aplicados

### Organizaciones: motor de filtros combinables
- `organizaciones/filter_config.py` (nuevo): `FIELD_MAP` / `FIELD_TYPES` /
  `FILTER_FIELDS` / operadores + `ORGANIZACION_ADVANCED_FILTER` (instancia de
  `AdvancedFilterEngine`) + `get_filters_ui_config()` con cache, espejando
  `comedores/services/filter_config`. Campos: nombre, sigla, CUIT, telefono,
  email, tipo y subtipo de entidad (choices desde la base), domicilio, partido,
  provincia, municipio, localidad, espacio comunitario, codigo de proyecto,
  sin vencimiento, fecha de vencimiento, fecha de creacion e ID.
- `organizaciones/views.py`: `_build_organizacion_list_queryset` acepta
  `request_or_get` y aplica el engine; el listado y la vista AJAX honran
  `filters` (sin UI que lo envie, ver "Ajustes de review").
- `organizaciones/views_export.py`: el CSV usa los mismos filtros que el listado.

### Comunicados: panel de destinatarios con filtros
- `comunicados/services_destinatarios.py` (nuevo): busca comedores y
  organizaciones reutilizando `COMEDOR_ADVANCED_FILTER` y
  `ORGANIZACION_ADVANCED_FILTER`, **siempre** acotado al alcance del usuario
  (`get_ids_*_del_usuario`). Pagina de a `PAGE_SIZE=25` y limita la seleccion
  masiva a `MAX_SELECCION_MASIVA=2000`.
- `comunicados/views.py` + `urls.py`: endpoints
  `comunicados/destinatarios/<universo>/buscar/` y `.../todos/` (requieren
  permiso de creacion), y `ComunicadoDestinatariosContextMixin` que inyecta
  config de filtros, URLs y seleccion previa en Create/Update.
- `comunicados/forms.py`: los campos `comedores` y `organizaciones` pasan de
  `SelectMultiple` a `MultipleHiddenInput`. El universo ya no se serializa en el
  HTML; el queryset por permisos sigue validando lo que llega por POST. (Luego
  reemplazado por un input unico, ver "Ajustes de review".)
- `templates/comunicados/partials/destinatarios_panel.html` (nuevo) y
  `static/custom/js/comunicadosDestinatarios.js` (nuevo): filas de filtro
  (campo + operador + valor, segun el tipo), busqueda paginada, agregar/quitar
  individual, "Agregar todos los resultados" y badges de seleccionados. Los
  filtros se pueden cambiar y volver a buscar sin perder lo ya elegido.
- `static/custom/js/comunicadosForm.js`: se elimino el selector viejo.
- `static/custom/css/comunicadoForm.css`: estilos del panel.

### Reordenamiento de la UI
- `templates/comunicados/comunicado_form.html`: el orden pasa a ser
  **Configuracion -> Destinatarios -> Redaccion -> Archivos Adjuntos**.

## Impacto esperado
- Al crear/editar un comunicado externo se puede segmentar destinatarios con
  filtros combinables (AND) equivalentes a los del listado correspondiente, y
  sumar de a uno o en bloque.
- El formulario deja de renderizar miles de `<option>`: el universo se consulta
  por AJAX. Los comunicados ya guardados se siguen editando igual (la seleccion
  previa se precarga como badges).
- El listado de organizaciones no cambia para el usuario: conserva la busqueda
  AJAX por texto libre.

## Validación
- `pytest tests/ comunicados/ organizaciones/ comedores/ -n auto`:
  3247 passed, 9 skipped. Tests nuevos:
  `tests/test_comunicados_destinatarios_unit.py` (12) y
  `tests/test_organizaciones_filter_config_unit.py` (4).
- `tests/test_csv_export_architecture.py::test_exportadores_csv_http_reutilizan_la_politica_central`
  falla, pero ya fallaba antes de este cambio (rompe al decodificar un archivo
  `cp1252` de `xlwt`); se verifico con `git stash`.
- `black`, `djlint --reformat` y `pylint -E` sobre los archivos tocados.

## Ajustes de review
- **Seleccion en un solo campo**: `comedores` y `organizaciones` viajan como un
  unico input oculto con ids separados por coma (`CommaSeparatedIdsInput` en
  `comunicados/forms.py`). Con un input por id, seleccionar ~1000 o mas
  destinatarios superaba `DATA_UPLOAD_MAX_NUMBER_FIELDS` (1000 por defecto) y el
  POST respondia 400. El widget sigue aceptando valores repetidos (`getlist`)
  por compatibilidad. Se descarto subir el setting global porque afloja una
  proteccion anti-DoS en todo el sitio.
- **Fechas de Organizaciones por dia**: `fecha_vencimiento` y `fecha_creacion`
  son `DateTimeField`; se mapean a `__date` (mismo patron que celiaquia, CDF y
  rendicion de cuentas). Antes `eq` comparaba contra medianoche y `gt`/`lt`
  quedaban corridos un dia.
- **Alcance sin `IN` gigante**: con alcance total
  (`permissions.tiene_alcance_total_destinatarios`) la busqueda usa el queryset
  completo en vez de materializar todos los ids.
- **Robustez**: ids no numericos en el POST se descartan al pintar la seleccion
  (antes 500); la paginacion del panel reutiliza la ultima busqueda ejecutada;
  el CSV de organizaciones cuenta comedores con `distinct=True` para no inflar
  el conteo al filtrar por relaciones.
- **Listado de Organizaciones sin cambio de UX**: se revirtio el paso a
  `filters_mode` en `organizacion_list.html` porque no estaba pedido en el issue.
  Los filtros combinables de organizaciones quedan para Comunicados; el backend
  del listado sigue aceptando `filters` y puede habilitarse en la UI con una
  decision de producto explicita.

## Segunda ronda de review (PR #2557)

- **La busqueda se movio a `comedores/api.py`.** `comunicados.services_destinatarios`
  importaba `comedores.models`, `comedores.services` y `organizaciones.models`, y
  eso rompe el contrato `comedores-core-public-boundary` de `.importlinter`
  (`architecture_imports` en rojo). Ademas `comedores.services.filter_config` es
  un alias por `sys.modules`, asi que pylint tiraba `E0611` sobre ese import.

  La fachada publica de Comedores Core ahora expone
  `buscar_comedores_para_destinatarios`, `buscar_organizaciones_para_destinatarios`,
  `nombres_de_comedores`, `nombres_de_organizaciones` y
  `get_filtros_destinatarios_config`. Devuelven **DTOs** (`DestinatarioDisponible`,
  `PaginaDestinatarios`): del lado de comunicados no circula ningun objeto del
  ORM. Se descarto agregar la excepcion en `ignore_imports`, porque seria aflojar
  el contrato para un caso que la fachada resuelve bien.

- **El panel dejo de exigir permiso de creacion.** Se renderiza tanto en el alta
  como en la edicion, y cada vista pide un permiso distinto: un usuario del grupo
  "Comunicado Editar" abria un borrador, tocaba Buscar y recibia 403. Ahora los
  dos endpoints usan `require_seleccionar_destinatarios_permission`
  (`can_create_comunicado or can_edit_comunicado`). El alcance lo sigue aplicando
  el servicio.

  Efecto lateral que importa: como `can_create_comunicado` era **exactamente**
  `tiene_alcance_total_destinatarios`, la rama de alcance acotado del servicio no
  se alcanzaba nunca desde estos endpoints. Ahora si, con un tecnico que entra
  por el permiso de edicion.

- **Tests con usuarios reales.** `test_buscar_respeta_el_alcance_del_usuario`
  forzaba `tiene_alcance_total_destinatarios=False` sobre un admin, un estado que
  no puede darse con permisos reales, y por eso no detectaba el 403. Se reemplazo
  por usuarios construidos con permisos de verdad: un editor sin alcance, un
  tecnico con dupla activa, y la vista de edicion junto a los dos endpoints.

- **`organizaciones/views.py`**: el `.distinct()` se aplicaba siempre que llegara
  `request_or_get`, aunque no hubiera `filters`. Como la UI del listado se
  revirtio y no manda `filters`, cada carga pagaba un `SELECT DISTINCT` de mas.
  Ahora se usa `build_q()` y solo se filtra y aplica `distinct()` si devuelve un
  `Q`. Tambien se movio el import de `filter_config` junto a los de
  `organizaciones` (`C0412 ungrouped-imports`).

- **`organizaciones/views_export.py`** importa `ORGANIZACION_ADVANCED_FILTER`
  directo de `organizaciones.filter_config`, para no acoplar el export a las
  views.

## Riesgos y rollback
- El tope de seleccion masiva (2000) es conservador; si molesta, subirlo en
  `comunicados/services_destinatarios.MAX_SELECCION_MASIVA`.
- Rollback: revertir el commit. No hay migraciones.
