# Cambio: validación de auditoría y consolidado JFIF (#2673)

## Alcance

Se implementan los cuatro ajustes
La guía vigente es [Rendiciones mensuales](../../../flujos/rendiciones_mensuales_proyectos.md).
Este cambio reemplaza la posibilidad de guardar solo la validación descrita en
el registro del 14/10/2026.

## Comportamiento

- Auditoría exige marcar Validada y elegir si se genera acta desde el primer
  guardado. Solo ofrece No y Sí; No es el valor inicial si no había decisión.
  Las decisiones vacías o inválidas se rechazan también desde el servicio.
- Guardar cierra la gestión individual, según el patrón de cierre existente.
  Los históricos sin decisión conservan sus datos y pueden completarse.
- El legajo y el detalle de rendición de organizaciones muestran Validación
  según `validada`, y Auditada según `genera_acta_auditoria`.
- El botón de revisión previa dice «Finalizar revisión para Carga».
- La extensión `.jfif` pasa por el conversor de imágenes existente, igual que
  `.jpg` y `.jpeg`, al generar el PDF consolidado. No se agregan dependencias,
  permisos, modelos ni migraciones.

## Implementación y patrón

Se reutilizan `AuditoriaForm`, la revalidación transaccional de `AuditoriaService`
y `_crear_lector_pdf_documento` de `rendicioncuentasmensual/services.py`, dentro
del vertical Comedores. Los indicadores se ajustan en las plantillas de
`gestion_organizaciones`. La propiedad `auditada` refleja exclusivamente
`genera_acta_auditoria is True`; las fechas y etapas no pueden convertir un No
en verdadero. Se conserva la información histórica almacenada.

## Verificación

- 132 tests de auditoría, servicio de rendiciones y actas aprobados. Incluyen
  rechazo de decisiones vacías, conservación del valor Sí, No inicial,
  validación obligatoria y conversión real de JFIF/JPG/JPEG con imagen en el PDF.
- 6 pruebas adicionales del legajo aprobadas: validación y acta independientes
  de la etapa y la carga documental, en listado y detalle.
- Tras unificar la propiedad `auditada`, 86 tests del módulo de auditoría
  aprobados, incluidos 12 casos de Sí/No/sin decisión con fechas y etapas
  históricas. Pylint del modelo aprobado (10/10). `makemigrations --check
  --dry-run` confirmó que no hay cambios de esquema.
- Black de los archivos Python modificados aprobado; Pylint de ambos archivos
  productivos aprobado (10/10). Djlint de las cuatro plantillas revisado;
  ajuste de formato de Auditoría aplicado y verificado.
- Sintaxis JavaScript, rutas documentadas y `git diff --check` aprobados.
- El contenedor local carecía de `django-unfold==0.91.0`; se instaló la versión
  ya declarada en `requirements/base.txt`, sin modificar dependencias del repo.
- Servidor local iniciado; `/health/` responde 200. Verificación visual humana
  pendiente. Sin commit, PR ni despliegue.

## Prueba local con adjunto

A pedido del usuario se creó una organización y proyecto identificados como
DUMMY LOCAL, con una rendición en Auditoría pendiente y el Formulario II JFIF
adjunto validado. La descarga consolidada del archivo real produjo una página
con una imagen. El adjunto y sus datos no se incorporan a Git ni a este registro.
