# 2026-10-06 - Detalle de nómina: dato "Dados de baja" (#2507)

## Contexto
- El resumen de nómina sobre asistentes activos y la tarjeta "Dados de baja" del legajo ya se
  entregaron (ver `docs/registro/cambios/2026-T3/2026-09-23-nomina-resumen-legajo-activos.md`).
- En la revisión del issue se pidió mostrar también "Dados de baja" en el detalle de nómina,
  debajo de "Lista de espera".

## Cambios aplicados
- `comedores/templates/comedor/nomina_detail.html`: fila "Dados de baja" en la tarjeta "Nómina",
  con el valor `nomina_rangos.baja` que ya calcula `ComedorService`. Aplica al detalle con
  admisión y al de nómina directa (comparten template).
- Test de render del detalle: género cuenta solo activos y "Dados de baja" aparece debajo de
  "Lista de espera".

## Riesgos y rollback
- Solo template; sin cambios de datos ni de servicio. Rollback: revertir el commit.
