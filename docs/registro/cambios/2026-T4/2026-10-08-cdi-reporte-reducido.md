# 2026-10-08 - Reporte CDI: variante reducida según rol

## Contexto
- El reporte de `/centrodeinfancia/reportes/` exportaba todas las columnas a cualquier rol con
  `auth.role_reportes_cdi`. Producto pidió que solo "SIMEPI - Administrador" y
  "SIMEPI - Equipo Nacional" accedan a todos los campos y que el resto de los roles CDI/SIMEPI
  descargue solo un subconjunto de Trabajadores y Nómina.

## Decisiones
- Dos variantes del mismo archivo: `completo` (sin cambios) y `reducido`. La hoja CDI es igual
  en ambas. En la reducida, Trabajadores trae 24 columnas y Nómina 22, en el orden del pedido.
  Diccionario y Metadatos se ajustan a la variante.
- Superusuario, SIMEPI Administrador y SIMEPI Equipo Nacional eligen la variante en la pantalla
  (por defecto, completo). El resto solo ve y descarga la reducida.
- La variante se resuelve en el servidor (`resolver_variante`): pedir `variante=completo` por URL
  sin el rol devuelve igual la reducida.
- El grupo "Admin" no está entre los roles del reporte completo: si no es superusuario, descarga
  la reducida.

## Cambios aplicados
- `centrodeinfancia/services_reportes.py`: columnas reducidas, `variantes_disponibles`,
  `resolver_variante` y parámetro `variante` en `generar_reporte_cdi_xlsx`.
- `centrodeinfancia/views_reportes.py` y `templates/centrodeinfancia/reportes.html`: selector
  "Tipo de reporte" solo para quienes tienen las dos variantes. El nombre del archivo reducido
  lleva el sufijo `-reducido`.
- `tests/test_reportes.py`: encabezados de la variante reducida, elección por rol y bloqueo del
  completo por URL.

## Riesgos y rollback
- Sin migraciones ni cambios de permisos. Rollback: revertir el commit.
