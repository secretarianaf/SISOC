# Cambio: menú lateral de tercer nivel y reglas de ruta del marco React (#2785)

## Alcance

Corrige la paridad del menú lateral de los marcos React compartidos con
`src/backends/kernel/templates/includes/sidebar/opciones.html`. Antes, el
marco oscuro (`routes/SisocShell.tsx`) dibujaba los grupos anidados (por
ejemplo «Legajos > Centro de Infancia > Ver/Reportes») como ítems de primer
nivel y solo abría una rama cuando la URL coincidía exactamente con un enlace;
el layout claro (`routes/ClaroFrame.tsx`) tenía el mismo defecto en los grupos
anidados. No cambia el backend ni el DTO de navegación: el árbol que devuelve
`build_web_navigation` ya trae el anidamiento.

Archivos:

- `src/frontends/apps/sisoc/src/routes/SisocShell.tsx`: marcado por nivel,
  reglas de ruta del template, ranura `headerItems` y prop `activePath`.
- `src/frontends/apps/sisoc/src/routes/ClaroFrame.tsx`: usa el mismo marcado y
  las mismas reglas.
- `src/frontends/apps/sisoc/src/identityFrames.tsx`: `legacyIdentityFrame`
  acepta `activePath` como último argumento opcional.
- `src/frontends/apps/sisoc/src/routes/cdiFrame.tsx`: el botón «Consultas» pasa
  por `headerItems`; se quita el portal que lo insertaba en el DOM de la
  cabecera.
- Pruebas: `src/frontends/apps/sisoc/src/routes/shellNavigation.test.tsx`.

## Comportamiento

| Nivel | Marcado (igual al template) |
| --- | --- |
| Grupo de segundo nivel | `li.nav-item` con `a.nav-link nav-dot ms-2` (más `active`) y flecha |
| Enlace de tercer nivel | `a.nav-link ms-4` con el ícono `bi-arrow-return-right` |
| Grupo de tercer nivel | `li.nav-item ms-4` con `a.nav-link`, ícono de retorno y flecha |
| Enlace de cuarto nivel | `a.nav-link nav-dot ms-4` |
| Celiaquía | enlaces `nav-link ms-2` con sus íconos propios; la rama nunca se abre sola |

Apertura y resaltado: el template evalúa `'<fragmento>' in pagina_actual`. El
marco copia esas condiciones por id de nodo (por ejemplo
`'centrodeinfancia' in pagina_actual` para el grupo y
`'centrodeinfancia/reportes'` para el enlace) y las evalúa sobre la ruta
actual, así las subpáginas (crear, editar, ficha) mantienen la rama abierta y
la entrada marcada. «Administración del sistema» nunca se abre sola, como en el
template. Si un nodo no tiene regla, sigue la coincidencia exacta anterior.
Las reglas solo aplican a los marcos de páginas nativas (`previewLinks=false`);
la vista previa `/v2/sisoc/insumos/` conserva su coincidencia exacta.

También: «Ver Comunicados» ya no muestra el ícono de su grupo, «Parametrías de
Voucher» muestra `bi-ticket-perforated` y OCR `bi-file-text`, como el template.

`activePath` (opcional) permite que una página evalúe las reglas sobre otra
ruta; lo usan los marcos de montos, Actividades PNUD y Equipos Técnicos (que
también lo pasan por `legacyIdentityFrame`). Con las reglas de fragmento ya no
es necesario para esas pantallas, pero se mantiene compatible. `headerItems` (opcional)
recibe los `nav-item` que `includes/header.html` agrega antes del botón de
salida.

## Verificación

- Pruebas nuevas en rojo sobre la base (19 de 22) y en verde con el cambio;
  vitest del workspace, `tsc`, `eslint` y `vite build` en verde.
- Capturas de la build base contra la build candidata en todas las pantallas
  React existentes (insumos, categorías, login, identidad, grupos, inicio,
  contraseña, lotes de usuarios, actas de Inspecciones), en escritorio y móvil,
  con un caso de superusuario de menú grande; y nativo contra candidato en los
  casos CDI (regla S13).

## Limitaciones

- «Mi cuenta» conserva `order-0`. El template usa `mt-auto`, pero en el marco
  oscuro nativo esa clase no mueve el ítem; aplicarla en React lo empujaba al
  pie (hasta 371 px).
- Los subgrupos de Tableros dependen de `item.activo`, que calcula el servidor
  y el DTO no expone; siguen con coincidencia exacta.
- El menú móvil sigue fuera de la comparación (dispensa de S2).
