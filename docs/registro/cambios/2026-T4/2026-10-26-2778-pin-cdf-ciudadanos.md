# Cambio: pin en Centros de Familia y Ciudadanos (#2778, tercera etapa)

## Alcance

- Centros de Familia incorpora latitud y longitud opcionales con seis decimales,
  validadores de rango y validación del par en el formulario. La migración
  `0017_centro_latitud_centro_longitud.py` agrega columnas anulables; no transforma
  ni borra domicilios previos. Aplicar antes de ejecutar el código actualizado.
- Su formulario muestra el editor junto a las coordenadas y conserva las
  acciones existentes de guardar/cancelar. La consulta prioriza coordenadas
  guardadas y mantiene búsqueda por domicilio si faltan.
- Ciudadanos expone sus coordenadas existentes en el formulario, con límites
  geográficos y validación del par. El editor usa la búsqueda compartida.
- El mapa de consulta de Ciudadanos usa el helper `google_maps_query` existente
  para normalizar números y mostrar también coordenadas cero; utiliza iframe
  como los otros legajos, en lugar de interpolar decimales localizados en JS.

## Permisos y riesgo

Se conserva el guardado de las vistas existentes. En CDF, la edición mantiene
el control de referente, superusuario o SSE de CentroUpdateView. Ciudadanos
conserva sus permisos de vista y formulario. El pin no escribe por un endpoint
alternativo ni cambia el domicilio textual.

Requiere revisión técnica: migración de CDF y cambios en el kernel. Sin nuevas
dependencias, modelos, settings ni permisos. El rollback de la migración elimina
los valores de las dos columnas nuevas; respaldarlos si se deben conservar.

## Verificación

- 39 tests pasaron: formularios de identidad de Ciudadanos, formulario de CDF,
  validación del par/rangos, guardado sin modificar domicilio, consulta del mapa
  de CDF y renderizado de los cuatro formularios integrados.
- Pylint de los tres archivos de aplicación: 10/10. Black aplicado. Cuatro
  templates sin errores de lint.
- Migración aplicada en MySQL local; makemigrations --check --dry-run sin cambios.
- Runtime aislado cdf_runtime: check sin problemas.
- Se corrigió el listado de campos visibles por tipo de CDF: Faro y Adherido
  incluyen latitud/longitud. Sin tipo no se muestra un mapa aislado; al elegir
  tipo aparece junto al domicilio y se recalcula su tamaño. Tres tests Node de
  esta regresión pasaron (20 junto al editor compartido).
- Chrome local automatizado: elegir Faro y Adherido muestra ambos campos y
  mapa visible. La URL de centro_form.js lleva versión para evitar la copia
  anterior en caché que ocultaba coordenadas y no mostraba el mapa.
- Quien pidió confirmó visualmente CDF tras corregir visibilidad/caché y
  Ciudadanos con sus coordenadas, mapa y botón de búsqueda. CI pendiente.
- Sin publicación, merge ni despliegue. Falta VPSL para completar el inventario
  del #2778, documentado en `docs/plans/2026-T4/2026-10-26-2778-pin-interactivo.md`.
