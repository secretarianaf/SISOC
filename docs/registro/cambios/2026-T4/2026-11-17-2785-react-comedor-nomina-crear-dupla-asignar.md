# Cambio: alta de nómina y asignación de equipo técnico de comedor en React sobre G1 v1 (#2785, CO01 y CO07)

## Alcance

Dos pantallas de Espacios Comunitarios que seguían nativas. No activa React en producción y no cambia ninguna
vista, ruta ni permiso nativo.

- CO07 `comedor/asignar_dupla_form.html` (`comedores/dupla/asignar/<pk>`): listado de equipos técnicos activos con
  filtro por nombre y un botón «Asignar» por fila.
- CO01 `comedor/nomina_form.html` («Agregar a Nómina»): `comedores/<pk>/nomina/crear/` (nómina directa) y
  `comedores/<pk>/admision/<admision_pk>/nomina/crear/` (convenio con admisión).

No requieren pantalla React, y siguen nativas: `comedores/<pk>/admision/<admision_pk>/nomina/importar/` (solo POST con
redirección), `comedores/<pk>/validar/` (solo POST con redirección, ya usado por la ficha), `comedores_nuevo/<pk>`
(redirección permanente a la ficha), `comedores/editar-nomina/<pk>/` (fragmento AJAX del modal de la nómina) y
`comedores/<pk>/observacion/crear` (ya servida por `comedorObservaciones.tsx`).

Archivos:

- `src/backends/comedores/comedores/web_api_dupla_asignar.py` y `web_api_dupla_asignar_urls.py`;
  `web_api_nomina_crear.py` y `web_api_nomina_crear_urls.py`: API web.
- `src/backends/comedores/comedores/web_preview_dupla_asignar.py` y `web_preview_nomina_crear.py`: entradas de la vista previa local.
- `src/backends/comedores/comedores_runtime/web_api_urls.py`, `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado): solo líneas agregadas.
- `src/frontends/apps/sisoc/src/routes/comedorDuplaAsignar.tsx` y `comedorNominaCrear.tsx`, con sus pruebas, y
  `routes/index.ts` (solo agregados).
- Pruebas: `test_web_dupla_asignar_co07.py`, `test_web_preview_dupla_asignar_co07.py`, `test_web_nomina_crear_co01.py` y
  `test_web_preview_nomina_crear_co01.py` en `src/backends/comedores/comedores/tests/`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/asignar-dupla/<pk>/` | Comedor del alcance (404 si no), equipos activos con coordinador, técnicos y abogado, y el equipo actual |
| `POST /api/web/comedores/asignar-dupla/<pk>/` | Ejecuta la vista nativa: asigna el equipo, fija el estado «Asignado a Dupla Técnica» y deja «Dupla asignada correctamente.» (o el error nativo) para la ficha |
| `GET /api/web/comedores/nomina-crear/<pk>/` y `.../<pk>/admision/<admision_pk>/` | Búsqueda por DNI (`?query=`, con consulta a RENAPER solo si no hay un ciudadano validado), coincidencias, los tres formularios y los avisos de cupo |
| `POST` de las mismas rutas | Agrega un ciudadano existente (`ciudadano_id`) o crea uno con o sin DNI y lo suma a la nómina; redirige a la nómina o devuelve 400 con los formularios ligados y los mensajes nativos |

Acceso, en este orden: G1, el permiso de la URL nativa (`duplas.change_dupla`, `comedores.add_nomina`; el superusuario pasa
siempre) y el alcance de la vista nativa. Solo se aceptan POST `application/x-www-form-urlencoded` o `multipart/form-data`
(otro formato responde 415 sin escribir). Un rechazo no escribe nada.

Rarezas nativas conservadas, a propósito:

- El filtro de equipos solo reacciona al soltar una tecla (`keyup`) y oculta filas por el texto de la primera columna, incluida la fila vacía.
- Las dos formas de crear un ciudadano (con y sin DNI) y el modal quedan en la misma página, con los controles de la forma inactiva deshabilitados.
- El modal solo valida el estado en el cliente; un rechazo del servidor vuelve a mostrar la página con el aviso «Datos inválidos para agregar ciudadano a la nómina.».

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada. Ver el informe de la entrega para los resultados de G1 y de la
comparación visual.

## Limitaciones

- No se agregan restricciones ni se modifican las vistas nativas.
- La consulta a RENAPER del buscador ocurre en la API igual que en la vista nativa (una por búsqueda); no se prueba contra el servicio real.
