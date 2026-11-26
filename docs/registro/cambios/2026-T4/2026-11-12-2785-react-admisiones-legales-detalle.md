# Cambio: detalle legal de admisión en React sobre G1 v1 (#2785, AD03.03)

## Alcance

Páginas `comedores/admisiones/legales/ver/<pk>` y `comedores/admisiones/legales/revisar-complementario/<pk>`,
según el [contrato AD03](../../../plans/2026-T4/2026-11-10-2785-admisiones-circuito-tecnico-legal-ad03-m2.md).
No cambia vistas, servicios ni modelos nativos, ni activa React en producción. Las brechas de acceso se
conservan, según la [decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos:

- `src/backends/comedores/admisiones/web_api_legales.py` y `web_api_legales_urls.py` (incluido desde
  `web_api_seguimiento_urls.py`), `web_preview_legales.py` (entrada local de los GET nativos).
- `src/backends/config/url_registry.json` (regenerado) y `middlewares/admindocs.py`.
- `src/frontends/apps/sisoc/src/routes/admisionesLegales.tsx` (con su prueba) y `routes/index.ts`.
- Prueba: `test_web_api_legales_ad03.py`.

## Comportamiento

- `GET /api/web/comedores/admisiones/legales/<pk>/` ejecuta `AdmisionesLegalesDetailView` y proyecta los
  mismos formularios, botones (`LegalesService.get_botones_disponibles`) e historial paginado. El acceso es
  el nativo (permisos técnicos más `expedientespagos.view_expedientepago`, sin alcance por objeto).
- `POST .../legales/<pk>/acciones/<accion>/` (`rectificar`, `numero-expediente`, `proyecto-convenio`,
  `if-proyecto-convenio`, `primera-providencia`, `gde-pv-primera`, `segunda-providencia`, `gde-pv-segunda`,
  `intervencion-juridicos`, `convenio`, `reinicio-expediente`, `solicitar-complementario`,
  `if-complementario`, `validar-juridicos`) llama al handler nativo con un POST que lleva solo los campos
  del botón. Los mensajes se devuelven en `messages`; un formulario inválido responde 400 con el formulario
  enlazado (equivale al modal abierto) y el corte de secuencia de las providencias responde 409 con el
  texto nativo.
- `GET`/`POST .../legales/<pk>/complementario/revision/` sirve la revisión del informe complementario.
- Los PDF y DOCX se enlazan por su URL de media; no hay endpoint nuevo de descarga.

## Verificación

Entorno sintético, sin red: pruebas de la API, `black`, `pylint`, Vitest de `sisoc`, `tsc`, ESLint, build,
visual (S13, estados clave en escritorio y móvil) y G1 sobre el árbol final.

## Limitaciones

- `ValidacionJuridicos` y `btnDocumentoExpediente` no tienen botón ni handler útil en el template nativo y no
  se agregan.
- La generación de PDF/DOCX sigue siendo nativa; sus errores llegan como mensaje nativo.
