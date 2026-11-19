# Cambio: formularios del gestor de templates en React sobre G1 v1 (#2785, AD01.02)

## Alcance

Entrega AD01.02 del
[contrato AD01](../../../plans/2026-T4/2026-11-10-2785-admisiones-gestor-templates-ad01-m2.md)
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md),
que completa [AD01.01](2026-11-10-2785-react-ad01-gestor-templates.md):

- Alta de template, `/comedores/configuracion/templates/crear/` (`form.html`).

No cambia vistas, formularios, servicios, modelos, plantillas ni URLs nativas.
No activa React en producción.

No hay nada que migrar en estas rutas, que siguen nativas:

- `.../<plantilla>/versiones/crear/`: solo `POST` con redirección, sin pantalla.
- `.../<plantilla>/versiones/<version>/previsualizar/`: `GET` que descarga el
  DOCX adjunto generado y protegido por la vista Django (decisión §7 y §9.2 del
  contrato).

Archivos:

- `src/backends/comedores/admisiones/web_api_template_crear.py` y su ruta en
  `src/backends/comedores/admisiones/web_api_templates_urls.py`.
- `src/backends/comedores/admisiones/web_preview_templates.py`: entrada React
  sin montar para el alta (`PlantillaCrearEntry`).
- `src/frontends/apps/sisoc/src/routes/admisionesTemplatesForm.tsx` y su
  registro en `routes/index.ts`; `admisionesTemplates.tsx` exporta sus piezas
  compartidas (marco, hero, migas).
- Pruebas: `src/backends/comedores/admisiones/tests/test_web_gestor_templates_crear_api.py`,
  `src/backends/comedores/admisiones/tests/test_web_preview_gestor_templates.py`
  y `src/frontends/apps/sisoc/src/routes/admisionesTemplatesForm.test.tsx`.

## Comportamiento

`GET /api/web/comedores/admisiones/plantillas-informe/crear/` devuelve lo que
dibuja el formulario nativo (campos, opciones, requeridos, errores y mensajes
pendientes). `POST` (urlencoded o multipart, nunca JSON: 415) ejecuta el
`post()` nativo: `PlantillaInformeTecnicoForm`, `crear_plantilla` y el mensaje
«Template {codigo} creado con su versión {numero} en preparación.». Una
redirección 302 pasa a `{"ok": true, "redirect": "<URL nativa>"}` y la pantalla
siguiente muestra el mensaje; un formulario rechazado devuelve 400 con el
formulario ligado y nada se guarda. Un `ValidationError` residual de
`crear_plantilla` sigue dando 500, como en la página Django.

Acceso, en este orden: G1 (sesión 401, requisitos web 403, firma del core en el
runtime separado), CSRF de sesión en el POST y la doble guarda nativa con
`admisiones.gestionar_templates_informe_tecnico`. Sin alcance por objeto.

La pantalla repite el script nativo: muestra el bloque de incorporación o de
renovación, exige sus campos y limpia el estado PNUD cuando Ex PNUD no es «sí».
Los errores se muestran donde los dibuja la plantilla; tras un rechazo la
página vuelve arriba. El POST no se reintenta: un resultado no confirmado
muestra un aviso y bloquea el envío.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre la base (9 de 9) y en verde.
- Frontend: la prueba de ruta se escribió junto con el módulo (sin rojo
  previo); `tsc`, ESLint y build.

## Limitaciones

- Diferencias del marco compartido (`SisocShell`): nombre accesible del logo y
  menú móvil, fuera de esta unidad.
