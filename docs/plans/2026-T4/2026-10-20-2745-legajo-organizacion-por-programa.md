# Plan: legajo de Organización desdoblado por programa (#2745)

Estado: aprobado funcionalmente por el área usuaria el 20/10/2026; pendiente
de revisión técnica en el PR de documentación. Sin implementar. Issue:
#2745. La implementación se hará en PRs posteriores, uno por etapa.

Las definiciones funcionales de la sección 1.2 son del área usuaria y se
acordaron sobre mockups del 19 y 20/10/2026 (variante "B v3"). La ubicación
técnica de los datos, los nombres de modelos, el orden del roadmap y las
recomendaciones marcadas como "propuesta" son del agente; la ubicación y los
permisos fueron aprobados por el área usuaria, pero requieren revisión
técnica antes de implementar.

Mockups (artifact privado, compartir antes de difundir):
https://claude.ai/artifact/CLXfC8znpFSP35yxRNGUik — tableros "B v2" y "B v3".

Decisión técnica asociada:
`docs/registro/decisiones/2026-10-20-2745-legajo-organizacion-por-programa.md`.

## 1. Descripción de los cambios

### 1.1 Problema actual

El legajo (`/organizaciones/detalle/<id>`,
`OrganizacionDetailView` en
`src/backends/comedores/gestion_organizaciones/views.py`, template
`src/backends/comedores/gestion_organizaciones/templates/organizacion_detail.html`)
muestra en una sola pantalla información de Alimentar Comunidad y de Abordaje
Comunitario:

- Códigos de Proyecto, Territorial y Rendiciones son de Abordaje, pero los ve
  cualquier equipo.
- Firmantes y Comedores Asociados listan registros de todos los programas en
  la misma tabla.
- La Organización no tiene programa propio: la pertenencia hoy se deduce de
  sus comedores (`Comedor.programa`) y firmantes (`Firmante.programa`).

### 1.2 Definiciones acordadas

1. La Organización tiene un dato propio "Programas" y puede tener más de uno.
   El comedor conserva su propio programa.
2. Los programas son tres y se ven por separado: Alimentar Comunidad,
   Abordaje Comunitario – Línea Secos y Abordaje Comunitario – Línea
   Tradicional (hoy ya existen como registros de `comedores.Programas`).
3. El legajo muestra solo los programas que tiene la organización; con uno
   solo no hay selector. Todos los usuarios que hoy acceden al legajo ven todas
   sus secciones (no cambia el filtro de acceso existente).
4. Historial, Editar y Eliminar quedan en el encabezado y no dependen del
   programa elegido (conservan sus permisos actuales).
5. Datos de la Organización (todos los datos actuales salvo Códigos de
   Proyecto y Territorial, más "Programas") son comunes a todos los programas.
6. Firmantes se carga por programa; una persona puede repetirse entre
   programas.
7. Documentación es exclusiva de Alimentar Comunidad.
8. Alimentar Comunidad no usa código de proyecto.
9. Una organización puede tener proyectos de las dos líneas de Abordaje, pero
   cada proyecto pertenece a una sola línea.
10. "Datos de Región" (Territorial asignado + Región + Subzona) es común a
    Línea Secos y Línea Tradicional, no aplica a Alimentar Comunidad, se
    completa después de asignar un programa de Abordaje y se mantiene al
    cambiar de línea.
11. "Datos de Convenio" es uno por proyecto: número de convenio, fecha, meses,
    monto total, componente alimentario, componente gastos generales,
    componente SIPH, componente gasto bancario e Imprevistos (este último
    solo en Línea Tradicional).
12. Todos los montos se cargan a mano. Si la suma de componentes no coincide
    con el monto total se muestra una advertencia que no impide guardar.
    Formato de visualización: `$100.000.000`.
13. Proyectos, Datos de Convenio y Rendiciones son propios de cada línea. La
    columna "Conv." de Rendiciones sigue siendo el orden (1, 2, 3). Cómo se
    asigna cada rendición a una línea: definición 23.
14. La organización determina el programa de sus comedores: para elegir el
    programa al crear un comedor, ese programa tiene que estar cargado antes
    en la organización. Es la misma lógica que ya funciona con los proyectos,
    que deben estar dados de alta en la organización antes de asociarse a un
    comedor. Al dar de alta un comedor se elige primero la organización; de
    ella salen los proyectos dados de alta y, de cada proyecto, su línea.
15. Los datos existentes se completan con una carga inicial versionada en el
    repo (migración de datos idempotente de la Etapa 1), igual en QA,
    homologación y producción. Reemplaza la query manual prevista antes de la
    revisión del PR #2746 (21/10/2026).
16. Región y Subzona ("Aglomerado/Subzona") se eligen de un desplegable. El
    listado confirmado el 20/10/2026 está en el Anexo A.
17. No se agregan permisos ni grupos: las acciones nuevas usan los permisos
    que existen hoy.
18. Carga inicial de los programas de cada organización: los programas de
    todos los comedores asociados a ella (`Comedor.programa` de los comedores
    con `organizacion` igual a esa organización), incluidos los dados de baja.
    Esta regla se usa solo para la carga inicial; en pantalla no se deducen
    programas.
19. Una organización sin programas cargados muestra solo Datos de la
    Organización y el aviso "Sin programas asignados".
20. Subzona depende de Región: el desplegable de Subzona se filtra por la
    Región elegida (el listado del Anexo A asigna cada subzona a una región).
21. Al dar de alta un proyecto en la organización se le asigna una línea
    (Línea Secos o Línea Tradicional) entre los programas de Abordaje que
    tenga la organización. La línea queda guardada en el proyecto; no se
    deduce de los comedores.
22. Mientras una organización no tenga programas cargados, las reglas nuevas
    no bloquean: el alta y la edición de comedores y firmantes funcionan como
    hoy. Las reglas se aplican desde que la organización tiene al menos un
    programa.
23. La línea de una rendición es la que guarda la propia rendición
    (`RendicionCuentaMensual.linea_programatica`, que hoy se toma del comedor
    al crearla). Cada pestaña de línea muestra las rendiciones de la
    organización con esa línea, tengan o no proyecto. El filtro por proyecto
    funciona dentro de la línea. Si una rendición tiene una línea distinta a
    la de su proyecto, se muestra en la pestaña de su propia línea.
24. El convenio se carga con el mismo permiso que hoy permite editar
    firmantes y avales (`organizaciones.view_organizacion`). Es un permiso de
    lectura que habilita escritura; se acepta como riesgo conocido para no
    sumar permisos (definición 17).

### 1.3 Cambios de datos

Restricción de arquitectura verificada: `Organizacion` y
`ProyectoOrganizacion` viven en el kernel (`src/backends/kernel/organizaciones/`)
y `Programas` en el vertical Comedores (`src/backends/comedores/comedores/`).
El kernel no puede depender de verticales (contrato
`kernel-no-core-ni-backends`, ver `docs/desarrollo/verticales_independientes.md`).
Por eso `Firmante` ya vive en `gestion_organizaciones`. Todo lo nuevo que
dependa de `Programas` va en
`src/backends/comedores/gestion_organizaciones/` (aprobado el 20/10/2026).

Nombres propuestos (se confirman en la decisión técnica):

| Modelo nuevo | Campos | Reglas |
| --- | --- | --- |
| `ProgramaOrganizacion` | `organizacion` (FK `organizaciones.Organizacion`), `programa` (FK `comedores.Programas`) | Único por par organización–programa |
| `LineaProyecto` | `proyecto` (1:1 `organizaciones.ProyectoOrganizacion`), `programa` (FK `comedores.Programas`) | El programa debe ser Línea Secos o Línea Tradicional y estar en los programas de la organización del proyecto |
| `RegionAbordaje` | `nombre` | Único. Catálogo del Anexo A |
| `SubzonaAbordaje` | `region` (FK `RegionAbordaje`), `nombre` | Único por región. Catálogo del Anexo A |
| `DatosRegionOrganizacion` | `organizacion` (1:1), `region` (FK), `subzona` (FK) | La subzona debe pertenecer a la región. Solo si la organización tiene un programa de Abordaje |
| `ConvenioProyecto` | `proyecto` (1:1), `numero`, `fecha`, `meses`, `monto_total`, `componente_alimentario`, `componente_gastos_generales`, `componente_siph`, `componente_gasto_bancario`, `imprevistos` | Montos `DecimalField(max_digits=14, decimal_places=2)`. `imprevistos` opcional y solo para Línea Tradicional. Suma distinta del total: advertencia, no error |

| Dato existente | Hoy | Cambio |
| --- | --- | --- |
| Firmantes | `Firmante.programa` (FK opcional) | Sin cambio de modelo; el formulario limita el programa a los de la organización |
| Territorial | `Organizacion.territoriales_abordaje_comunitario` (kernel) | Sin cambio de dato; se muestra en Datos de Región |
| Programa del comedor | `Comedor.programa` libre | El formulario lo limita a los programas de la organización |
| Proyecto del comedor | `Comedor.proyecto` filtrado por organización | Además, debe coincidir con la línea del programa del comedor |
| Rendiciones | `RendicionCuentaMensual.proyecto` y `linea_programatica` | Sin cambio de modelo; el servicio filtra por `linea_programatica` (definición 23) |
| Documentación | `DocumentacionOrganizacion` / `ArchivoOrganizacion` | Sin cambio de modelo; solo se muestra en Alimentar |

### 1.4 Cambios de pantalla (variante B v3)

- Encabezado: nombre, Historial / Editar / Eliminar y selector de programa.
- Card "Datos de la Organización", común.
- Franja del programa elegido.
- Alimentar Comunidad: Firmantes, Comedores Asociados (con Ver, badges
  CARITAS y validación, contador) y Documentación con sus cinco columnas.
- Línea Secos / Línea Tradicional: selector "Información del programa" /
  "Rendiciones Presentadas". Información: Proyectos (con editar), Datos de
  Región (con editar), Datos de Convenio por proyecto, Firmantes, Espacios
  Asociados. Rendiciones: cuadro a todo el ancho con filtro por proyecto.
- Edición de la organización: Programas, proyectos con línea y Datos de
  Región. Pantalla nueva: Datos de Convenio por proyecto.
- Formularios existentes que cambian: Firmante y Comedor.

### 1.5 Hechos del código que condicionan la implementación

- Los proyectos no tienen pantalla propia: se cargan en la edición de la
  organización como lista de códigos separados por coma (campo oculto
  `codigos_proyecto` de `OrganizacionForm` en
  `src/backends/comedores/gestion_organizaciones/forms.py`). Al guardar se
  crean o reactivan con `update_or_create` y se desactivan los que no están.
- El formulario de comedor pide los proyectos de la organización por AJAX
  (`proyectos_organizacion_ajax`, URL `organizacion_proyectos_ajax`) y valida
  el proyecto en `ComedorForm.clean`
  (`src/backends/comedores/comedores/forms/comedor_form.py`).
- Los programas se reconocen comparando el nombre del registro elegido en el
  desplegable, con funciones de `src/backends/comedores/comedores/utils.py`.
  `permite_codigo_de_proyecto(programa)` recibe un programa, pero
  `is_abordaje_comunitario_linea_secos_program` e
  `is_abordaje_comunitario_linea_tradicional_program` reciben un **comedor**
  (leen `comedor.programa.nombre`): pasarles un `Programas` devuelve `False`
  sin error. Hay que agregar variantes que reciban el programa, siguiendo el
  patrón de `permite_codigo_de_proyecto`, y que las funciones actuales las
  usen por dentro. No se agrega un campo nuevo.
- Hay dos fuentes de código de proyecto: `ProyectoOrganizacion` y
  `Comedor.codigo_de_proyecto` (texto). `RendicionesOrganizacionService.obtener_proyectos`
  combina ambas. Para listar proyectos por línea se usa `LineaProyecto`.
- Cada rendición guarda su línea en `RendicionCuentaMensual.linea_programatica`
  (`secos` o `tradicional`, por defecto `tradicional`; al crearla se infiere
  del comedor). `RendicionesOrganizacionService.obtener_rendiciones` trae
  también rendiciones sin proyecto, vía `comedor__organizacion`.
- Todo lo que entra a `development` viaja junto a homologación y `main`: no
  hay feature flag que frene una etapa. Por eso la carga inicial va en la
  Etapa 1 y las reglas nuevas no bloquean a organizaciones sin programas
  (definiciones 15 y 22).
- Las vistas de organización, firmante y aval exigen
  `organizaciones.view_organizacion` (`permissions_any_required`), y el legajo
  muestra Editar con `_puede_ver_todas_las_organizaciones`. Las acciones
  nuevas usan esos mismos controles; para el convenio es un riesgo aceptado
  (definición 24).
- El acceso al legajo ya se filtra por dupla
  (`_filtrar_organizaciones_por_dupla`); este plan no lo cambia.
- Firmante registra auditoría en
  `src/backends/comedores/gestion_organizaciones/audit_signals.py`.

### 1.6 Fuera de alcance

- Completar a mano Región, Subzona y Datos de Convenio de organizaciones y
  proyectos existentes: la carga inicial solo cubre programas y líneas.
- Cambios en la app mobile/PWA o en rendiciones más allá del filtro por línea.
- Corregir rendiciones cuya línea no coincide con la de su proyecto.
- Unificar las dos fuentes de código de proyecto.

## 2. Roadmap de implementación

Reglas para todas las etapas:

- Un PR por etapa contra `development` (la Etapa 1 se puede partir en dos).
  Commits en español con `<type>(<scope>): <subject>`.
- Cada PR: tests del módulo, `black`, `pylint` de los archivos tocados,
  `djlint` si hay templates, e `import-linter` sin violaciones.
- Cada PR con cambio visible o de datos suma su registro en
  `docs/registro/cambios/2026-T4/` (skill `registro-cambios`).
- Antes de abrir cada PR: `git fetch origin` y rebase sobre
  `origin/development`.
- Ninguna etapa cambia permisos, grupos ni el filtro de acceso por dupla.

Comandos de referencia (de `CLAUDE.md`):

```bash
docker compose exec django pytest src/backends/comedores/gestion_organizaciones -v
docker compose exec django pytest src/backends/comedores/tests -k organizacion -v
docker compose exec django pytest -n auto
black <archivos>
pylint <archivos>
djlint src/backends/comedores/gestion_organizaciones/templates/ --check
```

### Etapa 0 — Decisión técnica (bloquea todo lo demás)

Objetivo: dejar registrada y revisada la decisión de arquitectura.

1. Escribir
   `docs/registro/decisiones/2026-10-20-2745-legajo-organizacion-por-programa.md`
   con: modelos nuevos en `gestion_organizaciones`, línea del proyecto en una
   tabla nueva 1:1 (no mover `ProyectoOrganizacion` ni agregarle una FK desde
   el kernel), catálogo de Región/Subzona por migración de datos, reutilizar
   las funciones de `comedores/utils.py` para reconocer programas y reutilizar
   permisos existentes.
2. Recorrer el checklist 1 de `docs/desarrollo/verticales_independientes.md`
   (skill `verticales-checklist`) y dejar el resultado en la decisión.
3. Revisión en el PR de documentación (#2746). La decisión queda en
   "propuesta" hasta que se apruebe.

Hecho cuando: PR #2746 aprobado y mergeado. El primer PR de código pasa la
decisión a "aceptada".

### Etapa 1 — Modelos, migraciones y catálogo (sin cambios de pantalla)

Archivos: `src/backends/comedores/gestion_organizaciones/models.py`,
`admin.py`, `migrations/` y tests nuevos en
`src/backends/comedores/gestion_organizaciones/tests/`.

1. Crear los seis modelos de la sección 1.3 con sus restricciones
   (`UniqueConstraint`) y validaciones en `clean()` (subzona de la región,
   línea válida, imprevistos solo en Tradicional).
2. Migración de esquema (`makemigrations gestion_organizaciones`), solo
   aditiva: no toca tablas existentes.
3. Migración de datos aparte que carga las 5 regiones y 28 subzonas del
   Anexo A, con función de reversa.
4. Migración de datos de carga inicial (definiciones 15 y 18), idempotente y
   con reversa:
   - crea un `ProgramaOrganizacion` por cada programa distinto de los
     comedores de cada organización, incluidos los dados de baja;
   - asigna `LineaProyecto` a los proyectos existentes cuando todos los
     comedores que los usan (`Comedor.proyecto`) tienen el mismo programa de
     Abordaje; los demás quedan sin línea y se completan desde la edición de
     la organización (propuesta, a confirmar con el área usuaria);
   - no borra ni modifica registros existentes: volver a correrla no duplica.
5. Registrar los modelos en el admin (catálogos editables para corregirlos
   sin deploy).
6. Auditoría: agregar señales para `ProgramaOrganizacion`, `LineaProyecto`,
   `DatosRegionOrganizacion` y `ConvenioProyecto` siguiendo el patrón de
   `audit_signals.py`, para que aparezcan en Historial.
7. Tests: restricciones únicas, validaciones de `clean()`, que la migración
   del catálogo deja 5 regiones y 28 subzonas, y que la carga inicial crea los
   programas esperados (con comedores activos y dados de baja), asigna línea
   solo a proyectos sin ambigüedad y no duplica al correrse dos veces.

Hecho cuando: migraciones aplicadas con el migrador (grafo completo), tests
en verde, sin cambios visibles para el usuario. Al desplegarse, todas las
organizaciones con comedores ya tienen programas.

### Etapa 2 — Servicios

Paquete nuevo `services` dentro de
`src/backends/comedores/gestion_organizaciones/` (hoy la app no lo tiene).
Funciones propuestas:

0. En `src/backends/comedores/comedores/utils.py`: variantes que reciban un
   programa (por ejemplo `es_programa_linea_secos(programa)` y
   `es_programa_linea_tradicional(programa)`), con el patrón de
   `permite_codigo_de_proyecto(programa)`; las funciones actuales que reciben
   comedor pasan a usarlas por dentro sin cambiar su resultado.
1. `programas_de_organizacion(organizacion)`: programas cargados, en orden
   Alimentar, Secos, Tradicional.
2. `tiene_programa_abordaje(organizacion)` y
   `aplica_reglas_de_programa(organizacion)` (verdadero si la organización
   tiene al menos un programa cargado; definición 22).
3. `proyectos_por_linea(organizacion, programa)`: proyectos activos con esa
   línea.
4. `firmantes_por_programa(organizacion, programa)` y
   `comedores_por_programa(organizacion, programa)`.
5. Rendiciones por línea (definición 23): extender
   `RendicionesOrganizacionService.obtener_rendiciones`
   (`src/backends/comedores/rendicioncuentasmensual/services.py`) con un
   parámetro opcional `linea_programatica` que filtre por el campo de la
   rendición, conservando las rendiciones sin proyecto. El filtro por
   proyecto existente se combina con el de línea. Para el desplegable de
   proyectos de la pestaña, usar `proyectos_por_linea`. Sin el parámetro, el
   comportamiento actual no cambia.
6. `resumen_convenio(convenio)`: suma de componentes, si coincide con el total
   y la diferencia.
7. Filtro de template para montos `$100.000.000` (en
   `templatetags/` de la app).

Tests unitarios de cada función, incluidos: caso sin programa
(comportamiento actual intacto); las variantes de `utils.py` con un
`Programas` y las funciones actuales con un comedor dan el mismo resultado;
rendición sin proyecto aparece en su línea; rendición `secos` con proyecto
de línea Tradicional aparece en Secos; filtro de proyecto + línea.

Hecho cuando: servicios con tests en verde y sin uso todavía desde pantallas.

### Etapa 3 — Carga de datos en la organización

Archivos: `forms.py`, `views.py`, `urls.py` y templates de
`gestion_organizaciones`; `src/backends/config/url_registry.json`.

1. `OrganizacionForm`: campo "Programas" (selección múltiple de los tres
   programas). Al quitar un programa con proyectos, firmantes o comedores
   asociados, mostrar error y no permitirlo.
2. Proyectos con línea: reemplazar la lista de códigos (`codigos_proyecto`)
   por filas código + línea. Conservar la lógica actual de guardado
   (`update_or_create` y desactivar los que no están) y guardar la línea en
   `LineaProyecto`. La línea solo ofrece los programas de Abordaje elegidos
   en el mismo formulario. Proyectos existentes sin línea: se muestran con la
   línea vacía y la exigen al volver a guardar.
3. Datos de Región en el mismo formulario: Región y Subzona dependiente
   (Subzona filtrada por Región), visibles solo si hay un programa de
   Abordaje. Territorial sigue en su campo actual.
4. `FirmanteForm`: limitar `programa` a los programas de la organización. Si
   la organización no tiene programas, ofrecer todos, como hoy
   (definición 22).
5. Datos de Convenio: vistas CBV nuevas para cargar y editar el convenio de
   un proyecto (URL propuesta
   `organizaciones/proyectos/<int:proyecto_id>/convenio/`), con el mismo
   decorador de permisos que firmantes (riesgo aceptado, definición 24).
   Imprevistos solo si la línea es Tradicional; advertencia de suma sin
   bloquear el guardado.
6. Regenerar el registro de URLs:
   `DJANGO_SETTINGS_MODULE=config.settings_all python manage.py generar_registro_urls`.
7. Tests de formularios y vistas: alta y edición con y sin Abordaje,
   subzona de otra región, proyecto sin línea, firmante con programa ajeno,
   alta de firmante en una organización sin programas, convenio con y sin
   Imprevistos, advertencia de suma, usuario sin permiso.

Hecho cuando: se pueden cargar todos los datos nuevos desde la edición de la
organización y la pantalla de convenio; el legajo actual sigue igual.

### Etapa 4 — Regla Comedor–Organización

Archivos: `src/backends/comedores/comedores/forms/comedor_form.py`,
`proyectos_organizacion_ajax` en
`src/backends/comedores/gestion_organizaciones/views.py`, template
`src/backends/comedores/comedores/templates/comedor/comedor_form.html` y su JS.

1. Orden de selección (definición 14): organización → programas de la
   organización → proyectos de la línea elegida.
2. `programa`: solo los programas cargados en la organización. Si falta,
   mensaje: "La organización debe tener este programa cargado." (mismo estilo
   que el mensaje actual de proyectos).
3. `proyectos_organizacion_ajax`: devolver la línea de cada proyecto y
   aceptar un filtro opcional por programa, sin romper el uso actual.
4. `ComedorForm.clean`: validar que el proyecto pertenezca a la organización
   (ya existe) y que su línea coincida con el programa del comedor.
   Alimentar sigue sin proyecto.
5. Organización sin programas cargados (definición 22): no se aplica la
   regla de programa; el alta y la edición funcionan como hoy.
6. Comedores existentes cuyo programa no esté en su organización: la regla se
   aplica solo al cambiar organización, programa o proyecto; editar otros
   campos no se bloquea.
7. Revisar otros puntos que asignan programa o proyecto a un comedor (API
   territorial, PWA, importadores) y listar cuáles quedan fuera de la regla.
8. Tests: ampliar los del formulario de comedor existentes, incluidos alta
   de comedor en una organización sin programas (no bloquea), con programa
   ajeno (bloquea) y con proyecto de otra línea (bloquea).

Hecho cuando: no se puede asociar un comedor a un programa o proyecto que su
organización no tiene, las organizaciones sin programas siguen funcionando
como hoy y los comedores existentes se pueden seguir editando.

### Etapa 5 — Legajo nuevo (B v3)

Archivos: `OrganizacionDetailView` y template `organizacion_detail.html`
(dividido en partials por sección dentro de `templates/organizaciones/partials/`).

1. Contexto armado con los servicios de la Etapa 2; la vista no contiene
   reglas de negocio.
2. Programa y sección elegidos en la URL (`?programa=<id>` y
   `?seccion=info|rendiciones`), junto al `?proyecto=` actual de rendiciones,
   para que persistan al recargar o volver de un formulario. Programa
   inválido o ausente: el primero de la organización.
3. Orden de pantalla de B v3: encabezado, Datos de la Organización, franja
   del programa, selector Información / Rendiciones (solo Abordaje) y
   secciones.
4. Organización sin programas: solo Datos de la Organización y el aviso
   "Sin programas asignados".
5. Botones de editar de Proyectos y Región llevan a la edición de la
   organización (ancla a la sección); el de Convenio, a la pantalla nueva.
6. Proyectos sin línea (los que la carga inicial no pudo asignar): aviso en
   las pestañas de Abordaje con enlace a la edición de la organización.
7. Conservar estilos actuales (badges, botones, columnas de Documentación).
8. Tests de vista: organización con uno, dos y tres programas; sin
   programas; parámetro de programa inválido; Documentación solo en
   Alimentar; Rendiciones solo en Abordaje y filtradas por la línea de la
   rendición, incluidas las sin proyecto; aviso de proyectos sin línea;
   usuario sin permiso de edición no ve los botones.

Hecho cuando: el legajo coincide con B v3 para todas las combinaciones de
programas.

### Etapa 6 — Verificación de datos en homologación

La carga inicial ya no es un paso manual: viaja con la Etapa 1 como migración
de datos (definición 15) y las reglas no bloquean a organizaciones sin
programas (definición 22), así que no hay un orden de despliegue que cuidar.
Esta etapa solo verifica el resultado.

1. En homologación, después de desplegar la Etapa 1: contar organizaciones
   con comedores sin `ProgramaOrganizacion` (debe ser cero) y proyectos
   activos sin `LineaProyecto` (deben ser solo los ambiguos).
2. Revisar con el área usuaria una muestra de organizaciones con cada
   combinación de programas y completar la línea de los proyectos que
   quedaron sin asignar.
3. Repetir el conteo en producción después del despliegue.

Hecho cuando: los conteos dan lo esperado en homologación y producción.

### Etapa 7 — Cierre

1. Registro del cambio completo en `docs/registro/cambios/2026-T4/`, enlazado
   desde la decisión y este plan.
2. Actualizar `docs/ia/AGENT_REPO_MAP.md` si cambian módulos o flujos
   relevantes (por ejemplo, el paquete `services/` nuevo).
3. `python src/scripts/ci/check_docs_paths.py --existencia <archivo.md>` sobre
   los Markdown tocados.
4. `docker compose exec django pytest -n auto` completo.
5. Validación funcional con el área usuaria en homologación.

## 3. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Romper el boundary kernel/vertical | Todo lo nuevo en `gestion_organizaciones`; `import-linter` en cada PR |
| Etapas 3–5 en producción antes de que existan programas (no hay feature flag) | Carga inicial como migración en la Etapa 1 (definición 15) y reglas que no bloquean a organizaciones sin programas (definición 22) |
| Legajo vacío para organizaciones sin programas | La carga inicial cubre todas las que tienen comedores; aviso para las que no tienen |
| Proyectos existentes sin línea | La carga asigna los que no son ambiguos; el resto se completa desde la edición (aviso en el legajo) |
| Rendiciones sin proyecto o con línea distinta a la del proyecto | Manda la línea de la rendición (definición 23); tests de ambos casos |
| Escritura de montos de convenio con un permiso de lectura | Riesgo aceptado (definición 24); revisar si cambia la política de permisos |
| Funciones de `utils.py` que reciben comedor usadas con un programa | Variantes que reciben programa (Etapa 2, paso 0) con tests de equivalencia |
| Comedores existentes con programa fuera de su organización | Regla solo al cambiar organización, programa o proyecto |
| Doble fuente de código de proyecto | Filtrar por proyecto con línea, no por texto |
| Renombrar un programa desde el admin rompe su reconocimiento | Reutilizar las funciones de `utils.py` y no renombrar programas sin revisarlas |
| Errores en el catálogo de Región/Subzona | Cargar exactamente el Anexo A y testear 5 regiones y 28 subzonas |
| Sumar permisos o grupos por error | Reusar los controles existentes (definición 17); revisar en cada PR |
| Cambios de reglas que afecten API territorial o PWA | Paso 6 de la Etapa 4 antes de cerrar el PR |

## Anexo A — Región y Aglomerado/Subzona

Listado entregado por el área usuaria el 20/10/2026 (captura de planilla),
con dos correcciones confirmadas ese mismo día: se eliminó un "SAN JUAN"
duplicado y el nombre de la región es "CUYO PATAGONIA BAI" (en la captura
estaba cortado). Total: 5 regiones y 28 subzonas.

| Región | Aglomerado/Subzona |
| --- | --- |
| AGBA | CABA NORTE y OTROS |
| AGBA | NOROESTE |
| AGBA | SUR ESTE |
| AGBA | OESTE (LM) |
| CENTRO | CONCORDIA |
| CENTRO | CORDOBA |
| CENTRO | PARANA |
| CENTRO | ROSARIO |
| CENTRO | SANTA FE |
| CUYO PATAGONIA BAI | BARILOCHE |
| CUYO PATAGONIA BAI | LA PLATA |
| CUYO PATAGONIA BAI | MAR DEL PLATA |
| CUYO PATAGONIA BAI | MENDOZA |
| CUYO PATAGONIA BAI | SAN JUAN |
| CUYO PATAGONIA BAI | NEUQUEN |
| CUYO PATAGONIA BAI | RIO NEGRO |
| CUYO PATAGONIA BAI | LA PAMPA |
| CUYO PATAGONIA BAI | SAN LUIS |
| NEA | CORRIENTES |
| NEA | FORMOSA |
| NEA | MISIONES |
| NEA | CHACO |
| NOA | CATAMARCA |
| NOA | JUJUY |
| NOA | SALTA |
| NOA | SANTIAGO DEL ESTERO |
| NOA | TUCUMAN |
| NOA | LA RIOJA |
