# Cambio: textos del Anexo, actividad 8.1.16 y rótulo "Seguimiento Posterior" (#2781)

## Alcance

Puntos 6, 8 y 9 del issue #2781, lado SISOC (la app se cambia en un PR aparte).

- Punto 6: la pregunta del Anexo "¿Cuántas veces recibió estos insumos en el
  año 2024?" pasa a "...en el año anterior?", y la pregunta previa
  ("Durante el año 2024, ¿recibió insumos...") también. El campo
  `Anexo.veces_recibio_insumos_2024` conserva su nombre y su columna; solo
  cambian `verbose_name` (`relevamientos/models.py`), el label de
  `relevamientos/form.py` y el detalle `relevamiento_detail_secciones.html`.
- Punto 8: `ActividadesExtrasSeguimiento` suma `pueblo_indigena` (bool),
  `pueblo_indigena_donde` y `pueblo_indigena_frecuencia` (item 8.1.16 del
  Primer Seguimiento), con el mismo formato que `ayuda_tramites*`. Se agregan a
  `PrimerSeguimientoSerializer.ACTIVIDADES_FIELDS` (sync desde la app) y el
  detalle del seguimiento los muestra con el rótulo "8.1.16 ...".
- Punto 9: `PrimerSeguimiento.TIPO_CHOICES` rotula el tipo posterior como
  "Seguimiento Posterior" (también el popup de alta y el mensaje de creación).
  `PrimerSeguimiento.__str__` dejó de decir siempre "Primer seguimiento" y usa
  `get_tipo_display()`. Los títulos del detalle y del ciclo ya usaban el tipo.

## Comportamiento

- Migración `relevamientos`: `AddField` x3 (nullable, sin impacto en datos
  existentes) y `AlterField` por los `verbose_name` del Anexo y de las choices.
- Compatibilidad: el valor guardado de `tipo` (`posterior`) no cambia; solo la
  etiqueta. Los mensajes de log "Primer seguimiento <id> ..." se dejaron igual
  porque `reparacion_app_2809.py` los parsea.
- Si la app todavía no manda las claves nuevas, el bloque se guarda como antes.

## Verificación

Ver la sección de tests del PR. Tests nuevos en
`src/backends/comedores/tests/test_primer_seguimiento_relevamientos.py`
(sync de 8.1.16, detalle con 8.1.16 y título de un posterior).
