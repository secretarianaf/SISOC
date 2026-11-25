# Importaciones de Inspecciones: tres pasos en React (#2785, IN01)

El alta, la revisión y el resultado de importaciones masivas de escuelas y
asignaciones conservan sus URLs canónicas. «Cambiar archivo» y los errores
de carga permanecen visibles dentro del circuito React.

| Paso | URL bajo `/inspecciones/<tipo>/importar/` | Contrato |
| --- | --- | --- |
| Archivo | ruta base | GET del formulario y POST multipart con campo `archivo`. |
| Revisión | `<token>/` | Solo el titular de la subida ve el resumen, sus observaciones y los controles. |
| Resultado | `<token>/confirmar/` | Solo POST; muestra el resultado de ese mismo guardado. |

Las entradas React se habilitan con la activación de Inspecciones y un build
SISOC que incluya el marcador `sisoc-react-inspecciones-importacion`. Si falta
cualquiera, Django mantiene sus respuestas nativas.

El backend ejecuta las vistas originales: permisos, CSRF, análisis, validación,
carga de archivos, guardado y eliminación de la subida temporal no cambian.
La respuesta incluye un JSON escapado derivado del contexto visible de Django;
no proyecta filas normalizadas, archivos, ni datos de otro usuario. La
respuesta es privada y no se almacena en caché. React no hace un segundo POST
para obtener el resultado y no crea una URL ni un almacenamiento de resultados
consultable después. Cancelar y el CSV siguen siendo respuestas Django en sus
URLs originales.

## Verificación

- HTTP en Docker y SQLite con archivos sintéticos de ambos tipos, incluyendo
  carga inválida, sesión, permiso, propietario, CSRF, cancelación, reenvío,
  CSV, build anterior y resultado del POST.
- Vitest para los tres pasos y los paneles de origen. TypeScript y ESLint.
- Pendiente: comprobar el recorrido autenticado de extremo a extremo en el
  candidato integrado (no se pidió prueba en navegador real para este cierre).

## Cierre (2026-11-24)

La ruta `inspecciones-importacion` quedó registrada en el router compartido de
React y cubre carga, revisión (incluido "Cambiar archivo") y resultado para
escuelas y asignaciones. El hook común de pantallas de Inspecciones vuelve a
pedir primero la sesión y después los datos, ambos en paralelo, para no alterar
el orden que esperaban las demás pantallas. Con React desactivado o con un build
sin el marcador, Django sigue respondiendo con sus plantillas nativas.
