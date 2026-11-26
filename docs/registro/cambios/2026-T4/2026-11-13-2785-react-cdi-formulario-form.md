# Cambio: alta y edición de formularios institucionales CDI en React sobre G1 v1 (#2785, CDI03)

## Alcance

Cuarta entrega de la lane C5 sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): alta
(`/centrodeinfancia/<centro>/formularios/crear/`) y edición
(`.../formularios/<formulario>/editar/`) del formulario institucional, contrato
`2026-10-28-2785-cdi-formularios-trabajadores-m2.md`. Sigue después del
[listado y la ficha](2026-11-13-2785-react-cdi-formularios-listado-ficha.md). No hay
ruta de baja. No activa React en producción ni cambia el comportamiento nativo. No se
consulta ningún servicio externo.

Archivos: `web_api_formulario_form.py`, `web_api_urls_formularios_institucionales.py`,
`web_preview_formularios_institucionales.py`, `routes/cdiFormulariosForm.tsx` y
`cdiFormulariosForm.behavior.ts` con sus pruebas, `admindocs.py` y `url_registry.json`.

## Comportamiento

Las vistas de la API heredan `FormularioCDICreateView` y `FormularioCDIUpdateView`: el
centro y el formulario salen del alcance del actor (404 fuera de él), el alta toma el
snapshot de datos del centro, la edición usa la instancia (sin autosincronizar con el
centro), y `FormularioCDIForm`, los tres formsets fijos (sin borrado), la transacción de
guardado, `ensure_fixed_rows` y los mensajes «Formulario #<pk> creado/actualizado
correctamente.» son los nativos. Delante solo agregan G1, el permiso de la URL
(`add_formulariocdi`, `change_formulariocdi`) y CSRF; el veto CDI-A3 es el del `post`
nativo, antes de construir o guardar nada. Un redireccionamiento nativo pasa a
`{"ok": true, "redirect": ...}` y un formulario inválido responde 400 con el mismo cuerpo
(errores de campo, de fila, globales y de los ManagementForm). Solo POST urlencoded.

Riesgos de la fuente que no se corrigen (contrato): el GET de edición crea las filas fijas
que falten (`ensure_fixed_rows`; el veto de auditoría cubre solo el POST) y el POST guarda
con `save(commit=False)` y los formsets, no con `Form.save(commit=True)`. La API ejecuta
las mismas llamadas y dos pruebas comparan el efecto con la URL nativa (filas fijas creadas
y horarios persistidos tras el POST) en lugar de afirmarlo por nombre; la entrada de vista
previa no construye los formsets y por eso no crea filas.

Cada campo viaja como el marcado `as_crispy_field` del formulario nativo y las celdas de
los formsets como su widget; el diseño, las claves ocultas, los ManagementForm y el envío
están en React, y el script de la plantilla (horarios por día, condicionales, máscara de
CUIT, totales de salas y las dos cascadas geográficas) se porta a
`cdiFormulariosForm.behavior.ts`. El envío no valida en el navegador (`novalidate`) y el
POST no se reintenta.

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: 23 pruebas del formulario (paridad de campos, filas y ManagementForm con el HTML
  nativo, snapshot, alta y edición con efecto persistido, rechazos sin efecto, filas y
  ManagementForm manipulados, código inmutable, comparación con la URL nativa, alcance,
  permisos, veto de auditoría, CSRF, formato, runtime firmado) y la vista previa; la suite
  de CDI y los tests de puerta web, proxy y servicios pasan (329); black limpio, pylint
  10/10, `makemigrations --check` sin cambios; `url_registry.json` regenerado.
- Frontend: 11 pruebas de ruta; una corrida completa de `vitest` (1315), `tsc`, `eslint` y
  `vite build`.
- G1 de punta a punta: 26 verificaciones, incluidos alta rechazada sin efecto y alta
  válida persistida.
- Visual (S13), escritorio y móvil: alta, edición y rechazo del servidor sin diferencias
  (0,000 % de píxeles, geometría 0 px).

## Limitaciones

- Con el rol de auditoría el GET de edición sigue pudiendo crear filas fijas (comportamiento
  nativo registrado, no corregido).
