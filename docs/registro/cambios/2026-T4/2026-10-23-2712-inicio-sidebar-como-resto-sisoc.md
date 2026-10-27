# Cambio: Inicio y barra lateral vuelven a la vista del resto de SISOC (#2712)

## Alcance

Con el backoffice de Inspecciones escolares (#2705, #2706, #2707; ver
`docs/registro/cambios/2026-T4/2026-10-15-kernel-layout-claro-barra-lateral.md`)
la pantalla de Inicio pasó al layout claro y la barra lateral de todo SISOC
perdió el panel de usuario y cambió el estilo del ítem activo. El issue #2712
pide que Inicio y la barra lateral se vean como el resto de SISOC, tomando como
referencia la vista anterior.

Se implementó:

- `src/backends/kernel/templates/inicio.html` vuelve a extender
  `includes/main.html`, y `core.views.inicio_view` vuelve a pasar solo
  `ocultar_volver`. `static/custom/css/inicio.css` recupera su selector original.
- `src/backends/kernel/templates/includes/sidebar/opciones.html` recupera el
  panel de usuario (avatar, nombre y rol).
- `src/backends/kernel/static/custom/css/main.css` recupera el ítem activo en
  texto dorado, sin línea lateral ni fondo.
- En la misma barra lateral, el grupo "Legajos" ahora también se abre en las
  rutas `inspecciones/`, para que "Inspecciones escolares" quede marcado como
  pasa con el resto de los legajos. Antes ese grupo quedaba cerrado.
- El estilo de barra lateral de Inspecciones (sin panel de usuario, línea dorada
  y fondo oscuro en el ítem activo) queda acotado a `body.insp-cuerpo` en
  `src/backends/kernel/static/custom/css/layout_claro.css`.

## Comportamiento

- Inicio: barra azul superior con el logo, tema oscuro del marco, panel de
  usuario en la barra lateral, sin cabecera blanca ni breadcrumb.
- Barra lateral en todo SISOC: panel de usuario arriba e ítem activo en dorado.
- Inspecciones escolares no cambia: sigue con su layout claro y su barra
  lateral sin panel de usuario.
- `includes/base_claro.html` y `core.services.layout_claro` siguen en el kernel;
  ahora los usa solo Inspecciones.
- Sin migraciones ni cambios de datos.

## Verificación

- `pytest src/backends/inspecciones/tests src/backends/kernel/core/tests/test_sidebar_menu.py src/backends/kernel/tests/test_boton_volver_unificado.py src/backends/kernel/tests/test_header_branding_unit.py src/backends/sisoc_core/encuestas/tests -n auto`:
  505 passed, 4 skipped. `test_inspecciones_layout.py` ahora fija que Inicio
  usa el marco oscuro con panel de usuario, que el layout claro oculta ese panel
  y que en Inspecciones el grupo Legajos queda abierto con el ítem marcado
  (23 passed después de este último agregado).
- `black --check`, `pylint` (10.00/10) y `djlint --check` sobre los archivos tocados: sin cambios.
- Falta la verificación visual en el ambiente y la aceptación del issue.
