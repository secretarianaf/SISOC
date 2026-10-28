# CDI: Formulario de Calidad en el legajo

Rama `CDI_Formulario`. Especificación: documento `200_CalidadCDI_Especificaciones`
(103 preguntas, matriz de variables SQL y metadatos `0_*`).

## Pedido

Implementar el Formulario de Calidad dentro del legajo de cada CDI: se completa
el Referente del CDI o su Director, se puede guardar como borrador y, una vez
enviado, queda inmutable y forma parte del historial del centro.

## Solución

- Modelo nuevo `FormularioCalidadCDI`, separado de `FormularioCDI`: aunque
  algunas preguntas se superponen, es otro instrumento con otras opciones, y
  mezclarlos rompería el formulario en uso.
- Una columna por variable de la matriz SQL, con `db_column` igual al nombre de
  la especificación (`1_INF_TENENCIA_TIPO`, `0_CDI_ID`, `0_Timestamp`, ...). El
  campo Python lleva el prefijo `p` (`p1_inf_tenencia_tipo`) porque un
  identificador no puede empezar con un dígito. Las opciones guardan sólo el
  número de la opción (20.3 → 3). Los textos de las opciones no van como
  `choices` del modelo sino sólo en el schema: un ajuste de redacción no genera
  migración. El form valida las opciones y el modelo, el rango.
- `formulario_calidad_schema.py` describe preguntas, opciones, grillas y pases
  condicionales. De ahí salen los campos del modelo, el form, el template y el
  JS. La pantalla y la validación del servidor aplican las mismas reglas.
- Estados: `borrador` (Guardar, con el aviso de formulario parcial) y `enviado`
  (Enviar). Al enviar se exige completitud; si falta algo, el avance queda
  guardado como borrador y se marcan en rojo las preguntas y secciones
  pendientes. El envío completa jurisdicción, departamento, usuario y timestamp
  y ya no admite cambios ni borrado (`save`/`delete` lo impiden). Para corregir
  se carga un formulario nuevo. Un único borrador vigente por CDI.
- Al guardar se vacían las respuestas que un pase condicional ocultó y los
  textos de "especificar" que ya no aplican.
- Permisos: las vistas usan `view_centrodeinfancia` y el alcance territorial de
  CDI ya existente, sin tocar la semilla de grupos del kernel. Dentro del centro:
  - **Edita:** el referente con `AccesoCDI` activo o el `Trabajador` con rol
    Director vinculado al usuario. Auditoría no edita.
  - **Ve los envíos:** todos los perfiles salvo `CDI - Trabajador` que no sea
    Director.
  - **Borrador:** sólo lo ve quien edita.

## Decisiones tomadas ante huecos de la especificación

- Numeración 100–103: se usa la de la sección 3 (`100_ACC_ELEMENTOS_EXISTE`,
  `102_INCL_...`, `103_INCL_...`); la matriz SQL los desfasa en uno.
- P59 → P60: la P60 se muestra si P59 ≠ 59.5 (el texto "pasa a 61 en cualquier
  otro caso" se toma como error de tipeo).
- P101 sólo se exige si P100 = Sí, en línea con el pase condicional.
- Los textos de "especificar" (P1, P13, P90, P101) se exigen sólo cuando se
  elige la opción correspondiente.
- P101 "Otros": la especificación no trae campo de texto; producto pidió
  agregarlo. Columna `101_ACC_TIPO_OTRO_TEXT`, mismo criterio que
  `90_FAM_COM_OTRO_TEXT`.
- P85/P86 se condicionan a la P84 tal como dice la especificación (confirmado
  por producto).
- "Director/Coordinador": `Trabajador.Rol` no tiene Coordinador y no se agrega;
  edita sólo Director (confirmado por producto).
- En los enunciados se corrigió "qué/cómo" acentuado donde es conjunción o
  relativo ("altura que permite", "como mediador").

## Pendiente de producto

- P91: faltan los textos y la condición de `91_FAM_RECL_[CONOCIDO|ANONIMO|
  DERIVACION]`; esas tres columnas todavía no existen.

## Tests

- `centrodeinfancia/tests/test_formulario_calidad.py`: schema (103 preguntas,
  columnas de la matriz SQL), saltos y completitud, envío con metadatos e
  inmutabilidad, permisos por rol y flujo de vistas (guardar, continuar
  borrador, enviar incompleto y completo).
