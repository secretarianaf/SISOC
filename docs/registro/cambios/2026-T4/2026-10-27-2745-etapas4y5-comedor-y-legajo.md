# Cambio: regla Comedor–Organización y legajo por programa, Etapas 4 y 5 (#2745)

## Alcance

Etapas 4 y 5 del plan
`docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md`, en un
solo PR sobre `development`, que ya tiene las Etapas 2 y 3 (#2775,
`docs/registro/cambios/2026-T4/2026-10-23-2745-etapas2y3-carga-por-programa.md`).
Pantallas según los mockups validados el 27/10/2026.

### Ajustes a la carga de la organización (sobre #2775)

- Edición de la organización según el mockup validado: "Programas" solo
  elige programas; "Datos Abordaje Comunitario" aparece con Línea Secos o
  Línea Tradicional (o si ya tiene proyectos, región, subzona o territoriales
  anteriores) y reúne Región, Subzona y una fila por proyecto con su línea,
  sus territoriales y el botón de convenio. Con una sola línea, se asigna
  sola. Al servidor llegan los mismos campos de #2775: `proyectos_lineas` y
  `asignaciones_territoriales`.
- Quitar un proyecto sigue como en #2642: se desactiva, conserva línea y
  convenio y se le quitan los territoriales (decidido el 29/10/2026: así no
  cambia quién ve qué rendiciones). Si se lo vuelve a agregar en otra
  edición, se le propone la línea que tenía.
- Al guardar el convenio se vuelve al legajo, en la línea del proyecto.
- Migración `gestion_organizaciones/0005_region_desde_issue_2642`: retira
  `RegionAbordaje`, `SubzonaAbordaje` y `DatosRegionOrganizacion` (sin uso
  desde #2775), con su admin y su auditoría. Antes copia al kernel la región
  y subzona de cada organización, incluidas las dadas de baja, y agrega al
  catálogo del kernel solo las que use alguna organización y falten (el
  resto es el mismo Excel del #2642). Si tuviera que pisar un valor distinto, se
  frena y lista los casos; la reversa recrea las tablas vacías.

### Etapa 4: alta y edición de comedores

- `src/backends/comedores/comedores/forms/comedor_form.py`: el programa se
  limita a los de la organización y el proyecto debe ser de la línea del
  programa. La validación corre en altas y cuando cambia la organización, el
  programa o el proyecto; los comedores existentes no se bloquean.
- `comedor_form.html`: primero la organización, después sus programas y por
  último los proyectos de la línea elegida.
- `proyectos_organizacion_ajax` devuelve la línea de cada proyecto y los
  programas de la organización.
- La API territorial, la PWA y los importadores no asignan proyectos: no
  cambian.

### Etapa 5: legajo de la organización

- Servicio nuevo `src/backends/comedores/gestion_organizaciones/services/legajo.py`
  (`datos_legajo`): arma el legajo del programa y la sección elegidos.
  `OrganizacionDetailView` solo lo llama.
- `organizacion_detail.html` sigue B v3 y se divide en partials en
  `src/backends/comedores/gestion_organizaciones/templates/organizaciones/partials/legajo/`:
  - Encabezado con selector de programa (`?programa=`), Datos de la
    Organización (con el campo Programas) y franja del programa.
  - Abordaje: pestañas Información / Rendiciones (`?seccion=`); a todo el
    ancho y en este orden, Datos de Región (Región, Subzona y territoriales
    anteriores sin proyecto), Proyectos con sus territoriales (#2642) y
    Datos de Convenio por proyecto.
  - La tabla de rendiciones tiene las mismas columnas que la anterior,
    incluida "Validación" (de `development`), más Línea y Proyecto cuando se
    ven todas.
  - Firmantes y comedores del programa; Documentación en Alimentar
    Comunidad.
  - `?proyecto=` sigue filtrando rendiciones y abre esa pestaña, como antes.
- Casos especiales (mockup, casos 1 a 4), para que nada quede oculto:
  - Sin programas: aviso "Sin programas asignados"; firmantes y comedores
    en "Sin programa asignado"; la documentación se ve como hoy.
  - Firmantes y comedores sin programa o con uno que la organización no
    tiene: bloque "Sin programa asignado", visible en cualquier programa.
  - Proyectos sin línea o con una línea que la organización no tiene: aviso
    con enlace a la edición.
  - Rendiciones cuya línea no es un programa de la organización: bloque
    "Rendiciones de otras líneas".
  - Organización sin Secos ni Tradicional que igual tiene proyectos, región,
    territoriales o rendiciones: se muestran debajo de Datos de la
    Organización.
- Cada caso se normaliza solo al corregir el dato: el legajo se calcula al
  abrirlo y no guarda nada aparte.
- Filtro `etiqueta_territorial` en
  `src/backends/comedores/gestion_organizaciones/templatetags/organizaciones_tags.py`,
  con el mismo formato que la edición.
- Permisos: sin cambios. Los botones dependen del mismo
  `puede_gestionar_organizaciones` que el legajo anterior.
- Verificación previa al deploy:
  `src/scripts/operacion/verificar_2745_casos_legajo.sql` (casos 5 y 6,
  descartados por el área usuaria).

## Verificación

Local, en contenedor Docker de un solo uso (SQLite en memoria):

- `src/backends/comedores/tests/test_issue_2745_comedor_organizacion_programa.py`
  (Etapa 4).
- `src/backends/comedores/gestion_organizaciones/tests/test_issue_2745_legajo.py`
  (Etapa 5):
  - Organización con uno y con tres programas, elección por URL y programa
    inválido.
  - Abordaje con proyectos, territoriales, región y convenio; rendiciones
    por la línea de la rendición; `?proyecto=` sin sección.
  - Usuario sin gestión sin botones.
  - Casos 1 a 4, cada uno antes y después de resolverlo.
  - No pérdida: todo firmante, comedor, proyecto y rendición aparece en
    algún lugar del legajo.
  - Revisión contra el legajo anterior (29/10/2026): `?proyecto=` abre la
    línea de ese proyecto; el filtro ofrece los mismos códigos; sin
    Abordaje el filtro sigue visible sin resultados; sin programas se
    pueden agregar firmantes; total de comedores; documentación visible
    sin Alimentar si hay archivos.
- Tests anteriores del legajo adaptados: `gestion_organizaciones/tests.py`,
  `test_issue_2445_territorial_abordaje_organizacion.py` y
  `test_rendicion_auditoria_issue_2673.py` (la tabla de rendiciones suma
  Línea y Proyecto; Validación y Auditada se verifican igual).
- `pytest -n auto` sobre `src/backends/comedores`, `src/backends/kernel/organizaciones`
  y `test_servicios_backends.py` (29/10/2026, sobre `development` actualizado):
  2205 pasan. Fallan `test_issue_2641_c2_http.py`, que también falla en
  `development` limpio, y los tests de consultas del admin
  (`test_admin_operaciones_*`), que pasan al correrlos sin paralelismo,
  igual que en `development`.
- `black`, `pylint` (10/10) y `djlint --check`: sin observaciones.
- Base local: los legajos de todas las organizaciones, en cada programa y
  sección, responden 200.
