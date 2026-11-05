---
name: sisoc-figma-ds
description: >
  Interpretar e implementar el Nuevo DS SISOC del archivo Figma en pantallas web.
  Usar al diseñar o revisar UI, tokens, temas claro/oscuro y componentes SISOC/MUI
  vinculados a ese archivo; no aplicar a otros sistemas de diseño.
---

# Nuevo DS SISOC en Figma

Fuente: [Pantallas](https://www.figma.com/design/BUiPDYtrg9gHGJj4ZfBCtt/Nuevo-DS-SISOC--copia-?node-id=607-6827), [Componentes](https://www.figma.com/design/BUiPDYtrg9gHGJj4ZfBCtt/Nuevo-DS-SISOC--copia-?node-id=28-12456) y [Tokens](https://www.figma.com/design/BUiPDYtrg9gHGJj4ZfBCtt/Nuevo-DS-SISOC--copia-?node-id=22-2168). Extracción y verificación visual: 2026-10-05.

## Cómo usarlo

1. Identificar la pantalla en [pantallas.md](references/pantallas.md) y el componente en Figma; no deducir comportamientos de un nombre de capa.
2. Leer [tokens.md](references/tokens.md) para colores, tipografía, espaciado y modos; [elevacion.md](references/elevacion.md) cuando se necesiten sombras exactas. Consumir roles semánticos (`color/background/paper`, `color/text/primary`, etc.) y resolverlos según Light o Dark.
3. Leer [componentes.md](references/componentes.md) para saber qué familias existen y [variantes.md](references/variantes.md) cuando importe un estado o eje concreto. Buscar primero la familia SISOC o MUI correspondiente antes de crear una nueva.
4. Trasladar a la tecnología real del repositorio, respetando sus patrones y accesibilidad. Validar en ambos modos y en los estados que estén documentados para el componente.

El archivo tiene la colección `Sisoc Tokens` con 130 variables en modos Light y Dark, más `Icon Context` con una variable contextual. La página Pantallas contiene 28 frames claros y 28 oscuros. La página Componentes contiene 46 sets con variantes, 32 componentes principales individuales y 48 iconos individuales. El generador DESIGN.md/SKILL.md de Figma sólo exportó 40 colores, 19 estilos de texto y 12 espacios; su lista de 40 “familias” mezcla nombres de variantes de botón y no representa el catálogo real. Esta skill contrasta esa exportación con una lectura directa mediante Figma Plugin API.

## Reglas de decisión

- Usar nombres y valores de la colección Figma como referencia para este DS. Mantener Light y Dark separados; un valor de Light no sirve automáticamente en Dark.
- Para colores de texto, superficies y estados, preferir roles semánticos sobre hexadecimales de la escala base.
- No inventar anatomía, propiedades, estados, breakpoints de comportamiento ni reglas de interacción donde Figma sólo expone un nombre de componente.
- `MUI/*` nombra componentes base; `Sisoc/*` nombra composiciones propias. Reutilizar el patrón existente en el código antes de crear una abstracción nueva.
- Verificar foco visible, contraste, teclado y contenido largo en la implementación. Figma no sustituye esa validación.

## Relación con la skill anterior

`.agents/skills/tema-verde-institucional` documenta una traducción previa del tema verde. Para el **Nuevo DS SISOC (copia)**, la colección Figma consultada aquí tiene prioridad cuando hay discrepancias: por ejemplo `color/primary/light` Light es `#379F9B`, `color/nav/surfaceSelected` Light es `#033F3C` y Dark es `#0A5D58`, y `color/text/secondary` Dark es `#A8A29E`. No mezclar los dos mapeos sin decidir explícitamente cuál diseño se implementa.
