# Cambio: primera etapa del pin interactivo (#2778)

## Alcance

Editor reutilizable del kernel integrado al alta y edición de Dispositivos,
sobre el commit local del #2777. Plan e inventario:
`docs/plans/2026-T4/2026-10-26-2778-pin-interactivo.md`.
No cierra el issue transversal ni habilita escrituras en mapas de consulta.

## Comportamiento

- Arrastrar el pin actualiza únicamente latitud y longitud del formulario.
- Colocar en el centro ofrece alternativa al arrastre; el formulario conserva
  los campos numéricos para ingresar coordenadas.
- El guardado conserva las validaciones, permisos y alcance territorial existentes.
- Descartar ajuste recupera los valores anteriores. Cancelar o salir sin guardar
  no envía coordenadas a la base.
- Buscar la dirección actual del formulario, incluso nueva o modificada, solo
  centra el mapa y completa latitud/longitud si hay una coincidencia única. Los
  campos se persisten únicamente al guardar el formulario. La búsqueda usa un POST protegido por
  CSRF y permisos de alta/edición; valida los mismos campos y alcance territorial
  del formulario existente. Previsualizar ubicación también abre este editor.
  Una respuesta tardía no revierte un pin movido o un ajuste descartado.
- Sin coordenadas ni resultado de búsqueda se muestra Argentina, con instrucción
  para acercar y colocar el pin. No se guardan coordenadas por abrir el mapa.
- No modifica calle, altura, localidad, municipio ni provincia al arrastrar.
- Mapa de consulta del legajo sigue mostrando la ubicación guardada.

## Dueños y riesgo

El kernel contiene únicamente template, CSS y JS reutilizables; Dispositivos
configura sus campos y un endpoint de previsualización sin persistencia. Su ruta
se incorpora al registro generado. Sin imports entre verticales, modelos,
migraciones ni paquetes nuevos para esta etapa.
Requiere revisión técnica por recursos compartidos del kernel. Leaflet y
OpenStreetMap siguen el patrón ya usado por el mapa general de Dispositivos.

## Verificación

- Trece tests Node del editor compartido y diecinueve tests existentes de mapas:
  32 pasaron, incluidos arrastre, cancelación, cero, errores de carga y respuestas
  tardías.
- Suite de Dispositivos: 91 tests pasaron, incluidos guardar y volver a consultar
  el pin, conservar domicilio y rechazar coordenadas inválidas sin modificar las
  previas.
- Djlint de ambos templates sin errores; Black aplicado al archivo de tests.
- Verificación visual local confirmada: búsqueda del domicilio completa
  coordenadas, movimiento del pin mantiene el domicilio textual y Descartar
  ajuste recupera los valores anteriores.
- Resto de módulos, CI, publicación, merge y despliegue: pendientes.
