# Cambio: la etiqueta de estado del legajo respeta el estado general en Inactivo / En ejecución

## Alcance

Issue #2835. En el encabezado del legajo del comedor
(`comedor/comedor_detail.html`), la etiqueta verde muestra el subestado
(`estado_proceso`) del último estado registrado. 836 comedores quedaron, desde
la carga inicial del 17/11/2025, con la combinación Inactivo / En ejecución,
que no existe en el catálogo: la etiqueta decía "En ejecución" y Editar
"Inactivo".

Se agrega `Comedor.get_etiqueta_estado_display()` y la etiqueta lo usa.

Rutas: `src/backends/comedores/comedores/models.py`,
`src/backends/comedores/comedores/templates/comedor/comedor_detail.html`.

## Comportamiento

- Si el último estado es Inactivo con subestado "En ejecución", la etiqueta
  muestra "Inactivo", igual que Editar.
- Cualquier otra combinación muestra el subestado como antes; sin estado,
  "Sin proceso" como antes.
- Solo cambia la etiqueta. No se modifican estados registrados, historial,
  el campo "Subestado" de la ficha, ni la carga de expedientes de pago. Como
  la condición es exactamente la de la consulta del issue, solo alcanza a esos
  casos.

## Verificación

- `pytest src/backends/comedores/tests/test_issue_2835_etiqueta_estado.py`:
  5 pasan (la combinación inválida, tres combinaciones válidas, sin estado).
- Tests del legajo y del servicio de comedores: 179 pasan.
