# Instrumento DataCalle — **4.0.0**

Copia de los artefactos que publica la app en
`Desktop/DataCalle-SISOC/contrato/`. **No editar a mano**: los regenera
DATACALLE y se sincronizan pidiéndolo en el canal de coordinación.

SISOC los usa para tres cosas, ninguna de las cuales condiciona el contrato:

- mostrar las respuestas de un caso con etiquetas legibles en el backoffice;
- servir `GET /api/datacalle/catalogos/`, para que la app pueda actualizar
  textos y opciones sin publicar una versión nueva;
- leer la regla de qué franjas etarias no se entrevistan
  (`estados.rechazada` del cuestionario), en vez de hardcodearla.

Las respuestas se guardan siempre como llegan, así que una versión desfasada
del cuestionario nunca pierde datos: sólo muestra la clave cruda.

## Cómo sincronizar

Copiar los tres archivos desde `contrato/` y **subir la versión pinneada** en
`tests/test_datacalle_api.py::test_catalogos_sirven_el_instrumento_vigente`.
El pin está ahí para que una copia vieja falle en CI en vez de pasar inadvertida:
pasó con la 2.1.0 (publicada el 16/9, tomada el 18/9) y otra vez con la 2.3.0,
3.0.0 y 3.1.0, que nunca se tomaron y dejaron el endpoint cuatro versiones atrás.

## Qué cambió en 4.0.0 (formulario FINAL en papel, 2026-10-01)

Reemplazo total del instrumento, no un cambio aditivo: 19 claves nuevas, 27 que
dejan de preguntarse (marcadas `soloHistorico`) y la matriz etaria de 5 a 7
franjas con códigos nuevos. **Cero renombres y cero borrados**, a propósito: los
casos ya guardados se siguen leyendo con el instrumento vigente, sin tablas de
equivalencia.

Lo que **no** se puede hacer con estos archivos, porque el contrato lo prohíbe:

- sumar o mapear franjas etarias viejas a nuevas (`r19a59` ≠ `r18a29 + r30a45 +
  r46a64`: los cortes no coinciden);
- empalmar `tiempoEnCalle` con `desdeCuandoCalle`, ni `motivoPrincipalCalle` con
  `motivosCalle`: son escalas distintas;
- sumar `todosLosDias` con `todosLosDiasExactos` en `asisteComedor`.
