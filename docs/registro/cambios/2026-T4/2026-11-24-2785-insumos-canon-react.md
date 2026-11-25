# Insumos React en sus URLs canónicas (#2785)

El listado, alta, edición y baja de Insumos y de sus categorías se abren en
React bajo `/insumos/`. El menú, los enlaces de acción, los filtros, la
paginación y el retorno de los formularios conservan las rutas canónicas.
La vista previa bajo `/v2/sisoc/insumos/` sigue disponible para comparación.

## Activación y vuelta atrás

- La clave `insumos` participa en `REACT_VERTICALES_ACTIVAS`; necesita el
  `index.html` de `SISOC_REACT_BUILD_DIR`, como las demás entradas del core.
- Quitar `insumos` de una lista explícita o deshabilitar la activación
  devuelve las páginas a Django. Los nombres usados por `reverse()` no cambian.
- Las entradas solo reemplazan GET/HEAD de las ocho páginas. Conservan el
  permiso correspondiente y el 404 de objetos inexistentes o páginas inválidas.
  Los POST a las URLs originales y la descarga protegida siguen en Django.
- Los formularios React usan la API de sesión y CSRF que ya existía. El HTML
  es privado y no se almacena en caché; los recursos congelados se sirven
  bajo `/insumos/react/assets/`, sin depender de otra clave de activación.

## Verificación

- Pytest: entradas reales con el flag activo y desactivo, permisos, descarga,
  POST nativo y resolución de assets en SQLite sintético.
- Vitest: acciones, filtros, paginación y retorno canónicos, y preservación
  de la vista previa.
- Chromium sobre un backend local aislado y un build congelado: en escritorio
  (1440 × 900), inicio de sesión, filtro por teclado y descarga del PDF de
  prueba; en móvil (390 × 844), navegación a categorías, orden de Tab en el
  formulario, alta sintética y persistencia al recargar la lista canónica.
  Se bloquearon fuentes y estilos externos; no es una comparación visual.
- Esta unidad no retira templates, no acredita aceptación humana ni despliegue.
  La validación acumulada de #2785 debe confirmar las demás pantallas.

