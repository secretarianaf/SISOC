---
name: tema-sisoc
description: >-
  Aplicar o revisar el sistema de diseño SISOC en interfaces React con Material UI:
  tema claro y oscuro, colores semánticos, navegación, tipografía y componentes.
  Usar al construir o modificar estas interfaces; no aplicar sus colores como guía
  genérica de marca a otros productos.
---

# Sistema de diseño SISOC

Usá este skill para implementar interfaces fieles al archivo de Figma *Nuevo DS SISOC*. Las variables de Figma son la fuente de verdad. Los archivos incluidos son una copia de la especificación entregada: si Figma cambió, confirmá los nuevos valores antes de actualizar la implementación. No presentes las tablas o ejemplos de este skill como una segunda fuente de tokens.

## Referencias: leer solo lo pertinente

- **Tema, paleta, tipografía o estilos globales:** consultá [theme.ts](references/theme.ts) y [especificacion-theme.md](references/especificacion-theme.md). Para un proyecto MUI, integrá `getTheme(mode)` del archivo adjunto; no reconstruyas el tema desde un resumen.
- **Un componente o flujo:** consultá [especificacion-componentes.md](references/especificacion-componentes.md) y su descripción en Figma cuando esté disponible. Allí están el componente MUI de base, sus variantes y sus reglas de comportamiento.
- **Implementación completa del sistema:** seguí [hoja-de-ruta-implementacion.md](references/hoja-de-ruta-implementacion.md). Inspeccioná Figma para la jerarquía y las medidas exactas de cada pantalla. Si no hay acceso, explicá qué detalle visual queda sin verificar.

## Decisiones que no se deben perder

1. **Dos modos con los mismos componentes.** `getTheme('light')` es el valor por defecto; `getTheme('dark')` cambia los tokens, no el árbol de componentes. Si la aplicación guarda una preferencia de modo, respetá su mecanismo existente. La persistencia no forma parte de los tokens del diseño.
2. **Colores por rol.** Consumí `theme.palette.*` y las extensiones de `theme.ts`; no escribas hex en componentes. `primary` es marca; `secondary` es ámbar. `error`, `warning`, `info` y `success` expresan estados semánticos. El verde de marca no equivale automáticamente a “aprobado”. Los valores `brand` de `theme.ts` son registro del logo, no colores de interfaz.
3. **Texto de severidad legible.** Sobre una superficie neutra usá `palette.{error,warning,info,success,secondary}.text`. Sobre `main` de esa familia usá `.contrastText`. No uses `.dark` como sustituto de `.text`: en modo oscuro puede fallar el contraste. Para íconos ámbar sobre blanco, consultá la regla específica de `secondary.dark` en la especificación del tema.
4. **Navegación con tokens propios.** Header, Sidebar, Footer y Navigation card usan `palette.nav`. En claro `nav.surface` es `#045F5B`; en oscuro es `#073B38`. En oscuro la barra tiene mayor luminancia que la página y se distingue por el tono teal y el borde. El primer nivel seleccionado usa `nav.surfaceSelected`; el segundo y tercero usan `nav.selected`. Aplicá la clase `SisocNav-section` a los ítems de primer nivel para activar el override de `MuiListItemButton`. No reemplaces esta distinción por un único fondo activo ni agregues bordes de selección inventados.
5. **Tipografía y medidas del tema.** Cargá Roboto 300/400/500/700. Conservá las variantes estándar y las seis propias (`h4Bold`, `subtitle1Medium`, `buttonSmall`, `buttonLarge`, `chip`, `captionBold`). Usá `theme.spacing()`, `theme.radius`, `theme.border` y `theme.iconSize`. Los botones mantienen el tratamiento tipográfico y los overrides de `theme.ts`, incluida la transformación a mayúsculas.
6. **Componentes MUI y composiciones Sisoc.** Respetá la distinción `MUI/X` frente a `Sisoc/X` en la especificación. Los Chips de estado, puntaje, requisito y filtro tienen usos distintos. El grupo de filtros mantiene la selección en el padre. Las tarjetas clickeables usan `ButtonBase`; sus chips internos son solo informativos para evitar controles interactivos anidados.
7. **Severidad calculada.** Para Score chip, Circular progress y Linear progress, con requerido de 100: `0 → error`, `1…99 → warning`, `100 o más → success`. Derivá el color del valor; no lo elijas de forma independiente. La Stat card es una excepción: su color comunica el significado del dato. Para State chip, seguí la tabla de estados de la especificación de componentes.
8. **Navegación y desborde.** En el Hub, el Sidebar muestra en Módulos solo los programas seleccionados; Administración y Tableros conservan todo su contenido. El bloque del menú tiene scroll vertical y Cerrar Sesión permanece fuera de ese scroll. Las tablas usan `TableContainer` con scroll horizontal bajo sus anchos mínimos documentados.

## Al implementar o revisar

- Reutilizá los overrides de `theme.ts` para Button, Chip, Tabs, Paper, Card, OutlinedInput, AppBar, Drawer, ListItemButton y Alert. Evitá duplicarlos en `sx` salvo necesidad concreta del componente.
- En pantallas o componentes, inspeccioná la descripción correspondiente en Figma antes de decidir layout, medidas o variantes. Si falta acceso, implementá solo lo respaldado por las referencias y señalá la limitación.
- Comprobá ambos modos en un catálogo o pantalla de prueba: botones por tamaño y variante, Alert por severidad, chips y navegación seleccionada. Verificá contraste de texto y controles, las seis variantes tipográficas y el desborde de sidebar y tablas.
- Para implementaciones sin MUI, traducí los **roles y reglas** a tokens equivalentes. No copies el código de `createTheme` ni supongas que la mera coincidencia de hex reproduce los componentes.
