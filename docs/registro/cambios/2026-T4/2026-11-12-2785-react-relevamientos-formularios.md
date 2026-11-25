# Cambio: edición, baja y revisión de seguimientos, PNUD y actas en React sobre G1 v1 (#2785, R03.02 y R02.02)

## Alcance

Quinta y sexta entrega del
[contrato R01-R03](../../../plans/2026-T4/2026-11-10-2785-relevamientos-seguimientos-actas-m2.md),
sobre las anteriores
([listado y detalle](2026-11-12-2785-react-relevamientos-listado-detalle.md),
[detalle de seguimientos y actas](2026-11-12-2785-react-relevamientos-seguimientos-actas.md) y
[mutaciones de relevamientos](2026-11-12-2785-react-relevamientos-mutaciones.md)):

- R03.02: edición de una instancia del ciclo
  (`/comedores/<c>/relevamiento/<r>/seguimiento/<pk>/editar`), baja de la
  instancia (modal de la tabla «Ciclo de seguimiento») y revisión del
  coordinador de seguimientos y de seguimientos PNUD.
- R02.02: alta y edición del acta (`/comedores/<c>/acta-complementaria/crear` y
  `.../<pk>/editar`), revisión del coordinador y baja del acta.

Todas son escrituras sobre datos persistidos y repiten el código nativo; no
cambia vistas, formularios, plantillas ni modelos. Los POST nativos siguen
funcionando con las mismas entradas. No activa React en producción.

Archivos:

- `src/backends/comedores/relevamientos/web_api_forms.py` (nuevo),
  `web_api_urls.py`, `web_api_serializers.py` y `web_api_views.py`: endpoints bajo
  `/api/web/comedores/relevamientos/<comedor>/` (`relevamiento/<r>/seguimientos/<pk>/editar/`,
  `.../eliminar/`, `.../revision/`, `.../seguimientos/primero/eliminar/`,
  `pnud/<pk>/revision/`, `actas/crear/`, `actas/<pk>/editar/`, `.../revision/` y
  `.../eliminar/`); `src/backends/config/url_registry.json` regenerado y
  `src/backends/config/middlewares/admindocs.py` con las rutas nuevas.
- `src/backends/comedores/relevamientos/web_preview.py`: entradas React sin
  montar para la edición del seguimiento y el formulario del acta (el POST
  sigue siendo la vista nativa).
- `src/frontends/apps/sisoc/src/routes/relevamientosForms.tsx` (formularios),
  `relevamientosApi.tsx` (formularios devueltos con errores y aviso entre
  pantallas), cambios en `relevamientos.tsx`, `relevamientosShared.tsx`,
  `relevamientosSeguimientos.tsx` y `relevamientosActas.tsx` (revisión y baja por
  la API).
- Pruebas: `tests/test_web_relevamientos_formularios_api.py`,
  `tests/test_web_preview_relevamientos_seguimientos.py`,
  `routes/relevamientosFormularios.test.tsx` y casos nuevos de
  `routes/relevamientosMutaciones.test.tsx`, `relevamientosSeguimientos.test.tsx` y
  `relevamientosActas.test.tsx`.

## Comportamiento

Cada escritura pasa por el código nativo:

- Edición: `SeguimientoEditor` y `ActaComplementariaEditor` (validación,
  creación de un bloque solo si se completa algún campo, filas de prestaciones
  con «Eliminar», técnico por defecto y `@transaction.atomic`). Un formulario
  inválido responde 400 con el detalle «Revise los campos marcados en rojo.» y los
  campos ligados con sus errores; no se escribe nada.
- Baja: `PrimerSeguimientoEliminarView` (cascada de bloques, prestaciones y PDF
  oficial y la señal de baja en GESTIONAR si hay `gestionar_id`) y
  `ActaComplementariaEliminarView`; repetida, 404.
- Revisión: transacción con `select_for_update` y `aplicar_revision_coordinador`
  (el PNUD además guarda `fecha_actualizacion`); ya validado o sin cargar, 409;
  resultado inválido u observación faltante, 400; objeto ajeno, 404.

Variante de D7: en lugar de un descriptor propio de widgets, cada campo viaja
como el marcado real que genera Django (`{{ field }}`) más etiqueta, ayuda y
errores. React lo pinta con controles no controlados, de modo que select,
`NullBooleanSelect`, `datetime-local`, casillas y textareas conservan valores y
nombres nativos sin reescribir ninguna regla.

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero; después el permiso de ruta de cada URL nativa
(`change_primerseguimiento`, `delete_primerseguimiento`, `review_relevamiento`,
`add_actacomplementaria`, `change_actacomplementaria`, `delete_actacomplementaria`),
sin alcance por usuario. El POST exige CSRF. En React un 504 `{"uncertain": true}`
se muestra como «No se pudo confirmar el resultado.» con «Recargar» y el envío
queda deshabilitado: nunca se reenvía.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada; hoja de AdminLTE
presente. Como son escrituras, cada prueba afirma las filas exactas que quedan y
cada rechazo afirma que los datos no cambiaron.

- Backend: 19 pruebas nuevas de la API (efectos exactos, igualdad con la vista
  o el formulario nativo, rechazos sin cambios, permisos, CSRF), `black` y `pylint`
  10/10.
- Frontend: Vitest del proyecto completo, `tsc`, ESLint y build de Vite.
- G1 de punta a punta (core y runtime con gunicorn): edición, error de
  validación y alta de acta desde el navegador; revisión, bajas y rechazos con
  CSRF; anónimo, sin permiso, requisito pendiente y header falsificado.
- Visual (S13): edición de instancia completa y sin bloques, con errores, alta
  de acta, edición con errores, modal de baja del ciclo y de revisión, en
  1440x900 y 390x844.

## Limitaciones

- Un formulario inválido se vuelve a pintar sin recargar la página; React lleva
  la vista y el foco al inicio, como la recarga nativa.
- Un `NullBooleanSelect` se envía como `unknown`, `true` o `false`, igual que el
  navegador con la página nativa.
- El editor nativo guarda un texto vacío sin tocar como `""` en lugar de `NULL`
  (por ejemplo `motivo_diferencia_aprobado_declarado`); la API hace lo mismo
  porque es el mismo editor.
