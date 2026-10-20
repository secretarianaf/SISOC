# Ejemplo: "quiero filtrar el listado de comedores por un dato más"

Mismo caso que `.agents/skills/cambio-guiado/ejemplo.md`; acá se muestran solo
los pasos propios de esta skill. Antes de usarlo, confirmar en el código que el
caso sigue vigente.

## 1. Rama

```bash
git status            # limpio
git fetch origin
git switch -c feat/<issue>-filtro-otra-categoria origin/development
```

## 2. Lo que se le devuelve a quien pidió

> Entendí esto: hoy en el listado de comedores no podés filtrar por lo que se
> carga en "Otra categorización". Después del cambio vas a tener ese filtro: si
> escribís "merendero", solo vas a ver los comedores que tienen eso cargado.
> ¿Es así?

## 3. Implementación

Según `cambio-guiado`: se agrega el campo en
`src/backends/comedores/comedores/services/filter_config/impl.py`, con tests en
`src/backends/comedores/tests/test_comedores_filter_config_unit.py`.

## 4. Verificación visual guiada

> 1. Abrí http://localhost:8001/comedores/ y entrá con un usuario de prueba que
>    vea comedores (te paso cuál).
> 2. Tocá "Filtros", elegí "Otra categorización" y escribí "merendero".
>    Tendrías que ver solo comedores que tienen esa palabra en ese dato.
>    ¿Qué ves?
> 3. Ahora escribí una palabra que no exista, por ejemplo "zzz". Tendría que
>    aparecer el listado vacío, sin errores. ¿Qué ves?
> 4. ¿Es lo que querías?

Si responde "en el paso 2 me aparecen comedores sin esa palabra", se corrige, se
corren los tests y se repite desde el paso 1.

## 5. PR

Título: `feat(comedores): filtrar por otra categorización`.
En "Pruebas Manuales":

> Verificación visual en entorno local con quien pidió: filtro con "merendero"
> (solo aparecen los que lo tienen) y con "zzz" (listado vacío, sin error).
> Confirmado: "es lo que quería".
