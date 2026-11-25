# Cambio: Volver desde el historial de un comedor (#2957)

## Alcance

La cabecera React del historial de instancia no configuraba el destino de «Volver» y heredaba la página de inicio. El historial de comedores ahora da al marco un destino explícito, como otras vistas con enlace de retorno propio.

## Comportamiento

Se conserva el origen al filtrar, paginar, limpiar o abrir un evento, incluso antes de aplicar filtros. El enlace «Ver» incorpora el origen ya validado al retorno al mismo historial, sin perder la consulta existente. Solo se admiten la ficha del mismo comedor, el listado de comedores o la auditoría general; sin un origen admitido, el botón lleva a la ficha. No cambian los permisos ni las API.

## Verificación

Vitest verifica el enlace, el origen de la ficha, el contexto de filtros y página y el destino directo o ante una URL externa. En Chromium, en escritorio y viewport móvil, el recorrido de la ficha sintética por Historial → Ver → Auditoría → Volver regresó a la misma pestaña de la ficha. Un destino externo en la consulta no se usó; el botón siguió apuntando a la ficha.

La persona solicitante confirmó la prueba visual local. No se verificó en QA ni en producción.
