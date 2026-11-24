# Cambio: inscripciones a comisiones de oferta de VAT en React sobre G1 v1 (#2785, V03.01)

## Alcance

Segunda unidad del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): `/vat/inscripciones-oferta/` (lista con
búsqueda, estado y paginación), `<pk>/` (detalle), `nueva/`, `<pk>/editar/` y `<pk>/eliminar/`. Lee y escribe por
`InscripcionOferta{List,Detail,Create,Update,Delete}View`, sin tocar vistas, servicios, plantillas ni URLs nativas. No
activa React en producción. Se conserva el alcance de cada vista (paridad); cualquier acotamiento, incluido #2794, queda
para un ticket aparte.

Archivos:

- `src/backends/vat/VAT/web_api_inscripcion_oferta.py` (rutas en `web_api_urls.py`), `url_registry.json` regenerado y
  `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_inscripcion_oferta.py`: entradas de vista previa de las cinco rutas.
- `src/frontends/apps/sisoc/src/routes/vatInscripcionOferta.tsx` (lista y detalle) y `vatInscripcionOfertaForm.tsx`
  (formulario y baja), registrados en `routes/index.ts`.
- Pruebas: `test_web_vat_inscripcion_oferta_v03.py` y `vatInscripcionOferta.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y el permiso de la ruta nativa (`view`, `add`, `change` o `delete` de
  `inscripcionoferta`; 403), 404 si no existe, CSRF en los POST (403).
- La lista conserva el queryset nativo (filtros `oferta_id`, `estado`, `busqueda` o `q`, de a 20), las insignias de los
  cinco estados y los botones Editar y Eliminar según permiso. El detalle imprime lo mismo que la plantilla, incluido lo
  que sale vacío cuando la comisión no tiene el atributo (período, horario, días).
- El alta corre `form_valid` nativo: `InscripcionService.crear_inscripcion_oferta` (puede debitar voucher) y su mensaje
  («Inscripción creada exitosamente.» o el de descuento de créditos). Si el formulario o el servicio rechazan, responde 400
  sin guardar, con los errores por campo, los generales y los mensajes encolados («Error al crear la inscripción.» y, si
  fue el servicio, su texto). La edición y la baja corren las vistas nativas.
- Quirk conservado: la baja usa el `post` de `DeleteView` (no el método `delete` que agrega el mensaje), como la ruta nativa.

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas (efectos persistidos, «sin cambios» ante rechazos, comparación con los
  textos de la página nativa y entradas de vista previa), `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends`; `black`, `pylint` y `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (lista, detalle, formulario, formulario con error y baja;
  escritorio y móvil) y guardas.
