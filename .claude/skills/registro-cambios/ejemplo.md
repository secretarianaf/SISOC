# Ejemplo: registrar un cambio en un vertical

Caso basado en #2724 (DataCalle), cuyo registro real es
`docs/registro/cambios/2026-T4/2026-10-19-2724-datacalle-programa-local-provincial.md`.

## Pedido

"En el relevamiento de DataCalle, reemplazar la opción «Volver al trabajo» por
«Programa Local / Provincial»."

## 1. ¿Hace falta registrar?

Sí: cambia lo que ve el usuario en la ficha del caso y lo que publica
`GET /api/datacalle/catalogos/`. No hay decisión de arquitectura nueva, así que
no hace falta un archivo en `decisiones/`.

## 2. Ruta

Fecha 2026-10-19 → trimestre T4 →
`docs/registro/cambios/2026-T4/2026-10-19-2724-datacalle-programa-local-provincial.md`.

## 3. Contenido

- **Alcance:** código nuevo `programaLocalProvincial` (no se reusa el de
  «Volver al trabajo» porque es otro programa); `volverAlTrabajo` queda
  retirada.
- **Comportamiento:** los casos viejos siguen mostrando «Volver al trabajo»; la
  API publica la versión 4.1.1 y hay que desplegarla junto con la app.
- **Verificación:** el test nuevo del instrumento 4.1.1 y el pin de versión del
  test de la API.

## Contraejemplo: cuándo no registrar

Corregir un typo en un docstring o renombrar una variable local sin efecto
observable no se registra. En la entrega: "Sin registro: cambio trivial sin
impacto funcional".
