# Cambio: detalle de admisión en React sobre G1 v1 (#2785, AD03.01, segunda parte)

## Alcance

Página `comedores/<comedor_pk>/admision/<pk>/detalle/`, según el
[contrato AD03](../../../plans/2026-T4/2026-11-10-2785-admisiones-circuito-tecnico-legal-ad03-m2.md).
No cambia vistas, servicios ni modelos nativos, ni activa React en producción. El editor técnico y el
detalle legal quedan para la tercera parte de AD03.01. Las brechas de acceso se conservan tal cual,
según la [decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos:

- `src/backends/comedores/admisiones/web_api_detalle.py` (ruta en `web_api_seguimiento_urls.py`).
- `src/backends/comedores/admisiones/web_preview_seguimiento.py`: entrada local del GET nativo.
- `src/backends/config/url_registry.json` (regenerado) y `middlewares/admindocs.py`.
- `src/frontends/apps/sisoc/src/routes/admisionesDetalle.tsx`, `admisionesSeguimiento.tsx` y su prueba.
- Pruebas: `test_web_api_detalle_ad03.py` y `test_web_detalle_acciones_ad03.py`.

## Comportamiento

- `GET /api/web/comedores/admisiones/<comedor_pk>/<pk>/detalle/` ejecuta `AdmisionDetailView`
  (`setup`, `get_object`, `get_context_data`). La admisión se resuelve por clave global y solo se
  exige que `comedor_pk` coincida; si no, 404. Fechas y números salen ya con el formato del template.
- Acceso igual al nativo: sesión web (G1) y alguno de `comedores.view_comedor`,
  `admisiones.view_admision` o `acompanamientos.view_informacionrelevante` (superusuario incluido);
  sin alcance por objeto.
- «Forzar Cierre» (superusuario o grupo «Coordinador Equipo Tecnico», solo con la admisión activa)
  abre el modal y envía el formulario como POST a la URL nativa, que aplica sus reglas y mensajes.
- El historial de estados pagina de a 10 con `historial_estados_page`.

## Verificación

Entorno sintético, sin red: pruebas de la API y del preview, `black`, `pylint`, Vitest de `sisoc`,
`tsc`, ESLint, build, visual (S13) y G1 sobre el árbol final.

## Acciones del detalle (AD03.02, parte del detalle)

- Número de convenio (edición en línea), «Vigente PWA», carga de archivo adicional y «Forzar Cierre»
  se envían a las vistas nativas (`/ajax/actualizar-convenio-numero/`, `/ajax/actualizar-vigente-pwa/`
  y la URL de la página), con CSRF; las reglas, textos de error y efectos son los nativos. React replica
  los toasts, el revertido del interruptor y la recarga tras subir el archivo.
- `test_web_detalle_acciones_ad03.py` fija el efecto persistido de cada acción y que un rechazo
  (negativo, no numérico, sin rol de dupla, nombre vacío, sin permiso) deja los datos sin cambios.

## Limitaciones

- `SisocShell` tipa `heading` como texto; el encabezado con la insignia se pasa como nodo con un cast
  local hasta que el marco acepte `ReactNode`.
- Quedan para otras entregas el editor técnico y el detalle legal, y el resto de las acciones de AD03.02/03.
