# Cambio: AP único en el cuadro 6.1 del Primer Seguimiento (#2781, punto 7)

## Alcance y causa

La app (Gestionar) reemplazó el cuadro "6.1 Días, modalidad y tipo de
prestación" del Primer Seguimiento por un diseño por día y comida donde AP es un
único número y DE conserva presencial (P) y vianda (V). Para el primer
seguimiento la app envía en cada ítem de `prestaciones_seguimientos` la clave
nueva `ap_total` y manda `ap_presencial`/`ap_vianda` en `null`. Los seguimientos
posteriores y virtuales siguen enviando las claves viejas.

## Qué cambia

- `PrestacionSeguimiento.ap_total` (entero positivo, nullable). Migración
  `relevamientos` solo con `AddField`.
- El serializer de la API acepta y persiste `ap_total`.
- Propiedad `ap_total_efectivo`: devuelve `ap_total` o, en filas viejas sin él,
  `ap_presencial + ap_vianda`.
- El detalle de seguimiento muestra la columna única "AP" para el tipo primer y
  conserva "AP presencial"/"AP vianda" en posterior y virtual.
- El formulario de edición del backoffice incluye `ap_total` además de los
  campos existentes (no distingue por tipo).

## Compatibilidad y límites

No cambia `pdf_oficial.py`: SISOC sigue sirviendo el PDF generado por la app. No
hay permisos ni dependencias nuevas. Otra rama agrega una migración en
`relevamientos` a continuación de `0024`; se reconcilia al fusionar.

Código: `src/backends/comedores/relevamientos/models.py`,
`src/backends/comedores/relevamientos/serializer.py`,
`src/backends/comedores/relevamientos/templates/primer_seguimiento_detail.html`.
Tests: `src/backends/comedores/tests/test_primer_seguimiento_relevamientos.py`.
