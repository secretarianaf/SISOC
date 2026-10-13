# 2026-10-13 — Mapa de dispositivos (#2676)

Issue: https://github.com/secretarianaf/SISOC/issues/2676

## Comportamiento

El listado de dispositivos incorpora el botón **Mapa de dispositivos**, a la izquierda de Resetear/Agregar. Abre `/dispositivos/mapa/` conservando la búsqueda y los filtros. El listado también ofrece Ver en mapa para seleccionar un dispositivo y Ver detalle como acción separada.

La nueva pantalla muestra puntos individuales con Leaflet 1.9.4 y teselas OpenStreetMap. La ficha de cada punto incluye institución, tipo, dirección, representante (`responsable_nombre_completo`), teléfono de contacto (`telefono_prefijo` + `telefono_numero`) y enlace al detalle. No existe un teléfono separado de representante. Se conserva la atribución de OpenStreetMap y se usa el CDN autorizado por CSP, con Subresource Integrity (`integrity`) en el JS y CSS de Leaflet.

El desplegable inferior utiliza la tabla y el único buscador combinable institucional. Provincia es un selector con las provincias del alcance del usuario (no del resultado filtrado, para poder cambiarla sin resetear) y Estado de ubicación permite filtrar ubicados, pendientes, ambiguos, sin coincidencia y servicio no disponible. Los filtros persistidos se aplican en backend y el estado se filtra en navegador; ambos afectan tabla y marcadores. Resetear limpia los filtros sin salir del mapa. No aparece el botón Mapa de dispositivos en la propia pantalla del mapa.

La tabla muestra 15 dispositivos por página con Volver, números compactos y Continuar, sin recargar ni volver a geocodificar. El mapa conserva todos los puntos filtrados. Ver en mapa centra el dispositivo a zoom 16, abre la ficha y resalta la fila; seleccionar un punto activa la página de su fila. La carga posterior no cambia el encuadre elegido. Ver en mapa se habilita únicamente cuando hay una ubicación resuelta.

## Geocodificación y persistencia

`/dispositivos/<pk>/ubicacion/` consulta Georef, servicio oficial argentino, con calle/altura, provincia y localidad; si no hay coincidencias prueba departamento con el nombre del municipio. Solo una coincidencia válida genera un punto. Resultados múltiples se consideran ambiguos. No se utiliza un centro municipal como ubicación de una dirección.

La migración `dispositivos/0006_dispositivo_ubicacion_georef.py` agrega `ubicacion_georef`, JSON interno no editable con coordenadas y firma de calle, altura, IDs/nombres de municipio y provincia. Los resultados definitivos (ubicado, ambiguo, sin coincidencia) se reutilizan sin expiración si la firma coincide, así una dirección ambigua no vuelve a consultar Georef en cada carga del mapa; editar dirección invalida el resultado y cambiar nombre/contacto/tipo no lo invalida. El mapa recibe los puntos guardados en su respuesta y los dibuja primero sin nuevas consultas. La escritura condicionada a la dirección original protege ediciones concurrentes y no modifica `updated_at`.

La cache por dirección conserva resultados positivos por 30 días y negativos por 1 día. Los resultados definitivos se persisten incluso cuando vienen de cache; la indisponibilidad del servicio no se guarda. Las consultas son secuenciales, con timeout de 8 segundos por consulta, y se detienen ante indisponibilidad del proveedor. Las ubicaciones guardadas siguen mostrándose. La URL del proveedor se puede configurar con `DISPOSITIVOS_GEOREF_URL` en settings.

## Permisos y límites

Ambas rutas requieren `dispositivos.view_dispositivo` y conservan el alcance territorial del listado. La geocodificación envía solo la dirección al proveedor, sin CUIT, DNI ni contactos. El endpoint de ubicación responde con `Cache-Control: private, no-store`.

Un punto por **cada** dispositivo, criterio del issue, depende de resolver las direcciones ambiguas/sin coincidencia o incorporar coordenadas verificadas. No hay localidad propia en Dispositivo y municipio/departamento no siempre coinciden. La normalización del proveedor no equivale a confirmación humana en terreno. La implementación está validada localmente; no se desplegó ni verificó en homologación.

## Validación y operación

Tests de backend cubren permisos, alcance territorial, búsquedas, filtros, contactos, selección, cache, persistencia, invalidación por cambios y protección de ediciones concurrentes. Las pruebas de JavaScript cubren filtros, paginación, fichas, marcadores y reutilización de ubicaciones; se incorporan al job de JavaScript del PR. No realizan llamadas externas.

Aplicar la migración con el migrador antes de servir el código nuevo. En Docker local ya se aplicó sin modificar los 300 registros de prueba. Para revertir, quitar primero el código que usa el campo y luego revertir la migración; solo se pierden las coordenadas derivadas, que pueden resolverse nuevamente.

El botón de acceso al mapa en `components/search_bar.html` es genérico: recibe `map_url` y `map_text` (por defecto "Ver mapa"); el listado de dispositivos pasa "Mapa de dispositivos".
