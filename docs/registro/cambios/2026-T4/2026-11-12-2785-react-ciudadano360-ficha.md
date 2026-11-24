# Cambio: ficha Ciudadano 360 completa en React (#2785, C05.01)

## Qué cambia

- **API.** `GET /api/web/ciudadanos/<pk>/` (`ciudadanos/web_api.py`) suma a lo que ya
  entregaba (encabezado y lista `aportes`) la proyección `ciudadanos/web_ficha.py`:
  `identidad` (aviso de «Sin DNI», «RENAPER no validado» o «Requiere revisión»),
  `acciones` (enlaces de Historial, Editar, Dar de baja y Agregar familiar; Historial
  solo con `auditlog.view_logentry`), `datos` (todos los campos de «Datos
  Personales» ya formateados con las reglas del template: `default:'-'`, fechas
  `d/m/Y` y `d/m/Y H:i` en hora local), `mapa` y `foto_url`, `familia` (mismo
  orden que `CiudadanosDetailView.build_familia`), `historial` (series de
  `get_historial_context`), `interacciones` (las 10 últimas, estado `completo`,
  `en_plan` o `pendiente`), `observaciones` y `messages` (mensajes de Django en
  cola, consumidos una sola vez como en la página nativa). La vista nativa no
  cambia: la API la instancia con `setup()` y reutiliza sus métodos, sin llamar a
  `get_context_data` (los aportes ya viajan por `web_aportes`).
- **React.** `routes/ciudadano360.tsx` arma la ficha completa y
  `routes/ciudadano360Ficha.tsx` trae las secciones: encabezado con acciones, aviso
  de identidad, las once pestañas (Bootstrap sin su script: clic y flechas, con
  `role`, `aria-selected` y `tabindex` como los pone Bootstrap al cargar), Datos
  Personales (mapa, foto o marcador), Grupo Familiar, el gráfico de historial
  (Chart.js 3.9.1 desde el mismo CDN que usa el template, redibujado al cambiar de
  mes), las tarjetas de programas, Interacciones y Observaciones. Cada tarjeta de
  vertical queda en el lugar que tiene en su pestaña (Comedor, CDF, Celiaquía, VAT)
  y las colaboraciones debajo de las pestañas.
- **Acción.** `POST /api/web/ciudadanos/<pk>/marcar-revisado/`
  (`CiudadanoMarcarRevisadoWebView`) corre la vista nativa `marcar_revisado`:
  conserva su permiso (`ciudadanos.revision_identidad`, 403 sin él, también para un
  id inexistente), su 404, la escritura (`requiere_revision_manual=False` y
  `estado_revision_manual=APROBADA`, nada más) y su mensaje en cola; el 302 pasa a
  `{"ok": true, "redirect": "/ciudadanos/ver/<pk>"}` y el siguiente `GET` de la ficha
  consume el mensaje. React muestra el botón solo si la ficha trae
  `acciones.marcar_revisado_url` (revisión pendiente y permiso), pregunta «¿Marcar
  este ciudadano como revisado?» como el `confirm` nativo, envía una sola vez y
  navega a la ficha; un resultado no confirmado se informa sin reenviar. Se agregó
  la ruta a `_OWNED_PATTERNS` de `admindocs.py` y a `url_registry.json`.
- Los enlaces Editar, Dar de baja, Historial y Agregar familiar apuntan a las
  páginas Django, que no cambian (su migración es C05.02 y C05.03). Con esto la
  ficha React reemplaza a la nativa en la vista previa local, que ya servía el
  índice React en la URL nativa `ciudadanos/ver/<pk>`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): 14 pruebas nuevas de la proyección y
  de la acción (datos, vacíos, acciones y permiso de Historial, aviso de identidad,
  orden de familia, 10 interacciones, historial, mensajes consumidos una vez, solo
  lectura; marcar revisado: efecto persistido exacto, 401, 403 sin permiso, 404,
  405, CSRF 403 y datos sin cambios ante cada rechazo) y las 14 de aportes sin
  cambios.
- Vitest: pruebas nuevas de validador, acciones, aviso, pestañas, secciones,
  estados vacíos, mensajes, mapa/foto, configuración y ciclo del gráfico; tsc y
  eslint sin avisos.
- G1 (core y runtime con gunicorn): 401 anónimo, 403 sin permiso y con requisito
  pendiente, cabecera falsificada ignorada, POST sin CSRF 403, ficha 200, 404, y para
  la acción: 401, 403 sin permiso sin cambios, 200 con redirección, revisión
  resuelta y mensaje una sola vez.
- Visual S13 contra la ficha nativa real (ya no un anfitrión de laboratorio),
  escritorio y móvil: ficha completa, vacía y sin DNI con revisión pendiente
  (con el botón «Marcar revisado»), y las pestañas Comedor, CDF, Celiaquía, VAT y
  PAS: estructura, orden de Tab y texto iguales, geometría dentro de 0,06 px y
  diferencia perceptual de 0,04 % como máximo.

## Limitaciones y diferencias conocidas

- Las secciones de las pestañas «Socioeconómico», «PAS», «Prestación Alimentar»,
  «FCH», «Situación de Calle» y «Aduana» siguen siendo «Contenido en
  desarrollo...», como en la plantilla; los montos de programas y el «Monto total
  mes Dic 2025» son literales también allá. Los campos de búsqueda y los botones
  de Interacciones y Observaciones no hacen nada, igual que en Django.
- Si el proveedor de Centro de Familia no está listado, el monto muestra `$0.00`
  (el `default` del template).
- Chart.js se carga del CDN como en la ficha nativa; sin red el gráfico no se dibuja
  en ninguna de las dos.
- La plantilla nativa escribe «Interaccion» (sin tilde) en la tabla de todas las
  pestañas salvo «Datos personales»; React conserva esa ortografía.
- Los fragmentos nativos de CDF, Celiaquía y VAT muestran un comentario `{# ... #}`
  de varias líneas como texto visible; React no lo reproduce (la comparación visual
  lo quita de ambos lados). Conviene corregir esas plantillas con `{% comment %}` en
  un cambio aparte.
- La acción «Marcar revisado» no se compara visualmente después del envío (navega a
  la ficha): se cubre con G1 y con Vitest.
