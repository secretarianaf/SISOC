# Cambio: inscripciones de comisión, acciones de estado y buscador por ciudadano de VAT en React sobre G1 v1 (#2785, V03.02)

## Alcance

Tercera unidad del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): `/vat/inscripciones/` (lista con búsqueda y
paginación), `<pk>/` (detalle), `nueva/`, `<pk>/editar/` y `<pk>/eliminar/`, más `/vat/buscador-ciudadano/`. Lee y escribe
por las vistas nativas de `views/persona.py` y `views/buscador_ciudadano.py`, sin tocar vistas, servicios, plantillas ni URLs
nativas. No activa React en producción. Se conserva el alcance de cada vista (paridad); cualquier acotamiento, incluido #2794,
queda para un ticket aparte.

Además expone como API las acciones que hoy dispara el detalle de comisión (U4): cambio de estado de una inscripción de oferta
y de curso, cambio de estado en lote y alta rápida de oferta y de curso. Son endpoints sin pantalla propia: cada uno corre el
`post` de la vista nativa (alcance, `InscripcionService` y mensajes incluidos); el consumidor React es el detalle de comisión de U4.

Archivos:

- `src/backends/vat/VAT/web_api_inscripcion_persona.py`, `web_api_inscripcion_acciones.py` y `web_api_buscador_ciudadano.py`
  (rutas en `web_api_urls.py`, prefijo `inscripciones-persona/` porque `inscripciones/` es el recurso del front INET),
  `url_registry.json` regenerado y `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_inscripcion_persona.py`: entradas de vista previa de las seis páginas.
- `src/frontends/apps/sisoc/src/routes/vatInscripcion.tsx` (lista y detalle), `vatInscripcionForm.tsx` (formulario y baja) y
  `vatBuscadorCiudadano.tsx`, con sus hojas de estilo `vatInscripcionStyles.ts` y `vatBuscadorCiudadanoStyles.ts` (el bloque
  `<style>` de cada plantilla, literal), registrados en `routes/index.ts`.
- Pruebas: `test_web_vat_inscripcion_persona_v03.py`, `vatInscripcion.test.tsx`, `vatInscripcionForm.test.tsx` y
  `vatBuscadorCiudadano.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y el permiso de la ruta nativa (403), 404 si no existe o queda fuera del alcance, CSRF en los
  POST (403). El buscador exige `VAT.view_inscripcion` o `VAT.view_centro`.
- La lista conserva el queryset nativo (filtros `ciudadano_id`, `comision_id`, `estado`, `busqueda` o `q`, de a 20), las insignias
  por estado y los botones Editar y Eliminar según permiso. El detalle imprime lo mismo que la plantilla; Editar y Eliminar solo
  aparecen para inscripciones de comisión de oferta (las de curso no se editan ahí, como en el nativo).
- El alta corre `form_valid` nativo (`InscripcionService.crear_inscripcion`, con voucher y lista de espera) y su mensaje. Si el
  servicio rechaza, responde 400 sin guardar, con el formulario y el mensaje encolado. La edición y la baja lógica corren las
  vistas nativas.
- El buscador responde el estado inicial en GET y la búsqueda nativa en POST (`q`, `ciudadano_id`); React la envía por la API y
  muestra candidatos o la trayectoria con el alcance del usuario. Los botones CSV y XLSX siguen siendo el POST nativo de la página
  (descarga).
- Quirks nativos conservados: el alta con el ciudadano vacío da 500 (`Inscripcion.clean` lee `self.ciudadano`), el error de
  unicidad no se imprime (la plantilla solo muestra errores por campo), el DNI del detalle sale vacío (`ciudadano.dni` no existe) y el
  buscador escribe «inscripciónes». La alta rápida de oferta no filtra por alcance; la de curso sí.

## Verificación

- Backend (imagen fijada, sin red): `test_web_vat_inscripcion_persona_v03.py` (efectos persistidos y «sin cambios» ante rechazos),
  `test_web_gate`, `test_backend_proxy`, `test_servicios_backends`, `black`, `pylint` y `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (lista, detalle, formulario, formulario con error, baja y los
  estados del buscador; escritorio y móvil) y guardas.
