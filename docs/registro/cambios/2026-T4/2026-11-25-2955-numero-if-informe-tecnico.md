# Cambio: Carga del informe técnico GDE (#2955)

## Alcance y comportamiento

El modal React mostraba el número IF como campo controlado, pero descartaba las ediciones. Ahora mantiene el valor ingresado en el estado del modal y lo envía con el adjunto mediante el formulario multipart existente. Las reglas de estado, permisos, formato y archivo obligatorio no cambian.

## Verificación

La regresión de Vitest reproduce la pérdida del texto y verifica que la acción recibe el número nuevo y el campo del archivo. En Chromium, una admisión sintética aceptó escritura y pegado en escritorio y en viewport móvil, y no permitió guardar sin archivo. En escritorio se adjuntó un PDF sintético y se comprobó el número guardado después de la respuesta del servidor.

En escritorio y móvil, abrir una admisión sintética en estado que habilite «Cargar Informe Técnico -GDE» en /comedores/admisiones/tecnicos/editar/<id>. Llegar al campo con Tab, escribir y pegar un IF válido; adjuntar un PDF sintético y guardar. Repetir sin archivo y con número vacío o de más de 255 caracteres: no debe completarse la carga.

La persona solicitante confirmó la prueba visual local. No se verificó en QA ni en producción.
