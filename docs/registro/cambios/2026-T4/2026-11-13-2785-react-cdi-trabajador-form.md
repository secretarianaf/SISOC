# Cambio: alta y edición de trabajadores CDI en React sobre G1 v1 (#2785, CDI05)

## Alcance

Segunda entrega de la lane C5 sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): alta
(`/centrodeinfancia/<centro>/trabajadores/crear/`) y edición
(`.../trabajadores/<id>/editar/`) del trabajador, contrato
`2026-10-28-2785-cdi-formularios-trabajadores-m2.md`. Sigue después de la
[ficha](2026-11-13-2785-react-cdi-trabajador-ficha.md). No activa React en
producción y no cambia el comportamiento nativo. Las pruebas simulan RENAPER y el
aprovisionamiento: no se llama a ningún servicio externo.

Archivos: `web_api_trabajador_form.py`, `web_api_urls_trabajadores.py`,
`web_preview_trabajadores.py`, `routes/cdiTrabajadoresForm.tsx` y
`cdiTrabajadoresForm.behavior.ts` con sus pruebas, `admindocs.py` y
`url_registry.json`.

## Comportamiento

Las vistas de la API heredan `TrabajadorCentroInfanciaCreateView` y
`TrabajadorCentroInfanciaUpdateView`: alcance (404), búsqueda por DNI (local y
RENAPER solo como la hace la vista nativa), token firmado de 15 minutos,
`TrabajadorCDIForm` (obligatorios, bloqueos, condicionales), guardado,
aprovisionamiento de usuario, sincronización de email y mensajes son los nativos.
Delante solo agregan G1, el permiso de la URL (`add_trabajador`,
`change_trabajador`), CSRF y el veto de auditoría CDI-A3 en todo POST. Un
redireccionamiento nativo pasa a `{"ok": true, "redirect": ...}` y los mensajes (éxito
o aviso de provisión fallida, guardado parcial) salen en la ficha del centro; un
formulario inválido responde 400 con el mismo cuerpo. Solo se aceptan POST
urlencoded.

Cada campo viaja como el marcado `as_crispy_field` del formulario nativo (etiquetas,
widgets, bloqueo RENAPER y errores) y las cuatro listas de casillas como opciones; el
diseño, el plegado, la barra de progreso y el envío están en React. Los scripts
`trabajadorForm.js` y `cdiSinCuil.js` se portan al comportamiento del formulario. El
envío no valida en el navegador, como el botón nativo; el POST va a la URL de la página
con su consulta y no se reintenta.

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: 33 pruebas del formulario (paridad de campos con el HTML nativo, búsqueda,
  RENAPER simulado y token, altas y ediciones con efecto persistido, rechazos sin efecto,
  éxito parcial, alcance, permisos, veto de auditoría, CSRF, formato, runtime firmado)
  más las de la ficha y la vista previa: 142 pasan junto con la puerta web, el proxy y
  los servicios; black limpio, pylint 10/10, `makemigrations --check` sin cambios.
- Frontend: 12 pruebas de ruta; una corrida completa de `vitest` (1219), `tsc`, `eslint`
  y `vite build`.
- G1 de punta a punta: 15 verificaciones, incluido alta rechazada sin efecto y alta
  válida persistida.
- Visual (S13), escritorio y móvil: alta, alta con ciudadano, edición y rechazo del
  servidor sin diferencias (0,000 % de píxeles, geometría 0,02 px).

## Limitaciones

- El plegado alterna la clase `show` sin animar.
- Con RENAPER la API hace la misma consulta que la vista nativa; la verificación no la
  ejecuta.
