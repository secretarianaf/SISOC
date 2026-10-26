# Validación del coordinador y detalle del seguimiento (#2643, parte SISOC)

El #2643 junta 12 observaciones de QA sobre la app territorial y SISOC. Este
cambio cubre las de SISOC que siguen vigentes en el código, más un problema
de seguridad encontrado al analizarlas. El análisis completo, punto por
punto y con los dos repos, quedó en el issue.

## 1. La app no puede autovalidarse

`RelevamientoSerializer` y `PrimerSeguimientoSerializer` (los del
`PATCH /api/relevamiento` y `/api/relevamiento/primer-seguimiento`) dejaban
escribir `estado_validacion`, `observaciones_coordinador`, `coordinador` y
`fecha_revision_coordinador`. Si el registro ya estaba "Pendiente validación
coordinador", `_reenviar_a_validacion` no lo tocaba, así que un PATCH con
`"estado_validacion": "Validado"` lo dejaba validado sin pasar por el
coordinador.

Ahora esos campos son de solo lectura en los dos serializers
(`ValidacionCoordinadorMixin.CAMPOS_REVISION_COORDINADOR`). La revisión solo
la escribe la vista web del coordinador. La app no manda esos campos (se
revisó `origin/main` de `secretarianaf/Gestionar`) y no hay contrato que haga
a GESTIONAR mandarlos.

## 2. No se revisa lo que todavía no se envió

El botón "Revisar" y la vista de revisión solo bloqueaban los registros
`Validado`. Un relevamiento recién asignado ("Visita pendiente", sin estado de
validación) se podía validar, y eso lo bloqueaba para siempre en la app.

Se extendió a relevamientos y seguimientos PAC la regla `sin_cargar` que ya
usaban actas y PNUD:

- `Relevamiento.sin_cargar`: sin estado de validación y sin finalizar.
- `PrimerSeguimiento.sin_cargar`: sin estado de validación y no `Completo`.

`aplicar_revision_coordinador` ya rechaza los `sin_cargar` y las plantillas
ocultan el botón. Los relevamientos finalizados sin estado de validación
(históricos de GESTIONAR, anteriores al circuito) siguen siendo revisables.
"A subsanar" sigue admitiendo una nueva revisión, como antes.

## 3. Detalle del seguimiento sin datos internos

El detalle (`/comedores/<id>/relevamiento/<id>/seguimiento/<id>/`) vuelca los
campos de cada bloque. Ahora:

- no muestra los `id_*` que genera la app (`app-i47-menu`, `app-i47-actividades`…)
  ni los OneToOne internos (`fuente_recursos`, "Recursos #N");
- muestra las firmas como imagen y no como URL;
- las tablas de prestaciones y de ítems de receta ya no tienen la columna de id.

## Pendiente (decisiones del equipo funcional)

- Las escalas de asistencia técnica (`socio_organizativo`, etc.) se siguen
  mostrando como número: sus etiquetas salen del formulario en papel.
- Opción "No entrega viandas" en 2.1.11: puede resolverse solo en la app
  (pregunta previa) o sumar la opción en SISOC.
- Etiquetas legibles (`verbose_name`) para los campos del seguimiento.
