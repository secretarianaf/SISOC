# Cambio: Permisos de la Fuerza de Trabajo en CDI (#2943)

## Alcance

Pedido del área (issue #2943): restringir quién ve y gestiona los trabajadores
de un CDI (209Trabajadores) en la UI y en el Excel de reportes. Se implementó la
matriz 4.1 del documento funcional, sin descarga del Excel para la Fuerza de
Trabajo (decisión tomada al implementar; el texto del área la incluía y la matriz
de Sistemas no, se confirma con el área).

Implementado:

- Regla única en `src/backends/cdi/centrodeinfancia/access.py`:
  `ids_centros_trabajadores_visibles` y `puede_ver_trabajadores_cdi`.
- Legajo nativo (`centrodeinfancia_detail.html`, contexto en
  `src/backends/cdi/centrodeinfancia/views.py`) y su API web
  (`web_api_legajo.py`); legajo React
  (`src/frontends/apps/sisoc/src/routes/cdiCentroDetalle.tsx`).
- Ficha, alta, edición y baja de trabajador en `views.py`
  (`_trabajadores_cdi_queryset_scoped` y el `dispatch` del alta); las APIs web de
  trabajador reutilizan esas vistas.
- Reporte Excel en `src/backends/cdi/centrodeinfancia/services_reportes.py`.
- Semilla de grupos en `src/backends/kernel/users/bootstrap/groups_seed.py`.

## Comportamiento

Ven los trabajadores de un CDI (R1), siempre dentro de su alcance territorial:

- superusuario y SIMEPI Administrador, Equipo Nacional, Auditoría y EGP;
- `CDI - Referente centro` con acceso activo a ese CDI;
- `CDI - Trabajador` cuyo legajo vinculado en ese mismo CDI es del
  subcomponente CDI con `funcion_cdi` Director/a o coordinador/a o
  Administrativo/a. La función se evalúa por centro.

Sin la regla no se muestran el contador de la cabecera, la tarjeta Trabajadores
ni sus botones (R2), y la ficha, el alta y la edición por URL responden 404 (R3).
Falla cerrado (R5): trabajador sin legajo vinculado, sin función, con otra
función o de otro subcomponente no ve nada.

Acciones por perfil (matriz 4.1): `CDI - Trabajador` suma `add_trabajador` y
`change_trabajador` en la semilla (la regla por CDI limita quién los usa) y no
elimina. `SIMEPI - Analista de datos` deja de ver trabajadores: la semilla ya no
le da permisos de trabajador y la regla lo bloquea por código aunque su grupo
conserve permisos en la base (`create_groups` solo agrega permisos).

Excel (R4): quien descarga sin la regla (hoy, Analista de datos) recibe la hoja
Trabajadores solo con encabezados y el Resumen sin las filas de trabajadores.
Detalle en `docs/implementaciones/centrodeinfancia_reportes.md`.

Fuera de alcance: `es_director_cdi` (Formulario de Calidad) sigue mirando el
campo `Trabajador.rol`, que ya no se carga (brecha 5 del issue).

## Verificación

Ver la descripción del PR para los comandos y resultados.
