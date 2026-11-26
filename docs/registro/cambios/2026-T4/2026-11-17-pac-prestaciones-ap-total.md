# 2026-11-17 - Cuadro de prestaciones de Posterior y Virtual igual al del Primer Seguimiento

## Contexto
- Issue #2922. En Alimentar Comunidad, el Primer Seguimiento ya usaba el cuadro nuevo (#2781): AP único (`ap_total`) y DE presencial / vianda.
- Posterior (7.1) y Virtual (2.1.1) seguían con AP presencial y AP vianda.

## Cambios aplicados
- `primer_seguimiento_detail.html`: la tabla de prestaciones muestra una sola columna «AP» (`ap_total_efectivo`) en los tres tipos de PAC.
- `PrimerSeguimientoDetailView`: se quita `es_primer` del contexto, porque ya no se usa.
- Gestionar (secretarianaf/Gestionar, mismo issue): Posterior y Virtual usan el cuadro del Primer y mandan `ap_total`.

## Impacto esperado
- El detalle de un Posterior o Virtual muestra «AP» igual que el Primer.
- Los registros viejos sin `ap_total` muestran presencial + vianda.
- Sin cambios en modelo, serializer, API ni migraciones. Los formularios PNUD no cambian.

## Validación
- Tests nuevos en `test_primer_seguimiento_relevamientos.py`: el detalle de Posterior y de Virtual, con `ap_total` y con filas viejas.

## Riesgos y rollback
- Riesgo: ninguno en datos; solo cambia la presentación.
- Rollback: revertir el PR.
