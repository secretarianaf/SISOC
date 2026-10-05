# 2026-10-01 - API de Celiaquía: validación RENAPER

Cierra la serie de `2026-09-30-api-celiaquia-registros-erroneos.md` y
`2026-09-30-api-celiaquia-comentarios-subsanacion-lookups.md`.

## Extracción

`celiaquia/views/validacion_renaper.py` eran **772 líneas**: 23 helpers de
módulo, 10 constantes y dos métodos de 93 y 219 líneas. Toda esa lógica se movió
a `celiaquia/services/validacion_renaper_service/`.

La vista quedó en ~90 líneas: permisos y traducción a HTTP. Reexporta los
helpers con sus nombres viejos, declarados en `__all__`, porque los tests y
otros módulos los importan desde ahí.

El movimiento fue verbatim. Dos detalles del traslado:

- **`consultar` devuelve `(payload, status)`**, con el mismo status que usaba la
  vista. Los errores de negocio salían con **HTTP 200 y `success: False`**; la
  pantalla sigue recibiendo eso y la API los traduce a 400, que es lo que
  corresponde en REST. Así ninguno de los dos frentes cambia de contrato.
- **El `get_object_or_404` quedó dentro del `try`**, como estaba: un fallo al
  resolver el legajo también tiene que salir como 500 con mensaje genérico.

## Endpoints nuevos

| Método | Ruta | Qué hace |
| --- | --- | --- |
| POST | `legajos/{id}/validar-renaper/` | Consulta y devuelve la comparación. No guarda |
| POST | `legajos/{id}/validacion-renaper/` | Confirma: 1 acepta, 2 rechaza, 3 subsana |

Las tres ramas del guardado no son simétricas y quedaron documentadas en el
service: **2** degrada `revision_tecnico` a RECHAZADO y libera el cupo (un
rechazado no debe retener titularidad ni contar en padrón ni en pago); **3 con
comentario** deja el legajo en SUBSANAR con `subsanacion_tipo="RENAPER"`.

El contrato quedó en **64 rutas**.

## Prueba contra el RENAPER real: no se pudo

Con las credenciales del `.env` no se puede validar en vivo desde este entorno.
Dos bloqueos independientes:

1. **Falta `RENAPER_API_USERNAME`.** El `.env` tiene `RENAPER_API_PASSWORD` y
   `RENAPER_API_URL`, pero `APIClient._login()` hace
   `POST /auth/login` con `{"username", "password"}` y el username llega vacío.
2. **El certificado TLS no verifica**: `unable to get local issuer certificate`.
   El TCP a :443 abre y el DNS resuelve, así que hay red; falta la CA que firma
   ese endpoint dentro del contenedor. No se desactivó la verificación TLS para
   sortearlo.

Los endpoints quedan cubiertos con la consulta mockeada, que es como ya se
probaban las pantallas.

## Validación

- `pytest -n auto`: **5561 passed, 14 skipped**.
- 5 tests nuevos en `test_api_escrituras.py` (39 en total), incluido que un error
  de negocio salga como 400 y no como 200.
- Hubo que reapuntar los `patch` de `tests/test_validacion_renaper_view_unit.py`
  y `celiaquia/tests/test_validacion_renaper_ejemplar.py` al service: el seam se
  movió con la lógica.
- Front: `lint`, `typecheck`, `test`, `build` y `api:check` en verde.

## Pendiente

Queda `legajos/{id}/editar` y `corregir-evaluacion`, con la lógica dentro de sus
vistas.
