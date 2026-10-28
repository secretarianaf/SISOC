# Cambio: editor de pin en Comedores y CDI (#2778, segunda etapa)

## Alcance y comportamiento

Los formularios existentes de Comedores y CDI incorporan el editor compartido de
`src/backends/kernel/templates/components/map_pin_editor.html` junto a sus
coordenadas. El mapa y sus controles se ven por defecto; Buscar dirección ubica
el domicilio sin guardar. Al abrir la pantalla no se buscan ni completan
coordenadas automáticamente. Descartar recupera valores y deja el mapa visible.
Al buscar o mostrar coordenadas, centra el punto con zoom 18 y sin animación
para no dejar un acercamiento pendiente. No se cambia su persistencia, permisos ni alcance territorial.
CDI conserva su validación geográfica de coordenadas dentro de Argentina.

La búsqueda de direcciones reutiliza el algoritmo Georef existente, extraído de
Dispositivos a `src/backends/kernel/core/services/geolocation.py`. Dispositivos
conserva su caché, resultados persistidos y configuración de endpoint existentes.

El kernel ofrece `address_preview`, un POST con CSRF para usuarios autenticados.
Acepta exclusivamente texto de domicilio y nombres geográficos, consulta el
endpoint fijo de Georef y devuelve coordenadas o un estado de búsqueda. No lee
legajos ni autoriza escrituras sobre modelos. La edición y persistencia siguen
bajo los permisos del formulario de cada dueño. A diferencia del endpoint de
Dispositivos, este servicio público no restringe el texto de búsqueda por
alcance territorial: no consulta registros privados ni catálogos restringidos.

El navegador envía los nombres elegidos en los selectores, no sus IDs. Una
coincidencia única completa ambos campos; solo el guardado del formulario los
persiste. El movimiento del pin mantiene el domicilio textual y Descartar ajuste
recupera los valores que había al abrir el editor.

## Dueños, riesgo y despliegue

- Kernel: servicio de geocodificación, formulario/vista de previsualización,
  URL y recursos compartidos. Sin imports hacia core de entrada ni verticales.
- Comedores y CDI: únicamente inclusión del editor en sus templates.
- Dispositivos: adapta su servicio a la función compartida sin cambiar contrato.
- Configuración: registro de URLs regenerado desde la composición completa.
- Sin migraciones, paquetes, modelos ni permisos nuevos. La ruta es nueva y usa
  autenticación existente; no es un endpoint de guardado genérico.
- Requiere revisión técnica por kernel/configuración y despliegue completo más
  migrador/collectstatic para publicar los recursos, según el selector existente.
- No se hizo merge ni despliegue. Esta etapa no cierra #2778.

## Verificación

- 101 tests pasaron: búsqueda compartida más suite de Dispositivos.
- 121 tests pasaron: búsqueda compartida, formularios existentes de Comedores y
  CDI, y renderizado autenticado de ambas pantallas con el editor.
- 36 tests Node pasaron, incluido envío de nombres seleccionados y no IDs.
- Templates de editor y Comedores sin errores de lint. CDI mantiene el aviso
  H020 preexistente en la línea 12 (div vacío); no se modificó esa línea.
- Verificación visual local confirmada: Comedores muestra mapa y controles
  por defecto, búsqueda de domicilio y zoom de calle; CDI muestra el mapa y
  el botón de búsqueda sin desplegarlos.
- CI e imágenes aisladas: pendientes de publicación. No se publica sin la
  autorización solicitada previamente para el push a GitHub.
