# Cambio: alta y edición de intervenciones CDI en React sobre G1 v1 (#2785, CDI06)

## Alcance

Alta (`/centrodeinfancia/intervencion/crear/<centro>`) y edición
(`/centrodeinfancia/intervencion/editar/<centro>/<intervencion>`) de la intervención del
centro, con el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md) y la
decisión de [acceso conservado](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).
Sigue después del [detalle de intervención](2026-11-13-2785-react-cdi-documentacion.md). La baja
y la subida de documentación siguen nativas. No activa React en producción ni cambia el
comportamiento nativo. No se consulta ningún servicio externo.

Archivos: `web_api_intervencion_form.py`, `web_api_urls_intervencion_form.py`,
`web_preview_intervencion_form.py`, `cdi_runtime/web_api_urls.py`, `routes/cdiIntervencionForm.tsx`
con su prueba, `admindocs.py` y `url_registry.json`.

## Comportamiento

Las vistas de la API heredan las vistas nativas: formulario, destinatario fijo «Centro» en el alta,
autor, mensaje «Intervención creada correctamente.» y redirección al centro son los nativos. Delante
solo agregan G1, el permiso de la URL (`add_`/`change_intervencioncentroinfancia`) y CSRF. El template
dibuja `{{ form.as_p }}`, por eso la respuesta lleva ese marcado (`form_html`, sin el token CSRF) y
la pantalla lo inserta y agrega el token, «Guardar» y «Volver». Un redireccionamiento pasa a
`{"ok": true, "redirect": ...}` y un formulario inválido responde 400 con el formulario ligado; la
pantalla lo redibuja, sube al inicio y permite reintentar. El POST acepta multipart (el adjunto) o
urlencoded y rechaza JSON con 415. El navegador valida como el nativo (sin `novalidate`).

Acceso conservado: el GET del alta no comprueba el alcance del centro (solo lo hace al guardar) y la
API no agrega esa comprobación; la edición sí filtra por alcance y centro (404).

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: 8 pruebas nuevas (marcado, alta multipart con adjunto, urlencoded y 415 para JSON,
  rechazo 400 sin efecto, edición y centro ajeno 404, 401/403, CSRF, página nativa intacta); con las
  de observaciones, intervenciones y los tests de puerta web, proxy y servicios pasan (133); black
  limpio, pylint 10/10; `url_registry.json` regenerado (solo 2 nombres agregados).
- Frontend: 7 pruebas de ruta; una corrida completa de `vitest`, `tsc`, `eslint` y `vite build`.
- G1 de punta a punta: 18 verificaciones, incluido el alta multipart con adjunto a través del proxy del core.
- Visual (S13), escritorio y móvil: alta, edición y rechazo del servidor sin diferencias
  (0,000 % de píxeles, geometría 0 px).

## Limitaciones

- El enlace al adjunto actual en la edición apunta a `/media/`, como el nativo (el cierre del alias
  público es CDI-F2, aparte).
- Subtipo y tipo no se filtran en el navegador: el template nativo no tiene script y la pantalla
  tampoco.
