# Cambio: reordenamiento de preguntas (#2868)

## Alcance

Primera parte de #2868: editor de preguntas dentro de la app existente
`src/backends/sisoc_core/encuestas/`. Se sigue el constructor dinámico
`encuestaPreguntasBuilder.js`, el JSON de preguntas y el servicio de guardado
existentes. No se agregan dependencias, modelos, permisos ni migraciones.

## Comportamiento

- Arrastre desde un ícono junto al número de pregunta. Se usa la tarjeta
  completa como imagen de arrastre, se atenúa su lugar original y se señala
  el destino. El ícono también permite mover con las flechas del teclado.
- Se conserva «Quitar». Por indicación del solicitante se retiran los
  botones inicialmente propuestos «Mover», «Subir», «Bajar» y «Agregar debajo».
  Para intercalar se agrega con «Agregar pregunta» y se arrastra al lugar deseado.
- Por pedido del solicitante, «Quitar» pasa a rojo y tamaño compacto y
  solicita confirmación en un modal Bootstrap, siguiendo el modal de rechazo de
  `src/backends/sisoc_core/encuestas/templates/encuestas/encuesta_revision.html`.
  Cancelar o cerrar conserva el contenido y devuelve el foco;
  se advierte si existen preguntas dependientes. Se persiste al guardar.
- Renumeración sin perder opciones, puntajes, obligatoriedad ni la identidad
  de la pregunta referenciada por una condición.
- Los movimientos que dejan una pregunta antes de su referencia se rechazan,
  sin alterar el contenido, con un mensaje accesible.
- Se evita reinsertar todas las tarjetas al reordenar: se mueve solo la elegida,
  se conserva el scroll y se recupera el foco de teclado sin desplazar la página.
  Se anima el acomodo durante 180 ms, respetando la preferencia de movimiento
  reducido. El mensaje de posición se presenta en un toast de 3 segundos,
  abajo a la derecha, usando Toastr existente; se retira el mensaje fijo.
- Scroll automático continuo al acercar la tarjeta a los bordes superior
  e inferior. Velocidad progresiva, limitada a 18 px cada 16 ms. Se detiene
  al volver al centro, soltar, cancelar o salir de la ventana. Solo se activa
  para preguntas del editor y permite reordenar a varias posiciones de distancia.
- Guardado por el mismo formulario y JSON existentes. No cambia el contrato
  del servidor ni el versionado o aprobación de encuestas.

Guía vigente: `docs/implementaciones/encuestas.md`.

## Verificación

- `node --test src/backends/sisoc_core/encuestas/tests/js/encuestaPreguntasBuilder.test.js`:
  veintiuna pruebas aprobadas (movimientos, inserción, condiciones, serialización,
  imagen de tarjeta completa, indicadores, cancelación, controles del template
  y confirmación de borrado en modal, cancelación, foco, scroll, animación
  y desplazamiento automático continuo, velocidad, limpieza y duración del toast).
- Smoke con Chrome headless y una página de prueba que usa el template de
  tarjeta, CSS y JavaScript reales: el scroll se conserva a 1200 px y cerca
  del pie (2966 px) después de soltar y finalizar la animación. Las tarjetas
  se reordenan en ambos casos. No reemplaza la aceptación manual en SISOC.
- `pytest -q src/backends/sisoc_core/encuestas/tests` dentro del contenedor
  Django local: 289 pruebas aprobadas. Incluye guardar y reabrir la configuración.
- Black y djlint: validación local sobre los archivos modificados.
- CI pendiente. Se agrega el test JavaScript al workflow existente de tests;
  requiere revisión técnica por modificar `.github/workflows/tests.yml`.
- Aceptación visual humana pendiente, antes de commit y PR.

## Integración PWA

El indicador de destino ahora reserva un espacio entre las preguntas y muestra
una tarjeta de 56 px, semitransparente, con borde discontinuo y dos líneas de
esqueleto. Se dibuja con pseudoelementos para no incorporar filas ficticias al
contador ni al JSON guardado. Desaparece al cancelar o finalizar el arrastre.
Verificación en Chrome con el template, CSS y JavaScript reales: espacio de
84 px entre tarjetas, indicador de 56 px y doce preguntas conservadas; también
se verificaron cancelación, orden, scroll al soltar y desplazamiento continuo.
El skeleton usa celeste para distinguirlo del fondo. Se mantiene al pasar por
el hueco abierto y solo cambia al entrar en otra tarjeta: eliminarlo en
`dragleave` producía ciclos de apertura/cierre y saltos de las tarjetas.
Los eventos repetidos sobre el mismo destino no reconstruyen el espacio.
También se permite soltar dentro del hueco, y se retira antes de medir las
posiciones para la animación final. Las veintidós pruebas JavaScript están
aprobadas, incluyendo estabilidad del destino y soltar en el hueco. La prueba
en Chrome confirma orden y conservación del scroll al soltar, además del
desplazamiento automático en ambos sentidos.

La segunda parte está implementada localmente. Dueños, contratos, diseño,
validación y pendientes de aceptación se detallan en
`docs/registro/cambios/2026-T4/2026-11-04-2868-encuestas-pwa.md`.
