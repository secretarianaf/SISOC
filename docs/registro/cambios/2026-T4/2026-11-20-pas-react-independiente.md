# Frontend independiente de PAS

## Alcance

El back office React vive en `src/frontends/apps/pas-backoffice/` y se sirve
en `/v2/pas/` con su propio build y contenedor nginx, como INET y VPSL.
El workspace declara las dependencias de UI, router y consultas ya presentes
en el monorepo. El portal público de DDJJ conserva su app y rutas.

## Comportamiento

El layout institucional compartido aporta navegación y modo claro y oscuro.
El padrón, ficha, formación, cruces, liquidación e informes consultan
`/api/web/pas/` y la sesión web existente. El proxy autenticado de Django
sirve la SPA. Las reglas de negocio y permisos siguen en sus APIs.

La SPA incluye alta, edición, cambio de estado, importación CSV, filtros y
paginación de Formación, operaciones SINTyS y RENAPER, y consulta,
previsualización y generación de informes. Las descargas y la confirmación
de eliminación usan las rutas nativas y mantienen sus permisos. Mesa de
Ayuda queda fuera del menú de PAS. La fuente de Formación, el tablero
agregado y la preliquidación conservan las limitaciones del backend vigente.

## Arranque local

```powershell
docker compose up -d --build front_pas
```

La configuración del proxy y el Dockerfile compartido requieren revisión
técnica. Para un entorno con `DEBUG=False`, el origen de PAS se habilita
explícitamente con `FRONT_PAS_ORIGIN`.

## Composición del panel

La entrada abre el padrón junto a la ficha con cuatro pestañas. Las tarjetas de circuito se mantienen visibles durante la navegación. Formación muestra sus indicadores y cursos en tabla. Cruces muestra el circuito mensual, la bandeja de incompatibilidades y permite exportar el padrón e importar el retorno SINTyS con el permiso vigente. El reporte presenta el total que informa PAS y la liquidación conserva el bloqueo del sistema vigente.


La revisión manual de Figma ajustó la geometría del menú, las tarjetas y la ficha, el resaltado de las pestañas, el agrupamiento de DDJJ y las constancias de Formación. Los importes y campos financieros de las referencias requieren datos del backend.

El menú agrupa Panel de control, Dashboard e Informes bajo PAS. El dashboard conserva la composición de indicadores y paneles con los datos disponibles. La grilla de preliquidación muestra sus columnas y el aviso de que el circuito todavía no entrega filas.


Formación y la ficha mantienen visible la tabla de cursos cuando no hay registros. La fila vacía distingue la falta de selección de la ausencia de cursos del titular.


La ficha agrupa identidad, contacto y domicilio, presenta las versiones de DDJJ y muestra los eventos como línea de tiempo. Formación destaca el titular seleccionado. Cruces agrupa los registros por categoría y permite buscar al titular en el padrón desde la alerta.


El Figma y el libro de marca gobiernan la composición. Las acciones que no aparecen en sus pantallas quedan en menús contextuales del padrón, la ficha y Cruces. Los filtros avanzados de Formación se muestran a demanda.


## Alineación con el Figma de PAS (24/11/2026)

Las pantallas se revisaron contra el archivo de Figma de PAS (10 pantallas,
claro y oscuro) y la documentación de UX: `theme.ts` v5,
`especificacion-theme.md`, `nucleo-componentes.md`, `nucleo-implementacion.md`
y `modulo-pas.md`. Los tokens de `@sisoc/ui` ya coincidían con el theme v5,
así que no se tocó el paquete compartido.

- **Navegación:** el menú sigue el patrón de INET (Tus módulos, Módulos, PAS y
  sus tareas, con íconos) y suma Cerrar sesión. Las tarjetas 01 a 04 usan los
  textos de Figma y el contador de alertas de Cruces sale de sus
  incompatibilidades.
- **Componentes:** las composiciones `Sisoc/*` de PAS viven en
  `src/frontends/apps/pas-backoffice/src/componentes.tsx`: State chip con punto,
  Score chip, Data field, Alert message con progreso circular, Data check row,
  Status row y Pending row. Stat card sale de `@sisoc/ui`.
- **Formación:** el semáforo y el Score chip aplican la regla de severidad (sin
  puntos es error, no info). La tabla de cursos pagina con `TablePagination`.
- **Dashboard:** Estado operativo y Requieren atención usan el circuito de
  Cruces. Los Select de Provincia y Período se ven deshabilitados porque el
  backend no desagrega. "Exportar información filtrada" lleva a la generación
  de informes. Este destino es un supuesto, porque UX lo tiene como pendiente.

Sin fuente en el backend, y por eso sin dibujar: los chips DDJJ y FCH de la
tarjeta de titular, el contador de la tarjeta 01, la fecha de sincronización
del Portal FCH, las barras de cumplimiento y distribución (`Sisoc/Bar row`) y
las filas de preliquidación con `Sisoc/Check result`. Administración y Tableros
no figuran en el menú, igual que en INET, porque sus destinos son del shell de
SISOC.

## Buscador PAS en v2

`/v2/pas/buscador` es la versión v2 de `pas/persona_list.html` y de
`src/frontends/apps/sisoc/src/routes/pasBuscador.tsx`. Usa la misma API
`/api/web/pas/personas/` y conserva la búsqueda por texto, el estado, la tabla
con avisos, la paginación numerada, Importar titulares, Exportar tokens y el
acceso a Informes, cada uno con su permiso vigente. Cada fila abre la ficha en
el Panel de control. Se llega desde el menú (PAS › Buscador PAS) y desde las
acciones del padrón. Las URLs nativas `/pas/listar` no cambian.
