# Cambio: detalle de intervención CDI con descarga autenticada del adjunto en React sobre G1 v1 (#2785, CDI06 / CDI-F2)

## Alcance

Primera entrega de la lane de documentación e inventario del backend CDI,
parte del contrato `2026-10-28-2785-cdi-documentacion-inventario-f2.md`: la
pantalla de detalle de una intervención
(`/centrodeinfancia/intervencion/detalle/<id>/`) y el contrato de descarga por
objeto de su documentación adjunta. Sigue el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md). No
activa React en producción y no cambia el comportamiento nativo. No se llama a
ningún servicio externo.

Esta entrega **no cierra CDI-F2**: el alias directo `/media/documentacion/<nombre>`
sigue operativo en el serving actual. Cerrarlo exige el preflight de ownership
del contrato (la carpeta `documentacion/` también la usa Comedores) y una
decisión de entorno que no está autorizada. El enlace «Descargar» de React ya no
expone la ruta de almacenamiento.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api_intervenciones.py` y `web_api_urls.py`.
- `src/backends/cdi/centrodeinfancia/web_preview.py`: entrada de vista previa.
- `src/backends/config/middlewares/admindocs.py` y `url_registry.json`.
- `src/frontends/apps/sisoc/src/routes/cdiDocumentacion.tsx`, su prueba y `index.ts`.
- Pruebas: `tests/test_web_intervencion_documentacion.py` y
  `tests/test_web_preview_intervencion.py`.

## Comportamiento

- `GET /api/web/cdi/intervenciones/<id>/` ejecuta `IntervencionCentroInfanciaDetailView`
  (alcance nativo: otra provincia o baja lógica responde 404) y devuelve cada valor
  como lo imprime el template (`None` incluido, fecha en hora local). El botón
  «Eliminar» solo se ofrece a superusuarios, como en el template.
- `GET /api/web/cdi/intervenciones/<id>/documentacion/` es la descarga autenticada:
  resuelve la intervención por clave dentro del alcance del actor, lee nombre y
  storage del propio objeto (nunca una ruta ni un nombre enviados por el cliente) y
  devuelve los bytes como adjunto con nombre controlado, `private, no-store` y
  `nosniff`. Fuera de alcance, dada de baja, sin adjunto o con archivo ausente:
  mismo 404 sin revelar otros archivos.
- `POST /api/web/cdi/intervenciones/<id>/documentacion/eliminar/` ejecuta la función
  nativa `eliminar_archivo_intervencion_centrodeinfancia` (borra el archivo y la marca
  `tiene_documentacion`) y responde `{"ok": true, "redirect": <ficha del centro>}`; el
  mensaje nativo «El archivo fue eliminado correctamente.» llega en la ficha.
- Acceso, en este orden: G1 (401/403 JSON o constancia firmada), el mismo permiso que la
  URL nativa (`view_centrodeinfancia` para ver y descargar, `delete_intervencioncentroinfancia`
  para eliminar) y el despacho nativo. Brecha conservada, como la nativa: el permiso de
  baja, no solo el superusuario, habilita la API de eliminación.
- Pantalla React: tabla, enlace «Descargar» (`download`) hacia la descarga autenticada
  y modal de confirmación del marcado nativo; un único POST, sin reintento, y el resultado
  no confirmado se informa sin reenviar.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 13 pruebas nuevas en rojo (rutas inexistentes) y luego en verde, más una de
  la entrada de vista previa; con `test_web_observaciones`, `test_web_preview_cdi` y los
  tests del kernel de la puerta, el proxy y los servicios: en verde. `black` sin cambios,
  `makemigrations --check` sin cambios.
- Frontend: 7 pruebas de ruta en rojo y luego en verde; una corrida completa de
  `vitest`, `tsc`, `eslint` y `vite build`.
- G1 de punta a punta (core y runtime): anónimo 401, sin permiso 403, requisito pendiente
  403, cabecera falsificada ignorada, CSRF 403, descarga autorizada con los bytes y las
  cabeceras esperadas, baja del adjunto y descarga posterior 404.
- Visual (regla S13), escritorio y móvil, detalle con adjunto, sin adjunto, sin permiso de
  baja y modal de confirmación: 0,000 % de diferencia y misma geometría.

## Limitaciones

- La descarga nueva no bloquea `/media/documentacion/`; ver Alcance.
- La subida de documentación (`subir_archivo_intervencion_centrodeinfancia`) no tiene
  pantalla en el template nativo de detalle y no se migra.
- El `href` de «Descargar» cambia de la URL de media a la API autenticada; es la
  diferencia buscada del contrato.
