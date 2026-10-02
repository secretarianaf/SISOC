# 2026-09-24 - Homogeneizar los buscadores: filtros combinables en todos los listados

## Compatibilidad de enlaces existentes

Se conserva `?busqueda=` en los listados que ya lo aplicaban: importar
expedientes, CDI y sedes VPSL; en CDI tambien se respeta en el CSV. El listado
de itinerarios VPSL ya lo conservaba. El endpoint
`importarexpedientes/ajax/` mantiene su respuesta JSON y permisos para los
consumidores existentes. Los filtros combinables siguen siendo la interfaz
principal y se pueden combinar con el parametro anterior. En modalidades VAT
el parametro antiguo nunca filtraba resultados y conserva ese comportamiento.

Las notas posteriores que describen la eliminacion de estas URLs corresponden
al estado anterior a esta correccion de compatibilidad.

## Contexto
- Los 18 listados principales tenian buscadores con modos distintos. Auditados
  renderizando cada pantalla:
  - **11 con filtros combinables** (comedores, admisiones tecnicos y legales,
    acompanamientos, rendicion, dispositivos, centros CDF, beneficiarios,
    responsables, VAT centros, celiaquia).
  - **2 con busqueda AJAX por texto** (importar expedientes, organizaciones).
  - **5 con busqueda simple por texto** (centro de infancia, VPSL itinerarios,
    VPSL sedes, VAT modalidades de cursado, VAT planes curriculares).
- Ademas, en los dos catalogos de VAT el buscador era **decorativo**: el
  componente se renderizaba pero la vista nunca aplicaba `busqueda`.

## Cambios aplicados
Se migraron **6 listados** al componente de filtros combinables, conservando en
cada uno lo que ya buscaba:

| Listado | Antes | Config nueva |
|---|---|---|
| Importar expedientes | AJAX texto | `importarexpediente/filter_config.py` |
| Centro de Desarrollo Infantil | texto simple | `centrodeinfancia/filter_config.py` |
| VPSL itinerarios | texto simple + panel propio | `ver_para_ser_libre/filter_config.py` |
| VPSL sedes | texto simple | `ver_para_ser_libre/filter_config.py` |
| VAT modalidades de cursado | texto simple (inerte) | `VAT/catalogo_filter_config.py` |
| VAT planes curriculares | texto simple (inerte) | `VAT/catalogo_filter_config.py` |

Cada `filter_config` define `FIELD_MAP` / `FIELD_TYPES` / operadores /
`FILTER_FIELDS` y su `AdvancedFilterEngine`, igual que comedores y dispositivos.
Las vistas aplican el engine al queryset y exponen `filters_mode`,
`filters_config` y `filters_action`. Los campos filtrables cubren lo que cada
listado ya buscaba, de modo que ninguna busqueda se pierde: cambia el como, no
el que.

Detalles por pantalla:
- **VAT planes**: conserva sus filtros propios por los parametros `titulo` y
  `activo`.
- **VPSL itinerarios**: el modulo tenia un panel de filtros propio y un
  comentario en el template explicando por que no se habia migrado (la busqueda
  "todos" hace un OR entre siete campos, `estado` mapea texto con una funcion,
  `localidad` cruza tres rutas y `provincia` depende de permisos: nada de eso es
  expresable con el engine, que combina un `Q` por fila con AND). Se respeto esa
  decision: el panel y su texto libre **siguen existiendo**, re-apuntados con
  `form="filters-form"` para viajar en el mismo submit que los filtros
  combinables. Los combinables se suman, no reemplazan.

## Limpieza del buscador viejo
En las pantallas migradas, el mecanismo de busqueda anterior quedaba inalcanzable
(en `filters_mode` el componente no renderiza input de texto), asi que se removio:

- **Importar expedientes**: se elimino la vista `importarexpedientes_ajax`, su
  ruta y el `{% url ... as ajax_url %}` del template, que era el buscador AJAX en
  vivo del listado. Tambien el filtrado por `busqueda` de la ListView y el
  `query` que viajaba al componente y al paginador. El endpoint AJAX del
  **detalle** (`importarexpediente_detail_ajax`) no se toco: sigue en uso.
- **Centro de Desarrollo Infancia** y **VPSL sedes**: se removio el filtrado por
  `busqueda` y el `query` del contexto.
- **VAT modalidades de cursado**: se removio el filtrado por `busqueda`. Como el
  buscador viejo era inerte, no habia comportamiento que preservar.
- **VAT planes curriculares**: se removieron `titulos`, `titulo_filter` y
  `activo_filter` del contexto, que ningun template usaba. El filtrado por los
  parametros `titulo` y `activo` se conserva (no depende de la UI).
- **VPSL itinerarios**: es la excepcion, su buscador propio sigue vivo (ver
  arriba); se le repuso el input de texto libre, que antes ponia el componente.

## Decisiones y limites
- **Organizaciones quedo fuera a proposito**: ya se migro a filtros combinables
  en la rama del issue #2505 (`organizaciones/filter_config.py`). Incluirlo aca
  generaria un conflicto con ese trabajo.
- Solo se homogeneizo el **modo de busqueda**. Siguen difiriendo:
  - "Exportar busqueda": 11 listados no lo tienen.
  - "Agregar": depende de si la entidad tiene alta (admisiones, acompanamientos
    y rendicion no la tienen como flujo propio).

## Impacto esperado
- 17 de los 18 listados usan el mismo buscador de filtros combinables, con la
  misma UI y el mismo motor.
- Todos los campos que antes alcanzaba el texto libre siguen siendo buscables,
  pero **cambia el como**: ya no hay un OR implicito entre varios campos, hay que
  elegir el campo. En sedes VPSL, por ejemplo, un `?busqueda=Chaco` matcheaba
  nombre, CUE, jurisdiccion, localidad o domicilio; ahora se filtra por uno y se
  suman filas si se quieren mas. Los filtros propios de planes curriculares e
  itinerarios se conservan.
- Los dos catalogos de VAT pasan a buscar de verdad (antes el buscador no
  filtraba nada).
- **Cambio de contrato**: en las cinco pantallas limpiadas, una URL con
  `?busqueda=` deja de filtrar. El equivalente es `?filters=` con el campo
  correspondiente. Afecta a links guardados o compartidos.

## Validación
- `pytest -n auto`: 5506 passed, 14 skipped. Test nuevo
  `tests/test_buscadores_homogeneos.py` (25 casos): verifica que cada listado
  migrado exponga la UI y la config, que los campos declaren tipo y operadores
  validos, que los filtros efectivamente filtren (incluida una combinacion de
  dos campos), que el buscador viejo ya no altere el listado y que itinerarios
  conserve el suyo.
- Se actualizaron los tests de `importarexpediente/tests/test_ajax_endpoints.py`
  que cubrian el endpoint AJAX eliminado.
- `tests/test_csv_export_architecture.py` sigue fallando, pero ya fallaba antes
  (rompe al decodificar un archivo `cp1252` de `xlwt`).
- `black` y `djlint` sobre lo tocado.

## Riesgos y rollback
- Riesgo principal: no se probo en el navegador. Conviene revisar visualmente
  VPSL itinerarios, que es la unica pantalla donde conviven el panel propio y la
  barra de filtros combinables.
- Rollback: revertir el commit. No hay migraciones.


## Segunda ronda de review (PR #2575)

Seis correcciones sobre el primer estado del PR.

### 1. Se restauro el panel propio de itinerarios (bloqueante)

El commit "Sque el buscador viejo" habia borrado el panel del template, pero la
vista seguia procesando `busqueda`, `buscar_por`, `estado`, `provincia`,
`localidad` y el rango `fecha_desde`/`fecha_hasta`, y tanto este registro como
el test decian que el panel se conservaba. Quedaban dos caminos: restaurarlo o
removerlo del todo.

Se restauro, que es lo que la doc ya documentaba. Removerlo hubiera costado tres
capacidades que los filtros combinables **no** cubren:

- La busqueda "todos", un OR entre siete campos (codigo, provincia, estado por
  etiqueta, referente y las tres rutas de jornadas). El engine combina un `Q`
  por fila con AND.
- El rango Desde/Hasta por **solapamiento** (`fecha_fin >= desde` y
  `fecha_inicio <= hasta`). El componente no tiene selector de operador y un
  campo `date` filtra por igualdad.
- La localidad por tres rutas (`localidades_tentativas`, `sedes__localidad` y
  `jornadas__localidad`); el mapeo combinable solo llega a dos.

Con esto vuelven a pasar los dos tests que fallaban en CI:
`test_itinerarios_conserva_su_busqueda_libre_y_su_panel` y el preexistente
`ver_para_ser_libre/tests/test_workflow.py::test_itinerario_list_restringe_usuario_provincial_y_filtra`.

De paso se quito `query=filtros.busqueda` del `include` del componente: en
`filters_mode` no se renderiza input de texto, asi que ese argumento no tenia
efecto. El input de texto lo pone el panel.

### 2. "Fecha de subida" de importar expedientes no filtraba (importante)

`fecha_subida` es `DateTimeField(auto_now_add=True)` y el campo del filtro es de
tipo `date`, cuyo operador por defecto es `eq`. El engine armaba
`fecha_subida__exact=date(...)`, que con `USE_TZ=True` compara contra la
medianoche y no matcheaba nunca. Se mapeo a `fecha_subida__date`, el patron que
ya usan celiaquia, rendicion y CDF. Cubierto por
`test_importar_expedientes_filtra_por_fecha_de_subida`, que falla si se revierte
el mapeo.

### 3. "Exportar busqueda" de CDI ignoraba los filtros (importante)

`export_helper.js` reenvia `?filters=`, pero `CentroDeInfanciaExportView` solo
leia `busqueda`, que dejo de existir en la UI. El usuario filtraba, exportaba y
recibia el universo completo de su scope: una regresion, porque antes el export
si respetaba la busqueda. Ahora aplica
`CENTRODEINFANCIA_ADVANCED_FILTER.filter_queryset()` despues de
`aplicar_scope_centros_cdi`, en ese orden: el filtro acota dentro del alcance,
nunca lo abre.

### 4. `distinct()` de mas (menor)

Se saco de CDI, sedes VPSL, importar expedientes y modalidades VAT: ninguno de
esos `FIELD_MAP` cruza relaciones multivaluadas, asi que no hay filas
duplicadas que colapsar. En MySQL obligaba a un `SELECT DISTINCT` sobre todas
las columnas (incluidas las de `select_related` y la anotacion `Exists` de CDI)
y convertia el `COUNT` del paginador en una subconsulta.

Se conserva donde si hace falta y quedo comentado por que: planes VAT
(`titulos__nombre`, M2M) e itinerarios (`sedes__*`).

### 5. Tests en caminos criticos (menor)

Los casos originales corrian todos con superusuario, que no tiene scope. Se
agregaron cuatro que cubren lo que ese usuario no puede mostrar:

- `test_centro_de_infancia_el_filtro_no_amplia_el_alcance_provincial`: un usuario
  provincial filtrando por un valor que tambien matchea un centro de otra
  provincia sigue sin verlo.
- `test_el_export_de_cdi_aplica_los_filtros_combinables`.
- `test_el_export_de_cdi_no_escapa_del_alcance_del_usuario`.
- `test_importar_expedientes_filtra_por_fecha_de_subida`.

### 6. Este registro y la descripcion del PR

Se corrigio el impacto declarado ("ningun campo deja de ser buscable" era falso:
lo que se pierde es el OR implicito entre campos) y se actualizo la descripcion
del PR, que describia un estado intermedio del codigo.

### Limite conocido, no corregido

Los filtros por `mes_pago` / `ano_pago` de importar expedientes no encuentran
archivos viejos cuyo periodo todavia no se completo:
`_completar_periodos_faltantes` solo corre sobre las filas ya renderizadas de la
pagina, no sobre el queryset. Es preexistente a este PR y corregirlo implica
mover ese backfill fuera del render. Queda anotado.
