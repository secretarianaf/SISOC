# Cambio: registro de asistencia por sesión de VAT en React sobre G1 v1 (#2785, V02.01)

## Alcance

Primera unidad del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): las dos pantallas de asistencia por sesión,
`/vat/cursos/comisiones/sesiones/<pk>/asistencia/` y `/vat/comisiones/sesiones/<pk>/asistencia/`. Lee por
`AsistenciaSesionCursoView` y `AsistenciaSesionView` y guarda con su `post` nativo, sin tocar vistas, servicios,
plantillas ni URLs nativas. No activa React en producción.

Archivos:

- `src/backends/vat/VAT/web_api_asistencia.py` (rutas en `web_api_urls.py`), `url_registry.json` regenerado y
  `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_asistencia.py`: entradas de vista previa de las dos rutas.
- `src/frontends/apps/sisoc/src/routes/vatAsistencia.tsx` y `vatAsistenciaStyles.ts` (el `<style>` nativo, literal),
  registrado en `routes/index.ts`; `vatTour.tsx` (el menú «Tour de ayuda», extraído de `vatReporte.tsx` para
  compartirlo, sin cambio de comportamiento).
- Pruebas: `test_web_vat_asistencia_v02.py` y `vatAsistencia.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `VAT.add_asistenciasesion` o `VAT.change_asistenciasesion` (403), igual que la
  ruta nativa. El alcance es el de la vista: una sesión fuera de él, o inexistente, da 404 y el POST no escribe. El POST
  exige además CSRF (403).
- La tabla, las tres tarjetas, «Marcar todos» (presentes y ausentes), la paginación local de 10 filas y el estado sin
  inscriptos se comportan como la plantilla: las filas ocultas por la paginación siguen en el formulario y los contadores
  se recalculan al cambiar una marca.
- Guardar corre el `post` nativo: en la sesión de curso guarda **todas** las inscripciones activas (la fila sin marca
  queda ausente) y en la de oferta actualiza cada fila y pasa la sesión de «programada» a «realizada». El mensaje
  «Asistencia registrada exitosamente.» se encola y aparece en el detalle de la comisión, adonde redirige.
- Quirks nativos conservados: la variante de oferta no calcula los tres totales ni tiene `comision_curso`, por lo que el
  subtítulo del curso y la insignia de estado salen vacíos y los contadores se completan con el script de la página.

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas (incluida la comparación de los textos proyectados con los de la
  página nativa, los efectos persistidos y el «sin cambios» ante rechazos), `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends`; `black`, `pylint` y `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo: 401, 403, CSRF, 404 fuera de alcance, lectura y guardado persistido.
- Comparación visual nativo contra React (con asistencia, «Marcar todos», pocas filas, vacío y variante de oferta;
  escritorio y móvil) y guardas.

## Limitaciones

La asistencia no tiene un caso de formulario rechazado (la vista nativa no valida): un guardado fallido muestra el
aviso de resultado incierto y no reenvía. El POST de resultados de comisión y las exportaciones de nómina quedan para U4
(ver §8 del contrato).
