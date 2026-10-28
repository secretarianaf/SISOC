# INET: preservar la interfaz vigente

Instrucción del usuario del 2026-10-06: realizó mejoras en pantallas, visuales y
ubicaciones. La implementación actual es la base para las siguientes modificaciones.

- Antes de editar, releer los archivos actuales del flujo afectado; no reconstruir
  la interfaz desde resúmenes de conversaciones o versiones anteriores.
- Conservar el orden de bloques, campos, botones y columnas, la navegación, las
  pestañas, la ubicación de los diálogos y el comportamiento responsive vigente.
- Conservar colores, tipografía, tamaños, espaciados y variantes de componentes en
  ambos modos. Revisar también `../../packages/ui/src/theme.ts` y
  `../../packages/ui/src/layout.tsx` cuando corresponda: son compartidos con otras apps.
- Las correcciones de lógica, API o permisos deben mantener esta composición.
  Si requieren alterar la interfaz, explicar el impacto concreto antes de hacerlo;
  un pedido explícito del usuario de modificarla tiene prioridad.
- `docs/implementaciones/inet_react.md` documenta las pantallas y reglas vigentes;
  no reconstruir versiones anteriores ni revertir mejoras posteriores del usuario.
- Este registro no certifica una nueva prueba visual o funcional. Verificar el
  flujo afectado cuando una modificación futura lo requiera.
