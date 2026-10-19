# Kernel: layout claro compartido y barra lateral unificada

Fecha: 2026-10-15. PRs: #2705, #2706 y #2707 (registro retroactivo,
2026-10-19). Antecedente:
`docs/registro/cambios/2026-T4/2026-10-15-inspecciones-panel-backoffice.md`.

## Qué cambia

- `includes/base.html` expone bloques para que una pantalla cambie el marco
  sin copiar el layout: `tema`, `script_tema`, `clase_body`, `cabecera` y
  `barra_lateral`. Sus valores por defecto mantienen el tema oscuro y la
  barra azul superior del resto de SISOC.
- La barra lateral (`includes/sidebar/base.html`) recibe `con_logo` y
  `tema_lateral` explícitos desde `base.html`. Sin ellos Django registraba
  errores de variable faltante en todas las pantallas (#2706).
- Layout claro nuevo (`includes/base_claro.html`, `includes/cabecera_clara.html`,
  `static/custom/css/layout_claro.css`): tema claro, cabecera blanca con
  breadcrumb, iniciales y rol del usuario, barra lateral con logo. El
  contexto lo arma `core.services.layout_claro.contexto_layout_claro(usuario,
  migas)`; `base.js` conserva el tema claro que renderiza el servidor.
- Lo usan **Inicio** (`templates/inicio.html`) y el backoffice de
  **Inspecciones escolares** (`inspecciones/base_layout.html`). El resto del
  backoffice sigue en `includes/base.html`.
- En **todo SISOC** la barra lateral (`includes/sidebar/opciones.html`) deja
  de mostrar el panel de usuario y marca el ítem activo con la línea dorada.
  Afecta a todos los usuarios del backoffice.

## Cómo usarlo en una pantalla nueva

Extender `includes/base_claro.html`, llenar `contenido` (y `head_claro` si
hace falta CSS propio) y sumar al contexto
`contexto_layout_claro(request.user, [{"text": ..., "url": ...}, ...])`; el
último ítem de las migas es la página actual.

## Validación

`src/backends/inspecciones/tests/test_inspecciones_layout.py` y el test de
VAT que detecta variables faltantes en la barra de búsqueda.
