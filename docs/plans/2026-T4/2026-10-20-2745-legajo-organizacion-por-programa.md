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
13. Proyectos, Datos de Convenio y Rendiciones son propios de cada línea; las
    rendiciones se filtran por los proyectos de la línea. La columna "Conv." de
    Rendiciones sigue siendo el orden (1, 2, 3).
14. La organización determina el programa de sus comedores: para elegir el
    programa al crear un comedor, ese programa tiene que estar cargado antes
    en la organización. Es la misma lógica que ya funciona con los proyectos,
    que deben estar dados de alta en la organización antes de asociarse a un
    comedor. Al dar de alta un comedor se elige primero la organización; de
    ella salen los proyectos dados de alta y, de cada proyecto, su línea.
15. Los datos existentes se completarán por query después de implementar; no
    forma parte de este desarrollo.
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
| Rendiciones | `RendicionCuentaMensual.proyecto` y `linea_programatica` | Sin cambio de modelo; el servicio filtra por proyectos de la línea |
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
  desplegable, con funciones de `src/backends/comedores/comedores/utils.py`
  (`permite_codigo_de_proyecto`,
  `is_abordaje_comunitario_linea_secos_program`,
  `is_abordaje_comunitario_linea_tradicional_program`). Se reutilizan; no se
  agrega un campo nuevo.
- Hay dos fuentes de código de proyecto: `ProyectoOrganizacion` y
  `Comedor.codigo_de_proyecto` (texto). `RendicionesOrganizacionService.obtener_proyectos`
  combina ambas. Para filtrar por línea se usa el proyecto con línea.
- Las vistas de organización, firmante y aval exigen
  `organizaciones.view_organizacion` (`permissions_any_required`), y el legajo
  muestra Editar con `_puede_ver_todas_las_organizaciones`. Las acciones
  nuevas usan esos mismos controles.
- El acceso al legajo ya se filtra por dupla
  (`_filtrar_organizaciones_por_dupla`); este plan no lo cambia.
- Firmante registra auditoría en
  `src/backends/comedores/gestion_organizaciones/audit_signals.py`.

### 1.6 Fuera de alcance

- Completar programas, líneas y datos de organizaciones existentes (se hará
  por query, definición 15).
- Cambios en la app mobile/PWA o en rendiciones más allá del filtro por línea.
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
3. Revisión de una persona técnica del equipo. Hasta entonces la decisión
   queda en estado "propuesta".

Hecho cuando: decisión en estado "aceptada".

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
4. Registrar los modelos en el admin (catálogos editables para corregirlos
   sin deploy).
5. Auditoría: agregar señales para `ProgramaOrganizacion`, `LineaProyecto`,
   `DatosRegionOrganizacion` y `ConvenioProyecto` siguiendo el patrón de
   `audit_signals.py`, para que aparezcan en Historial.
6. Tests: restricciones únicas, validaciones de `clean()`, y que la
   migración de datos deja 5 regiones y 28 subzonas.

Hecho cuando: migraciones aplicadas con el migrador (grafo completo), tests
en verde, sin cambios visibles para el usuario.

### Etapa 2 — Servicios

Paquete nuevo `services` dentro de
`src/backends/comedores/gestion_organizaciones/` (hoy la app no lo tiene).
Funciones propuestas:

1. `programas_de_organizacion(organizacion)`: programas cargados, en orden
   Alimentar, Secos, Tradicional.
2. `tiene_programa_abordaje(organizacion)`.
3. `proyectos_por_linea(organizacion, programa)`: proyectos activos con esa
   línea.
4. `firmantes_por_programa(organizacion, programa)` y
   `comedores_por_programa(organizacion, programa)`.
5. Rendiciones por línea: extender
   `RendicionesOrganizacionService.obtener_proyectos` y `obtener_rendiciones`
   (`src/backends/comedores/rendicioncuentasmensual/services.py`) con un
   parámetro opcional de programa, sin cambiar el comportamiento actual
   cuando no se pasa.
6. `resumen_convenio(convenio)`: suma de componentes, si coincide con el total
   y la diferencia.
7. Filtro de template para montos `$100.000.000` (en
   `templatetags/` de la app).

Tests unitarios de cada función, incluido el caso sin programa (comportamiento
actual intacto).

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
4. `FirmanteForm`: limitar `programa` a los programas de la organización.
5. Datos de Convenio: vistas CBV nuevas para cargar y editar el convenio de
   un proyecto (URL propuesta
   `organizaciones/proyectos/<int:proyecto_id>/convenio/`), con el mismo
   decorador de permisos que firmantes. Imprevistos solo si la línea es
   Tradicional; advertencia de suma sin bloquear el guardado.
6. Regenerar el registro de URLs:
   `DJANGO_SETTINGS_MODULE=config.settings_all python manage.py generar_registro_urls`.
7. Tests de formularios y vistas: alta y edición con y sin Abordaje,
   subzona de otra región, proyecto sin línea, firmante con programa ajeno,
   convenio con y sin Imprevistos, advertencia de suma, usuario sin permiso.

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
5. Comedores existentes cuyo programa no esté en su organización: la regla se
   aplica solo al cambiar organización, programa o proyecto; editar otros
   campos no se bloquea.
6. Revisar otros puntos que asignan programa o proyecto a un comedor (API
   territorial, PWA, importadores) y listar cuáles quedan fuera de la regla.
7. Tests: ampliar los del formulario de comedor existentes.

Hecho cuando: no se puede asociar un comedor a un programa o proyecto que su
organización no tiene, y los comedores existentes se pueden seguir editando.

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
6. Conservar estilos actuales (badges, botones, columnas de Documentación).
7. Tests de vista: organización con uno, dos y tres programas; sin
   programas; parámetro de programa inválido; Documentación solo en
   Alimentar; Rendiciones solo en Abordaje y filtradas por línea; usuario sin
   permiso de edición no ve los botones.

Hecho cuando: el legajo coincide con B v3 para todas las combinaciones de
programas.

### Etapa 6 — Datos existentes y habilitación

1. Query de carga inicial (fuera de este desarrollo, definición 15):
   programas de cada organización a partir de todos sus comedores, incluidos
   los dados de baja (definición 18). Proyectos existentes: completar su
   línea.
2. Correrla primero en homologación y revisar una muestra de organizaciones
   con cada combinación de programas.
3. Desplegar las Etapas 1 a 5 a producción solo después de la carga, para que
   el legajo no aparezca vacío.

Hecho cuando: todas las organizaciones con comedores tienen programas y
todos los proyectos activos tienen línea.

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
| Legajo vacío para organizaciones sin programas | Carga inicial desde los comedores (definición 18) antes de desplegar; aviso para las que no tienen comedores |
| Proyectos existentes sin línea | Completarlos en la carga inicial; el formulario la exige al volver a guardar |
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
