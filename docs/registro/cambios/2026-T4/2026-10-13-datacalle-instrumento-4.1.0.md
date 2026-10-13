# Cambio: instrumento DataCalle 4.1.0, formulario de menores de 14 a 17 (#2664)

## Alcance

El área pidió en #2664 que a las personas de **14 a 17 años que aceptan
responder** se les haga solo el formulario adjunto
(`FORMULARIO_MENORES_DE_13_A_17_AÑOS.pdf`). La 4.0.0 (1/10) había retirado el
abreviado porque el papel final era "un solo cuestionario"; el área lo vuelve
a pedir con un formulario propio.

DATACALLE lo implementó como la variante `adolescente` del instrumento, que
pasa de **4.0.0 a 4.1.0**. Es un cambio **aditivo**: ninguna clave nace, se
renombra ni se borra. Es un subconjunto del papel general: consentimiento,
código de identificación y vínculos, documento (3 a 5), nivel educativo (6, con
6 opciones), dónde duerme esta noche (7), desde cuándo en calle (8) y cierre.
Fuente de verdad en la app: `docs/FORMULARIO-MENORES-14-17.md`; aviso a SISOC
en `docs/aviso-sisoc-instrumento-4.1.0.md` (repo `secretarianaf/DataCalle`).

## Lo que llega de más: la enmienda del área del 1/10

La copia 4.0.0 de SISOC se tomó antes del PR #15 de la app ("ajustes del área
2026-10-01"), así que esta sincronización trae también esa enmienda, que no
cambió la versión: en el consentimiento se retira la opción "ya fue
entrevistada" (y `yaEntrevistadaDatos` pasa a `soloHistorico`: 28 retiradas en
vez de 27) y vuelve "Otro" sin campo abierto; en nivel educativo vuelve
"Otro". Sin claves nuevas. Un caso histórico con esas opciones se sigue
leyendo igual.

## Comportamiento en SISOC

- `GET /api/datacalle/catalogos/` devuelve `"version": "4.1.0"`, con la regla
  de la variante (`personaEntrevistada` en `r14a17` y `realizaEntrevista = si`)
  y el catálogo `varianteCuestionario` con `adolescente` vigente.
- Un caso de menores llega con `variante: "adolescente"` y solo las claves del
  subconjunto. Como la ficha muestra lo que llegó, **sin decir qué formulario se
  usó un caso de menores parecía incompleto**. Ahora la cabecera de la ficha
  dice "Formulario de menores (14 a 17 años)", un aviso explica que las demás
  preguntas del papel general no se le hacen, y el listado del operativo marca
  el caso con el chip "Menores (14 a 17)". `Encuesta.variante_etiqueta` y
  `Encuesta.es_formulario_menores` salen del catálogo, no de un literal.
- Un caso de 14 a 17 cargado bajo 4.0.0 con el papel general entero se sigue
  leyendo igual. Si la app lo reabre, viaja con `variante: "adolescente"` y
  conserva las respuestas de más: la ficha las muestra todas. Es correcto, no
  un error.

## Decisiones tomadas con el pedido (registradas en la app)

- **Franja 14 a 17.** El PDF se llama "13 a 17", pero su grilla y el issue
  dicen 14 a 17, y en 4.0.0 alguien de 13 cae en la franja 6–13, que no se
  entrevista. Nada cambia para esa franja.
- **"No → 5" del PDF es una errata** heredada del papel general: en menores la
  5 es el número de documento. Se implementa "No → 6" (nivel educativo), igual
  que "NS/NC → 6", y no se pregunta el motivo de no tener documento.

## Tableros (N13, pendiente)

"Menores entrevistados" = `variante = adolescente` y estado `completa`. Los
casos de 14–17 anteriores a 4.1.0 tienen `variante = completo` hasta que se
reabran: para la serie histórica conviene mirar la franja de
`persona_entrevistada` (`r14a17`), no la variante.

## Tests

- `tests/test_datacalle_instrumento_4_1_0.py`: versión 4.1.0 sin claves nuevas,
  regla y catálogo de la variante, etiqueta del caso, ficha y listado.
- Se suben los pins de versión en `test_datacalle_api.py` y
  `test_datacalle_instrumento_4_0_0.py`.
