# Cambio: alta y edición de centros CDI en React sobre G1 v1 (#2785, CDI09)

## Alcance

Lane C9 del [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): alta
(`/centrodeinfancia/crear`) y edición (`/centrodeinfancia/editar/<id>`) del centro, contrato
`2026-10-28-2785-cdi-centros-y-credenciales.md`. No activa React en producción y no cambia el
comportamiento nativo. RENAPER y el aprovisionamiento se simulan en las pruebas.

Archivos: `web_api_centro_form.py`, `web_api_urls_centro_form.py`, `web_preview_centro_form.py`,
`routes/cdiCentroForm.tsx`, `cdiCentroFormBehavior.ts` y `cdiCentroFormMapa.tsx` con sus pruebas,
`admindocs.py` y `url_registry.json`.

## Comportamiento

Las vistas de la API heredan `CentroDeInfanciaCreateView` y `CentroDeInfanciaUpdateView`: alcance (404),
`CentroDeInfanciaForm`, token RENAPER firmado del referente, guardado, aprovisionamiento y mensajes son los
nativos. Delante solo agregan G1, el permiso de la URL (`add_centrodeinfancia`, `change_centrodeinfancia`),
CSRF y el veto de auditoría CDI-A3. Un redireccionamiento nativo pasa a `{"ok": true, "redirect": ...}` y un
formulario inválido responde 400 con el mismo cuerpo. Solo se aceptan POST urlencoded.

La API envía los campos que dibuja el template, las tres listas de casillas y los horarios por día; la
pantalla porta los scripts de la plantilla (máscara de CUIT, horarios, campos «otra», geografía y decil) y
reutiliza el bloque RENAPER y el editor de pin. El POST es único y sin reintento.

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: 22 pruebas nuevas (efecto persistido, rechazo sin efecto, token firmado, permisos, veto,
  alcance, 401, CSRF, 405/415, vista previa); 137 pasan junto con las del formulario de trabajadores y la
  puerta web, el proxy y los servicios; black, pylint 10/10 y `makemigrations --check` sin cambios.
- Frontend: 18 pruebas de ruta; una corrida completa de `vitest` (1367), `tsc`, `eslint` y `vite build`.
- G1 de punta a punta: 13 verificaciones, incluido alta rechazada sin efecto y alta válida.
- Visual (S13), escritorio y móvil: alta vacía, alta provincial, edición verificada, edición manual y
  rechazo sin diferencias (0,000 % de píxeles, geometría hasta 1 px).

## Limitaciones

- El decil de IPI queda vacío al elegir un departamento dibujado por el servidor, como el script nativo.
- El error de un día sin marcar queda en una fila oculta, como en la página nativa.
- Con RENAPER la API hace la misma consulta que la vista nativa; la verificación no la ejecuta.
