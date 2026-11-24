# Cambio: convenio, documentos, firmantes/avales y rendiciones de organización en React sobre G1 v1 (#2785, O01 a O04)

## Alcance

Entrega de O01 a O04 del
[contrato M2](../../../plans/2026-T4/2026-11-10-2785-organizaciones-convenio-documentos-firmantes-rendiciones-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md)
y el legajo de O05
([registro](2026-11-11-2785-react-organizaciones-listado.md)). Las secciones del
legajo que O05 mostraba como fragmento nativo pasan a componentes React, una
por sección y en el orden del contrato, y las páginas propias de cada familia
también:

| Unidad | Páginas React | Sección del legajo |
|---|---|---|
| O01 convenio | `/organizaciones/proyectos/<id>/convenio/` | «Datos de Convenio» (`legajo/convenios.html`) |
| O02 documentos | `/organizaciones/<id>/documentacion/<doc>/historial/` | «Documentación de la Organización», con subida, estado, vencimiento, GDE y documentación adicional |
| O03 firmantes y avales | `/organizaciones/firmante/{crear,editar,eliminar}/<id>` y `/organizaciones/aval/{crear,editar,eliminar}/<id>` | tablas «Firmantes» |
| O04 rendiciones | `/organizaciones/<id>/rendiciones/<pk>/detalle/` | tabla de rendiciones y filtro «Código de Proyecto» |

No cambia vistas, formularios, servicios, modelos, plantillas, JavaScript ni
URLs nativas. No activa React en producción. El acceso sigue siendo el de hoy
(ver [brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)).

> Actualización (O2-U5): el legajo ya no usa `sections` ni marcadores `data-legajo-seccion`;
> la API devuelve la página completa como datos y cada sección viaja dentro de `blocks`
> (ver [el registro del legajo](2026-11-13-2785-react-organizaciones-legajo-datos.md)).
> Las secciones, sus constructores y sus componentes son los descritos abajo.

## Cómo funciona

- **Secciones del legajo.** `OrganizacionLegajoWebView` sigue ejecutando
  `OrganizacionDetailView` y renderizando el bloque `content` de la plantilla.
  `web_api_secciones.py` reemplaza cada `{% include %}` que tiene un
  constructor registrado por `<div data-legajo-seccion="N"></div>` y agrega al
  JSON `sections` los datos calculados con el mismo contexto que habría recibido
  el parcial (variables de `with` incluidas). Los includes sin constructor
  conservan su HTML nativo. `organizacionesLegajo.tsx` monta cada componente
  React en su marcador con un portal; el HTML nativo alrededor no cambia.
- **Páginas de cada familia.** Cada endpoint ejecuta la vista nativa
  (`ConvenioProyectoView`, `FirmanteCreateView`/`UpdateView`/`DeleteView` y sus
  equivalentes de aval, `OrganizacionRendicionDetailView`) o la función nativa
  de documentos: mismas validaciones, efectos, mensajes y textos de error de
  Django. Las respuestas nativas de documentos traen una fila HTML; la API la
  descarta y devuelve la fila como datos (`fila`).
- **Convenio.** GET/POST `proyectos/<proyecto_id>/convenio/`; el proyecto sin
  línea responde 409 con el mensaje nativo y su destino
  (`/organizaciones/editar/<id>`); los decimales viajan como texto y React suma
  centavos solo para el aviso en pantalla, como el script nativo.
- **Documentos.** `<id>/documentacion/<doc>/historial/`, `.../subir/`,
  `<id>/documentacion/personalizada/` y `documentacion/<archivo>/{estado,vencimiento,numero-gde}/`.
  Subir sobre un documento no aceptado reemplaza el registro, sobre uno aceptado
  crea otro; el GDE se replica a las admisiones por el servicio nativo. La
  subida es un solo POST con progreso y sin reintento. Ya no se carga
  `organizacionesDocumentos.js` en el legajo.
- **Firmantes y avales.** `<id>/{firmantes,avales}/formulario/`,
  `<id>/{firmantes,avales}/`, `{firmantes,avales}/<pk>/{formulario/,,baja/}`. La
  organización del alta sale del campo `organizacion_id` del cuerpo, como en la
  vista nativa (el id de la URL solo arma el formulario).
- **Rendiciones.** `<id>/rendiciones/<pk>/`. La descarga del PDF (O04.02) no
  tiene API propia: React llama a los endpoints del trabajo de
  `rendicioncuentasmensual` como el script nativo (un POST, consulta cada 3 s,
  15 minutos como máximo, sin reintentar el POST).
- **Entradas locales.** `web_preview.py` suma las entradas sin montar de las
  páginas nuevas, con el decorador de ruta y la búsqueda nativos (el convenio sin
  línea redirige con su mensaje antes de servir React).

## Archivos

- Backend (`src/backends/comedores/gestion_organizaciones/`): `web_api_secciones.py`,
  `web_api_convenio.py`, `web_api_documentos.py`, `web_api_firmantes.py`,
  `web_api_rendiciones.py`; editados `web_api.py` (secciones, sin scripts),
  `web_api_urls.py` y `web_preview.py`; `src/backends/config/middlewares/admindocs.py`
  y `src/backends/config/url_registry.json` (regenerado con
  `generar_registro_urls`).
- Frontend (`src/frontends/apps/sisoc/src/routes/`): `organizacionConvenio.tsx`,
  `organizacionDocumentos.tsx`, `organizacionFirmantes.tsx`,
  `organizacionRendiciones.tsx` con sus pruebas; editados
  `organizacionesLegajo.tsx` (portales), `organizacionesForm.tsx` (exporta
  `CrispyField` y `Message`), `organizacionesBaja.tsx` (exporta
  `CascadePreview`) e `index.ts`.
- Pruebas backend: `test_web_organizaciones_convenio_api.py`,
  `test_web_organizaciones_documentos_api.py`,
  `test_web_organizaciones_firmantes_api.py`,
  `test_web_organizaciones_rendiciones_api.py` y
  `test_web_preview_organizaciones_secciones.py`; ajustado
  `test_web_organizaciones_legajo_api.py` (el fragmento es el bloque nativo salvo
  los marcadores de sección; `scripts` vacío).

## Verificación

Entorno sintético, sin red, imagen fijada. Backend: las pruebas nuevas fallan
sobre la base (10, 20, 17 y 8 fallos por unidad, sin ruta) y pasan con el
cambio. Frontend: pruebas con módulo inexistente en la base y en verde con el
cambio. Los resultados de las corridas completas (suites, `black`, `pylint`,
Vitest, `tsc`, ESLint, build) y de la verificación visual están en el informe de
entrega de la ola.

## Limitaciones

- **Avales en el legajo.** La tabla «Avales» es marcado en línea de
  `organizacion_detail.html`, no un include: sigue como HTML nativo dentro del
  legajo. Sus páginas (alta, edición, baja) sí son React.
- **Cabecera, selector de programa y datos de la organización** del legajo siguen
  como HTML nativo (O05.01).
- **Rasgos nativos conservados por paridad:** el alta de firmante toma la
  organización del cuerpo sin validar pertenencia; la regla `rol == "aval"` de
  `FirmanteForm.clean` nunca se cumple; la barra superior del alta de firmante y
  aval trae un ancla vacía (`<a href="" class="btn btn-submit">`); la baja de
  firmante y aval muestra migas sin texto (la vista usa `label` donde el
  componente lee `text`); archivos y actas se sirven por URL de media directa;
  convenio sin alcance de dupla.
- La descarga del PDF depende de los endpoints de `rendicioncuentasmensual`;
  si esa familia mueve el trabajo a `/api/web/comedores/`, O04.02 la sigue.
