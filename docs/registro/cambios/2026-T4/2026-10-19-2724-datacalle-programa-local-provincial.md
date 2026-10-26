# Cambio: instrumento DataCalle 4.1.1, "Programa Local / Provincial" (#2724)

## Alcance

En el relevamiento de DataCalle, la pregunta 25 ("¿Cuál?"), subopciones de
"Programa Social": el área pide reemplazar "Volver al trabajo" por
"Programa Local / Provincial".

La app lo implementa en el instrumento **4.1.1**:

- código nuevo `programaLocalProvincial`, porque es otro programa y no se
  reusa el código de "Volver al trabajo";
- `volverAlTrabajo` queda `retirada`: no se ofrece más y los casos ya
  guardados la conservan.

Aviso a SISOC en `docs/aviso-sisoc-instrumento-4.1.1.md` del repo
`secretarianaf/DataCalle`.

## Comportamiento en SISOC

- Se sincronizan `catalogos.json` y `cuestionario.json`.
  `diccionario-respuestas.json` no cambia: no hay claves nuevas.
- La ficha del caso muestra "Programa Local / Provincial". Un caso viejo con
  `volverAlTrabajo` sigue mostrando "Volver al trabajo".
- `GET /api/datacalle/catalogos/` publica 4.1.1. Hay que desplegarlo junto con
  la app: si las versiones no coinciden, la app avisa.

## Verificación

`tests/test_datacalle_instrumento_4_1_1.py`, y el pin de versión de
`test_datacalle_api.py` sube a 4.1.1.
