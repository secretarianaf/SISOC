# 2026-11-13 - Los tableros pueden leer tablas `bi_` que mantiene el equipo de Datos

## Estado
- propuesta (se revisa en el PR del Tablero Becas Progresar · Curso obligatorio)

## Contexto
- Algunos tableros muestran datos que no viven en SISOC (por ejemplo el padrón
  de Becas Progresar y el curso del WordPress de Formando Capital Humano) o
  cuya consulta en vivo es muy pesada para la base.
- El primer caso es el Tablero Becas Progresar · Curso obligatorio: cruzar el
  padrón (cerca de 625 mil titulares) con el curso tarda varios segundos por
  consulta.

## Decision
- El equipo de Datos carga esos datos, ya agregados, en tablas de la base de
  SISOC con prefijo `bi_<tablero>_<tema>` (y vistas `vw_bi_...`). Las crea,
  carga y mantiene el equipo de Datos, con su proceso diario.
- SISOC solo las **lee**, con modelos `managed=False`: Django no las crea, no
  las migra ni las modifica.
- Sistemas no modifica tablas `bi_` ni vistas `vw_bi_`. Si un cambio de
  Sistemas en una tabla de origen rompe uno de estos objetos, lo corrige
  Sistemas.
- Si las tablas faltan en un entorno, el tablero muestra "sin datos" en lugar
  de fallar.
- Tablas del primer tablero: `bi_progresar_curso_obligatorio_resumen` y
  `bi_progresar_curso_obligatorio_evolucion` (agregados, sin datos de
  personas). Tienen `id` (clave para Django), `provincia_id`
  (`core_provincia.id`, para el alcance territorial) y `fecha_carga`.

## Consecuencias
- Los tableros responden rápido y no cargan la base con cruces pesados.
- No hacen falta conexiones de SISOC a otras bases o servidores.
- Costo: el dato se actualiza una vez por día (el tablero muestra la fecha).
- Costo: QA y homologación necesitan las tablas (con una carga de prueba) para
  revisar los tableros con datos.

## Referencias
- `docs/registro/cambios/2026-T4/2026-11-13-tablero-progresar-curso-obligatorio.md`
- Patrón de modelos que leen tablas que no crea Django: `managed=False`.
