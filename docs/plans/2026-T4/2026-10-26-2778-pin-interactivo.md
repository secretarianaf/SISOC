# Plan: ajuste de ubicación con pin (#2778)

## Contrato

Arrastrar el pin actualiza coordenadas del formulario, sin modificar el domicilio.
Guardar confirma la ubicación; cancelar la edición conserva la ubicación guardada.
Los permisos y alcances propios de cada módulo siguen controlando el guardado.
No se escribe desde el navegador a un endpoint genérico de modelos.

## Inventario y etapas

| Módulo | Mapas encontrados | Persistencia y trabajo pendiente |
| --- | --- | --- |
| Dispositivos | Alta/edición y legajo; mapa general | Latitud/longitud del #2777. Primera integración del editor compartido. El mapa general permite consultar; la edición se hace en el formulario autorizado. |
| Comedores | Legajo | Editor integrado en formulario; mantiene mapa de consulta y guardado propios. Verificación visual pendiente. |
| CDI | Legajo | Editor integrado en formulario, con validación argentina existente. Verificación visual pendiente. |
| Centros de Familia | Legajo | No tiene coordenadas en Centro. Requiere migración aditiva y prioridad sobre domicilio en consulta. |
| Ciudadanos | Legajo con Google Maps JS | Coordenadas existentes. Revisar formulario, permisos y representación numérica. |
| Ver para ser libres | Sedes y jornadas Django; formularios y consultas React | Coordenadas existentes. Revisar limpieza automática en SedeCreateVPSLForm.save y resolución de ubicacion_url en JornadaVPSLForm para que no sobreescriban el ajuste manual ni alteren domicilio. Integrar ambos frontends. |
| Inspecciones | Tablero de escuelas | Vista agregada, sin legajo editable de ubicación en el tablero. No habilitar escrituras desde allí; documentar el alcance al cerrar el relevamiento. |

## Primera etapa implementada

Editor compartido en `src/backends/kernel/templates/components/map_pin_editor.html`
y estáticos `src/backends/kernel/static/custom/`, consumido por Dispositivos.
Leaflet 1.9.4 y teselas OpenStreetMap siguen el patrón del mapa general existente.
No agrega paquetes. El formulario autorizado de cada dueño persiste. Dispositivos
expone búsqueda de domicilio en borrador mediante POST protegido por CSRF y
permisos de alta/edición, sin persistir el dispositivo.

Permite arrastre y colocación explícita en el centro para usar controles de zoom
sin arrastrar. Descartar restaura los valores previos al ajuste. Una coincidencia única del domicilio completa coordenadas del formulario,
sin guardarlas en la base hasta confirmar el formulario. Sin ubicación inicial usa
vista de Argentina y requiere movimiento o colocación explícita. Dispositivos resuelve la dirección actual del formulario aunque no esté
guardada, validando catálogo territorial y alcance del usuario. Una respuesta
antigua se descarta si cambió el domicilio o se movió/descartó el pin.

## Límites y cierre

Esta primera etapa no cierra #2778. Falta integrar los demás módulos de la tabla,
validar sus permisos y reglas de guardado, comprobar runtimes aislados y hacer
verificación visual por etapa antes de commits/PRs. El editor compartido del
kernel no importa ni conoce modelos de verticales.

Cambios del kernel requieren revisión técnica y despliegue de sus consumidores
con los estáticos compartidos publicados mediante el migrador habitual.
