# Componentes de Nuevo DS SISOC

Fuente: [🧩 Componentes, Figma](https://www.figma.com/design/BUiPDYtrg9gHGJj4ZfBCtt/Nuevo-DS-SISOC--copia-?node-id=28-12456). Inventario corroborado mediante Figma Plugin API el 2026-10-05: 46 sets, 32 componentes principales individuales y 48 iconos individuales. Los nombres indican existencia, no contrato de implementación ni comportamiento. Los ejes y cantidades verificadas están en [variantes.md](variantes.md).

## Bases MUI

`Alert`, `Avatar`, `Breadcrumbs`, `Button`, `Checkbox`, `Circular progress`, `FormControlLabel`, `FormHelperText`, `IconButton`, `Linear progress`, `Link`, `List item`, `Radio`, `Select`, `Snackbar`, `Step`, `Tab`, `TablePagination`, `Text field`, `Timeline item`.

El set `MUI/Button` contiene 90 variantes: `Size` Small/Large, `Variant` Contained/Outlined/Text, `Color` Primary/Secondary/Error y `State` Enabled/Hovered/Focused/Pressed/Disabled. También expone propiedades de icono inicial e intercambio de icono. La exportación del plugin se cortó en 40 entradas; la cantidad y los ejes se verificaron directamente en Figma.

## Composiciones SISOC

- Navegación y estructura: `Header`, `Footer`, `Public header`, `Hero`, `CTA band`, `Module card`, `Module note bar`, `Navigation card`, `Program icon`, `Program card`, `Tabs Panel`.
- Filtros y datos: `Filter bar`, `Applied filter`, `Filter chip`, `Data field`, `Data check row`, `Personal data panel`, `CFP data panel`, `CFP row`, `Chart segment`, `Key figure`, `Stat card`, `Feature card`.
- Filas de dominio: `Attendance row`, `Class row`, `Enrollee row`, `Schedule row`, `Contact row`, `Location row`, `Commission row`, `Course row`, `Family row`, `Pending row`, `Status row`.
- Paneles y estados: `Program panel`, `Socioeconomic panel`, `Notice panel`, `Notice item`, `Service status`, `Alert message`, `Incompatibility alerts`, `Liquidation panel`, `Preliquidation table`, `Monthly circuit stepper`.
- Trabajo y tickets: `Task card`, `Recent card`, `Transfer card`, `Ticket inbox`, `Tickets panel`, `Ticket card`, `Priority label`, `Scoring selector`, `Scoring card`, `Score chip`, `Titular card`, `Requirement chip`, `State chip`, `Login card`.

La página incluye además `Iconos — librería Light` y `DOC — Cómo se arma el sidebar`; son recursos de referencia, no familias de componente. El inventario completo de iconos y sets está en [variantes.md](variantes.md). La página [🖥️ Pantallas](https://www.figma.com/design/BUiPDYtrg9gHGJj4ZfBCtt/Nuevo-DS-SISOC--copia-?node-id=607-6827) muestra el uso contextual; sus 56 frames están listados en [pantallas.md](pantallas.md).

## Límite de la extracción automática

El plugin `DESIGN.md Generator` devolvió 40 supuestas “component families” en la página de componentes, pero listó `MUI`, `Sisoc` y luego propiedades individuales de variantes como si fueran familias. En las páginas Tokens y Pantallas devolvió 0. El inventario se verificó mediante Figma Plugin API y no declara anatomía, API, espaciados internos ni interacciones.
