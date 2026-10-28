# Plan preventivo: adjuntos en HML y producción

Estado: propuesta de prevención; no autoriza cambios en producción.
Objetivo: detectar y corregir la desalineación entre usuario de ejecución, volúmenes y permisos antes de que un despliegue afecte las cargas.

## Evidencia y alcance
- HML presentó PermissionError al guardar adjuntos; el HTTP 400 ocultaba el motivo.
- La corrección inicial solo cubrió dos carpetas. La auditoría posterior encontró 92 de 96 directorios sin escritura para el usuario anterior.
- Contenedores posteriores ejecutaban como root: eso puede ocultar el defecto, no demostrar que el esquema de permisos sea correcto.
- Está preparada una implementación exclusiva HML: identidad de aplicación UID10001:GID1016, aprovisionamiento ACL idempotente con backup y herencia, y selección en el deploy. No está aplicada al servidor.
- Pasaron 29 tests aislados. La verificación independiente inicial y la comparación QA/PRD fueron satisfactorias; la revisión nativa detectó dos bloqueos, se corrigieron con RED/GREEN y la validación dirigida terminó aprobada y cerrada.
- No se inspeccionó producción: no se afirma que esté afectada ni protegida. No copiar automáticamente UID/GID de HML a otro entorno.

## 1. Definir una política por entorno
Estado: preparado para HML; propuesto para producción.

Mantener una identidad de aplicación estable y no-root, con una lista explícita de excepciones para procesos efímeros de administración. Enumerar servicios que escriben, media, logs y estado persistente del scheduler. Verificar mapeos reales de UID/GID y montajes de lectura/escritura; conservar propietarios y acceso efectivo existente. No utilizar chmod777 ni chown recursivo como reparación general.

## 2. Preflight obligatorio antes de interrumpir servicios
Estado: ampliación propuesta; no está completa en el candidato.

Validar configuración efectiva, identidad objetivo, rutas permitidas, montajes, espacio e inodos. Construir y comprobar disponibilidad del aprovisionador antes de detener el servicio anterior. Generar backup privado de ACL/modos/identidad de inodes y comprobar su destino de escritura.

Ejecutar el aprovisionamiento idempotente antes del corte y volver a verificar después de cualquier migrador que pueda crear archivos con otra identidad. El candidato actual construye el aprovisionador antes del corte, pero en el flujo completo aplica ACL después de bajar el stack: mover o agregar el primer pase previo al corte requiere implementación y pruebas adicionales.

Si falla el preflight, abortar manteniendo el servicio anterior; no elevar la aplicación a root para continuar.

## 3. Validar permisos en cada deploy, no reescribirlos ciegamente
Estado: aprovisionamiento preparado; gates completos propuestos.

Aplicar solo diferencias de ACL en rutas autorizadas, con herencia para nuevas carpetas. Una ACL predeterminada ignora la umask: no inferir permisos futuros de grupo/otros a partir de los bits de una carpeta. La política nueva debe evitar ampliar lectura de archivos privados y comprobar también a los consumidores legítimos de esos archivos. No modificar contenido ni conceder derechos efectivos adicionales a otros usuarios al ampliar la máscara. Rechazar symlinks o cambios concurrentes inesperados y conservar evidencia del fallo parcial.

Después, probar creación/escritura/lectura/eliminación con la identidad real o exactamente equivalente a la que arrancará la aplicación: no como root. Incluir el caso en que ese usuario es dueño de una carpeta restrictiva: una entrada ACL nominada para el mismo UID no reemplaza los permisos del dueño. Cubrir todos los destinos requeridos y una carpeta futura heredada, además de lectura/escritura sobre archivos sintéticos existentes. Los temporales deben ser inequívocos, quedar fuera de registros de negocio y retirarse al finalizar.

## 4. Gate posterior al arranque y reversión
Estado: pendiente de implementación y validación HML.

Comprobar UID/GID efectivos de los procesos, health de los servicios y acceso a media/logs/scheduler. Repetir la prueba sintética tras recrear contenedores; health verde solo no demuestra capacidad de adjuntar.

No declarar exitoso el deploy ni promoverlo si falla algún control. Conservar SHA, configuración efectiva, checks y backup de permisos. Probar una reversión acotada de versión/configuración y ACL antes de depender de ella; no restituir metadatos si el inode o los permisos cambiaron después del snapshot. Actualmente existe backup, no rollback automático implementado.

La prueba HTTP de carga necesita datos/cuenta sintéticos autorizados en HML. No adjuntar pruebas a expedientes reales ni crear registros en producción sin autorización específica.

## 5. CI y observabilidad
Estado: propuesto, salvo los tests ya preparados.

Las dos regresiones sobre umask restrictiva y dueño sin escritura ya están cubiertas: RED observado, corrección y suite aislada de 29 tests verdes. Extender además con fallos parciales, concurrencia, backup no escribible, validaciones previas al corte, servicio omitido, identidad root inesperada y ejecución repetida del despliegue. Mantener comparación diferencial de entornos no afectados.

Agregar controles que fallen si un nuevo servicio escritor queda fuera de la política o si un despliegue omite el aprovisionamiento y las pruebas. Alertar por PermissionError, filesystem de solo lectura, falta de espacio y aumento de errores en cargas. Registrar entorno, servicio, SHA y categoría de error; no documentos, payloads, nombres de archivos, cookies ni secretos.

## 6. Promoción segura a producción
Estado: no autorizada; requiere una etapa separada.

1. Cerrar revisión y probar en HML dos ejecuciones consecutivas, recreación y creación de carpetas futuras.
2. Autorizar una inspección de producción de solo lectura, indicando destino e identidad SSH; inventariar usuarios, volúmenes y permisos reales.
3. Adaptar la política a producción, sin asumir que sus identificadores numéricos son iguales a HML.
4. Aprobar la revisión exacta, ventana, backup y reversión. Integrar/publicar el cambio únicamente con autorización; un parche remoto no integrado no demuestra persistencia.
5. Desplegar el mismo artefacto validado, ejecutar controles previos/posteriores y observar errores de cargas. Una canary HTTP de producción requiere autorización y datos de prueba separados.

## Criterio de cierre
- Cada escritor tiene identidad y destinos explícitos, sin fallback a root para aplicaciones.
- El despliegue aborta antes del corte si la política no puede prepararse.
- Dos ejecuciones consecutivas conservan acceso correcto sin ampliar permisos ni modificar documentos.
- Recrear contenedores y crear nuevas carpetas no reintroduce el fallo.
- Gates de permisos, health y prueba sintética impiden marcar éxito cuando alguno falla.
- La reversión está probada y la aceptación HTTP/humana se registra por separado.

Riesgo residual: ningún plan garantiza ausencia absoluta de fallos. Cambios manuales, nuevos destinos, modos explícitos de creación, identidades o montajes pueden invalidar la política; por eso se combina aprovisionamiento, comprobación por deploy y observabilidad.
